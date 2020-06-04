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

from opentelemetry.sdk.trace import Span as SDKSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from opentelemetry.proto.common.v1.common_pb2 import AttributeKeyValue
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

    @staticmethod
    def _translate_spans(
        sdk_spans: Sequence[SDKSpan]
    ) -> ExportTraceServiceRequest:

        def translate_key_values(key, value):
            key_value = {"key": key}

            if isinstance(value, bool):
                key_value["bool_value"] = value

            elif isinstance(value, str):
                key_value["string_value"] = value

            elif isinstance(value, int):
                key_value["int_value"] = value

            elif isinstance(value, float):
                key_value["double_value"] = value

            else:
                raise Exception(
                    "Invalid type {} of value {}".format(
                        type(value), value
                    )
                )

            return key_value

        sdk_resource_instrumentation_library_spans = {}

        for sdk_span in sdk_spans:

            if sdk_span.resource not in (
                sdk_resource_instrumentation_library_spans.keys()
            ):
                sdk_resource_instrumentation_library_spans[
                    sdk_span.resource
                ] = InstrumentationLibrarySpans()

            collector_span_kwargs = {}

            if sdk_span.status is not None:
                collector_span_kwargs["status"] = Status(
                    code=sdk_span.status.canonical_code.value,
                    message=sdk_span.status.description,
                )

            if sdk_span.parent is not None:
                collector_span_kwargs["parent_span_id"] = (
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

                    try:
                        collector_span_kwargs["attributes"].append(
                            AttributeKeyValue(
                                **translate_key_values(key, value)
                            )
                        )
                    except Exception as error:
                        logger.exception(error)

            if sdk_span.events:
                collector_span_kwargs["events"] = []

                for sdk_span_event in sdk_span.events:

                    collector_span_event = CollectorSpan.Event(
                        name=sdk_span_event.name,
                        time_unix_nano=sdk_span_event.timestamp
                    )

                    for key, value in sdk_span_event.attributes.items():
                        try:
                            collector_span_event.attributes.append(
                                AttributeKeyValue(
                                    **translate_key_values(key, value)
                                )
                            )
                        except Exception as error:
                            logger.exception(error)

                    collector_span_kwargs["events"].append(
                        collector_span_event
                    )

            if sdk_span.links:
                collector_span_kwargs["links"] = []

                for sdk_span_link in sdk_span.links:

                    collector_span_link = CollectorSpan.Link(
                        trace_id=(
                            sdk_span_link.context.trace_id.to_bytes(16, "big")
                        ),
                        span_id=(
                            sdk_span_link.context.span_id.to_bytes(8, "big")
                        )
                    )

                    for key, value in sdk_span_link.attributes.items():
                        try:
                            collector_span_link.attributes.append(
                                AttributeKeyValue(
                                    **translate_key_values(key, value)
                                )
                            )
                        except Exception as error:
                            logger.exception(error)

                    collector_span_kwargs["links"].append(collector_span_link)

            collector_span_kwargs["kind"] = getattr(
                CollectorSpan.SpanKind, sdk_span.kind.name
            )

            sdk_resource_instrumentation_library_spans[
                sdk_span.resource
            ].spans.append(CollectorSpan(**collector_span_kwargs))

        resource_spans = []

        for sdk_resource, instrumentation_library_spans in (
            sdk_resource_instrumentation_library_spans.items()
        ):

            collector_resource = Resource()

            for key, value in sdk_resource.labels.items():

                try:
                    collector_resource.attributes.append(
                        AttributeKeyValue(**translate_key_values(key, value))
                    )
                except Exception as error:
                    logger.exception(error)

            resource_spans.append(
                ResourceSpans(
                    resource=collector_resource,
                    instrumentation_library_spans=[
                        instrumentation_library_spans
                    ]
                )
            )

        return ExportTraceServiceRequest(resource_spans=resource_spans)

    def export(self, sdk_spans: Sequence[SDKSpan]) -> SpanExportResult:

        # expo returns a generator that yields delay values which grow
        # exponentially. Once delay is greater than max_value, the yielded
        # value will remain constant.
        # max_value is set to 900 (900 seconds is 15 minutes) to use the same
        # value as used in the Go implementation.
        for delay in expo(max_value=900):
            try:
                response = self._client.Export(
                    self._translate_spans(sdk_spans)
                )
                response

                return SpanExportResult.SUCCESS

            except RpcError as error:
                raise

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

    def shutdown(self):
        pass
