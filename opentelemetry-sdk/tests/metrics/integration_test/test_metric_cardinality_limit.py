# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal._view_instrument_match import (
    _DEFAULT_CARDINALITY_LIMIT,
    _OVERFLOW_ATTRIBUTES,
)
from opentelemetry.sdk.metrics.export import InMemoryMetricReader


class TestCardinalityLimit(TestCase):
    def _record_distinct_attribute_sets(self, count):
        reader = InMemoryMetricReader()
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
