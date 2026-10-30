# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Protobuf encoding shared by the OTLP exporters.

This package turns SDK telemetry (spans, metrics and log records) into the
protobuf request messages defined by ``opentelemetry-proto``. It performs no
input and output of its own: the gRPC and HTTP OTLP exporters call it and then
send the messages they get back.

The encoders live in ``opentelemetry.exporter.otlp.proto.common.trace_encoder``,
``opentelemetry.exporter.otlp.proto.common.metrics_encoder`` and
``opentelemetry.exporter.otlp.proto.common._log_encoder``. The implementation
sits under the private ``_internal`` subpackage. Those three modules are the
whole surface an outside caller should rely on; the OTLP exporter packages of
this repository additionally import ``_get_resource_data`` and
``OTLPMetricExporterMixin`` out of ``_internal`` directly, so moving a name
within that subpackage breaks them.
"""

from opentelemetry.exporter.otlp.proto.common.version import __version__

__all__ = ["__version__"]
