# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
OpenTelemetry Zipkin JSON Exporter
----------------------------------

This library allows to export tracing data to `Zipkin <https://zipkin.io/>`_.

Usage
-----

The **OpenTelemetry Zipkin JSON Exporter** allows exporting of `OpenTelemetry`_
traces to `Zipkin`_. This exporter sends traces to the configured Zipkin
collector endpoint using JSON over HTTP and supports multiple versions (v1, v2).

.. _Zipkin: https://zipkin.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
.. _Specification: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/sdk-environment-variables.md#zipkin-exporter

.. code:: python

    import requests

    from opentelemetry import trace
    from opentelemetry.exporter.zipkin.json import ZipkinExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # create a ZipkinExporter
    zipkin_exporter = ZipkinExporter(
        # version=Protocol.V2
        # optional:
        # endpoint="http://localhost:9411/api/v2/spans",
        # local_node_ipv4="192.168.0.1",
        # local_node_ipv6="2001:db8::c001",
        # local_node_port=31313,
        # max_tag_value_length=256,
        # timeout=5 (in seconds),
        # session=requests.Session(),
    )

    # Create a BatchSpanProcessor and add the exporter to it
    span_processor = BatchSpanProcessor(zipkin_exporter)

    # add to the tracer
    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

The exporter supports the following environment variable for configuration:

- :envvar:`OTEL_EXPORTER_ZIPKIN_ENDPOINT`
- :envvar:`OTEL_EXPORTER_ZIPKIN_TIMEOUT`

API
---
"""

import logging
from collections.abc import Sequence
from os import environ

import requests

from opentelemetry.exporter.zipkin.encoder import Protocol
from opentelemetry.exporter.zipkin.json.v1 import JsonV1Encoder
from opentelemetry.exporter.zipkin.json.v2 import JsonV2Encoder
from opentelemetry.exporter.zipkin.node_endpoint import IpInput, NodeEndpoint
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_ZIPKIN_ENDPOINT,
    OTEL_EXPORTER_ZIPKIN_TIMEOUT,
)
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span

DEFAULT_ENDPOINT = "http://localhost:9411/api/v2/spans"
REQUESTS_SUCCESS_STATUS_CODES = (200, 202)

logger = logging.getLogger(__name__)


class ZipkinExporter(SpanExporter):
    """Span exporter that sends JSON over HTTP to a Zipkin collector.

    Each call to ``export`` encodes the batch it is given and sends it as one
    POST request, which makes export synchronous and blocking. Pair the
    exporter with a ``BatchSpanProcessor`` to keep that work off the thread
    that ends the spans.

    The tuple (local_node_ipv4, local_node_ipv6, local_node_port) is used to
    represent the network context of a node in the service graph.

    Args:
        version: The protocol version to be used.
        endpoint: The endpoint of the Zipkin collector. When ``None``, the
            value of the :envvar:`OTEL_EXPORTER_ZIPKIN_ENDPOINT` environment
            variable is used, falling back to
            ``http://localhost:9411/api/v2/spans``. The endpoint has to match
            the chosen version, since the default path names the v2 API.
        local_node_ipv4: Primary IPv4 address associated with this connection.
        local_node_ipv6: Primary IPv6 address associated with this connection.
        local_node_port: Depending on context, this could be a listen port or the
            client-side of a socket.
        max_tag_value_length: Max length string attribute values can have.
            Under ``Protocol.V2``, ``None`` leaves tag values untruncated.
            Under ``Protocol.V1``, ``None`` makes ``export`` raise
            ``TypeError``, so a length has to be given to use that version.
        timeout: Maximum time the Zipkin exporter will wait for each batch export.
            The default value is 10s. When ``None`` or zero, the value of the
            :envvar:`OTEL_EXPORTER_ZIPKIN_TIMEOUT` environment variable is
            used, falling back to 10 seconds when that variable is unset.
            The variable has to hold a decimal integer, since its value is
            passed to ``int``.
        session: Connection session to the Zipkin collector endpoint. When
            ``None``, the exporter creates its own ``requests.Session`` and
            closes it on shutdown. A session passed in here is closed on
            shutdown too, so do not share one with code that outlives the
            exporter.

    Raises:
        ValueError: If ``local_node_ipv4`` or ``local_node_ipv6`` does not
            parse as an address of the matching family, or if ``timeout`` is
            ``None`` or zero and :envvar:`OTEL_EXPORTER_ZIPKIN_TIMEOUT` is
            set to a value that is not a decimal integer.
        KeyError: If the resource of the globally registered tracer provider
            carries no ``service.name`` attribute, which ``NodeEndpoint``
            reads with a plain subscript.
    """

    def __init__(
        self,
        version: Protocol = Protocol.V2,
        endpoint: str | None = None,
        local_node_ipv4: IpInput = None,
        local_node_ipv6: IpInput = None,
        local_node_port: int | None = None,
        max_tag_value_length: int | None = None,
        timeout: int | None = None,
        session: requests.Session | None = None,
    ):
        """Initialize the exporter.

        The parameters are documented on the class.
        """
        self.local_node = NodeEndpoint(local_node_ipv4, local_node_ipv6, local_node_port)

        if endpoint is None:
            endpoint = environ.get(OTEL_EXPORTER_ZIPKIN_ENDPOINT) or DEFAULT_ENDPOINT
        self.endpoint = endpoint

        if version == Protocol.V1:
            self.encoder = JsonV1Encoder(max_tag_value_length)
        elif version == Protocol.V2:
            self.encoder = JsonV2Encoder(max_tag_value_length)

        self.session = session or requests.Session()
        self.session.headers.update({"Content-Type": self.encoder.content_type()})
        self._closed = False
        self.timeout = timeout or int(environ.get(OTEL_EXPORTER_ZIPKIN_TIMEOUT, 10))

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        """Encode a batch of spans and POST it to the Zipkin collector.

        The call blocks until the collector answers or the timeout expires.
        The service name of the local node is replaced, at the start of every
        non-empty export, with the one on the resource of the first span of
        that batch, whenever that span carries one. Otherwise the value held
        from before is kept, which for the first export is the one sampled
        when the exporter was built. Reading only the first span rests on the
        assumption that a span processor serves a single tracer provider and
        so a batch cannot mix resources.

        Failures are reported through the return value and logged on the
        ``opentelemetry.exporter.zipkin.json`` logger. A transport failure is
        not caught, so the exception raised by ``requests`` propagates to the
        caller, which for a ``BatchSpanProcessor`` means the batch is lost.

        Args:
            spans: The ended spans to export.

        Returns:
            ``SpanExportResult.SUCCESS`` when the collector answered 200 or
            202, and ``SpanExportResult.FAILURE`` for any other status code or
            when the exporter has already been shut down.

        Raises:
            TypeError: If the exporter was built with ``Protocol.V1`` and
                ``max_tag_value_length`` left unset, and the batch holds a
                span that contributes at least one tag, which in practice is
                every span. Give ``max_tag_value_length`` a length to use
                ``Protocol.V1``.
        """
        # After the call to Shutdown subsequent calls to Export are
        # not allowed and should return a Failure result
        if self._closed:
            logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        # Populate service_name from first span
        # We restrict any SpanProcessor to be only associated with a single
        # TracerProvider, so it is safe to assume that all Spans in a single
        # batch all originate from one TracerProvider (and in turn have all
        # the same service.name)
        if spans:
            service_name = spans[0].resource.attributes.get(SERVICE_NAME)
            if service_name:
                self.local_node.service_name = service_name
        result = self.session.post(
            url=self.endpoint,
            data=self.encoder.serialize(spans, self.local_node),
            timeout=self.timeout,
        )

        if result.status_code not in REQUESTS_SUCCESS_STATUS_CODES:
            logger.error(
                "Traces cannot be uploaded; status code: %s, message %s",
                result.status_code,
                result.text,
            )
            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        """Close the HTTP session and refuse any further export.

        Every later call to ``export`` returns
        ``SpanExportResult.FAILURE`` without contacting the collector. Calling
        this a second time does nothing beyond logging a warning on the
        ``opentelemetry.exporter.zipkin.json`` logger.
        """
        if self._closed:
            logger.warning("Exporter already shutdown, ignoring call")
            return
        self.session.close()
        self._closed = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Report that there is nothing buffered to flush.

        The exporter sends each batch during ``export`` and holds no queue of
        its own, so there is no work for this to do.

        Args:
            timeout_millis: Ignored, since the call returns at once. It is
                accepted so that the signature matches ``SpanExporter``.

        Returns:
            Always True.
        """
        return True
