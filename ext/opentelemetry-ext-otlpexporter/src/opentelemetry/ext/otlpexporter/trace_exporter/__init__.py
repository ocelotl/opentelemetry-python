# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OTLP Span Exporter"""

import logging
from time import sleep

from google.protobuf.timestamp_pb2 import Timestamp
from backoff import expo
from grpc import StatusCode, insecure_channel, RpcError
from typing import Sequence

from opentelemetry.trace import SpanKind
from opentelemetru.proto.trace.v1.trace.trace_pb2 import Span, Status
from opentelemetry.proto.collector.trace.v1.\
        trace_service_pb2_grpc import TraceServiceStub
from opentelemetry.proto.collector.trace.v1.\
        trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.sdk.trace import Span as SDKSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)


# pylint: disable=no-member
class OTLPSpanExporter(SpanExporter):
    """OTLP span exporter"""

    def __init__(self):
        super().__init__()
        self._client = TraceServiceStub(insecure_channel(self.endpoint))

    def export(
        self, metric_records: Sequence[SDKSpan]
    ) -> SpanExportResult:
        # expo returns a generator that yields delay values which grow
        # exponentially. Once delay is greater than max_value, the yielded
        # value will remain constant.
        # max_value is set to 900 (900 seconds is 15 minutes) to use the same
        # value as used in the Go implementation.
        for delay in expo(max_value=900):
            try:
                for _ in self.client.Export(
                    self.generate_metrics_requests(metric_records)
                ):
                    pass

                return SpanExportResult.SUCESS

            except RpcError as error:

                if error.code() in [
                    StatusCode.CANCELLED,
                    StatusCode.DEADLINE_EXCEEDED,
                    StatusCode.PERMISSION_DENIED,
                    StatusCode.UNAUTHENTICATED,
                    StatusCode.RESOURCE_EXHAUSTED,
                    StatusCode.ABORTED,
                    StatusCode.OUT_OF_RANGE,
                    StatusCode.UNAVAILABLE,
                    StatusCode.DATA_LOSS,
                ]:
                    sleep(delay)
                    continue

                if error.code() == StatusCode.OK:
                    return SpanExportResult.SUCESS

                return SpanExportResult.FAILURE

                # Find out from the error code if another attempt is to be
                # made.
                # Find out if the server has returned a delay, if so, use it to
                # wait instead of exponential backoff.
                return SpanExportResult.FAILURE

            return SpanExportResult.SUCESS

    def generate_spans_requests(
        self, spans: Sequence[SDKSpan]
    ) -> ExportTraceServiceRequest:
        collector_metrics = translate_to_collector(spans)
        service_request = ExportTraceServiceRequest(
            node=self.node, metrics=collector_metrics
        )
        yield service_request

    def shutdown(self):
        pass


# pylint: disable=too-many-branches
def translate_to_collector(spans: Sequence[SDKSpan]):
    collector_spans = []
    for span in spans:
        status = None
        if span.status is not None:
            status = Status(
                code=span.status.canonical_code.value,
                message=span.status.description,
            )

        collector_span = Span(
            name=trace_pb2.TruncatableString(value=span.name),
            kind=get_collector_span_kind(span.kind),
            trace_id=span.context.trace_id.to_bytes(16, "big"),
            span_id=span.context.span_id.to_bytes(8, "big"),
            start_time=proto_timestamp_from_time_ns(span.start_time),
            end_time=proto_timestamp_from_time_ns(span.end_time),
            status=status,
        )

        parent_id = 0
        if span.parent is not None:
            parent_id = span.parent.span_id

        collector_span.parent_span_id = parent_id.to_bytes(8, "big")

        if span.context.trace_state is not None:
            for (key, value) in span.context.trace_state.items():
                collector_span.tracestate.entries.add(key=key, value=value)

        if span.attributes:
            for (key, value) in span.attributes.items():
                add_proto_attribute_value(
                    collector_span.attributes, key, value
                )

        if span.events:
            for event in span.events:

                collector_annotation = Span.TimeEvent.Annotation(
                    description=trace_pb2.TruncatableString(value=event.name)
                )

                if event.attributes:
                    for (key, value) in event.attributes.items():
                        add_proto_attribute_value(
                            collector_annotation.attributes, key, value
                        )

                collector_span.time_events.time_event.add(
                    time=proto_timestamp_from_time_ns(event.timestamp),
                    annotation=collector_annotation,
                )

        if span.links:
            for link in span.links:
                collector_span_link = collector_span.links.link.add()
                collector_span_link.trace_id = link.context.trace_id.to_bytes(
                    16, "big"
                )
                collector_span_link.span_id = link.context.span_id.to_bytes(
                    8, "big"
                )

                collector_span_link.type = (
                    Span.Link.Type.TYPE_UNSPECIFIED
                )
                if span.parent is not None:
                    if (
                        link.context.span_id == span.parent.span_id
                        and link.context.trace_id == span.parent.trace_id
                    ):
                        collector_span_link.type = (
                            Span.Link.Type.PARENT_LINKED_SPAN
                        )

                if link.attributes:
                    for (key, value) in link.attributes.items():
                        add_proto_attribute_value(
                            collector_span_link.attributes, key, value
                        )

        collector_spans.append(collector_span)
    return collector_spans


# pylint: disable=no-member
def get_collector_span_kind(kind: SpanKind):
    if kind is SpanKind.SERVER:
        return Span.SpanKind.SERVER
    if kind is SpanKind.CLIENT:
        return Span.SpanKind.CLIENT
    return Span.SpanKind.SPAN_KIND_UNSPECIFIED


def add_proto_attribute_value(pb_attributes, key, value):
    """Sets string, int, boolean or float value on protobuf
        span, link or annotation attributes.

    Args:
        pb_attributes: protobuf Span's attributes property.
        key: attribute key to set.
        value: attribute value
    """

    if isinstance(value, bool):
        pb_attributes.attribute_map[key].bool_value = value
    elif isinstance(value, int):
        pb_attributes.attribute_map[key].int_value = value
    elif isinstance(value, str):
        pb_attributes.attribute_map[key].string_value.value = value
    elif isinstance(value, float):
        pb_attributes.attribute_map[key].double_value = value
    else:
        pb_attributes.attribute_map[key].string_value.value = str(value)


def proto_timestamp_from_time_ns(time_ns):
    """Converts datetime to protobuf timestamp.

    Args:
        time_ns: Time in nanoseconds

    Returns:
        Returns protobuf timestamp.
    """
    ts = Timestamp()
    if time_ns is not None:
        # pylint: disable=no-member
        ts.FromNanoseconds(time_ns)
    return ts
