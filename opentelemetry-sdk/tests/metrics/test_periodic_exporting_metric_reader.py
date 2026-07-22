# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access,invalid-name,no-self-use

import gc
import math
import weakref
from logging import WARNING
from time import sleep, time_ns
from typing import cast
from unittest.mock import Mock, patch

import pytest

from opentelemetry.sdk.environment_variables import (
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.metrics import (
    Counter,
    MeterProvider,
    MetricsTimeoutError,
)
from opentelemetry.sdk.metrics._internal import _Counter
from opentelemetry.sdk.metrics._internal.export import _batch_metrics_data
from opentelemetry.sdk.metrics._internal.point import (
    HistogramDataPoint,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge,
    Metric,
    MetricExporter,
    MetricExportResult,
    NumberDataPoint,
    PeriodicExportingMetricReader,
    Sum,
)
from opentelemetry.sdk.metrics.view import (
    DefaultAggregation,
    LastValueAggregation,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.test.concurrency_test import ConcurrencyTestBase


class FakeMetricsExporter(MetricExporter):
    def __init__(
        self, wait=0, preferred_temporality=None, preferred_aggregation=None
    ):
        self.wait = wait
        self.metrics: list[MetricsData] = []
        self._shutdown = False
        super().__init__(
            preferred_temporality=preferred_temporality,
            preferred_aggregation=preferred_aggregation,
        )

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        sleep(self.wait)
        self.metrics.append(metrics_data)
        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._shutdown = True

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True


class ExceptionAtCollectionPeriodicExportingMetricReader(
    PeriodicExportingMetricReader
):
    def __init__(
        self,
        exporter: MetricExporter,
        exception: Exception,
        export_interval_millis: float | None = None,
        export_timeout_millis: float | None = None,
    ) -> None:
        super().__init__(
            exporter, export_interval_millis, export_timeout_millis
        )
        self._collect_exception = exception

    # pylint: disable=overridden-final-method
    def collect(self, timeout_millis: float = 10_000) -> None:
        raise self._collect_exception


metrics_list = [
    Metric(
        name="sum_name",
        description="",
        unit="",
        data=Sum(
            data_points=[
                NumberDataPoint(
                    attributes={},
                    start_time_unix_nano=time_ns(),
                    time_unix_nano=time_ns(),
                    value=2,
                )
            ],
            aggregation_temporality=1,
            is_monotonic=True,
        ),
    ),
    Metric(
        name="gauge_name",
        description="",
        unit="",
        data=Gauge(
            data_points=[
                NumberDataPoint(
                    attributes={},
                    start_time_unix_nano=time_ns(),
                    time_unix_nano=time_ns(),
                    value=2,
                )
            ]
        ),
    ),
]
metrics = MetricsData(
    resource_metrics=[
        ResourceMetrics(
            scope_metrics=[
                ScopeMetrics(
                    metrics=metrics_list,
                    scope=InstrumentationScope(name="test"),
                    schema_url="",
                )
            ],
            resource=Resource.create(),
            schema_url="",
        )
    ]
)


def _metrics_data_point_count(metrics_data: MetricsData) -> int:
    return sum(
        len(metric.data.data_points)
        for resource_metrics in metrics_data.resource_metrics
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
    )


def _flattened_metric_names(batches) -> list:
    return [
        metric.name
        for batch in batches
        for resource_metrics in batch.resource_metrics
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
    ]


class TestPeriodicExportingMetricReader(ConcurrencyTestBase):
    def test_defaults(self):
        pmr = PeriodicExportingMetricReader(FakeMetricsExporter())
        self.assertEqual(pmr._export_interval_millis, 60000)
        self.assertEqual(pmr._export_timeout_millis, 30000)
        with self.assertLogs(level=WARNING):
            pmr.shutdown()

    def _create_periodic_reader(
        self,
        metrics_data: MetricsData,
        exporter,
        collect_wait=0,
        interval=60000,
        timeout=30000,
    ):
        pmr = PeriodicExportingMetricReader(
            exporter,
            export_interval_millis=interval,
            export_timeout_millis=timeout,
        )

        def _collect(reader, timeout_millis):
            sleep(collect_wait)
            return metrics_data

        pmr._set_collect_callback(_collect)
        return pmr

    def test_ticker_called(self):
        collect_mock = Mock()
        exporter = FakeMetricsExporter()
        exporter.export = Mock()
        pmr = PeriodicExportingMetricReader(exporter, export_interval_millis=1)
        pmr._set_collect_callback(collect_mock)
        sleep(0.1)
        self.assertTrue(collect_mock.assert_called_once)
        pmr.shutdown()

    def test_ticker_not_called_on_infinity(self):
        collect_mock = Mock()
        exporter = FakeMetricsExporter()
        exporter.export = Mock()
        pmr = PeriodicExportingMetricReader(
            exporter, export_interval_millis=math.inf
        )
        pmr._set_collect_callback(collect_mock)
        sleep(0.1)
        self.assertTrue(collect_mock.assert_not_called)
        pmr.shutdown()

    def test_ticker_value_exception_on_zero(self):
        exporter = FakeMetricsExporter()
        exporter.export = Mock()
        self.assertRaises(
            ValueError,
            PeriodicExportingMetricReader,
            exporter,
            export_interval_millis=0,
        )

    def test_ticker_value_exception_on_negative(self):
        exporter = FakeMetricsExporter()
        exporter.export = Mock()
        self.assertRaises(
            ValueError,
            PeriodicExportingMetricReader,
            exporter,
            export_interval_millis=-100,
        )

    @pytest.mark.flaky(max_runs=3, min_passes=1)
    def test_ticker_collects_metrics(self):
        exporter = FakeMetricsExporter()

        pmr = self._create_periodic_reader(metrics, exporter, interval=100)
        sleep(0.15)
        self.assertEqual(exporter.metrics[0], metrics)
        pmr.shutdown()

    def test_shutdown(self):
        exporter = FakeMetricsExporter()

        pmr = self._create_periodic_reader(
            MetricsData(resource_metrics=[]), exporter
        )
        pmr.shutdown()
        self.assertEqual(exporter.metrics[0], MetricsData(resource_metrics=[]))
        self.assertTrue(pmr._shutdown)
        self.assertTrue(exporter._shutdown)

    def test_shutdown_multiple_times(self):
        pmr = self._create_periodic_reader(
            MetricsData(resource_metrics=[]), FakeMetricsExporter()
        )
        with self.assertLogs(level="WARNING") as w:
            self.run_with_many_threads(pmr.shutdown)
        self.assertTrue("Can't shutdown multiple times" in w.output[0])
        with self.assertLogs(level="WARNING") as w:
            pmr.shutdown()

    def test_exporter_temporality_preference(self):
        exporter = FakeMetricsExporter(
            preferred_temporality={
                Counter: AggregationTemporality.DELTA,
            },
        )
        pmr = PeriodicExportingMetricReader(exporter)
        for key, value in pmr._instrument_class_temporality.items():
            if key is not _Counter:
                self.assertEqual(value, AggregationTemporality.CUMULATIVE)
            else:
                self.assertEqual(value, AggregationTemporality.DELTA)

    def test_exporter_aggregation_preference(self):
        exporter = FakeMetricsExporter(
            preferred_aggregation={
                Counter: LastValueAggregation(),
            },
        )
        pmr = PeriodicExportingMetricReader(exporter)
        for key, value in pmr._instrument_class_aggregation.items():
            if key is not _Counter:
                self.assertTrue(isinstance(value, DefaultAggregation))
            else:
                self.assertTrue(isinstance(value, LastValueAggregation))

    def test_metric_timeout_does_not_kill_worker_thread(self):
        exporter = FakeMetricsExporter()
        pmr = ExceptionAtCollectionPeriodicExportingMetricReader(
            exporter,
            MetricsTimeoutError("test timeout"),
            export_timeout_millis=1,
        )

        sleep(0.1)
        self.assertTrue(pmr._daemon_thread.is_alive())
        pmr.shutdown()

    def test_metric_exporer_gc(self):
        # Given a PeriodicExportingMetricReader
        exporter = FakeMetricsExporter(
            preferred_aggregation={
                Counter: LastValueAggregation(),
            },
        )
        processor = PeriodicExportingMetricReader(exporter)
        weak_ref = weakref.ref(processor)
        processor.shutdown()

        # When we garbage collect the reader
        del processor
        gc.collect()

        # Then the reference to the reader should no longer exist
        self.assertIsNone(
            weak_ref(),
            "The PeriodicExportingMetricReader object created by this test wasn't garbage collected",
        )

    def test_no_batching_by_default(self):
        exporter = FakeMetricsExporter()
        pmr = self._create_periodic_reader(metrics, exporter)
        pmr._receive_metrics(metrics)
        self.assertEqual(len(exporter.metrics), 1)
        self.assertEqual(exporter.metrics[0], metrics)
        pmr.shutdown()

    def test_max_export_batch_size_none_single_export(self):
        exporter = FakeMetricsExporter()
        pmr = PeriodicExportingMetricReader(
            exporter, max_export_batch_size=None
        )
        pmr._set_collect_callback(lambda reader, timeout_millis: metrics)
        pmr._receive_metrics(metrics)
        self.assertEqual(len(exporter.metrics), 1)
        self.assertEqual(exporter.metrics[0], metrics)
        pmr.shutdown()

    def test_max_export_batch_size_invalid(self):
        for invalid in (0, -1):
            with self.assertRaises(ValueError):
                PeriodicExportingMetricReader(
                    FakeMetricsExporter(),
                    max_export_batch_size=invalid,
                )

    def test_max_export_batch_size_chunks_data_points(self):
        # metrics contains one sum and one gauge, each with a single data point
        # (two data points total in a single scope of a single resource).
        exporter = FakeMetricsExporter()
        pmr = PeriodicExportingMetricReader(exporter, max_export_batch_size=1)
        pmr._set_collect_callback(lambda reader, timeout_millis: metrics)
        pmr._receive_metrics(metrics)

        # Two data points with a batch size of 1 -> two export calls.
        self.assertEqual(len(exporter.metrics), 2)
        for exported in exporter.metrics:
            self.assertEqual(_metrics_data_point_count(exported), 1)

        # No dropped or duplicated data points, structure preserved.
        self.assertEqual(
            _flattened_metric_names(exporter.metrics),
            [
                "sum_name",
                "gauge_name",
            ],
        )
        for exported in exporter.metrics:
            resource_metrics = exported.resource_metrics[0]
            self.assertEqual(
                resource_metrics.resource,
                metrics.resource_metrics[0].resource,
            )
            scope_metrics = resource_metrics.scope_metrics[0]
            self.assertEqual(
                scope_metrics.scope,
                metrics.resource_metrics[0].scope_metrics[0].scope,
            )
        pmr.shutdown()

    def test_max_export_batch_size_larger_than_total(self):
        exporter = FakeMetricsExporter()
        pmr = PeriodicExportingMetricReader(
            exporter, max_export_batch_size=100
        )
        pmr._set_collect_callback(lambda reader, timeout_millis: metrics)
        pmr._receive_metrics(metrics)
        self.assertEqual(len(exporter.metrics), 1)
        self.assertEqual(_metrics_data_point_count(exporter.metrics[0]), 2)
        pmr.shutdown()

    def test_batch_metrics_data_many_points_multiple_scopes(self):
        # Build a MetricsData with multiple resources, scopes and metrics,
        # each metric carrying several data points, then verify batching
        # preserves every data point exactly once and never exceeds the limit.
        def _number_metric(name, num_points):
            return Metric(
                name=name,
                description="",
                unit="",
                data=Sum(
                    data_points=[
                        NumberDataPoint(
                            attributes={"i": i},
                            start_time_unix_nano=time_ns(),
                            time_unix_nano=time_ns(),
                            value=i,
                        )
                        for i in range(num_points)
                    ],
                    aggregation_temporality=1,
                    is_monotonic=True,
                ),
            )

        source = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource.create({"r": 0}),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=InstrumentationScope(name="scope_a"),
                            metrics=[
                                _number_metric("m_a1", 3),
                                _number_metric("m_a2", 4),
                            ],
                            schema_url="",
                        ),
                        ScopeMetrics(
                            scope=InstrumentationScope(name="scope_b"),
                            metrics=[_number_metric("m_b1", 5)],
                            schema_url="",
                        ),
                    ],
                    schema_url="",
                ),
                ResourceMetrics(
                    resource=Resource.create({"r": 1}),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=InstrumentationScope(name="scope_c"),
                            metrics=[_number_metric("m_c1", 2)],
                            schema_url="",
                        ),
                    ],
                    schema_url="",
                ),
            ]
        )

        total_points = _metrics_data_point_count(source)
        self.assertEqual(total_points, 3 + 4 + 5 + 2)

        batches = list(_batch_metrics_data(source, 3))

        # Total data points preserved.
        self.assertEqual(
            sum(_metrics_data_point_count(b) for b in batches),
            total_points,
        )
        # All metric names present exactly once, in original order.
        self.assertEqual(
            _flattened_metric_names(batches),
            ["m_a1", "m_a2", "m_b1", "m_c1"],
        )
        # No batch exceeds the limit unless a single metric already does.
        for batch in batches:
            count = _metrics_data_point_count(batch)
            metric_counts = [
                len(metric.data.data_points)
                for rm in batch.resource_metrics
                for sm in rm.scope_metrics
                for metric in sm.metrics
            ]
            self.assertTrue(
                count <= 3 or (len(metric_counts) == 1),
                f"batch with {count} points and metric_counts {metric_counts}",
            )

    @patch.dict(
        "os.environ", {OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED: "true"}
    )
    def test_metric_reader_metrics(self):
        exporter = FakeMetricsExporter()
        pmr = PeriodicExportingMetricReader(
            exporter, export_interval_millis=100000
        )
        mp = MeterProvider(metric_readers=[pmr])

        counter = mp.get_meter("test").create_counter("test_counter")
        counter.add(1)

        mp.force_flush()
        self.assertEqual(len(exporter.metrics), 1)
        # Need a second collection to get the metric we recorded during first collection
        exporter.metrics.clear()
        mp.force_flush()
        self.assertEqual(len(exporter.metrics), 1)
        metric_data = exporter.metrics[0]

        scope_metrics = [
            sm
            for sm in metric_data.resource_metrics[0].scope_metrics
            if sm.scope.name == "opentelemetry-sdk"
        ]
        self.assertEqual(len(scope_metrics), 1)
        reader_metrics = [
            m
            for m in scope_metrics[0].metrics
            if m.name == "otel.sdk.metric_reader.collection.duration"
        ]
        self.assertEqual(len(reader_metrics), 1)
        metric = reader_metrics[0]

        point = metric.data.data_points[0]
        histogram = cast(HistogramDataPoint, point)
        self.assertEqual(histogram.count, 1)
        attrs = histogram.attributes
        assert attrs is not None
        self.assertEqual(
            attrs["otel.component.type"], "periodic_metric_reader"
        )
        name = attrs["otel.component.name"]
        assert isinstance(name, str)
        self.assertTrue(name.startswith("periodic_metric_reader/"))

        mp.shutdown()
