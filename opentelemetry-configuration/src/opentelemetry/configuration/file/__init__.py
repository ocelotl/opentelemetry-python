# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OpenTelemetry SDK File Configuration.

This module provides support for configuring the OpenTelemetry SDK
using declarative configuration files (YAML or JSON).

It re-exports the loader that reads a file, the per-signal ``create_*``
and ``configure_*`` factories that live in the parent package,
``configure_sdk`` which calls them all, the two exception classes
``ConfigurationError`` and ``MissingDependencyError``, and
``substitute_env_vars`` from the sibling module
``opentelemetry.configuration.file._env_substitution``, so an
application can import all of those from one place.
``configure_instrumentation`` is left out, and is importable only from
``opentelemetry.configuration.instrumentation``.

Example:
    >>> from opentelemetry.configuration.file import load_config_file
    >>> config = load_config_file("otel-config.yaml")
    >>> config.file_format
    '1.0'
"""

from opentelemetry.configuration._exceptions import (
    ConfigurationError,
    MissingDependencyError,
)
from opentelemetry.configuration._logger_provider import (
    configure_logger_provider,
    create_logger_provider,
)
from opentelemetry.configuration._meter_provider import (
    configure_meter_provider,
    create_meter_provider,
)
from opentelemetry.configuration._propagator import (
    configure_propagator,
    create_propagator,
)
from opentelemetry.configuration._resource import create_resource
from opentelemetry.configuration._sdk import configure_sdk
from opentelemetry.configuration._tracer_provider import (
    configure_tracer_provider,
    create_tracer_provider,
)
from opentelemetry.configuration.file._env_substitution import (
    substitute_env_vars,
)
from opentelemetry.configuration.file._loader import load_config_file

__all__ = [
    "ConfigurationError",
    "MissingDependencyError",
    "configure_logger_provider",
    "configure_meter_provider",
    "configure_propagator",
    "configure_sdk",
    "configure_tracer_provider",
    "create_logger_provider",
    "create_meter_provider",
    "create_propagator",
    "create_resource",
    "create_tracer_provider",
    "load_config_file",
    "substitute_env_vars",
]
