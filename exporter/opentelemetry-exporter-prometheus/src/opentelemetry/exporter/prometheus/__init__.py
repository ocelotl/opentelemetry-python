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
from collections.abc import Callable, Iterable, Mapping, Sequence
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
from prometheus_client.core import Metric as PrometheusMetric

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
    CardinalityLimits,
    DataT,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    MetricReader,
    MetricsData,
    Sum,
)
from opentelemetry.sdk.metrics.view import Aggregation
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.util.types import AnyValue, Attributes

_logger = getLogger(__name__)

_TARGET_INFO_NAME = "target"
_TARGET_INFO_DESCRIPTION = "Target metadata"

_DEFAULT_PORT = 9464


def _port_from_env() -> int:
    """Return ``OTEL_EXPORTER_PROMETHEUS_PORT`` as an int, defaulting to
    ``_DEFAULT_PORT`` when the variable is unset, empty, or not an integer.

    An invalid value is logged and ignored instead of raising, mirroring the
    OTLP/Zipkin exporters so a malformed environment variable cannot take
    auto-instrumentation startup down.

    Returns:
        The port the Prometheus HTTP server binds to. That is the integer
        parsed from the environment variable, or ``9464`` when the variable is
        unset, holds only whitespace, or does not parse as an integer. A value
        that parses but is outside the range of a TCP port is returned as it
        stands, and the failure surfaces later when the server binds.
    """
    raw = environ.get(OTEL_EXPORTER_PROMETHEUS_PORT)
    if raw is None or not raw.strip():
        return _DEFAULT_PORT
    try:
        return int(raw)
    except ValueError:
        _logger.warning(
            "Invalid value %r for %s, using default port %s",
            raw,
            OTEL_EXPORTER_PROMETHEUS_PORT,
            _DEFAULT_PORT,
        )
        return _DEFAULT_PORT


_OTEL_SCOPE_NAME_LABEL = "otel_scope_name"
_OTEL_SCOPE_VERSION_LABEL = "otel_scope_version"
_OTEL_SCOPE_SCHEMA_URL_LABEL = "otel_scope_schema_url"
_OTEL_SCOPE_ATTR_PREFIX = "otel_scope_"


def _convert_buckets(bucket_counts: Sequence[int], explicit_bounds: Sequence[float]) -> Sequence[tuple[str, int]]:
    """Turn the per-bucket counts of an OpenTelemetry histogram into cumulative Prometheus buckets.

    A Prometheus bucket reports how many observations fall at or below its
    upper bound, so each count returned here is the running total of every
    bucket up to and including the current one. The open-ended bucket above the
    last explicit bound is labelled ``+Inf``.

    Args:
        bucket_counts: The number of observations recorded in each bucket, in
            the order ``HistogramDataPoint`` holds them. It has one entry more
            than ``explicit_bounds``, the extra one being the open-ended bucket.
        explicit_bounds: The inclusive upper bound of every bucket except the
            open-ended one, in ascending order.

    Returns:
        One pair per bucket, holding the upper bound rendered as a string and
        the cumulative count of observations at or below it. The two arguments
        are paired positionally and pairing stops at the shorter of them, so a
        ``bucket_counts`` with fewer entries than expected drops the trailing
        buckets without an error.
    """
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
    """Report whether a metric carrying a Sum has to be exported as a Prometheus gauge.

    Args:
        metric: The metric about to be translated. Its ``data`` decides the
            answer and metrics carrying anything other than a ``Sum`` are
            rejected outright.

    Returns:
        ``True`` when the metric carries a ``Sum`` that is non-monotonic and
        cumulative, which a Prometheus counter cannot represent because a
        counter only increases. ``False`` otherwise, including for a
        non-monotonic ``Sum`` with delta temporality.
    """
    # The Prometheus compatibility spec requires cumulative non-monotonic Sums
    # to be exported as Gauges.
    if not isinstance(metric.data, Sum):
        return False
    return not metric.data.is_monotonic and metric.data.aggregation_temporality == AggregationTemporality.CUMULATIVE


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
    """Return the Prometheus metric family stored under ``family_id``, creating it when absent.

    A single scrape can contribute many data points to one family, and
    ``prometheus_client`` expects the family to be built once and then fed
    sample by sample. The first call for a given ``family_id`` constructs the
    family and stores it. Every later call ignores the construction arguments
    it was passed and hands back the stored family, so a second call that
    disagrees about the labels or the unit is silently ignored.

    Args:
        registry: The mapping from family identifier to family being assembled
            for the scrape in progress. It is modified in place.
        family_id: The key the family is stored under.
        factory: The ``prometheus_client`` family class to construct when the
            key is absent, such as ``CounterMetricFamily``.
        name: The sanitized Prometheus metric name.
        documentation: The description of the metric, empty when the instrument
            carries none.
        labels: The label names the family declares. Every sample added to the
            family has to supply a value for each of them, in this order.
        unit: The Prometheus spelling of the unit, which
            ``prometheus_client`` appends to the metric name. An empty string
            adds no suffix.

    Returns:
        The family held under ``family_id``, whether this call created it or
        found it already there.
    """
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
) -> None:
    """Add one sample per data point to the Prometheus counter family of a metric.

    Args:
        registry: The mapping from family identifier to family being assembled
            for the scrape in progress. It is modified in place.
        per_metric_family_id: The identifier shared by every family of this
            metric, built from its name, description and unit. The name of the
            family class is appended to it here, which keeps a metric that
            yields a counter apart from one that yields a gauge or a histogram.
        metric_name: The sanitized Prometheus metric name.
        description: The description of the metric, empty when the instrument
            carries none.
        unit: The Prometheus spelling of the unit.
        label_keys: The label names the family declares.
        label_rows: One row of label values per data point, each row ordered to
            match ``label_keys``.
        values: The value of each data point, paired positionally with
            ``label_rows``.
    """
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
    for label_values, value in zip(label_rows, values):
        family.add_metric(labels=label_values, value=value)


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
    """Add one sample per data point to the Prometheus gauge family of a metric.

    Both a ``Gauge`` and a cumulative non-monotonic ``Sum`` are exported this
    way, the latter because a Prometheus counter cannot decrease.

    Args:
        registry: The mapping from family identifier to family being assembled
            for the scrape in progress. It is modified in place.
        per_metric_family_id: The identifier shared by every family of this
            metric, built from its name, description and unit. The name of the
            family class is appended to it here, which keeps a metric that
            yields a gauge apart from one that yields a counter or a histogram.
        metric_name: The sanitized Prometheus metric name.
        description: The description of the metric, empty when the instrument
            carries none.
        unit: The Prometheus spelling of the unit.
        label_keys: The label names the family declares.
        label_rows: One row of label values per data point, each row ordered to
            match ``label_keys``.
        values: The value of each data point, paired positionally with
            ``label_rows``.
    """
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
) -> None:
    """Add one sample per data point to the Prometheus histogram family of a metric.

    Args:
        registry: The mapping from family identifier to family being assembled
            for the scrape in progress. It is modified in place.
        per_metric_family_id: The identifier shared by every family of this
            metric, built from its name, description and unit. The name of the
            family class is appended to it here, which keeps a metric that
            yields a histogram apart from one that yields a counter or a gauge.
        metric_name: The sanitized Prometheus metric name.
        description: The description of the metric, empty when the instrument
            carries none.
        unit: The Prometheus spelling of the unit.
        label_keys: The label names the family declares.
        label_rows: One row of label values per data point, each row ordered to
            match ``label_keys``.
        values: One mapping per data point, paired positionally with
            ``label_rows``. Each holds the keys ``bucket_counts``,
            ``explicit_bounds`` and ``sum``, taken from the
            ``HistogramDataPoint`` the mapping was built from. The bucket
            counts are made cumulative before the sample is added, and the
            ``_count`` series is left for ``prometheus_client`` to derive from
            the ``+Inf`` bucket. ``prometheus_client`` drops both ``_count``
            and ``_sum`` when ``sum`` is ``None`` or when the lowest explicit
            bound is negative, so such a histogram exports its buckets alone.
    """
    family_id = "|".join([per_metric_family_id, HistogramMetricFamily.__name__])
    family = _get_or_create_family(
        registry,
        family_id,
        HistogramMetricFamily,
        name=metric_name,
        documentation=description,
        labels=label_keys,
        unit=unit,
    )
    for label_values, value in zip(label_rows, values):
        family.add_metric(
            labels=label_values,
            buckets=_convert_buckets(value["bucket_counts"], value["explicit_bounds"]),
            sum_value=value["sum"],
        )


class PrometheusMetricReader(MetricReader):
    """Prometheus metric exporter for OpenTelemetry.

    Constructing the reader registers a ``prometheus_client`` collector on a
    Prometheus registry, so no metric is produced until something scrapes that
    registry. Each scrape calls back into the SDK for a fresh collection,
    translates the result into Prometheus metric families and serves them.
    This reader does not serve HTTP itself: start a server with
    ``prometheus_client.start_http_server``, or let ``opentelemetry-instrument``
    do it, which uses the entry point backed by ``_AutoPrometheusMetricReader``.

    Every instrument is read with cumulative temporality, which is the only
    temporality Prometheus can represent, and that choice cannot be overridden.

    Args:
        disable_target_info: Whether to disable the ``target_info`` metric.
        prefix: Prefix added to exported Prometheus metric names.
        scope_info_enabled: Whether to include instrumentation scope labels on
            exported metrics. Scope labels are exported by default.
        preferred_aggregation: A mapping between instrument classes and
            aggregation instances used to override the default aggregation of
            the corresponding instrument classes. Classes not included in the
            mapping retain their default aggregation. See
            :class:`~opentelemetry.sdk.metrics.export.MetricReader` for details.
        resource_attribute_filter: Optional callback to select resource attributes
            that are copied as labels on exported metrics. The callback receives
            the original resource attribute key. Selected keys are sanitized to
            valid Prometheus label names.
        registry: The ``prometheus_client`` registry the collector is
            registered on. It defaults to the process-wide default registry,
            which is the one ``prometheus_client.start_http_server`` serves.
            Pass a separate ``CollectorRegistry`` to keep these metrics off
            that endpoint, for example to serve two meter providers on two
            different ports.
        cardinality_limits: A mapping between instrument classes and the
            maximum number of metric points a metric stream of that class may
            export per collection cycle. Classes not included in the mapping
            use a limit of 2000. See
            :class:`~opentelemetry.sdk.metrics.export.MetricReader` for details.
    """

    def __init__(
        self,
        disable_target_info: bool = False,
        prefix: str = "",
        scope_info_enabled: bool = True,
        preferred_aggregation: Mapping[type, Aggregation] | None = None,
        *,
        resource_attribute_filter: Callable[[str], bool] | None = None,
        registry: CollectorRegistry = REGISTRY,
        cardinality_limits: CardinalityLimits | None = None,
    ) -> None:
        """Register a Prometheus collector that serves this reader.

        The parameters are documented on the class, which is what the API
        reference renders.
        """
        super().__init__(
            preferred_temporality={
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                HistogramInstrument: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            },
            preferred_aggregation=dict(preferred_aggregation) if preferred_aggregation is not None else None,
            cardinality_limits=cardinality_limits,
            otel_component_type=OtelComponentTypeValues.PROMETHEUS_HTTP_TEXT_METRIC_EXPORTER,
        )
        self._collector = _CustomCollector(
            disable_target_info=disable_target_info,
            prefix=prefix,
            scope_info_enabled=scope_info_enabled,
            resource_attribute_filter=resource_attribute_filter,
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
        """Hand a freshly collected batch of metrics to the Prometheus collector.

        ``MetricReader.collect`` calls this from inside the scrape that the
        collector started, so the batch is queued and then drained by that same
        scrape.

        Args:
            metrics_data: The metrics the SDK collected. The SDK path never
                delivers ``None``, because ``MetricReader.collect`` drops that
                case before calling here, so the guard below only matters to a
                caller invoking this method directly.
            timeout_millis: Accepted for the signature of
                :class:`~opentelemetry.sdk.metrics.export.MetricReader` and
                ignored, because queueing the batch does no blocking work.
            kwargs: Accepted for the same reason and ignored.
        """
        if metrics_data is None:
            return
        self._collector.add_metrics_data(metrics_data)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Unregister the collector, so later scrapes no longer report these metrics.

        Any batch still queued on the collector is dropped with it. No HTTP
        server is stopped, including the one ``_AutoPrometheusMetricReader``
        starts, because serving is not this reader's responsibility.

        Args:
            timeout_millis: Accepted for the signature of
                :class:`~opentelemetry.sdk.metrics.export.MetricReader` and
                ignored, because unregistering does no blocking work.
            kwargs: Accepted for the same reason and ignored.

        Raises:
            KeyError: If the collector is no longer on the registry, which
                happens when this method is called a second time directly.
                Shutting the meter provider down instead is guarded against
                that and calls this once.
        """
        self._registry.unregister(self._collector)


class _CustomCollector:
    """_CustomCollector represents the Prometheus Collector object

    See more:
    https://github.com/prometheus/client_python#custom-collectors

    ``prometheus_client`` calls ``collect`` on every registered collector each
    time the registry is scraped. This one answers by calling back into
    :class:`PrometheusMetricReader`, which collects from the SDK and queues the
    result here, and then translates the queue into Prometheus metric families.
    Holding a queue rather than a single batch means a batch delivered outside
    a scrape is kept until the next one.

    Args:
        disable_target_info: Whether to leave out the ``target_info`` metric
            that carries the resource attributes. When it is left in, the
            attributes are read once, from the first batch ever queued, and the
            metric is reused for the lifetime of the collector. It is built
            apart from the instrument metrics, so none of the three options
            below reaches it: its name never carries the prefix, it never
            carries scope labels, and it carries the resource attributes whole
            whatever the resource attribute filter says.
        prefix: String placed in front of the name of every metric translated
            from an instrument, joined to it with an underscore. An empty
            string adds nothing.
        scope_info_enabled: Whether to label every metric translated from an
            instrument with the instrumentation scope it came from.
        resource_attribute_filter: Callback deciding which resource attributes
            are copied as labels onto every metric translated from an
            instrument. It receives the unsanitized attribute key. ``None``
            copies none of them, which leaves the resource visible only through
            ``target_info``.
    """

    def __init__(
        self,
        disable_target_info: bool = False,
        prefix: str = "",
        scope_info_enabled: bool = True,
        resource_attribute_filter: Callable[[str], bool] | None = None,
    ):
        """Build a collector with an empty queue and no callback.

        The parameters are documented on the class. The callback is not one of
        them: :class:`PrometheusMetricReader` assigns it to ``_callback`` after
        constructing the collector.
        """
        self._callback = None
        self._metrics_datas: deque[MetricsData] = deque()
        self._disable_target_info = disable_target_info
        self._target_info = None
        self._prefix = prefix
        self._scope_info_enabled = scope_info_enabled
        self._resource_attribute_filter = resource_attribute_filter

    def add_metrics_data(self, metrics_data: MetricsData) -> None:
        """Add metrics to Prometheus data

        Args:
            metrics_data: A batch of metrics the SDK collected. It is queued as
                it stands and translated by the next ``collect``, so nothing is
                validated here and nothing bounds the queue if no scrape ever
                arrives.
        """
        self._metrics_datas.append(metrics_data)

    def collect(self) -> Iterable[PrometheusMetric]:
        """Collect fetches the metrics from OpenTelemetry
        and delivers them as Prometheus Metrics.
        Collect is invoked every time a ``prometheus.Gatherer`` is run
        for example when the HTTP endpoint is invoked by Prometheus.

        The callback installed by :class:`PrometheusMetricReader` runs first,
        which collects from the SDK and queues one batch, and the queue is then
        drained batch by batch into one shared set of metric families.

        Returns:
            A generator over the Prometheus metric families built from every
            queued batch, with ``target_info`` first when the collector was not
            told to leave it out. Nothing is produced while the queue is empty,
            so a scrape that arrives before the first collection reports no
            metrics at all. The families are yielded once per queued batch
            rather than once in total, so a queue holding more than one batch
            repeats the families built by the earlier ones.
        """
        if self._callback is not None:
            self._callback()

        metric_family_id_metric_family = {}

        if len(self._metrics_datas):
            if not self._disable_target_info:
                if self._target_info is None:
                    attributes: Attributes = {}
                    for res in self._metrics_datas[0].resource_metrics:
                        attributes = {**attributes, **res.resource.attributes}

                    self._target_info = self._create_info_metric(
                        _TARGET_INFO_NAME, _TARGET_INFO_DESCRIPTION, attributes
                    )
                metric_family_id_metric_family[_TARGET_INFO_NAME] = self._target_info

        while self._metrics_datas:
            self._translate_to_prometheus(self._metrics_datas.popleft(), metric_family_id_metric_family)

            if metric_family_id_metric_family:
                yield from metric_family_id_metric_family.values()

    def _translate_to_prometheus(
        self,
        metrics_data: MetricsData,
        metric_family_id_metric_family: dict[str, PrometheusMetric],
    ):
        """Translate one batch of SDK metrics into Prometheus metric families.

        The resource labels and the scope labels are computed once per resource
        and once per scope, then shared by every metric underneath, because
        they are the same for all of them.

        Args:
            metrics_data: A batch of metrics taken off the queue.
            metric_family_id_metric_family: The families being assembled for
                the scrape in progress. It is modified in place, and it is
                shared across batches so that two batches carrying the same
                metric contribute samples to one family.
        """
        for rm in metrics_data.resource_metrics:
            resource_attrs = self._build_resource_attrs(rm.resource)
            for sm in rm.scope_metrics:
                scope_attrs = self._build_scope_attrs(sm.scope)
                for metric in sm.metrics:
                    self._translate_metric(
                        metric=metric,
                        scope_attrs=scope_attrs,
                        resource_attrs=resource_attrs,
                        metric_family_id_metric_family=metric_family_id_metric_family,
                    )

    def _translate_metric(
        self,
        metric: Metric,
        scope_attrs: dict[str, AnyValue],
        resource_attrs: dict[str, AnyValue],
        metric_family_id_metric_family: dict[str, PrometheusMetric],
    ) -> None:
        """Add one metric to the Prometheus family that matches its data type.

        A ``Sum`` becomes a Prometheus counter unless it is cumulative and
        non-monotonic, in which case it becomes a gauge. A ``Gauge`` becomes a
        gauge and a ``Histogram`` becomes a histogram. Any other data type is
        logged at warning level and dropped, because Prometheus text format
        has nothing to map it onto, but only when it carries no data point:
        ``_collect_data_points`` runs before the choice is made and raises
        ``AttributeError`` on a data point that is neither a
        ``NumberDataPoint`` nor a ``HistogramDataPoint``, which is what an
        ``ExponentialHistogram`` holds.

        Args:
            metric: The metric to translate. Its name is prefixed and
                sanitized, its description defaults to the empty string, and
                its unit is mapped to the Prometheus spelling.
            scope_attrs: The labels describing the instrumentation scope the
                metric came from, empty when scope labels are switched off.
            resource_attrs: The labels copied from the resource, empty when no
                resource attribute filter was given.
            metric_family_id_metric_family: The families being assembled for
                the scrape in progress. It is modified in place.
        """
        metric_name = self._resolve_metric_name(metric.name)
        description = metric.description or ""
        unit = map_unit(metric.unit or "")
        label_keys, label_rows, values = self._collect_data_points(metric.data, scope_attrs, resource_attrs)
        per_metric_family_id = "|".join((metric_name, description, unit))

        convert_sum_to_gauge = _should_convert_sum_to_gauge(metric)

        if isinstance(metric.data, Sum) and not convert_sum_to_gauge:
            _populate_counter_family(
                registry=metric_family_id_metric_family,
                per_metric_family_id=per_metric_family_id,
                metric_name=metric_name,
                description=description,
                unit=unit,
                label_keys=label_keys,
                label_rows=label_rows,
                values=values,
            )
        elif isinstance(metric.data, Gauge) or convert_sum_to_gauge:
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
        elif isinstance(metric.data, Histogram):
            _populate_histogram_family(
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
            _logger.warning("Unsupported metric data. %s", type(metric.data))

    def _build_scope_attrs(self, scope: InstrumentationScope) -> dict[str, AnyValue]:
        """Build the labels that identify the instrumentation scope of a metric.

        Args:
            scope: The instrumentation scope the metrics were recorded under.

        Returns:
            An empty mapping when scope labels are switched off. Otherwise a
            mapping holding ``otel_scope_name``, ``otel_scope_version`` and
            ``otel_scope_schema_url``, each falling back to the empty string
            when the scope leaves it unset, plus one entry per scope attribute
            with ``otel_scope_`` in front of its key. A scope attribute named
            ``name``, ``version`` or ``schema_url`` collides with one of the
            three fixed keys and loses to it. The keys are sanitized later,
            along with the data point attributes.
        """
        if not self._scope_info_enabled:
            return {}
        attrs: dict[str, AnyValue] = {}
        if scope.attributes:
            for key, value in scope.attributes.items():
                attrs[_OTEL_SCOPE_ATTR_PREFIX + key] = value
        attrs[_OTEL_SCOPE_NAME_LABEL] = scope.name or ""
        attrs[_OTEL_SCOPE_VERSION_LABEL] = scope.version or ""
        attrs[_OTEL_SCOPE_SCHEMA_URL_LABEL] = scope.schema_url or ""
        return attrs

    def _build_resource_attrs(self, resource: Resource) -> dict[str, AnyValue]:
        """Select the resource attributes that become labels on every translated metric.

        Args:
            resource: The resource of the meter provider the metrics came from.

        Returns:
            An empty mapping when no resource attribute filter was configured,
            which is the default and leaves the resource reported only by
            ``target_info``. Otherwise the attributes the filter accepted, with
            their keys still unsanitized. A scope label or a data point
            attribute that sanitizes to the same label name takes precedence
            over the resource attribute. ``target_info`` is built elsewhere and
            carries the resource attributes whole, so the filter never narrows
            what it reports.
        """
        if not self._resource_attribute_filter:
            return {}
        return {key: value for key, value in resource.attributes.items() if self._resource_attribute_filter(key)}

    def _resolve_metric_name(self, name: str) -> str:
        """Apply the configured prefix to a metric name and sanitize the result.

        Args:
            name: The metric name as recorded through the OpenTelemetry API.

        Returns:
            The name with the configured prefix and an underscore in front of
            it, sanitized into a valid Prometheus metric name. The prefix is
            applied before sanitizing, so a prefix containing a character
            Prometheus rejects is rewritten rather than refused.
        """
        if self._prefix:
            name = self._prefix + "_" + name
        return sanitize_full_name(name)

    def _collect_data_points(
        self,
        metric_data: DataT,
        scope_attrs: dict[str, AnyValue],
        resource_attrs: dict[str, AnyValue],
    ) -> tuple[list[str], list[list[str]], list[float | dict[str, Any]]]:
        """Flatten the data points of a metric into a Prometheus label set and value list.

        Prometheus requires every sample of a family to carry the same label
        names, while OpenTelemetry lets each data point carry its own
        attributes. The union of the label names is taken here and every row is
        filled out against it.

        Args:
            metric_data: The ``Sum``, ``Gauge`` or ``Histogram`` holding the
                data points.
            scope_attrs: The instrumentation scope labels to add to every data
                point.
            resource_attrs: The resource labels to add to every data point.

        Returns:
            Three parallel structures. The first is the sorted list of
            sanitized label names, the union over all data points. The second
            holds one row of label values per data point, in the order of that
            list, with the empty string wherever a data point did not carry the
            attribute. The third holds one value per data point: a number for a
            ``NumberDataPoint``, and a mapping of ``bucket_counts``,
            ``explicit_bounds`` and ``sum`` for a ``HistogramDataPoint``.
            Resource, scope and data point attributes are merged in that order,
            so a later one wins when two of them sanitize to the same label
            name.

        Raises:
            AttributeError: If a data point is of neither of those two kinds,
                since the value is then read from a field the point does not
                have. An ``ExponentialHistogramDataPoint`` is the case that
                reaches this.
        """
        keys: set[str] = set()
        rows: list[dict[str, str]] = []
        values: list[float | dict[str, Any]] = []

        for point in metric_data.data_points:
            labels: dict[str, str] = {}
            for key, value in chain(
                resource_attrs.items(),
                scope_attrs.items(),
                point.attributes.items(),
            ):
                label = sanitize_attribute(key)
                keys.add(label)
                labels[label] = self._check_value(value)
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

        label_keys = sorted(keys)
        # Backfill missing labels with "" so every data point exposes the
        # full label set expected by the Prometheus family.
        label_rows = [[labels.get(k, "") for k in label_keys] for labels in rows]
        return label_keys, label_rows, values

    # pylint: disable=no-self-use
    def _check_value(self, value: float | str | Sequence) -> str:
        """Check the label value and return is appropriate representation

        Args:
            value: An attribute value taken from a data point, from an
                instrumentation scope or from the resource.

        Returns:
            The value as a Prometheus label value, which can only be a string.
            A string is returned unchanged. Anything else is serialized as
            JSON, so a sequence becomes ``["a", "b"]``, a boolean becomes
            ``true`` or ``false`` and ``None`` becomes ``null``. A value JSON
            cannot represent falls back to its ``str``.
        """
        if not isinstance(value, str):
            return dumps(value, default=str)
        return str(value)

    def _create_info_metric(self, name: str, description: str, attributes: dict[str, str]) -> InfoMetricFamily:
        """Create an Info Metric Family with list of attributes

        Args:
            name: The metric name without the ``_info`` suffix that
                ``prometheus_client`` appends. The only caller passes
                ``target``, which produces ``target_info``.
            description: The description of the metric.
            attributes: The resource attributes to carry as labels. Their keys
                are sanitized into valid Prometheus label names here, and two
                keys that sanitize to the same name leave only the later one.

        Returns:
            An info family holding one sample, whose value is the constant 1
            and whose labels are the sanitized attributes. The information is
            in the labels, which is how Prometheus carries metadata that has no
            numeric value of its own.
        """
        # sanitize the attribute names according to Prometheus rule
        attributes = {sanitize_attribute(key): self._check_value(value) for key, value in attributes.items()}
        info = InfoMetricFamily(name, description, labels=attributes)
        info.add_metric(labels=list(attributes.keys()), value=attributes)
        return info


class _AutoPrometheusMetricReader(PrometheusMetricReader):
    """Thin wrapper around PrometheusMetricReader used for the opentelemetry_metrics_exporter entry point.

    This allows users to use the prometheus exporter with opentelemetry-instrument. It handles
    starting the Prometheus http server on the correct port and host.

    Every option of :class:`PrometheusMetricReader` keeps its default here,
    because an entry point is constructed with no arguments. The host and the
    port are the only things configurable, through
    ``OTEL_EXPORTER_PROMETHEUS_HOST`` and ``OTEL_EXPORTER_PROMETHEUS_PORT``.
    """

    def __init__(self) -> None:
        """Register the collector and start a Prometheus HTTP server.

        The server binds to ``OTEL_EXPORTER_PROMETHEUS_HOST``, defaulting to
        ``localhost``, and to the port ``_port_from_env`` resolves. It runs on
        a daemon thread that nothing here stops, so it outlives a call to
        ``shutdown``.
        """
        super().__init__()

        # Default values are specified in
        # https://github.com/open-telemetry/opentelemetry-specification/blob/v1.24.0/specification/configuration/sdk-environment-variables.md#prometheus-exporter
        start_http_server(
            port=_port_from_env(),
            addr=environ.get(OTEL_EXPORTER_PROMETHEUS_HOST, "localhost"),
        )
