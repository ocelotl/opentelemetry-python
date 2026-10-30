# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
OpenTelemetry Zipkin Protobuf Exporter
--------------------------------------

This library allows to export tracing data to `Zipkin <https://zipkin.io/>`_.

Usage
-----

The **OpenTelemetry Zipkin Exporter** allows exporting of `OpenTelemetry`_
traces to `Zipkin`_. This exporter sends traces to the configured Zipkin
collector endpoint using HTTP and supports v2 protobuf.

.. _Zipkin: https://zipkin.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
.. _Specification: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/sdk-environment-variables.md#zipkin-exporter

.. code:: python

    import requests

    from opentelemetry import trace
    from opentelemetry.exporter.zipkin.proto.http import ZipkinExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # create a ZipkinExporter
    zipkin_exporter = ZipkinExporter(
        # optional:
        # endpoint="http://localhost:9411/api/v2/spans",
        # local_node_ipv4="192.168.0.1",
        # local_node_ipv6="2001:db8::c001",
        # local_node_port=31313,
        # max_tag_value_length=256,
        # timeout=5 (in seconds),
        # session=requests.Session()
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

from opentelemetry.exporter.zipkin.node_endpoint import IpInput, NodeEndpoint
from opentelemetry.exporter.zipkin.proto.http.v2 import ProtobufEncoder
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
    """Exports spans to a Zipkin collector as version 2 protobuf over HTTP.

    Each batch is serialized by ``ProtobufEncoder`` and sent as the body of a
    single HTTP POST to the collector. The session used for that POST carries a
    ``Content-Type`` of ``application/x-protobuf``, set when the exporter is
    constructed.

    The three ``local_node_`` arguments together describe the network context of
    the node that produced the spans, which Zipkin records as the local endpoint
    of every span in the batch. The service name of that local endpoint is not
    taken from an argument: it is read from the ``service.name`` resource
    attribute of the first span of each batch, and a batch whose first span
    carries none keeps the name the exporter last resolved. That is the name
    read from the global tracer provider when the exporter was constructed,
    until the first batch supplies one of its own.

    Args:
        endpoint: Full URL of the Zipkin collector endpoint that receives the
            spans. When ``None``, the value of the
            :envvar:`OTEL_EXPORTER_ZIPKIN_ENDPOINT` environment variable is used,
            and when that variable is unset or empty the endpoint falls back to
            ``http://localhost:9411/api/v2/spans``.
        local_node_ipv4: Primary IPv4 address associated with this connection,
            given either as a dotted-quad string or as the integer form of the
            address. ``None`` omits the IPv4 address from the local endpoint. A
            value that does not parse as an IPv4 address raises ``ValueError``.
        local_node_ipv6: Primary IPv6 address associated with this connection,
            given as a string. ``None`` omits the IPv6 address from the local
            endpoint. A value that does not parse as an IPv6 address raises
            ``ValueError``, which includes any integer below 2 ** 32, since
            ``ipaddress.ip_address`` reads those as IPv4 addresses.
        local_node_port: Depending on context, this could be a listen port or the
            client-side of a socket. ``None`` omits the port from the local
            endpoint.
        max_tag_value_length: Maximum length a string value may reach before it
            is truncated. The limit covers both tag values and the string
            attribute values of span events, which are written into the
            annotations of the encoded span. ``None`` disables truncation, which
            is the default for this exporter and differs from the encoder
            default of 128 characters.
        timeout: Maximum number of seconds to wait for each batch export. When
            ``None`` or zero, the value of the
            :envvar:`OTEL_EXPORTER_ZIPKIN_TIMEOUT` environment variable is used,
            and when that is unset the timeout is 10 seconds. A value of that
            variable that is not a decimal integer, an empty one included,
            raises ``ValueError`` out of the constructor.
        session: Connection session used to reach the Zipkin collector endpoint.
            Pass one to control connection pooling, retries or authentication.
            When ``None``, this exporter creates one. Either way the exporter
            takes the session over: it sets ``Content-Type`` on the session
            headers, and :meth:`shutdown` closes the session even when the
            caller supplied it. Do not pass a session the application also uses
            for its own requests.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        local_node_ipv4: IpInput = None,
        local_node_ipv6: IpInput = None,
        local_node_port: int | None = None,
        max_tag_value_length: int | None = None,
        timeout: int | None = None,
        session: requests.Session | None = None,
    ):
        """Build a Zipkin protobuf exporter.

        The parameters are documented on the class.
        """
        self.local_node = NodeEndpoint(local_node_ipv4, local_node_ipv6, local_node_port)

        if endpoint is None:
            endpoint = environ.get(OTEL_EXPORTER_ZIPKIN_ENDPOINT) or DEFAULT_ENDPOINT
        self.endpoint = endpoint

        self.encoder = ProtobufEncoder(max_tag_value_length)

        self.session = session or requests.Session()
        self.session.headers.update({"Content-Type": self.encoder.content_type()})
        self._closed = False
        self.timeout = timeout or int(environ.get(OTEL_EXPORTER_ZIPKIN_TIMEOUT, 10))

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        """Serialize one batch of spans and POST it to the Zipkin collector.

        The ``service.name`` resource attribute of the first span of the batch
        becomes the service name of the local endpoint for every span in it. All
        spans of a batch come from one tracer provider, so they share a resource
        and therefore a service name. A batch whose first span carries no
        ``service.name`` leaves the previously resolved service name in place.

        A collector response whose status code is neither 200 nor 202 is logged
        at error level together with the response body, and counts as a failed
        export. Network and timeout failures are not caught here: they surface
        to the caller as the exception raised by the underlying session.

        Args:
            spans: The batch of ended spans to export. An empty batch is still
                serialized and posted.

        Returns:
            ``SpanExportResult.SUCCESS`` when the collector accepted the batch,
            and ``SpanExportResult.FAILURE`` when it rejected it or when this
            exporter has already been shut down.
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
        """Close the session and refuse any further export.

        Closing the session releases its connection pool, including a session
        that was passed to the constructor rather than created here. Every later
        call to :meth:`export` logs a warning and returns
        ``SpanExportResult.FAILURE``. A second call to this method logs a
        warning and does nothing else, so shutting down twice is safe.
        """
        if self._closed:
            logger.warning("Exporter already shutdown, ignoring call")
            return
        self.session.close()
        self._closed = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Report that there is nothing left to flush.

        This exporter holds no queue of its own: :meth:`export` posts each batch
        before it returns, so by the time this method runs every batch handed to
        the exporter has already been sent. Buffering belongs to the span
        processor in front of the exporter, and the span processors of the SDK
        drain their own queue through :meth:`export` rather than through this
        method, which none of them calls. It exists to satisfy the
        :class:`~opentelemetry.sdk.trace.export.SpanExporter` interface.

        Args:
            timeout_millis: Budget in milliseconds for the flush. Ignored,
                because nothing is waited on.

        Returns:
            ``True`` always.
        """
        return True
