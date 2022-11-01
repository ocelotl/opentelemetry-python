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

from abc import ABC, abstractmethod
from bisect import bisect_left
from enum import IntEnum
from logging import getLogger
from math import inf
from threading import Lock
from typing import Generic, List, Optional, Sequence, TypeVar, Tuple, Union

from opentelemetry.metrics import (
    Asynchronous,
    Counter,
    Histogram,
    Instrument,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    Synchronous,
    UpDownCounter,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.exponent_mapping import (
    ExponentMapping,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.logarithm_mapping import (
    LogarithmMapping,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.buckets import (
    Buckets,
)
from opentelemetry.sdk.metrics._internal.point import (
    ExponentialHistogramDataPoint,
)
from opentelemetry.sdk.metrics._internal.point import Buckets as BucketsPoint
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.point import Gauge
from opentelemetry.sdk.metrics._internal.point import (
    Histogram as HistogramPoint,
)
from opentelemetry.sdk.metrics._internal.point import (
    HistogramDataPoint,
    NumberDataPoint,
    Sum,
)
from opentelemetry.util.types import Attributes

_DataPointVarT = TypeVar("_DataPointVarT", NumberDataPoint, HistogramDataPoint)

_logger = getLogger(__name__)


class AggregationTemporality(IntEnum):
    """
    The temporality to use when aggregating data.

    Can be one of the following values:
    """

    UNSPECIFIED = 0
    DELTA = 1
    CUMULATIVE = 2


class _Aggregation(ABC, Generic[_DataPointVarT]):
    def __init__(self, attributes: Attributes):
        self._lock = Lock()
        self._attributes = attributes
        self._previous_point = None

    @abstractmethod
    def aggregate(self, measurement: Measurement) -> None:
        pass

    @abstractmethod
    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        pass


class _DropAggregation(_Aggregation):
    def aggregate(self, measurement: Measurement) -> None:
        pass

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        pass


class _SumAggregation(_Aggregation[Sum]):
    def __init__(
        self,
        attributes: Attributes,
        instrument_is_monotonic: bool,
        instrument_temporality: AggregationTemporality,
        start_time_unix_nano: int,
    ):
        super().__init__(attributes)

        self._start_time_unix_nano = start_time_unix_nano
        self._instrument_temporality = instrument_temporality
        self._instrument_is_monotonic = instrument_is_monotonic

        if self._instrument_temporality is AggregationTemporality.DELTA:
            self._value = 0
        else:
            self._value = None

    def aggregate(self, measurement: Measurement) -> None:
        with self._lock:
            if self._value is None:
                self._value = 0
            self._value = self._value + measurement.value

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[NumberDataPoint]:
        """
        Atomically return a point for the current value of the metric and
        reset the aggregation value.
        """
        if self._instrument_temporality is AggregationTemporality.DELTA:

            with self._lock:
                value = self._value
                start_time_unix_nano = self._start_time_unix_nano

                self._value = 0
                self._start_time_unix_nano = collection_start_nano

        else:

            with self._lock:
                if self._value is None:
                    return None
                value = self._value
                self._value = None
                start_time_unix_nano = self._start_time_unix_nano

        current_point = NumberDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=collection_start_nano,
            value=value,
        )

        if self._previous_point is None or (
            self._instrument_temporality is aggregation_temporality
        ):
            # Output DELTA for a synchronous instrument
            # Output CUMULATIVE for an asynchronous instrument
            self._previous_point = current_point
            return current_point

        if aggregation_temporality is AggregationTemporality.DELTA:
            # Output temporality DELTA for an asynchronous instrument
            value = current_point.value - self._previous_point.value
            output_start_time_unix_nano = self._previous_point.time_unix_nano

        else:
            # Output CUMULATIVE for a synchronous instrument
            value = current_point.value + self._previous_point.value
            output_start_time_unix_nano = (
                self._previous_point.start_time_unix_nano
            )

        current_point = NumberDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=output_start_time_unix_nano,
            time_unix_nano=current_point.time_unix_nano,
            value=value,
        )

        self._previous_point = current_point
        return current_point


class _LastValueAggregation(_Aggregation[Gauge]):
    def __init__(self, attributes: Attributes):
        super().__init__(attributes)
        self._value = None

    def aggregate(self, measurement: Measurement):
        with self._lock:
            self._value = measurement.value

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        """
        Atomically return a point for the current value of the metric.
        """
        with self._lock:
            if self._value is None:
                return None
            value = self._value
            self._value = None

        return NumberDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=0,
            time_unix_nano=collection_start_nano,
            value=value,
        )


class _ExplicitBucketHistogramAggregation(_Aggregation[HistogramPoint]):
    def __init__(
        self,
        attributes: Attributes,
        start_time_unix_nano: int,
        boundaries: Sequence[float] = (
            0.0,
            5.0,
            10.0,
            25.0,
            50.0,
            75.0,
            100.0,
            250.0,
            500.0,
            750.0,
            1000.0,
            2500.0,
            5000.0,
            7500.0,
            10000.0,
        ),
        record_min_max: bool = True,
    ):
        super().__init__(attributes)
        self._boundaries = tuple(boundaries)
        self._bucket_counts = self._get_empty_bucket_counts()
        self._min = inf
        self._max = -inf
        self._sum = 0
        self._record_min_max = record_min_max
        self._start_time_unix_nano = start_time_unix_nano
        # It is assumed that the "natural" aggregation temporality for a
        # Histogram instrument is DELTA, like the "natural" aggregation
        # temporality for a Counter is DELTA and the "natural" aggregation
        # temporality for an ObservableCounter is CUMULATIVE.
        self._instrument_temporality = AggregationTemporality.DELTA

    def _get_empty_bucket_counts(self) -> List[int]:
        return [0] * (len(self._boundaries) + 1)

    def aggregate(self, measurement: Measurement) -> None:

        value = measurement.value

        if self._record_min_max:
            self._min = min(self._min, value)
            self._max = max(self._max, value)

        self._sum += value

        self._bucket_counts[bisect_left(self._boundaries, value)] += 1

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        """
        Atomically return a point for the current value of the metric.
        """
        with self._lock:
            if not any(self._bucket_counts):
                return None

            bucket_counts = self._bucket_counts
            start_time_unix_nano = self._start_time_unix_nano
            sum_ = self._sum
            max_ = self._max
            min_ = self._min

            self._bucket_counts = self._get_empty_bucket_counts()
            self._start_time_unix_nano = collection_start_nano
            self._sum = 0
            self._min = inf
            self._max = -inf

        current_point = HistogramDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=collection_start_nano,
            count=sum(bucket_counts),
            sum=sum_,
            bucket_counts=tuple(bucket_counts),
            explicit_bounds=self._boundaries,
            min=min_,
            max=max_,
        )

        if self._previous_point is None or (
            self._instrument_temporality is aggregation_temporality
        ):
            self._previous_point = current_point
            return current_point

        max_ = current_point.max
        min_ = current_point.min

        if aggregation_temporality is AggregationTemporality.CUMULATIVE:
            start_time_unix_nano = self._previous_point.start_time_unix_nano
            sum_ = current_point.sum + self._previous_point.sum
            # Only update min/max on delta -> cumulative
            max_ = max(current_point.max, self._previous_point.max)
            min_ = min(current_point.min, self._previous_point.min)
            bucket_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.bucket_counts,
                    self._previous_point.bucket_counts,
                )
            ]
        else:
            start_time_unix_nano = self._previous_point.time_unix_nano
            sum_ = current_point.sum - self._previous_point.sum
            bucket_counts = [
                curr_count - prev_count
                for curr_count, prev_count in zip(
                    current_point.bucket_counts,
                    self._previous_point.bucket_counts,
                )
            ]

        current_point = HistogramDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=current_point.time_unix_nano,
            count=sum(bucket_counts),
            sum=sum_,
            bucket_counts=tuple(bucket_counts),
            explicit_bounds=current_point.explicit_bounds,
            min=min_,
            max=max_,
        )
        self._previous_point = current_point
        return current_point


# pylint: disable=protected-access
class _ExponentialBucketHistogramAggregation(_Aggregation[HistogramPoint]):
    # min_max_size is the smallest reasonable configuration, which is small
    # enough to contain the entire normal floating point range at min
    # scale.
    _min_max_size = 2

    # max_max_size is an arbitrary limit meant to limit accidental use of
    # giant histograms.
    _max_max_size = 16384

    def __init__(
        self,
        attributes: Attributes,
        start_time_unix_nano: int,
        # This is the default maximum number of buckets per positive or
        # negative number range.  The value 160 is specified by OpenTelemetry.
        # See the derivation here:
        # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#exponential-bucket-histogram-aggregation)
        max_size: int = 160,
    ):
        super().__init__(attributes)
        # maxSize is the maximum capacity of the positive and negative ranges.
        # it is set by Init(), preserved by Copy and Move.)

        if max_size < self._min_max_size:
            raise Exception("size {max_size} is smaller than {min_max_size}")

        if max_size > self._max_max_size:
            raise Exception("size {max_size} is larter than {max_max_size}")

        self._max_size = max_size

        # _sum is the sum of all calls to aggregate reflected in the
        # aggregator.
        self._sum = 0

        # count is incremented by 1 per call to aggregate.
        self._count = 0

        # zero_count is incremented by 1 when the measured value is exactly 0.
        self._zero_count = 0

        # _min is set when count > 0
        self._min = 0

        # _max is set when count > 0
        self._max = 0

        # _positive holds the positive values
        self._positive = Buckets()

        # _negative holds the negative values by their absolute value
        self._negative = Buckets()

        # _mapping corresponds to the current scale, is shared by both positive
        # and negative ranges.

        self._mapping = LogarithmMapping(LogarithmMapping._max_scale)
        self._instrument_temporality = AggregationTemporality.DELTA
        self._start_time_unix_nano = start_time_unix_nano

    @property
    def _scale(self):
        if self._count == self._zero_count:
            return 0

        return self._mapping.scale

    def aggregate(self, measurement: Measurement) -> None:
        self._update_by_incr(measurement.value, 1)

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        """
        Atomically return a point for the current value of the metric.
        """

        with self._lock:
            if not any(self._negative._backing._counts) and not any(
                self._positive._backing._counts
            ):
                return None

            start_time_unix_nano = self._start_time_unix_nano
            sum_ = self._sum
            max_ = self._max
            min_ = self._min

            self._negative._counts = [0]
            self._positive._counts = [0]
            self._start_time_unix_nano = collection_start_nano
            self._sum = 0
            self._min = inf
            self._max = -inf

        current_point = ExponentialHistogramDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=collection_start_nano,
            count=(
                sum(self._negative._backing._counts)
                + sum(self._positive._backing._counts)
                + self._zero_count
            ),
            sum=sum_,
            scale=self._scale,
            zero_count=self._zero_count,
            positive=BucketsPoint(
                self._positive.offset, self._positive._backing._counts
            ),
            negative=BucketsPoint(
                self._negative.offset, self._negative._counts
            ),
            # FIXME: Find the right value for flags
            flags=0,
            min=min_,
            max=max_,
        )

        if self._previous_point is None or (
            self._instrument_temporality is aggregation_temporality
        ):
            self._previous_point = current_point
            return current_point

        max_ = current_point.max
        min_ = current_point.min

        if aggregation_temporality is AggregationTemporality.CUMULATIVE:
            start_time_unix_nano = self._previous_point.start_time_unix_nano
            sum_ = current_point.sum + self._previous_point.sum
            # Only update min/max on delta -> cumulative
            max_ = max(current_point.max, self._previous_point.max)
            min_ = min(current_point.min, self._previous_point.min)

            negative_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.negative.bucket_counts,
                    self._previous_point.negative.bucket_counts,
                )
            ]
            positive_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.positive.bucket_counts,
                    self._previous_point.positive.bucket_counts,
                )
            ]
        else:
            start_time_unix_nano = self._previous_point.time_unix_nano
            sum_ = current_point.sum - self._previous_point.sum

            negative_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.negative.bucket_counts,
                    self._previous_point.negative.bucket_counts,
                )
            ]
            positive_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.positive.bucket_counts,
                    self._previous_point.positive.bucket_counts,
                )
            ]

        current_point = ExponentialHistogramDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=current_point.time_unix_nano,
            count=(
                sum(negative_counts) + sum(positive_counts) + self._zero_count
            ),
            sum=sum_,
            scale=self._scale,
            zero_count=self._zero_count,
            positive=BucketsPoint(self._positive.offset, positive_counts),
            negative=BucketsPoint(self._negative.offset, negative_counts),
            # FIXME: Find the right value for flags
            flags=0,
            min=min_,
            max=max_,
        )

        self._previous_point = current_point
        return current_point

    def _clear(self) -> None:
        self._positive.clear()
        self._negative.clear()
        self._sum = 0
        self._count = 0
        self._zero_count = 0
        self._min = 0
        self._max = 0
        self._mapping = LogarithmMapping(LogarithmMapping._max_scale)

    def _swap(self, other: "_ExponentialBucketHistogramAggregation") -> None:

        for attribute in [
            "_positive",
            "_negative",
            "_sum",
            "_count",
            "_zero_count",
            "_min",
            "_max",
            "_mapping",
        ]:
            temp = getattr(self, attribute)
            setattr(self, attribute, getattr(other, attribute))
            setattr(other, attribute, temp)

    def _copy_into(
        self, other: "_ExponentialBucketHistogramAggregation"
    ) -> None:
        other._clear()

        for attribute in [
            "_positive",
            "_negative",
            "_sum",
            "_count",
            "_zero_count",
            "_min",
            "_max",
            "_mapping",
        ]:
            setattr(other, attribute, getattr(self, attribute))

    def _update_by_incr(self, number: Union[int, float], incr: int) -> None:

        value = float(number)

        if self._count == 0:
            self._min = number
            self._max = number

        else:
            if number < self._min:
                self._min = number
            if number > self._max:
                self._max = number

        self._count += incr

        if value == 0:
            self._zero_count += incr
            return

        self._sum += number * incr

        if value > 0:
            buckets = self._positive
        else:
            value = -value
            buckets = self._negative

        self._update(buckets, value, incr)

    def _downscale(self, change: int) -> None:
        """
        Subtracts change from the current mapping scale
        """

        if change == 0:
            return

        if change < 0:
            raise Exception(f"Impossible change of scale: {change}")

        new_scale = self._mapping.scale - change

        self._positive.downscale(change)
        self._negative.downscale(change)

        if new_scale <= 0:
            mapping = ExponentMapping(new_scale)
        else:
            mapping = LogarithmMapping(new_scale)

        self._mapping = mapping

    # pylint: disable=no-self-use
    def _change_scale(self, high: int, low: int, size: int) -> int:
        """
        Calculates how much downscaling is needed by shifting the high and low
        values until they are separated by no more than size.
        """

        change = 0

        while high - low >= size:
            high = high >> 1
            low = low >> 1

            change += 1
        return change

    def _update(self, buckets: Buckets, value: float, incr: int) -> None:

        index = self._mapping.map_to_index(value)

        low, high, success = self._increment_index_by(buckets, index, incr)

        if success:
            return

        self._downscale(self._change_scale(high, low, self._max_size))

        index = self._mapping.map_to_index(value)

        _, _, success = self._increment_index_by(buckets, index, incr)

        if not success:
            raise Exception("Downscale logic error")

    def _increment_index_by(
        self, buckets: Buckets, index: int, incr: int
    ) -> tuple:
        """
        Determines if the index lies inside the current range
        [indexStart, indexEnd] and, if not, returns the minimum size (up to
        maxSize) will satisfy the new value.)]

        Returns a tuple: low, high, success
        """

        if incr == 0:
            # Skipping a bunch of work for 0 increment.  This
            # happens when merging sparse data, for example.
            # This also happens UpdateByIncr is used with a 0
            # increment, means it can be safely skipped.

            return 0, 0, True

        if buckets.len() == 0:
            # Go initializes its backing here if it hasn't been done before.
            # I think we don't need to worry about that because the backing
            # has been initialized already.
            buckets._index_start = index
            buckets._index_end = index
            buckets._index_base = index

        elif index < buckets._index_start:
            span = buckets._index_end - index

            if span >= self._max_size:
                # rescaling needed, mapped value to the right

                return index, buckets._index_end, False

            if span >= buckets._backing.size():
                self._grow(buckets, span + 1)

            buckets._index_start = index

        elif index > buckets._index_end:
            span = index - buckets._index_start

            if span >= self._max_size:
                # rescaling needed, mapped value to the right

                return buckets._index_start, index, False

            if span >= buckets._backing.size():

                self._grow(buckets, span + 1)

            buckets._index_end = index

        bucket_index = index - buckets._index_base

        if bucket_index < 0:
            bucket_index += buckets._backing.size()

        buckets.increment_bucket(bucket_index, incr)

        return 0, 0, True

    def _grow(self, buckets: Buckets, needed: int):
        """
        Resizes the backing array by doubling in size up to maxSize.
        this extends the array with a bunch of zeros and copies the
        existing counts to the same position.
        """

        size = buckets._backing.size()
        bias = buckets._index_base - buckets._index_start
        old_positive_limit = size - bias
        new_size = self._power_of_two_rounded_up(needed)
        if new_size > self._max_size:
            new_size = self._max_size

        new_positive_limit = new_size - bias
        buckets._backing.grow_to(
            new_size, old_positive_limit, new_positive_limit
        )

    def _low_high_at_scale(self, buckets: Buckets, scale: int) -> tuple:
        """
        Returns low, high
        """

        if buckets.len() == 0:
            return 0, -1

        shift = self._scale - scale

        return buckets._index_start >> shift, buckets._index_end >> shift

    def _merge_from(self, other: "_ExponentialBucketHistogramAggregation"):

        if self._count == 0:
            self._min = other._min
            self._max = other._max

        elif other._count != 0:
            if other._min < self._min:
                self._min = other._min
            if other._max > self._max:
                self._max = other._max

        self._sum += other._sum
        self._count += other._count
        self._zero_count += other._zero_count

        min_scale = min(self._scale, other._scale)

        low_positive, high_positive = self._combine_low_high(
            *self._low_high_at_scale(self._positive, min_scale),
            *other._low_high_at_scale(other._positive, min_scale),
        )

        low_negative, high_negative = self._combine_low_high(
            *self._low_high_at_scale(self._negative, min_scale),
            *other._low_high_at_scale(other._negative, min_scale),
        )

        min_scale = min(
            min_scale
            - self._change_scale(high_positive, low_positive, self._max_size),
            min_scale
            - self._change_scale(high_negative, low_negative, self._max_size),
        )

        self._downscale(self._scale - min_scale)

        self._merge_buckets(self._positive, other, other._positive, min_scale)
        self._merge_buckets(self._negative, other, other._negative, min_scale)

    def _merge_buckets(
        self,
        mine: Buckets,
        other: "_ExponentialBucketHistogramAggregation",
        theirs: Buckets,
        scale: int,
    ) -> None:

        their_offset = theirs.offset()
        their_change = other._scale - scale

        for index in range(theirs.len()):

            _, _, success = self._increment_index_by(
                mine, (their_offset + index) >> their_change, theirs.at(index)
            )

            if not success:
                raise Exception("Incorrect merge scale")

    @staticmethod
    def _combine_low_high(
        a_low: int, a_high: int, b_low: int, o_high: int
    ) -> Tuple[int, int]:
        """
        Returns the combination of low and high pairs
        """
        if b_low > o_high:
            return a_low, a_high

        if a_low > a_high:
            return b_low, o_high

        return min(a_low, b_low), max(a_high, o_high)

    @staticmethod
    def _power_of_two_rounded_up(number: int) -> int:
        """
        Computes the least power of two that is >= number.
        """

        number = number - 1

        number |= number >> 1
        number |= number >> 2
        number |= number >> 4
        number |= number >> 8
        number |= number >> 16

        number = number + 1

        return number


class Aggregation(ABC):
    """
    Base class for all aggregation types.
    """

    @abstractmethod
    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        """Creates an aggregation"""


class DefaultAggregation(Aggregation):
    """
    The default aggregation to be used in a `View`.

    This aggregation will create an actual aggregation depending on the
    instrument type, as specified next:

    ==================================================== ====================================
    Instrument                                           Aggregation
    ==================================================== ====================================
    `opentelemetry.sdk.metrics.Counter`                  `SumAggregation`
    `opentelemetry.sdk.metrics.UpDownCounter`            `SumAggregation`
    `opentelemetry.sdk.metrics.ObservableCounter`        `SumAggregation`
    `opentelemetry.sdk.metrics.ObservableUpDownCounter`  `SumAggregation`
    `opentelemetry.sdk.metrics.Histogram`                `ExplicitBucketHistogramAggregation`
    `opentelemetry.sdk.metrics.ObservableGauge`          `LastValueAggregation`
    ==================================================== ====================================
    """

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:

        # pylint: disable=too-many-return-statements
        if isinstance(instrument, Counter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=True,
                instrument_temporality=AggregationTemporality.DELTA,
                start_time_unix_nano=start_time_unix_nano,
            )
        if isinstance(instrument, UpDownCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=False,
                instrument_temporality=AggregationTemporality.DELTA,
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=True,
                instrument_temporality=AggregationTemporality.CUMULATIVE,
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableUpDownCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=False,
                instrument_temporality=AggregationTemporality.CUMULATIVE,
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, Histogram):
            # return _ExplicitBucketHistogramAggregation(
            #     attributes, start_time_unix_nano
            # )
            return _ExponentialBucketHistogramAggregation(
                attributes, start_time_unix_nano
            )

        if isinstance(instrument, ObservableGauge):
            return _LastValueAggregation(attributes)

        raise Exception(f"Invalid instrument type {type(instrument)} found")


class ExplicitBucketHistogramAggregation(Aggregation):
    """This aggregation informs the SDK to collect:

    - Count of Measurement values falling within explicit bucket boundaries.
    - Arithmetic sum of Measurement values in population. This SHOULD NOT be collected when used with instruments that record negative measurements, e.g. UpDownCounter or ObservableGauge.
    - Min (optional) Measurement value in population.
    - Max (optional) Measurement value in population.


    Args:
        boundaries: Array of increasing values representing explicit bucket boundary values.
        record_min_max: Whether to record min and max.
    """

    def __init__(
        self,
        boundaries: Sequence[float] = (
            0.0,
            5.0,
            10.0,
            25.0,
            50.0,
            75.0,
            100.0,
            250.0,
            500.0,
            750.0,
            1000.0,
            2500.0,
            5000.0,
            7500.0,
            10000.0,
        ),
        record_min_max: bool = True,
    ) -> None:
        self._boundaries = boundaries
        self._record_min_max = record_min_max

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        return _ExplicitBucketHistogramAggregation(
            attributes,
            start_time_unix_nano,
            self._boundaries,
            self._record_min_max,
        )


class SumAggregation(Aggregation):
    """This aggregation informs the SDK to collect:

    - The arithmetic sum of Measurement values.
    """

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:

        temporality = AggregationTemporality.UNSPECIFIED
        if isinstance(instrument, Synchronous):
            temporality = AggregationTemporality.DELTA
        elif isinstance(instrument, Asynchronous):
            temporality = AggregationTemporality.CUMULATIVE

        return _SumAggregation(
            attributes,
            isinstance(instrument, (Counter, ObservableCounter)),
            temporality,
            start_time_unix_nano,
        )


class LastValueAggregation(Aggregation):
    """
    This aggregation informs the SDK to collect:

    - The last Measurement.
    - The timestamp of the last Measurement.
    """

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        return _LastValueAggregation(attributes)


class DropAggregation(Aggregation):
    """Using this aggregation will make all measurements be ignored."""

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        return _DropAggregation(attributes)
