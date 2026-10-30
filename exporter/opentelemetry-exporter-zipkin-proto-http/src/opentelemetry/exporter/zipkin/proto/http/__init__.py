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
    attribute of the first span of each batch, falling back to the service name
    resolved when the exporter was constructed.

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
            given either as a string or as the integer form of the address.
            ``None`` omits the IPv6 address from the local endpoint. A value that
            does not parse as an IPv6 address raises ``ValueError``.
        local_node_port: Depending on context, this could be a listen port or the
            client-side of a socket. ``None`` omits the port from the local
            endpoint.
        max_tag_value_length: Maximum length a string tag value may reach before
            it is truncated. ``None`` disables truncation, which is the default
            for this exporter and differs from the encoder default of 128
            characters.
        timeout: Maximum number of seconds to wait for each batch export. When
            ``None`` or zero, the value of the
            :envvar:`OTEL_EXPORTER_ZIPKIN_TIMEOUT` environment variable is used,
            and when that is unset the timeout is 10 seconds.
        session: Connection session used to reach the Zipkin collector endpoint.
            Pass one to control connection pooling, retries or authentication.
            When ``None``, this exporter creates its own session and closes it
            on shutdown.
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
        if self._closed:
            logger.warning("Exporter already shutdown, ignoring call")
            return
        self.session.close()
        self._closed = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
