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

from ipdb import set_trace
import logging
from time import sleep
from typing import Sequence

from backoff import expo
from grpc import StatusCode, insecure_channel, RpcError
from google.rpc.error_details_pb2 import RetryInfo
from google.protobuf.timestamp_pb2 import Timestamp

from opentelemetry.trace import SpanKind
from opentelemetry.sdk.trace import Span as SDKSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.proto.trace.v1.trace_pb2 import Span as CollectorSpan
from opentelemetry.proto.trace.v1.trace_pb2 import Status
from opentelemetry.proto.collector.trace.v1.\
        trace_service_pb2_grpc import TraceServiceStub
from opentelemetry.proto.collector.trace.v1.\
        trace_service_pb2 import ExportTraceServiceRequest

logger = logging.getLogger(__name__)


# pylint: disable=no-member
class OTLPSpanExporter(SpanExporter):
    """OTLP span exporter"""

    def __init__(self, endpoint="localhost:55678"):
        super().__init__()
        self._client = TraceServiceStub(insecure_channel(endpoint))

    def export(self, sdk_spans: Sequence[SDKSpan]) -> SpanExportResult:
        # expo returns a generator that yields delay values which grow
        # exponentially. Once delay is greater than max_value, the yielded
        # value will remain constant.
        # max_value is set to 900 (900 seconds is 15 minutes) to use the same
        # value as used in the Go implementation.
        for delay in expo(max_value=900):
            try:
                for _ in self._client.Export(
                    self._generate_spans_requests(sdk_spans)
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

                    retry_info_bin = dict(error.trailing_metadata()).get(
                        "google.rpc.retryinfo-bin"
                    )
                    if retry_info_bin is not None:
                        retry_info = RetryInfo()
                        retry_info.ParseFromString(retry_info_bin)
                        delay = (
                            retry_info.retry_delay.seconds +
                            retry_info.retry_delay.nanos / 1.0e9
                        )

                    sleep(delay)
                    continue

                if error.code() == StatusCode.OK:
                    return SpanExportResult.SUCESS

                return SpanExportResult.FAILURE

            return SpanExportResult.SUCESS

    def _generate_spans_requests(
        self, sdk_spans: Sequence[SDKSpan]
    ) -> ExportTraceServiceRequest:

        set_trace
        collector_spans = []

        for sdk_span in sdk_spans:
            status = None

            if sdk_span.status is not None:
                status = Status(
                    code=sdk_span.status.canonical_code.value,
                    message=sdk_span.status.description,
                )

            if sdk_span.kind is SpanKind.SERVER:
                collector_span_kind = CollectorSpan.CollectorSpanKind.SERVER

            elif sdk_span.kind is SpanKind.CLIENT:
                collector_span_kind = CollectorSpan.SpanKind.CLIENT

            collector_span_kind = CollectorSpan.SpanKind.SPAN_KIND_UNSPECIFIED

            collector_span = CollectorSpan(
                name=sdk_span.name,
                kind=collector_span_kind,
                trace_id=sdk_span.context.trace_id.to_bytes(16, "big"),
                span_id=sdk_span.context.span_id.to_bytes(8, "big"),
                start_time_unix_nano=proto_timestamp_from_time_ns(
                    sdk_span.start_time),
                end_time_unix_nano=proto_timestamp_from_time_ns(
                    sdk_span.end_time
                ),
                status=status,
            )

            parent_id = 0

            if sdk_span.parent is not None:
                parent_id = sdk_span.parent.span_id

            collector_span.parent_span_id = parent_id.to_bytes(8, "big")

            if sdk_span.context.trace_state is not None:
                for (key, value) in sdk_span.context.trace_state.items():
                    collector_span.tracestate.entries.add(key=key, value=value)

            if sdk_span.attributes:
                for (key, value) in sdk_span.attributes.items():
                    add_proto_attribute_value(
                        collector_span.attributes, key, value
                    )

            if sdk_span.events:
                for event in sdk_span.events:

                    collector_annotation = CollectorSpan.TimeEvent.Annotation(
                        description=event.name
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

            if sdk_span.links:
                for link in sdk_span.links:
                    collector_span_link = collector_span.links.link.add()
                    collector_span_link.trace_id = (
                        link.context.trace_id.to_bytes(16, "big")
                    )
                    collector_span_link.span_id = (
                        link.context.span_id.to_bytes(8, "big")
                    )

                    collector_span_link.type = (
                        CollectorSpan.Link.Type.TYPE_UNSPECIFIED
                    )
                    if sdk_span.parent is not None:
                        if (
                            link.context.span_id == sdk_span.parent.span_id
                            and link.context.trace_id == (
                                sdk_span.parent.trace_id
                            )
                        ):
                            collector_span_link.type = (
                                CollectorSpan.Link.Type.PARENT_LINKED_SPAN
                            )

                    if link.attributes:
                        for (key, value) in link.attributes.items():
                            add_proto_attribute_value(
                                collector_span_link.attributes, key, value
                            )

            collector_spans.append(collector_span)

        service_request = ExportTraceServiceRequest(
            node=self.node, metrics=collector_spans
        )
        return service_request

    def shutdown(self):
        pass


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
