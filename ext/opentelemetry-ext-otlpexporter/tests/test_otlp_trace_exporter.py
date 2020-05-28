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

from unittest import TestCase

from pytest import fixture

from opentelemetry.proto.collector.trace.v1.\
    trace_service_pb2 import (
        ExportTraceServiceRequest, ExportTraceServiceResponse
    )


@fixture(scope="module")
def grpc_add_to_server():
    from opentelemetry.proto.collector.trace.v1.\
        trace_service_pb2_grpc import add_TraceServiceServicer_to_server

    return add_TraceServiceServicer_to_server


@fixture(scope="module")
def gprc_servicer():
    from servicer

# pylint: disable=no-member
class TestOTLPSpanExporter(TestCase):

    def test_case(self):
        pass
