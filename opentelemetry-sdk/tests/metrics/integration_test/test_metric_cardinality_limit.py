# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal._view_instrument_match import (
    _DEFAULT_CARDINALITY_LIMIT,
    _OVERFLOW_ATTRIBUTES,
)
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.metrics.view import View


class TestCardinalityLimit(TestCase):
    @staticmethod
    def _record_distinct_attribute_sets(count, cardinality_limit=None):
        if cardinality_limit is None:
            reader = InMemoryMetricReader()
        else:
            reader = InMemoryMetricReader(cardinality_limit=cardinality_limit)
        meter_provider = MeterProvider(metric_readers=[reader])
        meter = meter_provider.get_meter("testmeter")
        counter = meter.create_counter("testcounter")

        for index in range(count):
            counter.add(1, {"index": index})

        metrics_data = reader.get_metrics_data()
        return (
            metrics_data.resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points
        )

    def test_no_overflow_below_limit(self):
        # One slot is reserved for the overflow series, so up to
        # ``limit - 1`` distinct attribute sets are aggregated independently
        # without producing an overflow series.
        data_points = self._record_distinct_attribute_sets(
            _DEFAULT_CARDINALITY_LIMIT - 1
        )

        self.assertEqual(len(data_points), _DEFAULT_CARDINALITY_LIMIT - 1)
        self.assertNotIn(
            _OVERFLOW_ATTRIBUTES,
            [dict(data_point.attributes) for data_point in data_points],
        )

    def test_overflow_at_limit(self):
        # At and beyond the limit, the total number of metric points stays
        # capped at the limit and the excess is folded into a single overflow
        # series.
        excess = 500
        data_points = self._record_distinct_attribute_sets(
            _DEFAULT_CARDINALITY_LIMIT + excess
        )

        self.assertEqual(len(data_points), _DEFAULT_CARDINALITY_LIMIT)

        overflow_points = [
            data_point
            for data_point in data_points
            if dict(data_point.attributes) == _OVERFLOW_ATTRIBUTES
        ]
        self.assertEqual(len(overflow_points), 1)

    def test_no_measurement_dropped_during_overflow(self):
        # Every measurement must be reflected in exactly one aggregator, so the
        # summed value across all series (including overflow) equals the total
        # number of measurements recorded.
        total_measurements = _DEFAULT_CARDINALITY_LIMIT + 500
        data_points = self._record_distinct_attribute_sets(total_measurements)

        self.assertEqual(
            sum(data_point.value for data_point in data_points),
            total_measurements,
        )

    def test_reader_cardinality_limit_overflows_at_reader_limit(self):
        # A reader configured with a small cardinality limit overflows at that
        # limit, independently of the base default.
        reader_limit = 10
        data_points = self._record_distinct_attribute_sets(
            reader_limit + 20, cardinality_limit=reader_limit
        )

        self.assertEqual(len(data_points), reader_limit)

        overflow_points = [
            data_point
            for data_point in data_points
            if dict(data_point.attributes) == _OVERFLOW_ATTRIBUTES
        ]
        self.assertEqual(len(overflow_points), 1)

    def test_reader_cardinality_limit_no_overflow_below_reader_limit(self):
        # Below the reader's own limit no overflow series is produced.
        reader_limit = 10
        data_points = self._record_distinct_attribute_sets(
            reader_limit - 1, cardinality_limit=reader_limit
        )

        self.assertEqual(len(data_points), reader_limit - 1)
        self.assertNotIn(
            _OVERFLOW_ATTRIBUTES,
            [dict(data_point.attributes) for data_point in data_points],
        )

    def test_reader_cardinality_limit_unset_falls_back_to_default(self):
        # When the reader does not set a cardinality limit, the base default
        # applies (no regression to the base behavior).
        data_points = self._record_distinct_attribute_sets(
            _DEFAULT_CARDINALITY_LIMIT + 100
        )

        self.assertEqual(len(data_points), _DEFAULT_CARDINALITY_LIMIT)

    def test_reader_cardinality_limit_rejects_non_positive(self):
        for invalid in (0, -1):
            with self.subTest(cardinality_limit=invalid):
                with self.assertRaises(ValueError):
                    InMemoryMetricReader(cardinality_limit=invalid)

    @staticmethod
    def _record_distinct_attribute_sets_with_view(
        count, view_limit=None, reader_limit=None
    ):
        if reader_limit is None:
            reader = InMemoryMetricReader()
        else:
            reader = InMemoryMetricReader(cardinality_limit=reader_limit)
        view = View(
            instrument_name="testcounter",
            aggregation_cardinality_limit=view_limit,
        )
        meter_provider = MeterProvider(
            metric_readers=[reader], views=[view]
        )
        meter = meter_provider.get_meter("testmeter")
        counter = meter.create_counter("testcounter")

        for index in range(count):
            counter.add(1, {"index": index})

        metrics_data = reader.get_metrics_data()
        return (
            metrics_data.resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points
        )

    def test_view_cardinality_limit_overflows_at_view_limit(self):
        # A view configured with a small cardinality limit overflows at that
        # limit, overriding the base default.
        view_limit = 10
        data_points = self._record_distinct_attribute_sets_with_view(
            view_limit + 20, view_limit=view_limit
        )

        self.assertEqual(len(data_points), view_limit)

        overflow_points = [
            data_point
            for data_point in data_points
            if dict(data_point.attributes) == _OVERFLOW_ATTRIBUTES
        ]
        self.assertEqual(len(overflow_points), 1)

    def test_view_cardinality_limit_overrides_larger_reader_limit(self):
        # The view override wins over a larger per-reader default: streams
        # matched by the view overflow at the (smaller) view limit.
        view_limit = 10
        reader_limit = 100
        data_points = self._record_distinct_attribute_sets_with_view(
            view_limit + 20, view_limit=view_limit, reader_limit=reader_limit
        )

        self.assertEqual(len(data_points), view_limit)

    def test_view_cardinality_limit_overrides_unset_reader(self):
        # The view override wins over the base default even when the reader
        # sets no cardinality limit of its own.
        view_limit = 10
        data_points = self._record_distinct_attribute_sets_with_view(
            view_limit + 20, view_limit=view_limit, reader_limit=None
        )

        self.assertEqual(len(data_points), view_limit)

    def test_view_cardinality_limit_unset_falls_back_to_reader(self):
        # An unset view override falls through to the per-reader default.
        reader_limit = 10
        data_points = self._record_distinct_attribute_sets_with_view(
            reader_limit + 20, view_limit=None, reader_limit=reader_limit
        )

        self.assertEqual(len(data_points), reader_limit)

    def test_view_cardinality_limit_unset_falls_back_to_base_default(self):
        # An unset view override with an unset reader falls through to the base
        # default (no regression).
        data_points = self._record_distinct_attribute_sets_with_view(
            _DEFAULT_CARDINALITY_LIMIT + 100,
            view_limit=None,
            reader_limit=None,
        )

        self.assertEqual(len(data_points), _DEFAULT_CARDINALITY_LIMIT)
