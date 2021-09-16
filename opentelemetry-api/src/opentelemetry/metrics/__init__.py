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

# pylint: disable=too-many-ancestors
# type: ignore

# FIXME enhance the documentation of this module
"""
This module provides abstract and concrete (but noop) classes that can be used
to generate metrics.
"""


from abc import ABC, abstractmethod
from logging import getLogger
from os import environ
from threading import Lock
from typing import Optional, cast

from opentelemetry.environment_variables import OTEL_PYTHON_METER_PROVIDER
from opentelemetry.metrics.instrument import (
    Counter,
    DefaultCounter,
    DefaultHistogram,
    DefaultObservableCounter,
    DefaultObservableGauge,
    DefaultObservableUpDownCounter,
    DefaultUpDownCounter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.util._providers import _load_provider

_logger = getLogger(__name__)


class MeterProvider(ABC):
    def __init__(self):
        super().__init__()
        self._lock = Lock()

    @staticmethod
    def _validate_meter_name(name: str) -> bool:
        """Check if a meter name is valid

        Returns: if the name is valid
        """

        if name is None or name == "":
            _logger.warning("Invalid name: %s", name)
            return False
        return True

    @abstractmethod
    def get_meter(
        self,
        name,
        version=None,
        schema_url=None,
    ) -> "Meter":
        pass


class _DefaultMeterProvider(MeterProvider):
    def get_meter(
        self,
        name,
        version=None,
        schema_url=None,
    ) -> "Meter":
        self._validate_meter_name(name)
        return _DefaultMeter(name, version=version, schema_url=schema_url)


class ProxyMeterProvider(MeterProvider):
    def get_meter(
        self,
        name,
        version=None,
        schema_url=None,
    ) -> "Meter":
        with self._lock:
            if _METER_PROVIDER:
                return _METER_PROVIDER.get_meter(
                    name, version=version, schema_url=schema_url
                )
            return ProxyMeter(name, version=version, schema_url=schema_url)


class Meter(ABC):
    def __init__(self, name, version=None, schema_url=None):
        super().__init__()
        self._lock = Lock()
        self._name = name
        self._version = version
        self._schema_url = schema_url
        self._instrument_names = set()
        self._meter_provider = None

    def _secure_instrument_name(self, name):
        """Secure the instrument name on this meter.

        Logs an error if the instrument name has already been used on this meter.

        Returns: whether the instrument name was successfully secured
        """
        name = name.lower()
        with self._lock:
            if name in self._instrument_names:
                _logger.error("Instrument name %s has been used already", name)
                return False
            self._instrument_names.add(name)
        return True

    @abstractmethod
    def create_counter(self, name, unit="", description="") -> Counter:
        pass

    @abstractmethod
    def create_up_down_counter(
        self, name, unit="", description=""
    ) -> UpDownCounter:
        pass

    @abstractmethod
    def create_observable_counter(
        self, name, callback, unit="", description=""
    ) -> ObservableCounter:
        pass

    @abstractmethod
    def create_histogram(self, name, unit="", description="") -> Histogram:
        pass

    @abstractmethod
    def create_observable_gauge(
        self, name, callback, unit="", description=""
    ) -> ObservableGauge:
        pass

    @abstractmethod
    def create_observable_up_down_counter(
        self, name, callback, unit="", description=""
    ) -> ObservableUpDownCounter:
        pass


class ProxyMeter(Meter):
    def __init__(
        self,
        name,
        version=None,
        schema_url=None,
    ):
        super().__init__(name, version=version, schema_url=schema_url)
        self._real_meter: Optional[Meter] = None
        self._noop_meter = _DefaultMeter(
            name, version=version, schema_url=schema_url
        )

    @property
    def _meter(self) -> Meter:
        with self._lock:
            if self._real_meter is not None:
                return self._real_meter

            if _METER_PROVIDER:
                self._real_meter = _METER_PROVIDER.get_meter(
                    self._name,
                    self._version,
                )
                return self._real_meter

        return self._noop_meter

    def create_counter(self, *args, **kwargs) -> Counter:
        return self._meter.create_counter(*args, **kwargs)

    def create_up_down_counter(self, *args, **kwargs) -> UpDownCounter:
        return self._meter.create_up_down_counter(*args, **kwargs)

    def create_observable_counter(self, *args, **kwargs) -> ObservableCounter:
        return self._meter.create_observable_counter(*args, **kwargs)

    def create_histogram(self, *args, **kwargs) -> Histogram:
        return self._meter.create_histogram(*args, **kwargs)

    def create_observable_gauge(self, *args, **kwargs) -> ObservableGauge:
        return self._meter.create_observable_gauge(*args, **kwargs)

    def create_observable_up_down_counter(
        self, *args, **kwargs
    ) -> ObservableUpDownCounter:
        return self._meter.create_observable_up_down_counter(*args, **kwargs)


class _DefaultMeter(Meter):
    def __init__(self, name, version=None, schema_url=None):
        super().__init__(name, version=version, schema_url=schema_url)

    def create_counter(self, name, unit="", description="") -> Counter:
        self._secure_instrument_name(name)
        return DefaultCounter(name, unit=unit, description=description)

    def create_up_down_counter(
        self, name, unit="", description=""
    ) -> UpDownCounter:
        self._secure_instrument_name(name)
        return DefaultUpDownCounter(name, unit=unit, description=description)

    def create_observable_counter(
        self, name, callback, unit="", description=""
    ) -> ObservableCounter:
        self._secure_instrument_name(name)
        return DefaultObservableCounter(
            name,
            callback,
            unit=unit,
            description=description,
        )

    def create_histogram(self, name, unit="", description="") -> Histogram:
        self._secure_instrument_name(name)
        return DefaultHistogram(name, unit=unit, description=description)

    def create_observable_gauge(
        self, name, callback, unit="", description=""
    ) -> ObservableGauge:
        self._secure_instrument_name(name)
        return DefaultObservableGauge(
            name,
            callback,
            unit=unit,
            description=description,
        )

    def create_observable_up_down_counter(
        self, name, callback, unit="", description=""
    ) -> ObservableUpDownCounter:
        self._secure_instrument_name(name)
        return DefaultObservableUpDownCounter(
            name,
            callback,
            unit=unit,
            description=description,
        )


_METER_PROVIDER = None
_PROXY_METER_PROVIDER = None


def get_meter(
    name: str,
    version: str = "",
    meter_provider: Optional[MeterProvider] = None,
) -> "Meter":
    """Returns a `Meter` for use by the given instrumentation library.

    This function is a convenience wrapper for
    opentelemetry.trace.MeterProvider.get_meter.

    If meter_provider is omitted the current configured one is used.
    """
    if meter_provider is None:
        meter_provider = get_meter_provider()
    return meter_provider.get_meter(name, version)


def set_meter_provider(meter_provider: MeterProvider) -> None:
    """Sets the current global :class:`~.MeterProvider` object.

    This can only be done once, a warning will be logged if any furter attempt
    is made.
    """
    global _METER_PROVIDER  # pylint: disable=global-statement

    if _METER_PROVIDER is not None:
        _logger.warning("Overriding of current MeterProvider is not allowed")
        return

    _METER_PROVIDER = meter_provider


def get_meter_provider() -> MeterProvider:
    """Gets the current global :class:`~.MeterProvider` object."""
    # pylint: disable=global-statement
    global _METER_PROVIDER
    global _PROXY_METER_PROVIDER

    if _METER_PROVIDER is None:
        if OTEL_PYTHON_METER_PROVIDER not in environ.keys():
            if _PROXY_METER_PROVIDER is None:
                _PROXY_METER_PROVIDER = ProxyMeterProvider()
            return _PROXY_METER_PROVIDER

        _METER_PROVIDER = cast(
            "MeterProvider",
            _load_provider(OTEL_PYTHON_METER_PROVIDER, "meter_provider"),
        )
    return _METER_PROVIDER
