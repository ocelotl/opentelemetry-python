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
from typing import Sequence

from backoff import expo
from grpc import StatusCode, insecure_channel, RpcError
from google.rpc.error_details_pb2 import RetryInfo
from google.protobuf.timestamp_pb2 import Timestamp

from opentelemetry.sdk.trace import Span as SDKSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from opentelemetry.proto.common.v1.common_pb2 import (
    AttributeKeyValue, InstrumentationLibrary
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.proto.trace.v1.trace_pb2 import Span as CollectorSpan
from opentelemetry.proto.trace.v1.trace_pb2 import (
    Status, ResourceSpans, InstrumentationLibrarySpans
)
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

        ExportTraceServiceRequest(
            resource_spans=ResourceSpans(
                resource=Resource(
                    attributes=[
                        AttributeKeyValue(key="string", int_value=2)
                    ],
                    dropped_attributes_count=8,
                ),
                instrumentation_library_spans=[
                    InstrumentationLibrarySpans(
                        instrumentation_library=InstrumentationLibrary(
                            name="sdf", version="sdf"
                        ),
                        spans=[CollectorSpan()]
                    )
                ]
            )
        )

        collector_spans = []

        for sdk_span in sdk_spans:

            collector_span_kwargs = {}

            if sdk_span.status is not None:
                collector_span_kwargs["status"] = Status(
                    code=sdk_span.status.canonical_code.value,
                    message=sdk_span.status.description,
                )

            if sdk_span.parent is not None:
                collector_span_kwargs["parent_id"] = (
                    sdk_span.parent.span_id.to_bytes(8, "big")
                )

            if sdk_span.context.trace_state is not None:
                collector_span_kwargs["trace_state"] = ",".join(
                    [
                        "{}={}".format(key, value) for key, value in (
                            sdk_span.context.trace_state.items()
                        )
                    ]
                )

            if sdk_span.attributes:
                collector_span_kwargs["attributes"] = []

                for key, value in sdk_span.attributes.items():

                    attribute_key_value_kwargs = {"key": key}

                    if isinstance(value, str):
                        attribute_key_value_kwargs["string_value"] = value

                    elif isinstance(value, int):
                        attribute_key_value_kwargs["int_value"] = value

                    elif isinstance(value, float):
                        attribute_key_value_kwargs["double_value"] = value

                    elif isinstance(value, bool):
                        attribute_key_value_kwargs["bool_value"] = value

                    else:
                        logger.warning(
                            "Unable to set attribute of type {}".format(
                                type(value)
                            )
                        )

                    collector_span_kwargs["attributes"].append(
                        AttributeKeyValue(**attribute_key_value_kwargs)
                    )

            if sdk_span.events:
                collector_span_kwargs["events"] = []

                for sdk_span_event in sdk_span.events:

                    collector_span_event = CollectorSpan.Event(
                        name=sdk_span_event.name,
                        time_unix_nano=sdk_span_event.timestamp
                    )

                    for key, value in sdk_span_event.attributes.items():
                        collector_span_event.attributes.append(
                            AttributeKeyValue(key=key, value=value)
                        )

            if sdk_span.links:
                collector_span_kwargs["links"] = []

                for sdk_span_link in sdk_span.links:

                    collector_span_link = CollectorSpan.Link(
                        trace_id=(
                            sdk_span_link.context.trace_id.to_bytes(16, "big"),
                        ),
                        span_id=(
                            sdk_span_link.context.span_id.to_bytes(8, "big"),
                        )
                    )

                    for key, value in sdk_span_link.attributes.items():
                        collector_span_link.attributes.append(
                            AttributeKeyValue(key=key, value=value)
                        )

            collector_span_kwargs["kind"] = getattr(
                CollectorSpan.SpanKind, sdk_span.kind.name
            )

            collector_spans.append(CollectorSpan(**collector_span_kwargs))

        service_request = ExportTraceServiceRequest(
            resource_spans=collector_spans
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
