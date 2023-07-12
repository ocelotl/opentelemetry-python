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

from time import sleep
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
    AggregationTemporality
)
from opentelemetry.sdk.metrics.view import SumAggregation


def test_forrest_issue():

    exporter = ConsoleMetricExporter(
        preferred_aggregation={Counter: SumAggregation()},
        preferred_temporality={Counter: AggregationTemporality.DELTA}
    )

    reader = PeriodicExportingMetricReader(
        exporter, export_interval_millis=15000
    )

    provider = MeterProvider(metric_readers=[reader])
    set_meter_provider(provider)

    meter = get_meter_provider().get_meter("preferred-aggregation", "0.1.2")

    counter = meter.create_counter("my-counter")

    for x in [2, 3, 9]:
        sleep(60)
        counter.add(x)

    counter.add(10.7)

    counter.add(18)

    counter.add(21)
    counter.add(22)
