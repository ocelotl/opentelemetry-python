# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Instrumentor activation from declarative configuration.

This is the part of declarative configuration that runs third party
instrumentors rather than building SDK objects, and it swallows every
failure. An instrumentor that cannot be found, cannot be built, or
raises while instrumenting is logged and skipped, and the instrumentors
after it still run. The only other place that swallows a failure is
``_resource._load_detector``, which skips a resource detector that no
installed distribution registers. A configuration file that names a
package the user forgot to install therefore starts the application with
less instrumentation rather than not at all.

The module name has no leading underscore, unlike every other
implementation module here, but ``configure_instrumentation`` is not
re-exported from ``opentelemetry.configuration`` or from
``opentelemetry.configuration.file`` either, so ``configure_sdk`` is the
only caller inside the package.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from inspect import isclass
from logging import getLogger

from opentelemetry.configuration._common import load_entry_point
from opentelemetry.configuration._conversion import _dict_to_dataclass
from opentelemetry.configuration._exceptions import ConfigurationError
from opentelemetry.configuration.models import ExperimentalInstrumentation

_logger = getLogger(__name__)


def configure_instrumentation(
    configuration: ExperimentalInstrumentation | None,
) -> None:
    """Activate instrumentors listed under ``instrumentation/development.python``.

    For each entry in ``configuration.python`` the matching
    ``opentelemetry_instrumentor`` entry point is loaded.  If the instrumentor
    class exposes a ``configuration`` attribute that is a dataclass type, the
    raw options are validated through ``_dict_to_dataclass`` before being
    forwarded to ``instrument()``.  An ``enabled: false`` value suppresses
    instrumentation without raising.

    If an instrumentor is already active (e.g. ``opentelemetry-instrument``
    ran before the SDK was configured from the file) its ``instrument()`` call
    is skipped to avoid a double-instrumentation warning.

    Absent or unknown entry points are logged as warnings; runtime errors from
    an instrumentor are logged as exceptions.  Neither stops the remaining
    instrumentors from being applied.

    When the instrumentor declares a ``configuration`` dataclass, only the
    fields of that dataclass whose resolved value is not ``None`` are
    forwarded, so an option set explicitly to null is dropped and the
    instrumentor applies its own default. An option the dataclass does not
    declare is not dropped: building the dataclass raises ``TypeError``,
    which is logged as an error, and that instrumentor is skipped entirely
    rather than instrumented with its remaining options.

    Args:
        configuration: The ``instrumentation/development`` section of the
            parsed configuration. ``None``, and a section whose ``python``
            field is absent, both return without doing anything. Each key of
            ``python`` is an entry point name in the
            ``opentelemetry_instrumentor`` group, and each value is the
            option mapping for it.
    """
    if configuration is None or configuration.python is None:
        return

    for name, options in configuration.python.items():
        options = dict(options)
        if not options.pop("enabled", True):
            _logger.debug(
                "Instrumentation '%s' is disabled in declarative config; skipping",
                name,
            )
            continue

        try:
            cls = load_entry_point("opentelemetry_instrumentor", name)
            configuration_cls = getattr(cls, "configuration", None)
            if isclass(configuration_cls) and is_dataclass(configuration_cls):
                configuration_obj = _dict_to_dataclass(options, configuration_cls)
                options = {
                    f.name: value
                    for f in fields(configuration_obj)
                    if (value := getattr(configuration_obj, f.name)) is not None
                }
            instance = cls()
            if getattr(instance, "is_instrumented_by_opentelemetry", False):
                _logger.debug("Skipping '%s': already instrumented", name)
            else:
                instance.instrument(**options)
                _logger.debug("Instrumented '%s' via declarative config", name)
        except ConfigurationError as exc:
            _logger.warning(
                "Skipping instrumentation '%s' in declarative config: %s",
                name,
                exc,
            )
        except Exception:  # pylint: disable=broad-except
            _logger.exception("Failed to instrument '%s' via declarative config", name)
