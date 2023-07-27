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


eight_step_generator = count(start=8, step=8)


def observable_gauge_callback(callback_options):

    yield Observation(next(eight_step_generator))


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

    def test_observable_gauge_multiple(self):

        even_generator = count(start=2, step=2)
        odd_generator = count(start=1, step=2)

        def even_callback(callback_options):
            yield Observation(next(even_generator))

        def odd_callback(callback_options):
            yield Observation(next(odd_generator))

        def setUp(self):
            reset_metrics_globals()

        def tearDown(self):
            reset_metrics_globals()

        exporter = ConsoleMetricExporter()

        reader_even = PeriodicExportingMetricReader(
            exporter, export_interval_millis=50
        )
        reader_odd = PeriodicExportingMetricReader(
            exporter, export_interval_millis=100
        )

        provider_even = MeterProvider(metric_readers=[reader_even])
        provider_odd = MeterProvider(metric_readers=[reader_odd])

        meter_even = provider_even.get_meter(
            "meter_even", "0.1.2"
        )
        meter_odd = provider_odd.get_meter(
            "meter_odd", "0.1.2"
        )

        meter_even.create_observable_gauge(
            "even_observable_gauge", [even_callback]
        )
        meter_odd.create_observable_gauge(
            "odd_observable_gauge", [odd_callback]
        )

        sleep(1)

        provider_even.shutdown()
        provider_odd.shutdown()
