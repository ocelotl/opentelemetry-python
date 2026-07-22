# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
This library allows export of metrics data to `Prometheus <https://prometheus.io/>`_.

Usage
-----

The **OpenTelemetry Prometheus Exporter** allows export of `OpenTelemetry`_
metrics to `Prometheus`_.


.. _Prometheus: https://prometheus.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. code:: python

    from prometheus_client import start_http_server

    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.metrics import get_meter_provider, set_meter_provider
    from opentelemetry.sdk.metrics import MeterProvider

    # Start Prometheus client
    start_http_server(port=8000, addr="localhost")

    # Exporter to export metrics to Prometheus
    prefix = "MyAppPrefix"
    reader = PrometheusMetricReader(prefix=prefix)

    # Meter is responsible for creating and recording metrics
    set_meter_provider(MeterProvider(metric_readers=[reader]))
    meter = get_meter_provider().get_meter("myapp", "0.1.2")

    counter = meter.create_counter(
        "requests",
        "requests",
        "number of requests",
    )

    # Labels are used to identify key-values that are associated with a specific
    # metric that you want to record. These are useful for pre-aggregation and can
    # be used to store custom dimensions pertaining to a metric
    labels = {"environment": "staging"}

    counter.add(25, labels)
    input("Press any key to exit...")

API
---
"""

from collections import deque
from collections.abc import Callable, Iterable, Sequence
from itertools import chain
from json import dumps
from logging import getLogger
from os import environ
from typing import (
    Any,
    TypeVar,
)

from prometheus_client import CollectorRegistry, start_http_server
from prometheus_client.core import (
    REGISTRY,
    CounterMetricFamily,
    GaugeMetricFamily,
    HistogramMetricFamily,
    InfoMetricFamily,
)
from prometheus_client.core import Exemplar as PrometheusExemplar
from prometheus_client.core import Metric as PrometheusMetric
from prometheus_client.samples import Sample

from opentelemetry.exporter.prometheus._mapping import (
    map_unit,
    sanitize_attribute,
    sanitize_full_name,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_PROMETHEUS_HOST,
    OTEL_EXPORTER_PROMETHEUS_PORT,
)
from opentelemetry.sdk.metrics import (
    Counter,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics import Histogram as HistogramInstrument
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    DataT,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    MetricReader,
    MetricsData,
    Sum,
)
from opentelemetry.sdk.metrics._internal.point import Exemplar as OTelExemplar
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.trace import format_span_id, format_trace_id
from opentelemetry.util.types import Attributes, AttributeValue

_logger = getLogger(__name__)

_TARGET_INFO_NAME = "target"
_TARGET_INFO_DESCRIPTION = "Target metadata"

_OTEL_SCOPE_NAME_LABEL = "otel_scope_name"
_OTEL_SCOPE_VERSION_LABEL = "otel_scope_version"
_OTEL_SCOPE_SCHEMA_URL_LABEL = "otel_scope_schema_url"
_OTEL_SCOPE_ATTR_PREFIX = "otel_scope_"

_RESERVED_SCOPE_LABELS = frozenset(
    {
        _OTEL_SCOPE_NAME_LABEL,
        _OTEL_SCOPE_VERSION_LABEL,
        _OTEL_SCOPE_SCHEMA_URL_LABEL,
    }
)

# Exemplar label names as defined by the Prometheus/OpenMetrics compatibility
# specification.
_EXEMPLAR_TRACE_ID_LABEL = "trace_id"
_EXEMPLAR_SPAN_ID_LABEL = "span_id"


def _convert_exemplar(
    exemplar: OTelExemplar,
) -> PrometheusExemplar:
    """Map an OpenTelemetry exemplar to a ``prometheus_client`` exemplar.

    The trace and span identifiers, when present, are exposed as the
    ``trace_id`` and ``span_id`` labels as required by the Prometheus and
    OpenMetrics compatibility specification.
    """
    labels: dict[str, str] = {}
    if exemplar.trace_id is not None:
        labels[_EXEMPLAR_TRACE_ID_LABEL] = format_trace_id(exemplar.trace_id)
    if exemplar.span_id is not None:
        labels[_EXEMPLAR_SPAN_ID_LABEL] = format_span_id(exemplar.span_id)
    timestamp = None
    if exemplar.time_unix_nano is not None:
        timestamp = exemplar.time_unix_nano / 1e9
    return PrometheusExemplar(
        labels=labels,
        value=exemplar.value,
        timestamp=timestamp,
    )


def _first_exemplar(
    exemplars: Sequence[OTelExemplar] | None,
) -> PrometheusExemplar | None:
    """Return the first exemplar of a data point converted for Prometheus.

    Prometheus attaches at most one exemplar per sample, so only the first
    OpenTelemetry exemplar is used.
    """
    if not exemplars:
        return None
    return _convert_exemplar(exemplars[0])


def _convert_buckets(
    bucket_counts: Sequence[int], explicit_bounds: Sequence[float]
) -> Sequence[tuple[str, int]]:
    buckets = []
    total_count = 0
    for upper_bound, count in zip(
        chain(explicit_bounds, ["+Inf"]),
        bucket_counts,
    ):
        total_count += count
        buckets.append((f"{upper_bound}", total_count))

    return buckets


def _should_convert_sum_to_gauge(metric: Metric) -> bool:
    # The Prometheus compatibility spec requires cumulative non-monotonic Sums
    # to be exported as Gauges.
    if not isinstance(metric.data, Sum):
        return False
    return (
        not metric.data.is_monotonic
        and metric.data.aggregation_temporality
        == AggregationTemporality.CUMULATIVE
    )


_FamilyT = TypeVar("_FamilyT", bound=PrometheusMetric)


def _get_or_create_family(
    registry: dict[str, PrometheusMetric],
    family_id: str,
    factory: Callable[..., _FamilyT],
    *,
    name: str,
    documentation: str,
    labels: Sequence[str],
    unit: str,
) -> _FamilyT:
    if family_id not in registry:
        registry[family_id] = factory(
            name=name,
            documentation=documentation,
            labels=labels,
            unit=unit,
        )
    return registry[family_id]


def _populate_counter_family(
    registry: dict[str, PrometheusMetric],
    per_metric_family_id: str,
    metric_name: str,
    description: str,
    unit: str,
    label_keys: Sequence[str],
    label_rows: Sequence[Sequence[str]],
    values: Sequence[float],
    exemplars: Sequence[PrometheusExemplar | None],
    without_counter_suffixes: bool,
) -> None:
    family_id = "|".join([per_metric_family_id, CounterMetricFamily.__name__])
    family = _get_or_create_family(
        registry,
        family_id,
        CounterMetricFamily,
        name=metric_name,
        documentation=description,
        labels=label_keys,
        unit=unit,
    )
    for label_values, value, exemplar in zip(label_rows, values, exemplars):
        family.add_metric(labels=label_values, value=value, exemplar=exemplar)
    if without_counter_suffixes:
        family.samples = [
            sample._replace(name=sample.name[: -len("_total")])
            if sample.name.endswith("_total")
            else sample
            for sample in family.samples
        ]


def _populate_gauge_family(
    registry: dict[str, PrometheusMetric],
    per_metric_family_id: str,
    metric_name: str,
    description: str,
    unit: str,
    label_keys: Sequence[str],
    label_rows: Sequence[Sequence[str]],
    values: Sequence[float],
) -> None:
    family_id = "|".join([per_metric_family_id, GaugeMetricFamily.__name__])
    family = _get_or_create_family(
        registry,
        family_id,
        GaugeMetricFamily,
        name=metric_name,
        documentation=description,
        labels=label_keys,
        unit=unit,
    )
    for label_values, value in zip(label_rows, values):
        family.add_metric(labels=label_values, value=value)


def _populate_histogram_family(
    registry: dict[str, PrometheusMetric],
    per_metric_family_id: str,
    metric_name: str,
    description: str,
    unit: str,
    label_keys: Sequence[str],
    label_rows: Sequence[Sequence[str]],
    values: Sequence[dict[str, Any]],
    exemplars: Sequence[PrometheusExemplar | None],
) -> None:
    family_id = "|".join(
        [per_metric_family_id, HistogramMetricFamily.__name__]
    )
    family = _get_or_create_family(
        registry,
        family_id,
        HistogramMetricFamily,
        name=metric_name,
        documentation=description,
        labels=label_keys,
        unit=unit,
    )
    for label_values, value, exemplar in zip(label_rows, values, exemplars):
        buckets = _convert_buckets(
            value["bucket_counts"], value["explicit_bounds"]
        )
        if exemplar is not None and buckets:
            # Prometheus attaches an exemplar to a single bucket; use the
            # catch-all (+Inf) bucket so it is always present.
            upper_bound, count = buckets[-1]
            buckets[-1] = (upper_bound, count, exemplar)
        family.add_metric(
            labels=label_values,
            buckets=buckets,
            sum_value=value["sum"],
        )


class PrometheusMetricReader(MetricReader):
    """Prometheus metric exporter for OpenTelemetry.

    Args:
        disable_target_info: Whether to disable the ``target_info`` metric.
        scope_info_enabled: Whether to include instrumentation scope labels on
            exported metrics. Scope labels are exported by default.
        prefix: Prefix added to exported Prometheus metric names.
        without_counter_suffixes: Whether to suppress the ``_total`` suffix
            that is otherwise appended to counter (monotonic Sum) metrics.
    """

    def __init__(
        self,
        disable_target_info: bool = False,
        prefix: str = "",
        scope_info_enabled: bool = True,
        *,
        registry: CollectorRegistry = REGISTRY,
        without_counter_suffixes: bool = False,
    ) -> None:
        super().__init__(
            preferred_temporality={
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                HistogramInstrument: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            },
            otel_component_type=OtelComponentTypeValues.PROMETHEUS_HTTP_TEXT_METRIC_EXPORTER,
        )
        self._collector = _CustomCollector(
            disable_target_info=disable_target_info,
            prefix=prefix,
            scope_info_enabled=scope_info_enabled,
            without_counter_suffixes=without_counter_suffixes,
        )
        self._registry = registry
        self._registry.register(self._collector)
        self._collector._callback = self.collect
        self._prefix = prefix

    def _receive_metrics(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        if metrics_data is None:
            return
        self._collector.add_metrics_data(metrics_data)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._registry.unregister(self._collector)


class _CustomCollector:
    """_CustomCollector represents the Prometheus Collector object

    See more:
    https://github.com/prometheus/client_python#custom-collectors
    """

    def __init__(
        self,
        disable_target_info: bool = False,
        prefix: str = "",
        scope_info_enabled: bool = True,
        without_counter_suffixes: bool = False,
    ):
        self._callback = None
        self._metrics_datas: deque[MetricsData] = deque()
        self._disable_target_info = disable_target_info
        self._scope_info_enabled = scope_info_enabled
        self._without_counter_suffixes = without_counter_suffixes
        self._target_info = None
        self._prefix = prefix
        self._metric_name_to_type: dict[str, str] = {}

    def add_metrics_data(self, metrics_data: MetricsData) -> None:
        """Add metrics to Prometheus data"""
        self._metrics_datas.append(metrics_data)

    def collect(self) -> Iterable[PrometheusMetric]:
        """Collect fetches the metrics from OpenTelemetry
        and delivers them as Prometheus Metrics.
        Collect is invoked every time a ``prometheus.Gatherer`` is run
        for example when the HTTP endpoint is invoked by Prometheus.
        """
        if self._callback is not None:
            self._callback()

        metric_family_id_metric_family = {}
        # Track the Prometheus type chosen for each metric name during this
        # collection so conflicting-type families can be detected and dropped.
        self._metric_name_to_type: dict[str, str] = {}

        if len(self._metrics_datas):
            if not self._disable_target_info:
                if self._target_info is None:
                    attributes: Attributes = {}
                    for res in self._metrics_datas[0].resource_metrics:
                        attributes = {**attributes, **res.resource.attributes}

                    self._target_info = self._create_info_metric(
                        _TARGET_INFO_NAME, _TARGET_INFO_DESCRIPTION, attributes
                    )
                metric_family_id_metric_family[_TARGET_INFO_NAME] = (
                    self._target_info
                )

        while self._metrics_datas:
            self._translate_to_prometheus(
                self._metrics_datas.popleft(), metric_family_id_metric_family
            )

            if metric_family_id_metric_family:
                yield from metric_family_id_metric_family.values()

    def _translate_to_prometheus(
        self,
        metrics_data: MetricsData,
        metric_family_id_metric_family: dict[str, PrometheusMetric],
    ):
        for rm in metrics_data.resource_metrics:
            for sm in rm.scope_metrics:
                scope_attrs = self._build_scope_attrs(sm.scope)
                for metric in sm.metrics:
                    self._translate_metric(
                        metric,
                        scope_attrs,
                        metric_family_id_metric_family,
                    )

    def _translate_metric(
        self,
        metric: Metric,
        scope_attrs: dict[str, Any],
        metric_family_id_metric_family: dict[str, PrometheusMetric],
    ) -> None:
        metric_name = self._resolve_metric_name(metric.name)
        description = metric.description or ""
        unit = map_unit(metric.unit or "")

        convert_sum_to_gauge = _should_convert_sum_to_gauge(metric)

        if isinstance(metric.data, Sum) and not convert_sum_to_gauge:
            prometheus_type = "counter"
        elif isinstance(metric.data, Gauge) or convert_sum_to_gauge:
            prometheus_type = "gauge"
        elif isinstance(metric.data, Histogram):
            prometheus_type = "histogram"
        else:
            _logger.warning("Unsupported metric data. %s", type(metric.data))
            return

        # Prometheus does not allow two metric families that share a name but
        # have conflicting types. Keep the first type seen for a name and drop
        # any later metric of a different type, emitting a warning.
        existing_type = self._metric_name_to_type.get(metric_name)
        if existing_type is None:
            self._metric_name_to_type[metric_name] = prometheus_type
        elif existing_type != prometheus_type:
            _logger.warning(
                "Dropping metric '%s' with type '%s' because a metric with "
                "the same name and conflicting type '%s' was already exported.",
                metric_name,
                prometheus_type,
                existing_type,
            )
            return

        label_keys, label_rows, values, exemplars = self._collect_data_points(
            metric.data, scope_attrs
        )
        per_metric_family_id = "|".join((metric_name, description, unit))

        if prometheus_type == "counter":
            _populate_counter_family(
                registry=metric_family_id_metric_family,
                per_metric_family_id=per_metric_family_id,
                metric_name=metric_name,
                description=description,
                unit=unit,
                label_keys=label_keys,
                label_rows=label_rows,
                values=values,
                exemplars=exemplars,
                without_counter_suffixes=self._without_counter_suffixes,
            )
        elif prometheus_type == "gauge":
            _populate_gauge_family(
                registry=metric_family_id_metric_family,
                per_metric_family_id=per_metric_family_id,
                metric_name=metric_name,
                description=description,
                unit=unit,
                label_keys=label_keys,
                label_rows=label_rows,
                values=values,
            )
        else:
            _populate_histogram_family(
                registry=metric_family_id_metric_family,
                per_metric_family_id=per_metric_family_id,
                metric_name=metric_name,
                description=description,
                unit=unit,
                label_keys=label_keys,
                label_rows=label_rows,
                values=values,
                exemplars=exemplars,
            )

    def _build_scope_attrs(
        self, scope: InstrumentationScope
    ) -> dict[str, AttributeValue]:
        if not self._scope_info_enabled:
            return {}
        attrs: dict[str, AttributeValue] = {}
        if scope.attributes:
            for key, value in scope.attributes.items():
                attrs[_OTEL_SCOPE_ATTR_PREFIX + key] = value
        attrs[_OTEL_SCOPE_NAME_LABEL] = scope.name or ""
        attrs[_OTEL_SCOPE_VERSION_LABEL] = scope.version or ""
        attrs[_OTEL_SCOPE_SCHEMA_URL_LABEL] = scope.schema_url or ""
        return attrs

    def _resolve_metric_name(self, name: str) -> str:
        if self._prefix:
            name = self._prefix + "_" + name
        return sanitize_full_name(name)

    def _collect_data_points(
        self,
        metric_data: DataT,
        scope_attrs: dict[str, AttributeValue],
    ) -> tuple[
        list[str],
        list[list[str]],
        list[float | dict[str, Any]],
        list[PrometheusExemplar | None],
    ]:
        keys: set[str] = set()
        rows: list[dict[str, str]] = []
        values: list[float | dict[str, Any]] = []
        exemplars: list[PrometheusExemplar | None] = []

        # Reserved scope labels are supplied by the scope and must never be
        # overwritten by data point attributes that sanitize to the same name.
        reserved_scope_labels = _RESERVED_SCOPE_LABELS & set(
            scope_attrs.keys()
        )

        for point in metric_data.data_points:
            # Multiple original attribute keys may sanitize to the same
            # Prometheus label. Accumulate the value of every colliding key so
            # they can be merged instead of silently overwriting one another.
            label_values_by_key: dict[str, dict[str, str]] = {}
            for from_scope, (key, value) in chain(
                ((True, item) for item in scope_attrs.items()),
                ((False, item) for item in point.attributes.items()),
            ):
                label = sanitize_attribute(key)
                if not from_scope and label in reserved_scope_labels:
                    # A data point attribute collides with a reserved
                    # otel_scope_* label; skip it in favor of the scope value.
                    continue
                keys.add(label)
                label_values_by_key.setdefault(label, {})[key] = (
                    self._check_value(value)
                )

            labels: dict[str, str] = {}
            for label, original_key_values in label_values_by_key.items():
                labels[label] = ";".join(
                    original_key_values[original_key]
                    for original_key in sorted(original_key_values)
                )
            rows.append(labels)

            if isinstance(point, HistogramDataPoint):
                values.append(
                    {
                        "bucket_counts": point.bucket_counts,
                        "explicit_bounds": point.explicit_bounds,
                        "sum": point.sum,
                    }
                )
            else:
                values.append(point.value)

            exemplars.append(
                _first_exemplar(getattr(point, "exemplars", None))
            )

        label_keys = sorted(keys)
        # Backfill missing labels with "" so every data point exposes the
        # full label set expected by the Prometheus family.
        label_rows = [
            [labels.get(k, "") for k in label_keys] for labels in rows
        ]
        return label_keys, label_rows, values, exemplars

    # pylint: disable=no-self-use
    def _check_value(self, value: int | float | str | Sequence) -> str:
        """Check the label value and return is appropriate representation"""
        if not isinstance(value, str):
            return dumps(value, default=str)
        return str(value)

    def _create_info_metric(
        self, name: str, description: str, attributes: dict[str, str]
    ) -> InfoMetricFamily:
        """Create an Info Metric Family with list of attributes"""
        # sanitize the attribute names according to Prometheus rule
        attributes = {
            sanitize_attribute(key): self._check_value(value)
            for key, value in attributes.items()
        }
        info = InfoMetricFamily(name, description, labels=attributes)
        info.add_metric(labels=list(attributes.keys()), value=attributes)
        return info


class _AutoPrometheusMetricReader(PrometheusMetricReader):
    """Thin wrapper around PrometheusMetricReader used for the opentelemetry_metrics_exporter entry point.

    This allows users to use the prometheus exporter with opentelemetry-instrument. It handles
    starting the Prometheus http server on the the correct port and host.
    """

    def __init__(self) -> None:
        super().__init__()

        # Default values are specified in
        # https://github.com/open-telemetry/opentelemetry-specification/blob/v1.24.0/specification/configuration/sdk-environment-variables.md#prometheus-exporter
        start_http_server(
            port=int(environ.get(OTEL_EXPORTER_PROMETHEUS_PORT, "9464")),
            addr=environ.get(OTEL_EXPORTER_PROMETHEUS_HOST, "localhost"),
        )
