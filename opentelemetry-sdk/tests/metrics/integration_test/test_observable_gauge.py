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
from time import sleep
from unittest import TestCase

from opentelemetry.metrics import (
    Observation,
    get_meter_provider,
    set_meter_provider,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.test.globals_test import reset_metrics_globals

network_bytes_generator = count(start=8, step=8)


def observable_gauge_callback(callback_options):

    yield Observation(next(network_bytes_generator))


class TestDelta(TestCase):
    def test_observable_gauge_delta(self):
        def setUp(self):
            reset_metrics_globals()

        def tearDown(self):
            reset_metrics_globals()

        exporter = ConsoleMetricExporter()

        reader = PeriodicExportingMetricReader(
            exporter, export_interval_millis=100
        )

        provider = MeterProvider(metric_readers=[reader])
        set_meter_provider(provider)

        meter = get_meter_provider().get_meter(
            "preferred-aggregation", "0.1.2"
        )

        meter.create_observable_gauge(
            "observable_gauge", [observable_gauge_callback]
        )

        sleep(1)

        provider.shutdown()
