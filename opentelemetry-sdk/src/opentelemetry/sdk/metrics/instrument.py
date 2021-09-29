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

from typing import Generator

from opentelemetry.metrics.instrument import (
    Asynchronous,
    Counter,
    Histogram,
    Instrument,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    Synchronous,
    UpDownCounter,
    _Adding,
    _Grouping,
    _Monotonic,
    _NonMonotonic,
)
from opentelemetry.sdk.metrics.aggregator import SumAggregator


class _Instrument(Instrument):
    def __init__(self, name, unit=None, description=None):

        super().__init__(name, unit=unit, description=description)

        aggregator_class = None

        if isinstance(self, _Adding):
            if isinstance(self, Synchronous):
                aggregator_class = SumAggregator

            elif isinstance(self, Asynchronous):
                aggregator_class = None

        elif isinstance(self, Histogram):
            aggregator_class = None

        elif isinstance(self, ObservableGauge):
            aggregator_class = None

        self._aggregator_class = aggregator_class
        self._name = name
        self._unit = unit
        self._description = description

    @property
    def aggregator_class(self):
        return self._aggregator_class

    @property
    def name(self):
        return self._name

    @property
    def unit(self):
        return self._unit

    @property
    def description(self):
        return self._description


class _Synchronous(Synchronous, _Instrument):
    def __init__(self, name, unit=None, description=None):
        super().__init__(name, unit=unit, description=description)


class _Asynchronous(Asynchronous, _Instrument):
    def __init__(self, name, callback, unit=None, description=None):
        super().__init__(
            name,
            callback,
            unit=unit,
            description=description,
        )
        if not isinstance(callback, Generator):
            raise TypeError("callback must be a generator")

        self._callback = callback

    def observe(self):
        # FIXME make this limited by a timeout
        return next(self._callback)


class _Adding(_Adding, _Instrument):
    pass


class _Grouping(_Grouping, _Instrument):
    pass


class _Monotonic(_Monotonic, _Adding):
    pass


class _NonMonotonic(_NonMonotonic, _Adding):
    pass


class Counter(Counter, _Monotonic, _Synchronous):
    def add(self, amount, attributes=None):
        return super().add(amount, attributes=attributes)


class UpDownCounter(UpDownCounter, _NonMonotonic, _Synchronous):
    def add(self, amount, attributes=None):
        return super().add(amount, attributes=attributes)


class ObservableCounter(ObservableCounter, _Monotonic, _Asynchronous):
    pass


class ObservableUpDownCounter(
    ObservableUpDownCounter, _NonMonotonic, _Asynchronous
):
    pass


class Histogram(Histogram, _Grouping, _Synchronous):
    def record(self, amount, attributes=None):
        return super().record(amount, attributes=attributes)


class ObservableGauge(ObservableGauge, _Grouping, _Asynchronous):
    pass
