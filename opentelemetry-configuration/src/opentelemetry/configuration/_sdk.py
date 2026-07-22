# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Top-level orchestrator for declarative SDK configuration.

Provides two entry points on the declarative path:

* :func:`create` builds the SDK providers from a parsed
  ``OpenTelemetryConfiguration`` and returns them **without** touching any
  process-global state. It mirrors Java's ``DeclarativeConfiguration.create``.
* :func:`configure_sdk` applies a parsed configuration by delegating to
  :func:`create` and then installing the built providers as the process
  globals (tracer, meter, logger, propagator, ConfigProvider) and running
  instrumentation. This is the "apply this config" entry point.
"""

from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.configuration._config_provider import (
    ConfigProperties,
    ConfigProvider,
    _node_to_mapping,
    set_config_provider,
)
from opentelemetry.configuration._logger_provider import (
    create_logger_provider,
)
from opentelemetry.configuration._meter_provider import (
    create_meter_provider,
)
from opentelemetry.configuration._propagator import create_propagator
from opentelemetry.configuration._resource import create_resource
from opentelemetry.configuration._tracer_provider import (
    create_tracer_provider,
)
from opentelemetry.configuration.instrumentation import (
    configure_instrumentation,
)
from opentelemetry.configuration.models import OpenTelemetryConfiguration
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider

_logger = getLogger(__name__)


@dataclass
class Providers:
    """The SDK objects built from a declarative configuration.

    A provider is ``None`` when its config section was absent (matching the
    spec's "noop default" behavior). The propagator is always built (an empty
    :class:`CompositePropagator` when no propagator section is present).
    ``config_provider`` exposes the instrumentation config as a read view.
    """

    tracer_provider: TracerProvider | None
    meter_provider: MeterProvider | None
    logger_provider: LoggerProvider | None
    propagator: TextMapPropagator
    config_provider: ConfigProvider


def create(config: OpenTelemetryConfiguration) -> Providers:
    """Build SDK providers from a parsed declarative configuration.

    This is a pure builder: it constructs and returns the providers without
    mutating any process-global state (no ``set_tracer_provider``, etc.) and
    without running instrumentation. Use :func:`configure_sdk` to also install
    the result as the process globals.

    Sections absent from the config (``None``) yield a ``None`` provider,
    matching the spec's "noop default" behavior. The instrumentation config
    is always exposed via ``config_provider`` (empty when absent).

    Args:
        config: Parsed ``OpenTelemetryConfiguration`` (typically from
            ``load_config_file``).

    Returns:
        A :class:`Providers` bundle of the built objects.
    """
    resource = create_resource(config.resource)
    return Providers(
        tracer_provider=(
            create_tracer_provider(config.tracer_provider, resource)
            if config.tracer_provider is not None
            else None
        ),
        meter_provider=(
            create_meter_provider(config.meter_provider, resource)
            if config.meter_provider is not None
            else None
        ),
        logger_provider=(
            create_logger_provider(config.logger_provider, resource)
            if config.logger_provider is not None
            else None
        ),
        propagator=create_propagator(config.propagator),
        config_provider=ConfigProvider(
            ConfigProperties(
                _node_to_mapping(config.instrumentation_development)
            )
        ),
    )


def configure_sdk(config: OpenTelemetryConfiguration) -> None:
    """Configure the global SDK from a parsed declarative configuration.

    Delegates to :func:`create` to build the providers, then installs them as
    the process globals: sets the global tracer provider, meter provider,
    logger provider, text map propagator, and :class:`ConfigProvider` from the
    built objects. Sections absent from the config leave the corresponding
    global untouched — matching the spec's "noop default" behavior. Finally
    runs instrumentation from the ``instrumentation`` section.

    Honors the top-level ``disabled`` flag: when true, no globals are set.

    Args:
        config: Parsed ``OpenTelemetryConfiguration`` (typically from
            ``load_config_file``).

    Example:
        >>> from opentelemetry.configuration import (
        ...     load_config_file, configure_sdk,
        ... )
        >>> config = load_config_file("otel-config.yaml")
        >>> configure_sdk(config)
    """
    if config.disabled:
        _logger.warning(
            "Declarative configuration has disabled=true; skipping SDK setup."
        )
        return

    providers = create(config)

    if providers.tracer_provider is not None:
        trace.set_tracer_provider(providers.tracer_provider)
    if providers.meter_provider is not None:
        metrics.set_meter_provider(providers.meter_provider)
    if providers.logger_provider is not None:
        set_logger_provider(providers.logger_provider)
    set_global_textmap(providers.propagator)
    set_config_provider(providers.config_provider)

    configure_instrumentation(config.instrumentation_development)
