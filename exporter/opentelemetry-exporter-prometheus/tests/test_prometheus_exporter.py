# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from textwrap import dedent
from unittest import TestCase
from unittest.mock import Mock, patch

from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client.core import (
    CounterMetricFamily,
    GaugeMetricFamily,
    InfoMetricFamily,
)

from opentelemetry.exporter.prometheus import (
    _OTEL_SCOPE_ATTR_PREFIX,
    _OTEL_SCOPE_NAME_LABEL,
    _OTEL_SCOPE_SCHEMA_URL_LABEL,
    _OTEL_SCOPE_VERSION_LABEL,
    PrometheusMetricReader,
    _CustomCollector,
)
from opentelemetry.metrics import NoOpMeterProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.point import Exemplar
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    MetricsData,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.test.metrictestutil import (
    _generate_gauge,
    _generate_histogram,
    _generate_sum,
    _generate_unsupported_metric,
)


class TestPrometheusMetricReader(TestCase):  # pylint: disable=too-many-public-methods
    def setUp(self):
        self._mock_registry_register = Mock()
        self._registry_register_patch = patch(
            "prometheus_client.core.REGISTRY.register",
            side_effect=self._mock_registry_register,
        )

    def test_custom_registry(self):
        with self._registry_register_patch:
            custom_registry = CollectorRegistry()
            reader = PrometheusMetricReader(registry=custom_registry)
            # global REGISTRY should NOT be used
            self._mock_registry_register.assert_not_called()
            # check custom_registry was registered
            self.assertIn(
                reader._collector,  # pylint: disable=protected-access
                custom_registry._collector_to_names,  # pylint: disable=protected-access
            )
            reader.shutdown()

    def verify_text_format(
        self,
        metric: Metric,
        expect_prometheus_text: str,
        prefix: str = "",
        scope: InstrumentationScope | None = None,
        scope_info_enabled: bool = False,
    ) -> None:
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=scope or Mock(),
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )

        collector = _CustomCollector(
            disable_target_info=True,
            scope_info_enabled=scope_info_enabled,
            prefix=prefix,
        )
        collector.add_metrics_data(metrics_data)
        result_bytes = generate_latest(collector)
        result = result_bytes.decode("utf-8")
        self.assertEqual(result, expect_prometheus_text)

    # pylint: disable=protected-access
    def test_constructor(self):
        """Test the constructor."""
        with self._registry_register_patch:
            _ = PrometheusMetricReader()
            self.assertTrue(self._mock_registry_register.called)

    def test_shutdown(self):
        with patch(
            "prometheus_client.core.REGISTRY.unregister"
        ) as registry_unregister_patch:
            exporter = PrometheusMetricReader()
            exporter.shutdown()
            self.assertTrue(registry_unregister_patch.called)

    def test_histogram_to_prometheus(self):
        metric = Metric(
            name="test@name",
            description="foo",
            unit="s",
            data=Histogram(
                data_points=[
                    HistogramDataPoint(
                        attributes={"histo": 1},
                        start_time_unix_nano=1641946016139533244,
                        time_unix_nano=1641946016139533244,
                        count=6,
                        sum=579.0,
                        bucket_counts=[1, 3, 2],
                        explicit_bounds=[123.0, 456.0],
                        min=1,
                        max=457,
                    )
                ],
                aggregation_temporality=AggregationTemporality.DELTA,
            ),
        )
        self.verify_text_format(
            metric,
            dedent(
                """\
                # HELP test_name_seconds foo
                # TYPE test_name_seconds histogram
                test_name_seconds_bucket{histo="1",le="123.0"} 1.0
                test_name_seconds_bucket{histo="1",le="456.0"} 4.0
                test_name_seconds_bucket{histo="1",le="+Inf"} 6.0
                test_name_seconds_count{histo="1"} 6.0
                test_name_seconds_sum{histo="1"} 579.0
                """
            ),
        )

    def test_monotonic_sum_to_prometheus(self):
        labels = {"environment@": "staging", "os": "Windows"}
        metric = _generate_sum(
            "test@sum_monotonic",
            123,
            attributes=labels,
            description="testdesc",
            unit="testunit",
        )

        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=Mock(),
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )

        collector = _CustomCollector(
            disable_target_info=True, scope_info_enabled=False
        )
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), CounterMetricFamily)
            self.assertEqual(
                prometheus_metric.name, "test_sum_monotonic_testunit"
            )
            self.assertEqual(prometheus_metric.documentation, "testdesc")
            self.assertTrue(len(prometheus_metric.samples) == 1)
            self.assertEqual(prometheus_metric.samples[0].value, 123)
            self.assertTrue(len(prometheus_metric.samples[0].labels) == 2)
            self.assertEqual(
                prometheus_metric.samples[0].labels["environment_"], "staging"
            )
            self.assertEqual(
                prometheus_metric.samples[0].labels["os"], "Windows"
            )

    def test_non_monotonic_sum_to_prometheus(self):
        labels = {"environment@": "staging", "os": "Windows"}
        metric = _generate_sum(
            "test@sum_nonmonotonic",
            123,
            attributes=labels,
            description="testdesc",
            unit="testunit",
            is_monotonic=False,
        )

        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=Mock(),
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )

        collector = _CustomCollector(
            disable_target_info=True, scope_info_enabled=False
        )
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), GaugeMetricFamily)
            self.assertEqual(
                prometheus_metric.name, "test_sum_nonmonotonic_testunit"
            )
            self.assertEqual(prometheus_metric.documentation, "testdesc")
            self.assertTrue(len(prometheus_metric.samples) == 1)
            self.assertEqual(prometheus_metric.samples[0].value, 123)
            self.assertTrue(len(prometheus_metric.samples[0].labels) == 2)
            self.assertEqual(
                prometheus_metric.samples[0].labels["environment_"], "staging"
            )
            self.assertEqual(
                prometheus_metric.samples[0].labels["os"], "Windows"
            )

    def test_gauge_to_prometheus(self):
        labels = {"environment@": "dev", "os": "Unix"}
        metric = _generate_gauge(
            "test@gauge",
            123,
            attributes=labels,
            description="testdesc",
            unit="testunit",
        )

        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=Mock(),
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )

        collector = _CustomCollector(
            disable_target_info=True, scope_info_enabled=False
        )
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), GaugeMetricFamily)
            self.assertEqual(prometheus_metric.name, "test_gauge_testunit")
            self.assertEqual(prometheus_metric.documentation, "testdesc")
            self.assertTrue(len(prometheus_metric.samples) == 1)
            self.assertEqual(prometheus_metric.samples[0].value, 123)
            self.assertTrue(len(prometheus_metric.samples[0].labels) == 2)
            self.assertEqual(
                prometheus_metric.samples[0].labels["environment_"], "dev"
            )
            self.assertEqual(prometheus_metric.samples[0].labels["os"], "Unix")

    def test_invalid_metric(self):
        labels = {"environment": "staging"}
        record = _generate_unsupported_metric(
            "tesname",
            attributes=labels,
            description="testdesc",
            unit="testunit",
        )
        collector = _CustomCollector()
        collector.add_metrics_data([record])
        collector.collect()
        self.assertLogs("opentelemetry.exporter.prometheus", level="WARNING")

    def test_list_labels(self):
        labels = {"environment@": ["1", "2", "3"], "os": "Unix"}
        metric = _generate_gauge(
            "test@gauge",
            123,
            attributes=labels,
            description="testdesc",
            unit="testunit",
        )
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=Mock(),
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )
        collector = _CustomCollector(
            disable_target_info=True, scope_info_enabled=False
        )
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), GaugeMetricFamily)
            self.assertEqual(prometheus_metric.name, "test_gauge_testunit")
            self.assertEqual(prometheus_metric.documentation, "testdesc")
            self.assertTrue(len(prometheus_metric.samples) == 1)
            self.assertEqual(prometheus_metric.samples[0].value, 123)
            self.assertTrue(len(prometheus_metric.samples[0].labels) == 2)
            self.assertEqual(
                prometheus_metric.samples[0].labels["environment_"],
                '["1", "2", "3"]',
            )
            self.assertEqual(prometheus_metric.samples[0].labels["os"], "Unix")

    def test_check_value(self):
        collector = _CustomCollector()

        self.assertEqual(collector._check_value(1), "1")
        self.assertEqual(collector._check_value(1.0), "1.0")
        self.assertEqual(collector._check_value("a"), "a")
        self.assertEqual(collector._check_value([1, 2]), "[1, 2]")
        self.assertEqual(collector._check_value((1, 2)), "[1, 2]")
        self.assertEqual(collector._check_value(["a", 2]), '["a", 2]')
        self.assertEqual(collector._check_value(True), "true")
        self.assertEqual(collector._check_value(False), "false")
        self.assertEqual(collector._check_value(None), "null")

    def test_multiple_collection_calls(self):
        metric_reader = PrometheusMetricReader()
        provider = MeterProvider(metric_readers=[metric_reader])
        # Disable SDK metrics since they are not constant across collections
        metric_reader._set_meter_provider(NoOpMeterProvider())
        meter = provider.get_meter("getting-started", "0.1.2")
        counter = meter.create_counter("counter")
        counter.add(1)
        result_0 = list(metric_reader._collector.collect())
        result_1 = list(metric_reader._collector.collect())
        result_2 = list(metric_reader._collector.collect())
        self.assertEqual(result_0, result_1)
        self.assertEqual(result_1, result_2)

    def test_target_info_enabled_by_default(self):
        metric_reader = PrometheusMetricReader()
        provider = MeterProvider(
            metric_readers=[metric_reader],
            resource=Resource({"os": "Unix", "version": "1.2.3"}),
        )
        meter = provider.get_meter("getting-started", "0.1.2")
        counter = meter.create_counter("counter")
        counter.add(1)
        result = list(metric_reader._collector.collect())

        self.assertEqual(len(result), 2)

        prometheus_metric = result[0]

        self.assertEqual(type(prometheus_metric), InfoMetricFamily)
        self.assertEqual(prometheus_metric.name, "target")
        self.assertEqual(prometheus_metric.documentation, "Target metadata")
        self.assertTrue(len(prometheus_metric.samples) == 1)
        self.assertEqual(prometheus_metric.samples[0].value, 1)
        self.assertTrue(len(prometheus_metric.samples[0].labels) == 2)
        self.assertEqual(prometheus_metric.samples[0].labels["os"], "Unix")
        self.assertEqual(
            prometheus_metric.samples[0].labels["version"], "1.2.3"
        )

    def test_target_info_disabled(self):
        metric_reader = PrometheusMetricReader(disable_target_info=True)
        provider = MeterProvider(
            metric_readers=[metric_reader],
            resource=Resource({"os": "Unix", "version": "1.2.3"}),
        )
        meter = provider.get_meter("getting-started", "0.1.2")
        counter = meter.create_counter("counter")
        counter.add(1)
        result = list(metric_reader._collector.collect())

        for prometheus_metric in result:
            self.assertNotEqual(type(prometheus_metric), InfoMetricFamily)
            self.assertNotEqual(prometheus_metric.name, "target")
            self.assertNotEqual(
                prometheus_metric.documentation, "Target metadata"
            )
            self.assertNotIn("os", prometheus_metric.samples[0].labels)
            self.assertNotIn("version", prometheus_metric.samples[0].labels)

    def test_target_info_sanitize(self):
        metric_reader = PrometheusMetricReader()
        provider = MeterProvider(
            metric_readers=[metric_reader],
            resource=Resource(
                {
                    "system.os": "Unix",
                    "system.name": "Prometheus Target Sanitize",
                    "histo": 1,
                    "ratio": 0.1,
                }
            ),
        )
        meter = provider.get_meter("getting-started", "0.1.2")
        counter = meter.create_counter("counter")
        counter.add(1)
        prometheus_metric = list(metric_reader._collector.collect())[0]

        self.assertEqual(type(prometheus_metric), InfoMetricFamily)
        self.assertEqual(prometheus_metric.name, "target")
        self.assertEqual(prometheus_metric.documentation, "Target metadata")
        self.assertTrue(len(prometheus_metric.samples) == 1)
        self.assertEqual(prometheus_metric.samples[0].value, 1)
        self.assertTrue(len(prometheus_metric.samples[0].labels) == 4)
        self.assertTrue("system_os" in prometheus_metric.samples[0].labels)
        self.assertEqual(
            prometheus_metric.samples[0].labels["system_os"], "Unix"
        )
        self.assertTrue("system_name" in prometheus_metric.samples[0].labels)
        self.assertEqual(
            prometheus_metric.samples[0].labels["system_name"],
            "Prometheus Target Sanitize",
        )
        self.assertTrue("histo" in prometheus_metric.samples[0].labels)
        self.assertEqual(
            prometheus_metric.samples[0].labels["histo"],
            "1",
        )
        self.assertTrue("ratio" in prometheus_metric.samples[0].labels)
        self.assertEqual(
            prometheus_metric.samples[0].labels["ratio"],
            "0.1",
        )

    def test_label_order_does_not_matter(self):
        metric_reader = PrometheusMetricReader()
        provider = MeterProvider(metric_readers=[metric_reader])
        meter = provider.get_meter("getting-started", "0.1.2")
        counter = meter.create_counter("counter")

        counter.add(1, {"cause": "cause1", "reason": "reason1"})
        counter.add(1, {"reason": "reason2", "cause": "cause2"})

        prometheus_output = generate_latest().decode()

        # All labels are mapped correctly
        self.assertIn('cause="cause1"', prometheus_output)
        self.assertIn('cause="cause2"', prometheus_output)
        self.assertIn('reason="reason1"', prometheus_output)
        self.assertIn('reason="reason2"', prometheus_output)

        # Only one metric is generated
        metric_count = prometheus_output.count("# HELP counter_total")
        self.assertEqual(metric_count, 1)

    def test_metric_name(self):
        self.verify_text_format(
            _generate_sum(name="test_counter", value=1, unit=""),
            dedent(
                """\
                # HELP test_counter_total foo
                # TYPE test_counter_total counter
                test_counter_total{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_sum(name="test_counter_w_prefix", value=1, unit=""),
            dedent(
                """\
                # HELP foo_test_counter_w_prefix_total foo
                # TYPE foo_test_counter_w_prefix_total counter
                foo_test_counter_w_prefix_total{a="1",b="true"} 1.0
                """
            ),
            prefix="foo",
        )
        self.verify_text_format(
            _generate_sum(
                name="test_counter_w_invalid_chars_prefix", value=1, unit=""
            ),
            dedent(
                """\
                # HELP _foo_test_counter_w_invalid_chars_prefix_total foo
                # TYPE _foo_test_counter_w_invalid_chars_prefix_total counter
                _foo_test_counter_w_invalid_chars_prefix_total{a="1",b="true"} 1.0
                """
            ),
            prefix="#foo",
        )
        self.verify_text_format(
            _generate_sum(name="1leading_digit", value=1, unit=""),
            dedent(
                """\
                # HELP _leading_digit_total foo
                # TYPE _leading_digit_total counter
                _leading_digit_total{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_sum(name="!@#counter_invalid_chars", value=1, unit=""),
            dedent(
                """\
                # HELP _counter_invalid_chars_total foo
                # TYPE _counter_invalid_chars_total counter
                _counter_invalid_chars_total{a="1",b="true"} 1.0
                """
            ),
        )

    def test_metric_name_with_unit(self):
        self.verify_text_format(
            _generate_gauge(name="test.metric.no_unit", value=1, unit=""),
            dedent(
                """\
                # HELP test_metric_no_unit foo
                # TYPE test_metric_no_unit gauge
                test_metric_no_unit{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_gauge(
                name="test.metric.spaces", value=1, unit="   \t  "
            ),
            dedent(
                """\
                # HELP test_metric_spaces foo
                # TYPE test_metric_spaces gauge
                test_metric_spaces{a="1",b="true"} 1.0
                """
            ),
        )

        # UCUM annotations should be stripped
        self.verify_text_format(
            _generate_sum(name="test_counter", value=1, unit="{requests}"),
            dedent(
                """\
                # HELP test_counter_total foo
                # TYPE test_counter_total counter
                test_counter_total{a="1",b="true"} 1.0
                """
            ),
        )

        # slash converts to "per"
        self.verify_text_format(
            _generate_gauge(name="test_gauge", value=1, unit="m/s"),
            dedent(
                """\
                # HELP test_gauge_meters_per_second foo
                # TYPE test_gauge_meters_per_second gauge
                test_gauge_meters_per_second{a="1",b="true"} 1.0
                """
            ),
        )

        # invalid characters in name are sanitized before being passed to prom client, which
        # would throw errors
        self.verify_text_format(
            _generate_sum(name="test_counter", value=1, unit="%{foo}@?"),
            dedent(
                """\
                # HELP test_counter_total foo
                # TYPE test_counter_total counter
                test_counter_total{a="1",b="true"} 1.0
                """
            ),
        )

    def test_semconv(self):
        """Tests that a few select semconv metrics get converted to the expected prometheus
        text format"""
        self.verify_text_format(
            _generate_sum(
                name="system.filesystem.usage",
                value=1,
                is_monotonic=False,
                unit="By",
            ),
            dedent(
                """\
                # HELP system_filesystem_usage_bytes foo
                # TYPE system_filesystem_usage_bytes gauge
                system_filesystem_usage_bytes{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_sum(
                name="system.network.dropped",
                value=1,
                unit="{packets}",
            ),
            dedent(
                """\
                # HELP system_network_dropped_total foo
                # TYPE system_network_dropped_total counter
                system_network_dropped_total{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_histogram(
                name="http.server.request.duration",
                unit="s",
            ),
            dedent(
                """\
                # HELP http_server_request_duration_seconds foo
                # TYPE http_server_request_duration_seconds histogram
                http_server_request_duration_seconds_bucket{a="1",b="true",le="123.0"} 1.0
                http_server_request_duration_seconds_bucket{a="1",b="true",le="456.0"} 4.0
                http_server_request_duration_seconds_bucket{a="1",b="true",le="+Inf"} 6.0
                http_server_request_duration_seconds_count{a="1",b="true"} 6.0
                http_server_request_duration_seconds_sum{a="1",b="true"} 579.0
                """
            ),
        )
        self.verify_text_format(
            _generate_sum(
                name="http.server.active_requests",
                value=1,
                unit="{request}",
                is_monotonic=False,
            ),
            dedent(
                """\
                # HELP http_server_active_requests foo
                # TYPE http_server_active_requests gauge
                http_server_active_requests{a="1",b="true"} 1.0
                """
            ),
        )
        # if the metric name already contains the unit, it shouldn't be added again
        self.verify_text_format(
            _generate_sum(
                name="metric_name_with_myunit",
                value=1,
                unit="myunit",
            ),
            dedent(
                """\
                # HELP metric_name_with_myunit_total foo
                # TYPE metric_name_with_myunit_total counter
                metric_name_with_myunit_total{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_gauge(
                name="metric_name_percent",
                value=1,
                unit="%",
            ),
            dedent(
                """\
                # HELP metric_name_percent foo
                # TYPE metric_name_percent gauge
                metric_name_percent{a="1",b="true"} 1.0
                """
            ),
        )

    def test_scope_info_labels_default(self):
        scope = InstrumentationScope(
            name="library.test",
            version="1.2.3",
            schema_url="schema_url",
        )
        metric = _generate_gauge(
            "test_gauge",
            42,
            attributes={"env": "prod"},
            description="testdesc",
            unit="",
        )
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource({}),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=scope,
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )
        collector = _CustomCollector()
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            if isinstance(prometheus_metric, InfoMetricFamily):
                continue
            labels = prometheus_metric.samples[0].labels
            self.assertEqual(labels[_OTEL_SCOPE_NAME_LABEL], "library.test")
            self.assertEqual(labels[_OTEL_SCOPE_VERSION_LABEL], "1.2.3")
            self.assertEqual(
                labels[_OTEL_SCOPE_SCHEMA_URL_LABEL],
                "schema_url",
            )
            self.assertEqual(labels["env"], "prod")

    def test_scope_info_labels_text_format(self):
        scope = InstrumentationScope(
            name="library.test",
            version="1.2.3",
        )
        self.verify_text_format(
            _generate_gauge(
                "test_gauge",
                42,
                attributes={"env": "prod"},
                description="testdesc",
                unit="",
            ),
            dedent(
                """\
                # HELP test_gauge testdesc
                # TYPE test_gauge gauge
                test_gauge{env="prod",otel_scope_name="library.test",otel_scope_schema_url="",otel_scope_version="1.2.3"} 42.0
                """
            ),
            scope=scope,
            scope_info_enabled=True,
        )

    def test_scope_attributes_text_format(self):
        scope = InstrumentationScope(
            name="library.test",
            version="1.0",
            schema_url="schema_url",
            attributes={"region": "us-east-1"},
        )
        self.verify_text_format(
            _generate_gauge(
                "test_gauge",
                7,
                attributes={},
                description="testdesc",
                unit="",
            ),
            dedent(
                """\
                # HELP test_gauge testdesc
                # TYPE test_gauge gauge
                test_gauge{otel_scope_name="library.test",otel_scope_region="us-east-1",otel_scope_schema_url="schema_url",otel_scope_version="1.0"} 7.0
                """
            ),
            scope=scope,
            scope_info_enabled=True,
        )

    def test_scope_info_disabled(self):
        scope = InstrumentationScope(name="library.test", version="1.2.3")
        metric = _generate_gauge(
            "test_gauge",
            42,
            attributes={"env": "prod"},
            description="testdesc",
            unit="",
        )
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=scope,
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )
        collector = _CustomCollector(
            disable_target_info=True, scope_info_enabled=False
        )
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            labels = prometheus_metric.samples[0].labels
            self.assertNotIn(_OTEL_SCOPE_NAME_LABEL, labels)
            self.assertNotIn(_OTEL_SCOPE_VERSION_LABEL, labels)
            self.assertNotIn(_OTEL_SCOPE_SCHEMA_URL_LABEL, labels)
            self.assertNotIn(_OTEL_SCOPE_ATTR_PREFIX + "region", labels)

    def test_scope_attributes_labels(self):
        scope = InstrumentationScope(
            name="library.test",
            version="1.0",
            schema_url="schema_url",
            attributes={
                "region": "us-east-1",
                "name": "should-be-dropped",
                "version": "should-be-dropped",
                "schema_url": "should-be-dropped",
            },
        )
        metric = _generate_gauge(
            "test_gauge",
            7,
            attributes={},
            description="testdesc",
            unit="",
        )
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=scope,
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )
        collector = _CustomCollector(disable_target_info=True)
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            labels = prometheus_metric.samples[0].labels
            self.assertEqual(
                labels[_OTEL_SCOPE_ATTR_PREFIX + "region"], "us-east-1"
            )
            self.assertEqual(labels[_OTEL_SCOPE_NAME_LABEL], "library.test")
            self.assertEqual(labels[_OTEL_SCOPE_VERSION_LABEL], "1.0")
            self.assertEqual(
                labels[_OTEL_SCOPE_SCHEMA_URL_LABEL], "schema_url"
            )

    def test_multiple_data_points_with_different_label_sets(self):
        hist_point_1 = HistogramDataPoint(
            attributes={"http_target": "/foobar", "net_host_port": 8080},
            start_time_unix_nano=1641946016139533244,
            time_unix_nano=1641946016139533244,
            count=6,
            sum=579.0,
            bucket_counts=[1, 3, 2],
            explicit_bounds=[123.0, 456.0],
            min=1,
            max=457,
        )
        hist_point_2 = HistogramDataPoint(
            attributes={"net_host_port": 8080},
            start_time_unix_nano=1641946016139533245,
            time_unix_nano=1641946016139533245,
            count=7,
            sum=579.0,
            bucket_counts=[1, 3, 3],
            explicit_bounds=[123.0, 456.0],
            min=1,
            max=457,
        )

        metric = Metric(
            name="http.server.request.duration",
            description="test multiple label sets",
            unit="s",
            data=Histogram(
                data_points=[hist_point_1, hist_point_2],
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
            ),
        )

        self.verify_text_format(
            metric,
            dedent(
                """\
                # HELP http_server_request_duration_seconds test multiple label sets
                # TYPE http_server_request_duration_seconds histogram
                http_server_request_duration_seconds_bucket{http_target="/foobar",le="123.0",net_host_port="8080"} 1.0
                http_server_request_duration_seconds_bucket{http_target="/foobar",le="456.0",net_host_port="8080"} 4.0
                http_server_request_duration_seconds_bucket{http_target="/foobar",le="+Inf",net_host_port="8080"} 6.0
                http_server_request_duration_seconds_count{http_target="/foobar",net_host_port="8080"} 6.0
                http_server_request_duration_seconds_sum{http_target="/foobar",net_host_port="8080"} 579.0
                http_server_request_duration_seconds_bucket{http_target="",le="123.0",net_host_port="8080"} 1.0
                http_server_request_duration_seconds_bucket{http_target="",le="456.0",net_host_port="8080"} 4.0
                http_server_request_duration_seconds_bucket{http_target="",le="+Inf",net_host_port="8080"} 7.0
                http_server_request_duration_seconds_count{http_target="",net_host_port="8080"} 7.0
                http_server_request_duration_seconds_sum{http_target="",net_host_port="8080"} 579.0
                """
            ),
        )

    def _collect_single_metric(self, metric, **collector_kwargs):
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=Mock(),
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )
        collector = _CustomCollector(
            disable_target_info=True,
            scope_info_enabled=False,
            **collector_kwargs,
        )
        collector.add_metrics_data(metrics_data)
        return list(collector.collect())

    def test_colliding_sanitized_attribute_keys_are_merged(self):
        # "foo.bar" and "foo/bar" both sanitize to "foo_bar" and must be
        # merged into a single semicolon-joined label sorted by original key.
        metric = Metric(
            name="test_counter",
            description="desc",
            unit="",
            data=Sum(
                data_points=[
                    NumberDataPoint(
                        attributes={"foo/bar": "second", "foo.bar": "first"},
                        start_time_unix_nano=0,
                        time_unix_nano=0,
                        value=1,
                    )
                ],
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
            ),
        )
        families = self._collect_single_metric(metric)
        self.assertEqual(len(families), 1)
        sample = families[0].samples[0]
        # Sorted by original key: "foo.bar" (first) then "foo/bar" (second).
        self.assertEqual(sample.labels["foo_bar"], "first;second")

    def test_exemplars_emitted_on_counter(self):
        exemplar = Exemplar(
            filtered_attributes={},
            value=1.0,
            time_unix_nano=1_000_000_000,
            span_id=42,
            trace_id=1234567890,
        )
        metric = Metric(
            name="test_counter",
            description="desc",
            unit="",
            data=Sum(
                data_points=[
                    NumberDataPoint(
                        attributes={},
                        start_time_unix_nano=0,
                        time_unix_nano=0,
                        value=5,
                        exemplars=[exemplar],
                    )
                ],
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
            ),
        )
        families = self._collect_single_metric(metric)
        sample = families[0].samples[0]
        self.assertIsNotNone(sample.exemplar)
        self.assertEqual(sample.exemplar.value, 1.0)
        self.assertEqual(sample.exemplar.labels["span_id"], "000000000000002a")
        self.assertEqual(
            sample.exemplar.labels["trace_id"],
            "000000000000000000000000499602d2",
        )

    def test_exemplars_emitted_on_histogram(self):
        exemplar = Exemplar(
            filtered_attributes={},
            value=2.0,
            time_unix_nano=1_000_000_000,
            span_id=42,
            trace_id=1234567890,
        )
        metric = Metric(
            name="test_histogram",
            description="desc",
            unit="",
            data=Histogram(
                data_points=[
                    HistogramDataPoint(
                        attributes={},
                        start_time_unix_nano=0,
                        time_unix_nano=0,
                        count=6,
                        sum=579.0,
                        bucket_counts=[1, 3, 2],
                        explicit_bounds=[123.0, 456.0],
                        min=1,
                        max=457,
                        exemplars=[exemplar],
                    )
                ],
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
            ),
        )
        families = self._collect_single_metric(metric)
        inf_bucket = [
            sample
            for sample in families[0].samples
            if sample.name.endswith("_bucket")
            and sample.labels.get("le") == "+Inf"
        ][0]
        self.assertIsNotNone(inf_bucket.exemplar)
        self.assertEqual(inf_bucket.exemplar.value, 2.0)

    def test_without_counter_suffixes_drops_total(self):
        metric = _generate_sum(name="test_counter", value=1, unit="")
        families = self._collect_single_metric(
            metric, without_counter_suffixes=True
        )
        sample_names = {sample.name for sample in families[0].samples}
        self.assertIn("test_counter", sample_names)
        self.assertNotIn("test_counter_total", sample_names)

    def test_counter_suffix_present_by_default(self):
        metric = _generate_sum(name="test_counter", value=1, unit="")
        families = self._collect_single_metric(metric)
        sample_names = {sample.name for sample in families[0].samples}
        self.assertIn("test_counter_total", sample_names)

    def test_conflicting_type_same_name_family_dropped(self):
        counter = Metric(
            name="conflict",
            description="desc",
            unit="",
            data=Sum(
                data_points=[
                    NumberDataPoint(
                        attributes={},
                        start_time_unix_nano=0,
                        time_unix_nano=0,
                        value=1,
                    )
                ],
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
            ),
        )
        gauge = Metric(
            name="conflict",
            description="desc",
            unit="",
            data=Gauge(
                data_points=[
                    NumberDataPoint(
                        attributes={},
                        start_time_unix_nano=0,
                        time_unix_nano=0,
                        value=2,
                    )
                ],
            ),
        )
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=Mock(),
                            metrics=[counter, gauge],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )
        collector = _CustomCollector(
            disable_target_info=True, scope_info_enabled=False
        )
        collector.add_metrics_data(metrics_data)
        with self.assertLogs(
            "opentelemetry.exporter.prometheus", level="WARNING"
        ) as log_ctx:
            families = list(collector.collect())
        # Only the first (counter) family survives.
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0].type, "counter")
        self.assertTrue(
            any("conflicting type" in msg for msg in log_ctx.output)
        )

    def test_scope_attribute_colliding_with_reserved_label_skipped(self):
        scope = InstrumentationScope(
            name="library.test",
            version="1.0",
            schema_url="schema_url",
        )
        # A data point attribute that sanitizes to a reserved otel_scope_*
        # label must be dropped in favor of the scope-provided value.
        metric = Metric(
            name="test_gauge",
            description="desc",
            unit="",
            data=Gauge(
                data_points=[
                    NumberDataPoint(
                        attributes={"otel_scope_name": "attacker"},
                        start_time_unix_nano=0,
                        time_unix_nano=0,
                        value=1,
                    )
                ],
            ),
        )
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=scope,
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )
        collector = _CustomCollector(
            disable_target_info=True, scope_info_enabled=True
        )
        collector.add_metrics_data(metrics_data)
        families = list(collector.collect())
        sample = families[0].samples[0]
        self.assertEqual(sample.labels["otel_scope_name"], "library.test")
