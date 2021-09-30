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

# pylint: disable=function-redefined,too-many-ancestors

from opentelemetry.metrics import Meter, MeterProvider
from opentelemetry.metrics.measurement import Measurement
from opentelemetry.sdk.metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.util.types import Attributes


class Measurement(Measurement):
    def __init__(self, value, **attributes: Attributes):
        self._value = value
        self._attributes = attributes
        super().__init__(value, **attributes)

    @property
    def value(self):
        return self._value

    @property
    def attributes(self):
        return self._attributes


class Meter(Meter):
    def __init__(self, name, version=None, schema_url=None):

        super().__init__(name, version=version, schema_url=schema_url)

    def create_counter(self, name, unit=None, description=None) -> Counter:
        # pylint: disable=abstract-class-instantiated
        return Counter(name, unit=unit, description=description)

    def create_up_down_counter(
        self, name, unit=None, description=None
    ) -> UpDownCounter:
        # pylint: disable=abstract-class-instantiated
        return UpDownCounter(name, unit=unit, description=description)

    def create_observable_counter(
        self, name, callback, unit=None, description=None
    ) -> ObservableCounter:
        # pylint: disable=abstract-class-instantiated
        return ObservableCounter(
            name, callback, unit=unit, description=description
        )

    def create_histogram(self, name, unit=None, description=None) -> Histogram:
        # pylint: disable=abstract-class-instantiated
        return Histogram(name, unit=unit, description=description)

    def create_observable_gauge(
        self, name, callback, unit=None, description=None
    ) -> ObservableGauge:
        # pylint: disable=abstract-class-instantiated
        return ObservableGauge(
            name, callback, unit=unit, description=description
        )

    def create_observable_up_down_counter(
        self, name, callback, unit=None, description=None
    ) -> ObservableUpDownCounter:
        # pylint: disable=abstract-class-instantiated
        return ObservableUpDownCounter(
            name, callback, unit=unit, description=description
        )


class MeterProvider(MeterProvider):
    def add_pipeline(self):
        pass

    def configure_views(self):
        pass

    def configure_timint(self):
        pass

    def get_meter(
        self,
        name,
        version=None,
        schema_url=None,
    ) -> Meter:
        return Meter(name, version=version, schema_url=schema_url)
