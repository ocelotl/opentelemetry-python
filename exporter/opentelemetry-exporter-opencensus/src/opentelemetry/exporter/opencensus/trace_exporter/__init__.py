# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OpenCensus Span Exporter.

The exporter reads ended spans in the OpenTelemetry model, the one the
application produced through ``opentelemetry.sdk.trace``, and sends them in
the OpenCensus model, the one the OpenCensus Agent and the OpenTelemetry
Collector accept on their OpenCensus receiver port. The two models are not
the same shape, so the translation loses some information. Each place where
it does is named in the docstring of the function responsible.

The wire protocol is the OpenCensus Agent trace service, a bidirectional gRPC
stream, and the generated stubs for it come from ``opencensus.proto``.
"""

import logging
from collections.abc import Sequence

import grpc
from opencensus.proto.agent.trace.v1 import (
    trace_service_pb2,
    trace_service_pb2_grpc,
)
from opencensus.proto.trace.v1 import trace_pb2

import opentelemetry.exporter.opencensus.util as utils
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

DEFAULT_ENDPOINT = "localhost:55678"

logger = logging.getLogger(__name__)


# pylint: disable=no-member
class OpenCensusSpanExporter(SpanExporter):
    """OpenCensus Collector span exporter.

    An instance translates each batch of ended OpenTelemetry spans into
    OpenCensus spans and sends them over the OpenCensus Agent trace service.
    Export is synchronous and blocks until the collector has answered, so the
    exporter belongs behind a ``BatchSpanProcessor`` rather than behind a
    ``SimpleSpanProcessor``.

    The service name the collector is told comes from the ``service.name``
    resource attribute, sampled once when the exporter is constructed and
    replaced on every later batch whose first span carries one. The
    constructor takes it from the resource of the global tracer provider when
    that provider has one, and otherwise builds a fresh ``Resource``, which
    runs the resource detectors and falls back to
    ``unknown_service:<executable>`` when none of them supplies a service
    name. An exporter built before the tracer provider is set therefore
    starts on whatever that detection found and reports the name carried by
    the spans from its first non-empty export onwards.

    The first of those two branches reads the attribute by subscript, so a
    global tracer provider whose resource carries no ``service.name`` makes
    the constructor raise ``KeyError`` rather than leave the name empty. The
    second branch reads it with ``get`` and does not.

    Args:
        endpoint: Host and port of the OpenCensus receiver of the collector,
            written as ``host:port`` with no scheme, since gRPC takes a
            target rather than a URL. Defaults to ``localhost:55678``. The
            value is ignored when ``client`` is given, because no channel is
            opened in that case.
        host_name: Host name to report to the collector as part of the
            process identifier. ``None`` means the host name of the machine
            is read with ``socket.gethostname()``.
        client: An already built ``TraceServiceStub``. ``None`` means the
            exporter opens its own insecure gRPC channel to ``endpoint``,
            with no TLS and no credentials. Passing a stub is how the tests
            avoid a network connection, and it is also the way to reach a
            collector that needs a secured channel.
    """

    def __init__(
        self,
        endpoint=DEFAULT_ENDPOINT,
        host_name=None,
        client=None,
    ):
        """Initialize the exporter.

        The parameters are documented on the class.
        """
        tracer_provider = trace.get_tracer_provider()
        service_name = (
            tracer_provider.resource.attributes[SERVICE_NAME]
            if getattr(tracer_provider, "resource", None)
            else Resource.create().attributes.get(SERVICE_NAME)
        )
        self.endpoint = endpoint
        if client is None:
            self.channel = grpc.insecure_channel(self.endpoint)
            self.client = trace_service_pb2_grpc.TraceServiceStub(channel=self.channel)
        else:
            self.client = client

        self.host_name = host_name
        self.node = utils.get_node(service_name, host_name)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Translate a batch of ended spans and send it to the collector.

        The call blocks until the collector has answered, since the whole
        response stream is consumed before returning. An empty batch still
        reaches the collector, as a request carrying the node and no spans.

        Before sending, the node is rebuilt from the ``service.name``
        attribute on the resource of the first span of the batch, whenever
        that span carries one. Otherwise the node held from before is reused.
        Reading only the first span rests on the assumption that one span
        processor serves one tracer provider, so a batch cannot mix
        resources.

        This exporter logs nothing of its own, and the ``grpc.RpcError`` it
        catches is discarded without being read, so the status code and the
        details that say why the call failed do not outlive the call. An
        exception raised while a span is being translated is reported on the
        ``grpc._channel`` logger instead, because gRPC is the code consuming
        the request stream when the translation runs.

        Args:
            spans: The ended OpenTelemetry spans to export.

        Returns:
            ``SpanExportResult.SUCCESS`` when the whole stream was sent and
            read without a gRPC error, and ``SpanExportResult.FAILURE`` in
            every other case. A failure covers a collector that is
            unreachable, one that rejected the request, one that closed the
            stream early, and an exception raised while translating a span,
            which gRPC fails with status ``UNKNOWN`` and the details
            ``Exception iterating requests!`` rather than letting it reach
            the caller of ``export``. An
            exporter already shut down still exports and still reports
            success, because ``shutdown`` sets no flag to check here.
        """
        # Populate service_name from first span
        # We restrict any SpanProcessor to be only associated with a single
        # TracerProvider, so it is safe to assume that all Spans in a single
        # batch all originate from one TracerProvider (and in turn have all
        # the same service_name)
        if spans:
            service_name = spans[0].resource.attributes.get(SERVICE_NAME)
            if service_name:
                self.node = utils.get_node(service_name, self.host_name)
        try:
            responses = self.client.Export(self.generate_span_requests(spans))

            # Read response
            for _ in responses:
                pass

        except grpc.RpcError:
            return SpanExportResult.FAILURE

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        """Do nothing.

        ``SpanExporter.shutdown`` is itself a no-op and no base class
        requires an override, so this method adds nothing to the one it
        replaces. It releases nothing: the insecure gRPC channel opened by
        the constructor stays open, and no flag is set, so a later call to
        ``export`` still sends spans instead of refusing them. A process that
        has to free the channel has to close it itself.
        """

    def generate_span_requests(self, spans):
        """Produce the request stream that the trace service is called with.

        The OpenCensus Agent trace service takes a stream of requests, so the
        batch is handed to gRPC as this generator rather than as one value.
        The translation therefore runs while gRPC consumes the generator, not
        before the call.

        Args:
            spans: The ended OpenTelemetry spans to translate.

        Yields:
            Exactly one OpenCensus ``ExportTraceServiceRequest``, carrying the
            node of this exporter and every translated span of the batch. The
            batch is never split, so a batch too large for the limit the
            collector puts on a message is rejected whole.
        """
        collector_spans = translate_to_collector(spans)
        service_request = trace_service_pb2.ExportTraceServiceRequest(node=self.node, spans=collector_spans)
        yield service_request

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Report that there is nothing left to send.

        ``export`` sends each batch before it returns and the exporter keeps
        no queue of its own, so there is never anything to flush and the call
        does no work.

        Args:
            timeout_millis: Ignored. The parameter is part of the
                ``SpanExporter`` signature and no waiting happens here.

        Returns:
            ``True``, always.
        """
        return True


# pylint: disable=too-many-branches
def translate_to_collector(spans: Sequence[ReadableSpan]):
    """Translate OpenTelemetry spans into OpenCensus spans.

    One OpenCensus span is produced per OpenTelemetry span, in the order
    given. The identifiers become fixed width big endian byte strings, 16
    bytes for the trace id and 8 for the span id, and the times go through
    ``opentelemetry.exporter.opencensus.util.proto_timestamp_from_time_ns``,
    so a span that has not ended reports the Unix epoch as its end time.

    Information the OpenTelemetry span carries that does not reach the
    collector, whether because OpenCensus has no field for it or because this
    function leaves the field it has unfilled:

    - The status code number is copied across without being mapped. An
      OpenCensus status code is a canonical gRPC code, where 0 means OK and 1
      means CANCELLED, while the OpenTelemetry codes are UNSET 0, OK 1 and
      ERROR 2. An OpenTelemetry OK therefore arrives at the collector as the
      code that means CANCELLED, and an ERROR as the one that means UNKNOWN.
    - Three of the five span kinds have no OpenCensus counterpart. See
      ``opentelemetry.exporter.opencensus.util.get_collector_span_kind``.
    - A span with no parent is given a parent span id of eight zero bytes
      rather than no parent span id at all.
    - A link is typed ``PARENT_LINKED_SPAN`` only when it points at the
      parent of the span that carries it, matching on both the trace id and
      the span id. Every other link is typed ``TYPE_UNSPECIFIED``, since
      nothing in an OpenTelemetry link says that the target is a child.
    - Every event becomes an annotation, with the event name as the
      annotation description. OpenCensus also has message events, and none
      are produced.
    - The instrumentation scope of the span has no OpenCensus field at all
      and is not sent.
    - Every resource attribute other than ``service.name``, which
      ``OpenCensusSpanExporter.export`` reads on its own, is not sent either,
      although OpenCensus has room for it. Both ``Span`` and
      ``ExportTraceServiceRequest`` carry a ``Resource`` message, whose
      ``labels`` field maps string to string, and this exporter fills neither
      of them.
    - The counts of attributes, events and links that the span limits
      dropped are left at zero, so the collector cannot tell a truncated span
      from a complete one. OpenCensus has a counter for each of the three:
      ``Span.Attributes.dropped_attributes_count``,
      ``Span.TimeEvents.dropped_annotations_count`` and
      ``Span.Links.dropped_links_count``.

    Args:
        spans: The ended OpenTelemetry spans to translate.

    Returns:
        A list of OpenCensus ``trace_pb2.Span`` messages.

    Raises:
        AttributeError: If a span carries no span context, which is read
            without a check for ``None``. Reached through
            ``OpenCensusSpanExporter.export`` the exception does not surface
            here, because gRPC is what consumes the generator that calls this
            function and it turns the exception into a failed call.
    """
    collector_spans = []
    for span in spans:
        status = None
        if span.status is not None:
            status = trace_pb2.Status(
                code=span.status.status_code.value,
                message=span.status.description,
            )

        collector_span = trace_pb2.Span(
            name=trace_pb2.TruncatableString(value=span.name),
            kind=utils.get_collector_span_kind(span.kind),
            trace_id=span.context.trace_id.to_bytes(16, "big"),
            span_id=span.context.span_id.to_bytes(8, "big"),
            start_time=utils.proto_timestamp_from_time_ns(span.start_time),
            end_time=utils.proto_timestamp_from_time_ns(span.end_time),
            status=status,
        )

        parent_id = 0
        if span.parent is not None:
            parent_id = span.parent.span_id

        collector_span.parent_span_id = parent_id.to_bytes(8, "big")

        if span.context.trace_state is not None:
            for key, value in span.context.trace_state.items():
                collector_span.tracestate.entries.add(key=key, value=value)

        if span.attributes:
            for key, value in span.attributes.items():
                utils.add_proto_attribute_value(collector_span.attributes, key, value)

        if span.events:
            for event in span.events:
                collector_annotation = trace_pb2.Span.TimeEvent.Annotation(
                    description=trace_pb2.TruncatableString(value=event.name)
                )

                if event.attributes:
                    for key, value in event.attributes.items():
                        utils.add_proto_attribute_value(collector_annotation.attributes, key, value)

                collector_span.time_events.time_event.add(
                    time=utils.proto_timestamp_from_time_ns(event.timestamp),
                    annotation=collector_annotation,
                )

        if span.links:
            for link in span.links:
                collector_span_link = collector_span.links.link.add()
                collector_span_link.trace_id = link.context.trace_id.to_bytes(16, "big")
                collector_span_link.span_id = link.context.span_id.to_bytes(8, "big")

                collector_span_link.type = trace_pb2.Span.Link.Type.TYPE_UNSPECIFIED
                if span.parent is not None:
                    if link.context.span_id == span.parent.span_id and link.context.trace_id == span.parent.trace_id:
                        collector_span_link.type = trace_pb2.Span.Link.Type.PARENT_LINKED_SPAN

                if link.attributes:
                    for key, value in link.attributes.items():
                        utils.add_proto_attribute_value(collector_span_link.attributes, key, value)

        collector_spans.append(collector_span)
    return collector_spans
