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

from grpc import server, insecure_channel, StatusCode
from google.rpc.error_details_pb2 import RetryInfo

from google.protobuf.duration_pb2 import Duration
from concurrent.futures import ThreadPoolExecutor

from unittest import TestCase
from unittest.mock import Mock, PropertyMock, patch

from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.proto.common.v1.common_pb2 import AttributeKeyValue
from opentelemetry.trace import SpanKind
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
from opentelemetry.sdk.trace import TracerProvider, Span
from opentelemetry.ext.otlpexporter.trace_exporter import OTLPSpanExporter
from opentelemetry.proto.trace.v1.trace_pb2 import Span as CollectorSpan

from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.proto.collector.trace.v1.\
    trace_service_pb2 import (
        ExportTraceServiceRequest, ExportTraceServiceResponse
    )

from opentelemetry.proto.collector.trace.v1.\
    trace_service_pb2_grpc import (
        add_TraceServiceServicer_to_server,
        TraceServiceServicer,
        TraceServiceStub
    )
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans, InstrumentationLibrarySpans
)
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as CollectorResource
)


class TraceServiceServicerUNAVAILABLEDelay(TraceServiceServicer):
    def Export(self, request, context):
        context.set_code(StatusCode.UNAVAILABLE)

        context.send_initial_metadata(
            (
                ("google.rpc.retryinfo-bin", RetryInfo().SerializeToString()),
            )
        )
        context.set_trailing_metadata(
            (
                (
                    "google.rpc.retryinfo-bin",
                    RetryInfo(
                        retry_delay=Duration(seconds=4)
                    ).SerializeToString(),
                ),
            )
        )

        return ExportTraceServiceResponse()


class TraceServiceServicerUNAVAILABLE(TraceServiceServicer):
    def Export(self, request, context):
        context.set_code(StatusCode.UNAVAILABLE)

        return ExportTraceServiceResponse()


class TraceServiceServicerSUCCESS(TraceServiceServicer):
    def Export(self, request, context):
        context.set_code(StatusCode.OK)

        return ExportTraceServiceResponse()


class TestRealServer(TestCase):

    def setUp(self):
        tracer_provider = TracerProvider()
        self.exporter = OTLPSpanExporter()
        tracer_provider.add_span_processor(
            SimpleExportSpanProcessor(self.exporter)
        )
        self.tracer = tracer_provider.get_tracer(__name__)

        self.server = server(ThreadPoolExecutor(max_workers=10))

        self.server.add_insecure_port("[::]:55678")

        self.server.start()

        event_mock = Mock(
            **{
                "timestamp": 1591240820506462784,
                "attributes": {"a": 1, "b": False}
            }
        )

        type(event_mock).name = PropertyMock(return_value="a")

        self.span = Span(
            "a",
            Mock(**{"trace_state": {"a": "b", "c": "d"}}),
            resource=SDKResource({"a": 1, "b": False}),
            parent=Mock(**{"span_id": 12345}),
            attributes={"a": 1, "b": True},
            events=[event_mock],
            links=[
                Mock(
                    **{
                        "context.trace_id": 1,
                        "context.span_id": 2,
                        "attributes": {"a": 1, "b": False},
                        "kind": SpanKind.INTERNAL
                    }
                )
            ]
        )

    def tearDown(self):
        self.server.stop(None)

    @patch("opentelemetry.ext.otlpexporter.trace_exporter.expo")
    @patch("opentelemetry.ext.otlpexporter.trace_exporter.sleep")
    def test_unavailable(self, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [1]})

        add_TraceServiceServicer_to_server(
            TraceServiceServicerUNAVAILABLE(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.span]), SpanExportResult.FAILURE
        )
        mock_sleep.assert_called_with(1)

    @patch("opentelemetry.ext.otlpexporter.trace_exporter.expo")
    @patch("opentelemetry.ext.otlpexporter.trace_exporter.sleep")
    def test_unavailable_delay(self, mock_sleep, mock_expo):

        mock_expo.configure_mock(**{"return_value": [1]})

        add_TraceServiceServicer_to_server(
            TraceServiceServicerUNAVAILABLEDelay(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.span]), SpanExportResult.FAILURE
        )
        mock_sleep.assert_called_with(4)

    def test_success(self):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerSUCCESS(), self.server
        )
        self.assertEqual(
            self.exporter.export([self.span]), SpanExportResult.SUCCESS
        )

    def test_translate_spans(self):

        expected = ExportTraceServiceRequest(
            resource_spans=[
                ResourceSpans(
                    resource=CollectorResource(
                        attributes=[
                            AttributeKeyValue(key="a", int_value=1),
                            AttributeKeyValue(key="b", bool_value=False)
                        ]
                    ),
                    instrumentation_library_spans=[
                        InstrumentationLibrarySpans(
                            spans=[
                                CollectorSpan(
                                    trace_state="a=b,c=d",
                                    parent_span_id=(
                                        b"\000\000\000\000\000\00009"
                                    ),
                                    kind=CollectorSpan.SpanKind.INTERNAL,
                                    attributes=[
                                        AttributeKeyValue(
                                            key="a", int_value=1
                                        ),
                                        AttributeKeyValue(
                                            key="b", bool_value=True
                                        )
                                    ],
                                    events=[
                                        CollectorSpan.Event(
                                            name="a",
                                            time_unix_nano=1591240820506462784,
                                            attributes=[
                                                AttributeKeyValue(
                                                    key="a", int_value=1
                                                ),
                                                AttributeKeyValue(
                                                    key="b", int_value=False
                                                ),
                                            ]
                                        )
                                    ],
                                    links=[
                                        CollectorSpan.Link(
                                            trace_id=int.to_bytes(
                                                1, 16, "big"
                                            ),
                                            span_id=int.to_bytes(2, 8, "big"),
                                            attributes=[
                                                AttributeKeyValue(
                                                    key="a", int_value=1
                                                ),
                                                AttributeKeyValue(
                                                    key="b", bool_value=False
                                                )
                                            ]
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
            ]
        )

        self.assertEqual(expected, self.exporter._translate_spans([self.span]))
