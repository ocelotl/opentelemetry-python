# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


"""
This library allows to export tracing data to an OTLP collector.

Usage
-----

The **OTLP Span Exporter** allows to export `OpenTelemetry`_ traces to the
`OTLP`_ collector.

You can configure the exporter with the following environment variables:

- :envvar:`OTEL_EXPORTER_OTLP_TRACES_TIMEOUT`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_PROTOCOL`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_HEADERS`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_COMPRESSION`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE`
- :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT`
- :envvar:`OTEL_EXPORTER_OTLP_PROTOCOL`
- :envvar:`OTEL_EXPORTER_OTLP_HEADERS`
- :envvar:`OTEL_EXPORTER_OTLP_ENDPOINT`
- :envvar:`OTEL_EXPORTER_OTLP_COMPRESSION`
- :envvar:`OTEL_EXPORTER_OTLP_CERTIFICATE`

.. _OTLP: https://github.com/open-telemetry/opentelemetry-collector/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # Resource can be required for some backends, e.g. Jaeger
    # If resource wouldn't be set - traces wouldn't appears in Jaeger
    resource = Resource.create({
        "service.name": "service"
    })

    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = trace.get_tracer(__name__)

    otlp_exporter = OTLPSpanExporter()

    span_processor = BatchSpanProcessor(otlp_exporter)

    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

API
---
"""

import enum

from .version import __version__

_OTLP_HTTP_HEADERS = {
    "Content-Type": "application/x-protobuf",
    "User-Agent": "OTel-OTLP-Exporter-Python/" + __version__,
}


class Compression(enum.Enum):
    """Content encoding applied to the body of an OTLP/HTTP export request.

    The value of each member is what the ``OTEL_EXPORTER_OTLP_COMPRESSION``
    environment variable and its per-signal variants accept for that encoding.
    The OTLP specification names only ``none`` and ``gzip``, and requires a
    receiver to support only those two, so ``Deflate`` is an extension of this
    package that a given collector may reject. An exporter
    constructed with ``Gzip`` or ``Deflate`` compresses every request body. It
    also sends the matching ``Content-Encoding`` header, unless the resolved
    headers already carry a ``Content-Encoding`` key, in which case the body is
    still compressed and the value found there is sent as it stands. An
    exporter constructed with ``NoCompression`` sends the body uncompressed and
    sets no such header.

    Passing a member of this enum to an exporter constructor overrides the
    environment variables. Passing ``None`` instead, which is the default,
    leaves the choice to them.
    """

    NoCompression = "none"
    Deflate = "deflate"
    Gzip = "gzip"
