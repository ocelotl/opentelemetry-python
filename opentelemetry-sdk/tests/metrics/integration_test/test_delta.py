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

from itertools import count
from unittest import TestCase

from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider, ObservableCounter
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
)
from opentelemetry.sdk.metrics.view import SumAggregation


class TestDelta(TestCase):
    def test_observable_counter_delta(self):

        eight_multiple_generator = count(start=8, step=8)

        counter = 0

        def observable_counter_callback(callback_options):
            nonlocal counter
            counter += 1
            yield Observation(next(eight_multiple_generator))

        aggregation = SumAggregation()

        reader = InMemoryMetricReader(
            preferred_aggregation={ObservableCounter: aggregation},
            preferred_temporality={
                ObservableCounter: AggregationTemporality.DELTA
            },
        )

        provider = MeterProvider(metric_readers=[reader])
        meter = provider.get_meter("preferred-aggregation", "0.1.2")

        meter.create_observable_counter(
            "observable_counter", [observable_counter_callback]
        )

        results = []

        for _ in range(10):

            results.append(reader.get_metrics_data())

        self.assertEqual(counter, 10)

        provider.shutdown()

        previous_time_unix_nano = (
            results[0]
            .resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points[0]
            .time_unix_nano
        )

        self.assertEqual(
            (
                results[0]
                .resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
                .value
            ),
            8,
        )

        for metrics_data in results[1:]:

            metric_data = (
                metrics_data.resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
            )

            self.assertEqual(
                previous_time_unix_nano, metric_data.start_time_unix_nano
            )
            previous_time_unix_nano = metric_data.time_unix_nano
            self.assertEqual(metric_data.value, 8)
