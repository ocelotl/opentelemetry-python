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

from opentelemetry.ext.otlpexporter.trace_exporter import OTLPSpanExporter
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans

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


class MockTraceServiceServicer(TraceServiceServicer):
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

        self.server = server(
            ThreadPoolExecutor(max_workers=10),
            options=[("grpc.min_recoisdfnect_backoff_ms", 3)]
        )

        add_TraceServiceServicer_to_server(
            MockTraceServiceServicer(), self.server
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
                from ipdb import set_trace
                set_trace()
                error
                True

    def test_otlp_span_exporter(self):

        exporter = OTLPSpanExporter()
        exporter.export()
