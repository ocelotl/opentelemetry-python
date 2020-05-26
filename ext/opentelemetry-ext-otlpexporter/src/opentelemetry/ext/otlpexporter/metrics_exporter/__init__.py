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

"""OTLP Metrics Exporter."""

import logging
from time import sleep

from backoff import expo
from grpc import StatusCode, insecure_channel, RpcError
from typing import Sequence

from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceService
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import Metric
from opentelemetry.sdk.metrics.export import (
    MetricsExporter,
    MetricRecord,
    MetricsExportResult,
)

logger = logging.getLogger(__name__)


# pylint: disable=no-member
class OTLPMetricsExporter(MetricsExporter):
    """OTLP metrics exporter"""

    def __init__(self):
        super().__init__()
        self._client = TraceService(insecure_channel(self.endpoint))

    def export(
        self, metric_records: Sequence[MetricRecord]
    ) -> MetricsExportResult:
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

                return MetricsExportResult.SUCESS

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
                    return MetricsExportResult.SUCESS

                return MetricsExportResult.FAILURE

                # Find out from the error code if another attempt is to be
                # made.
                # Find out if the server has returned a delay, if so, use it to
                # wait instead of exponential backoff.
                return MetricsExportResult.FAILURE

            return MetricsExportResult.SUCESS

    def shutdown(self):
        pass


def translate_to_collector(
    metric_records: Sequence[MetricRecord],
) -> Sequence[Metric]:
    pass
