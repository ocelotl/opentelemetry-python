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

This distribution registers an entry point named ``otlp`` in each of the
``opentelemetry_traces_exporter``, ``opentelemetry_metrics_exporter`` and
``opentelemetry_logs_exporter`` groups, all three pointing at the gRPC
exporters. The SDK's environment-variable configuration does not load those
entry points. Reading ``OTEL_TRACES_EXPORTER=otlp``, it first rewrites the
name ``otlp`` to either ``otlp_proto_grpc`` or ``otlp_proto_http`` and then
loads the entry point of that rewritten name, which the gRPC and HTTP
distributions register. The choice comes from
``OTEL_EXPORTER_OTLP_TRACES_PROTOCOL``, or from ``OTEL_EXPORTER_OTLP_PROTOCOL``
when the signal-specific variable is unset or empty: ``http/protobuf`` gives
HTTP, ``grpc`` gives gRPC, and any other non-empty value raises
``RuntimeError``. Both variables unset or empty gives gRPC, so an unfilled
placeholder is read as no setting at all rather than as an error.
``OTEL_METRICS_EXPORTER`` and ``OTEL_LOGS_EXPORTER`` work the same way, against
``OTEL_EXPORTER_OTLP_METRICS_PROTOCOL`` and
``OTEL_EXPORTER_OTLP_LOGS_PROTOCOL``.

Depend on the single distribution you need once that choice is settled, since
depending on this one installs both.
"""

__version__ = "1.46.0.dev"
"""The installed version of ``opentelemetry-exporter-otlp``, as a :pep:`440` string."""
