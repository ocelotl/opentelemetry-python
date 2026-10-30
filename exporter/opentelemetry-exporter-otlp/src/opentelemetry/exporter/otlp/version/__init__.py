# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-otlp`` distribution.

``opentelemetry-exporter-otlp`` defines no exporter of its own. Installing it
installs ``opentelemetry-exporter-otlp-proto-grpc`` and
``opentelemetry-exporter-otlp-proto-http``, both pinned to the same version,
which is what this module records. Import an exporter class from one of those
two distributions rather than from here. ``OTLPSpanExporter`` comes from
``trace_exporter``, ``OTLPMetricExporter`` from ``metric_exporter`` and
``OTLPLogExporter`` from ``_log_exporter``, and each of those three modules
exists under both ``opentelemetry.exporter.otlp.proto.grpc`` and
``opentelemetry.exporter.otlp.proto.http``. The package you import from
decides whether telemetry is sent over gRPC or over HTTP.

The entry points this distribution registers under the ``otlp`` name, for the
``opentelemetry_traces_exporter``, ``opentelemetry_metrics_exporter`` and
``opentelemetry_logs_exporter`` groups, all point at the gRPC exporters, so
``OTEL_TRACES_EXPORTER=otlp`` selects gRPC. Depend on the single distribution
you need once that choice is settled, since depending on this one pulls in
both.
"""

__version__ = "1.46.0.dev"
"""The installed version of ``opentelemetry-exporter-otlp``, as a :pep:`440` string."""
