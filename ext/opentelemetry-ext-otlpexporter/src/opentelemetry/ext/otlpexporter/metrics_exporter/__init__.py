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

from google.protobuf.timestamp_pb2 import Timestamp
from backoff import expo
from grpc import StatusCode, insecure_channel, RpcError
from typing import Sequence

from opentelemetry.proto.collector.metrics.v1.\
        metrics_service_pb2_grpc import MetricsServiceStub
from opentelemetry.proto.collector.metrics.v1.\
        metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    Metric, MetricDescriptor
)
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
        self._client = MetricsServiceStub(insecure_channel(self.endpoint))

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

    def generate_metrics_requests(
        self, metrics: Sequence[MetricRecord]
    ) -> ExportMetricsServiceRequest:
        collector_metrics = translate_to_collector(metrics)
        service_request = ExportMetricsServiceRequest(
            node=self.node, metrics=collector_metrics
        )
        yield service_request

    def shutdown(self):
        pass


# pylint: disable=too-many-branches
def translate_to_collector(
    metric_records: Sequence[MetricRecord],
) -> Sequence[Metric]:
    collector_metrics = []
    for metric_record in metric_records:

        label_values = []
        label_keys = []
        for label_tuple in metric_record.labels:
            label_keys.append(LabelKey(key=label_tuple[0]))
            label_values.append(
                LabelValue(
                    has_value=label_tuple[1] is not None, value=label_tuple[1]
                )
            )

        metric_descriptor = MetricDescriptor(
            name=metric_record.metric.name,
            description=metric_record.metric.description,
            unit=metric_record.metric.unit,
            type=get_collector_metric_type(metric_record.metric),
            label_keys=label_keys,
        )

        timeseries = TimeSeries(
            label_values=label_values,
            points=[get_collector_point(metric_record)],
        )
        collector_metrics.append(
            Metric(
                metric_descriptor=metric_descriptor, timeseries=[timeseries]
            )
        )
    return collector_metrics


# pylint: disable=no-else-return
def get_collector_metric_type(metric: Metric) -> MetricDescriptor:
    if isinstance(metric, Counter):
        if metric.value_type == int:
            return MetricDescriptor.CUMULATIVE_INT64
        elif metric.value_type == float:
            return MetricDescriptor.CUMULATIVE_DOUBLE
    return MetricDescriptor.UNSPECIFIED


def get_collector_point(metric_record: MetricRecord) -> Point:
    # TODO: horrible hack to get original list of keys to then get the bound
    # instrument
    point = Point(
        timestamp=proto_timestamp_from_time_ns(
            metric_record.aggregator.last_update_timestamp
        )
    )
    if metric_record.metric.value_type == int:
        point.int64_value = metric_record.aggregator.checkpoint
    elif metric_record.metric.value_type == float:
        point.double_value = metric_record.aggregator.checkpoint
    else:
        raise TypeError(
            "Unsupported metric type: {}".format(
                metric_record.metric.value_type
            )
        )
    return point


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
