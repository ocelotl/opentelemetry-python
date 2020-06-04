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

from ipdb import set_trace
from grpc import server, insecure_channel, StatusCode
from google.rpc.error_details_pb2 import RetryInfo

from google.protobuf.duration_pb2 import Duration
from concurrent.futures import ThreadPoolExecutor

from unittest import TestCase
from unittest.mock import Mock, PropertyMock

from opentelemetry.trace import SpanKind
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
from opentelemetry.sdk.trace import TracerProvider, Span
from opentelemetry.ext.otlpexporter.trace_exporter import OTLPSpanExporter

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
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as CollectorResource
)


class MockTraceErrorServiceServicer(TraceServiceServicer):
    def Export(self, request, context):
        context.set_details("var")
        context.set_code(StatusCode.UNAVAILABLE)

        context.send_initial_metadata(
            (
                ("google.rpc.retryinfo-bin", RetryInfo().SerializeToString()),
                ("retry", ""),
            )
        )
        context.set_trailing_metadata(
            (
                (
                    "google.rpc.retryinfo-bin",
                    RetryInfo(
                        retry_delay=Duration(seconds=1)
                    ).SerializeToString(),
                ),
                ("retry", "true"),
            )
        )

        response = ExportTraceServiceResponse()
        return response


class TestRealServer(TestCase):
    def setUp(self):

        tracer_provider = TracerProvider()
        self.exporter = OTLPSpanExporter()
        tracer_provider.add_span_processor(
            SimpleExportSpanProcessor(self.exporter)
        )
        self.tracer = tracer_provider.get_tracer(__name__)

        self.server = server(ThreadPoolExecutor(max_workers=10))

        add_TraceServiceServicer_to_server(
            MockTraceErrorServiceServicer(), self.server
        )

        self.server.add_insecure_port("[::]:50051")

        self.server.start()

    def tearDown(self):
        self.server.stop(None)

    def test_server(self):
        with insecure_channel("localhost:50051") as channel:
            stub = TraceServiceStub(channel)

            try:
                stub.Export.with_call(
                    ExportTraceServiceRequest(
                        resource_spans=[ResourceSpans()]
                    ),
                    metadata=(("random", "sdf"),)
                )
            except Exception as error:
                set_trace
                error
                True

    def test_otlp_span_exporter(self):

        with self.tracer.start_as_current_span("a"):
            pass
            # with self.tracer.start_as_current_span("b"):
            # with self.tracer.start_as_current_span("c"):
            # pass

        set_trace
        True

    def test_translate_spans(self):

        exporter = OTLPSpanExporter()
        exporter

        event_mock = Mock(
            **{
                "timestamp": 1591240820506462784,
                "attributes": {"a": 1, "b": False}
            }
        )

        type(event_mock).name = PropertyMock(return_value="a")

        span = Span(
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

        expected = ExportTraceServiceRequest(
            resource_spans=[
                ResourceSpans(
                    resource=CollectorResource(),
                    instrumentation_library_spans=[]
                ),
            ]
        )

        actual = exporter._translate_spans([span])

        self.assertEqual(expected, actual)
