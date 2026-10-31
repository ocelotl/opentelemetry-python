# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
The **OpenCensus Exporter** allows to export traces using OpenCensus.

Spans are produced by the application in the OpenTelemetry model and sent in
the OpenCensus model, over the gRPC trace service that the OpenCensus Agent
and the OpenCensus receiver of the OpenTelemetry Collector both listen on.
The exporter is for sending OpenTelemetry spans to a collector that only
speaks OpenCensus. Instrumenting an application written against the
OpenCensus API is a different job, done by ``opentelemetry-opencensus-shim``.

``opentelemetry.exporter.opencensus.trace_exporter`` holds
``OpenCensusSpanExporter``, the only name an application uses, and
``opentelemetry.exporter.opencensus.util`` holds the value conversions it
calls. The two models do not line up field for field, and each docstring in
those two modules names what its own conversion drops.

An application need not import the class at all. The distribution registers
it under the entry point group ``opentelemetry_traces_exporter`` with the
name ``opencensus``, so setting ``OTEL_TRACES_EXPORTER=opencensus`` makes
``opentelemetry.sdk._configuration`` build one with no arguments.

The receiver endpoint defaults to ``localhost:55678`` and the channel opened
to it is insecure, so a collector reached over an untrusted network needs a
``TraceServiceStub`` built elsewhere and passed to the exporter.
"""
