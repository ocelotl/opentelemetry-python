# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# type: ignore[reportArgumentType]
# pyright: reportCallIssue=false

"""Encoding of SDK metrics into OTLP JSON metrics messages.

``encode_metrics`` is the entry point and is re-exported from
``opentelemetry.exporter.otlp.json.common.metrics_encoder``, which is where a
metric exporter should import it from. The rest of this module is private.

The grouping by resource and by instrumentation scope that the trace and log
encoders have to rebuild is already present in ``MetricsData``, so the encoding
here is a direct walk of that structure. The extra work is in
``split_metrics_data``, which cuts an encoded request into smaller requests
when a receiver limits how many data points one request may carry.

``_METRIC_DATA_FIELDS`` names the five mutually exclusive fields of an OTLP
``Metric`` that hold data points. ``encode_metrics`` produces four of them: a
summary is a legacy type that the SDK does not aggregate to, so nothing here
writes one, but ``split_metrics_data`` still handles it for a request built
elsewhere.
"""

from __future__ import annotations

import logging
from collections.abc import Collection, Iterable
from dataclasses import replace
from typing import TYPE_CHECKING

from opentelemetry.exporter.otlp.json.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry.proto_json.collector.metrics.v1.metrics_service import (
    ExportMetricsServiceRequest as JSONExportMetricsServiceRequest,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    Exemplar as JSONExemplar,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ExponentialHistogram as JSONExponentialHistogram,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ExponentialHistogramDataPoint as JSONExponentialHistogramDataPoint,
)
from opentelemetry.proto_json.metrics.v1.metrics import Gauge as JSONGauge
from opentelemetry.proto_json.metrics.v1.metrics import (
    Histogram as JSONHistogram,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    HistogramDataPoint as JSONHistogramDataPoint,
)
from opentelemetry.proto_json.metrics.v1.metrics import Metric as JSONMetric
from opentelemetry.proto_json.metrics.v1.metrics import (
    NumberDataPoint as JSONNumberDataPoint,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ResourceMetrics as JSONResourceMetrics,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ScopeMetrics as JSONScopeMetrics,
)
from opentelemetry.proto_json.metrics.v1.metrics import Sum as JSONSum
from opentelemetry.proto_json.resource.v1.resource import (
    Resource as JSONResource,
)
from opentelemetry.sdk.metrics import (
    Exemplar,
)
from opentelemetry.sdk.metrics._internal.point import (
    ExponentialHistogramDataPoint,
    HistogramDataPoint,
    Metric,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.export import (
    ExponentialHistogram,
    Gauge,
    Histogram,
    MetricsData,
    Sum,
)

if TYPE_CHECKING:
    from typing_extensions import assert_never

_logger = logging.getLogger(__name__)

_METRIC_DATA_FIELDS = (
    "gauge",
    "sum",
    "histogram",
    "exponential_histogram",
    "summary",
)


def encode_metrics(data: MetricsData) -> JSONExportMetricsServiceRequest:
    """Encode collected SDK metrics as an OTLP export request.

    Args:
        data: the metrics a metric reader collected, already grouped by
            resource and by instrumentation scope.

    Returns:
        An ``ExportMetricsServiceRequest`` mirroring the grouping of ``data``,
        one ``ResourceMetrics`` per entry and in the same order. A metric whose
        aggregated data is of a type this encoder does not recognise is logged
        as a warning and encoded with its name, description and unit but no
        data points.

    Raises:
        ValueError: if an exemplar carries a value that is neither an ``int``
            nor a ``float``.
    """
    return JSONExportMetricsServiceRequest(
        resource_metrics=[_encode_resource_metrics(rm) for rm in data.resource_metrics]
    )


# pylint: disable-next=too-many-locals
def split_metrics_data(
    metrics_data: JSONExportMetricsServiceRequest,
    max_export_batch_size: int | None,
) -> Iterable[JSONExportMetricsServiceRequest]:
    """Split an ExportMetricsServiceRequest into batches of at most
    max_export_batch_size data points, preserving resource/scope hierarchy.

    That limit holds only for a ``max_export_batch_size`` above zero. ``None``
    hands the request back unsplit, whatever it holds, and a value of zero or
    less puts one data point in each batch.

    Every batch repeats the resource and the instrumentation scope that its
    data points belong to, so each one is a request a receiver can accept on
    its own. A metric whose data points span a batch boundary appears in both
    batches, each time carrying only the data points of that batch.

    When ``max_export_batch_size`` is not ``None``, a metric that has none of
    the five data fields set, and a metric whose data field holds no data
    points, are both logged as a warning and left out of every batch. Neither
    check runs on the unlimited path, which hands ``metrics_data`` back
    untouched.

    Args:
        metrics_data: the encoded request to split. It is read but never
            modified, and the batches reuse its messages rather than copying
            their contents.
        max_export_batch_size: the largest number of data points a batch may
            carry. ``None`` means no limit. A value of zero or less puts one
            data point in each batch.

    Yields:
        One ``ExportMetricsServiceRequest`` per batch. With
        ``max_export_batch_size`` of ``None`` that is ``metrics_data`` itself,
        unchanged and yielded once, even when it holds no data points at all.
        For a ``max_export_batch_size`` above zero, every batch but the last
        carries exactly that many data points, and a ``metrics_data`` holding
        no data points at all yields nothing.
    """
    if max_export_batch_size is None:
        yield metrics_data
        return

    batch_size: int = 0
    resource_metrics_batch: list[JSONResourceMetrics] = []
    scope_metrics_batch: list[JSONScopeMetrics] = []
    metrics_batch: list[JSONMetric] = []

    for (
        resource_metrics,
        scope_metrics,
        metric,
        field_name,
        data_points,
    ) in _iter_metric_data_points(metrics_data):
        if not resource_metrics_batch or resource_metrics_batch[-1].resource is not resource_metrics.resource:
            scope_metrics_batch = []
            resource_metrics_batch.append(replace(resource_metrics, scope_metrics=scope_metrics_batch))

        if not scope_metrics_batch or scope_metrics_batch[-1].scope is not scope_metrics.scope:
            metrics_batch = []
            scope_metrics_batch.append(replace(scope_metrics, metrics=metrics_batch))

        data_points_batch: list = []
        metrics_batch.append(_build_metric_with_data_points(metric, field_name, data_points_batch))

        for data_point in data_points:
            data_points_batch.append(data_point)
            batch_size += 1

            if batch_size >= max_export_batch_size:
                yield JSONExportMetricsServiceRequest(resource_metrics=resource_metrics_batch)
                (
                    resource_metrics_batch,
                    scope_metrics_batch,
                    metrics_batch,
                    data_points_batch,
                ) = _build_empty_metric_batches(resource_metrics, scope_metrics, metric, field_name)
                batch_size = 0

        if not batch_size:
            resource_metrics_batch = []
            scope_metrics_batch = []
            metrics_batch = []

    if batch_size:
        yield JSONExportMetricsServiceRequest(resource_metrics=resource_metrics_batch)


def _get_metric_data_field_name(metric: JSONMetric) -> str | None:
    """Find which of the five data fields of an OTLP metric is set.

    Args:
        metric: the encoded metric to inspect.

    Returns:
        The attribute name of the first field in ``_METRIC_DATA_FIELDS`` that
        is not ``None``, or ``None`` when every one of them is unset. The five
        fields are mutually exclusive in a well-formed metric, so at most one
        can match.
    """
    return next(
        (f for f in _METRIC_DATA_FIELDS if getattr(metric, f) is not None),
        None,
    )


def _iter_metric_data_points(
    metrics_data: JSONExportMetricsServiceRequest,
) -> Iterable[tuple[JSONResourceMetrics, JSONScopeMetrics, JSONMetric, str, list]]:
    """Walk an encoded request down to the data points of each metric.

    Args:
        metrics_data: the encoded request to walk. It is read but never
            modified.

    Yields:
        One tuple per metric that has data points, holding the
        ``ResourceMetrics`` and the ``ScopeMetrics`` it sits under, the metric
        itself, the attribute name of the data field that is set on it, and the
        list of data points held by that field. Everything in the tuple is the
        object from ``metrics_data`` rather than a copy.

        A metric with no data field set is skipped with a warning, and so is a
        metric whose data field holds an empty list of data points, since
        neither can be split into batches.
    """
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                field_name = _get_metric_data_field_name(metric)
                if field_name is None:
                    _logger.warning("Tried to split and export an unsupported metric type. Skipping.")
                    continue
                dps = getattr(metric, field_name).data_points
                if not dps:
                    _logger.warning("Unexpected empty metric datapoints. Skipping.")
                    continue
                yield (
                    resource_metrics,
                    scope_metrics,
                    metric,
                    field_name,
                    dps,
                )


def _build_metric_with_data_points(
    metric: JSONMetric,
    field_name: str,
    data_points: list,
) -> JSONMetric:
    """Copy a metric, replacing its data points with another list.

    The copy shares the list object passed in rather than its contents, so
    appending to ``data_points`` afterwards changes the metric that comes back.
    ``split_metrics_data`` relies on that: it attaches an empty list to the
    metric of a batch and fills it as it walks the data points.

    Args:
        metric: the metric to copy. It is left as it was.
        field_name: the attribute name of the data field that is set on
            ``metric``, as ``_get_metric_data_field_name`` returns it.
        data_points: the list of data points the copy should carry.

    Returns:
        A new ``Metric`` with the name, description, unit and aggregation
        settings of ``metric`` and with ``data_points`` in place of its data
        points.
    """
    new_data = replace(getattr(metric, field_name), data_points=data_points)
    return replace(metric, **{field_name: new_data})


def _build_empty_metric_batches(
    resource_metrics: JSONResourceMetrics,
    scope_metrics: JSONScopeMetrics,
    metric: JSONMetric,
    field_name: str,
) -> tuple[list[JSONResourceMetrics], list[JSONScopeMetrics], list[JSONMetric], list]:
    """Start the next batch, repeating the hierarchy the current metric sits in.

    ``split_metrics_data`` calls this straight after yielding a full batch.
    When the batch boundary falls part way through the data points of a metric,
    the data points that are left need somewhere to go, and OTLP requires them
    to be reachable through a resource and a scope, so the enclosing messages
    are repeated in the new batch. When the boundary instead falls on the last
    data point of a metric, ``split_metrics_data`` discards what this returns
    and starts the next batch from the next metric.

    Args:
        resource_metrics: the ``ResourceMetrics`` the current metric sits
            under.
        scope_metrics: the ``ScopeMetrics`` the current metric sits under.
        metric: the metric whose data points the new batch continues with.
        field_name: the attribute name of the data field that is set on
            ``metric``.

    Returns:
        The four lists that make up a batch, nested into one another and all
        empty of data points: the resource metrics list that becomes the
        request, the scope metrics list inside it, the metrics list inside
        that, and the data points list the caller appends to.
    """
    data_points_batch = []
    metrics_batch = [_build_metric_with_data_points(metric, field_name, data_points_batch)]
    scope_metrics_batch = [replace(scope_metrics, metrics=metrics_batch)]
    resource_metrics_batch = [replace(resource_metrics, scope_metrics=scope_metrics_batch)]
    return (
        resource_metrics_batch,
        scope_metrics_batch,
        metrics_batch,
        data_points_batch,
    )


def _encode_resource_metrics(
    rm: ResourceMetrics,
) -> JSONResourceMetrics:
    """Encode the metrics collected under one resource.

    Args:
        rm: the resource and the per-scope metrics collected under it.

    Returns:
        A ``ResourceMetrics`` carrying the attributes and the schema URL of the
        resource and one ``ScopeMetrics`` per instrumentation scope, in the
        order ``rm`` holds them.
    """
    return JSONResourceMetrics(
        resource=JSONResource(attributes=_encode_attributes(rm.resource.attributes)),
        scope_metrics=[_encode_scope_metrics(sm) for sm in rm.scope_metrics],
        schema_url=rm.resource.schema_url,
    )


def _encode_scope_metrics(
    sm: ScopeMetrics,
) -> JSONScopeMetrics:
    """Encode the metrics collected under one instrumentation scope.

    Args:
        sm: the instrumentation scope and the metrics collected under it.

    Returns:
        A ``ScopeMetrics`` carrying the encoded scope, the schema URL of the
        scope and one ``Metric`` per metric, in the order ``sm`` holds them.
    """
    return JSONScopeMetrics(
        scope=_encode_instrumentation_scope(sm.scope),
        schema_url=sm.scope.schema_url,
        metrics=[_encode_metric(m) for m in sm.metrics],
    )


def _encode_metric(metric: Metric) -> JSONMetric:
    """Encode one metric, choosing the data field from its aggregated type.

    A gauge, a histogram, a sum and an exponential histogram each map to the
    OTLP field of that name. Anything else is logged as a warning and produces
    a metric with no data field set. Exported unsplit, such a metric reaches a
    receiver as a metric with no data points rather than as an error. Passed to
    ``split_metrics_data`` with a ``max_export_batch_size`` that is not
    ``None``, it is warned about a second time and left out of every batch, so
    it reaches no receiver at all.

    Args:
        metric: the metric to encode, carrying its aggregated data.

    Returns:
        A ``Metric`` with the name, the description and the unit of ``metric``.
        When the aggregated data is a gauge, a histogram, a sum or an
        exponential histogram, the matching one of the five data fields holds
        the encoded data points and the other four are left unset. Any other
        aggregated type leaves all five unset. The fifth field, ``summary``,
        is never written here, so only four of the five can ever carry data
        points. For a sum and for both kinds of histogram the aggregation
        temporality is copied across, and for a sum so is whether it is
        monotonic.

    Raises:
        ValueError: if an exemplar on one of the data points carries a value
            that is neither an ``int`` nor a ``float``.
    """
    json_metric = JSONMetric(
        name=metric.name,
        description=metric.description,
        unit=metric.unit,
    )
    if isinstance(metric.data, Gauge):
        json_metric.gauge = JSONGauge(data_points=[_encode_gauge_data_point(pt) for pt in metric.data.data_points])
    elif isinstance(metric.data, Histogram):
        json_metric.histogram = JSONHistogram(
            data_points=[_encode_histogram_data_point(pt) for pt in metric.data.data_points],
            aggregation_temporality=metric.data.aggregation_temporality,
        )
    elif isinstance(metric.data, Sum):
        json_metric.sum = JSONSum(
            data_points=[_encode_sum_data_point(pt) for pt in metric.data.data_points],
            aggregation_temporality=metric.data.aggregation_temporality,
            is_monotonic=metric.data.is_monotonic,
        )
    elif isinstance(metric.data, ExponentialHistogram):
        json_metric.exponential_histogram = JSONExponentialHistogram(
            data_points=[_encode_exponential_histogram_data_point(pt) for pt in metric.data.data_points],
            aggregation_temporality=metric.data.aggregation_temporality,
        )
    else:
        if TYPE_CHECKING:
            assert_never(metric.data)
        _logger.warning(
            "unsupported data type %s",
            metric.data.__class__.__name__,
        )
    return json_metric


def _encode_gauge_data_point(
    data_point: NumberDataPoint,
) -> JSONNumberDataPoint:
    """Encode one data point of a gauge.

    The start time of the data point is left out, since a gauge reports the
    value at an instant rather than over an interval.

    Args:
        data_point: the data point to encode.

    Returns:
        A ``NumberDataPoint`` whose value is in ``as_int`` for an ``int`` and
        in ``as_double`` for anything else, which in practice means a
        ``float``.

    Raises:
        ValueError: if an exemplar on the data point carries a value that is
            neither an ``int`` nor a ``float``.
    """
    pt = JSONNumberDataPoint(
        attributes=_encode_attributes(data_point.attributes),
        time_unix_nano=data_point.time_unix_nano,
        exemplars=_encode_exemplars(data_point.exemplars),
    )
    if isinstance(data_point.value, int):
        pt.as_int = data_point.value
    else:
        pt.as_double = data_point.value
    return pt


def _encode_sum_data_point(
    data_point: NumberDataPoint,
) -> JSONNumberDataPoint:
    """Encode one data point of a sum.

    The start time of the data point is carried across, which is what lets a
    receiver detect a reset in a cumulative series and bound the interval a
    delta value covers. Whether the sum is cumulative or delta is carried by
    ``aggregation_temporality`` on the enclosing ``Sum``, not by the start
    time, which both kinds have.

    Args:
        data_point: the data point to encode.

    Returns:
        A ``NumberDataPoint`` whose value is in ``as_int`` for an ``int`` and
        in ``as_double`` for anything else, which in practice means a
        ``float``.

    Raises:
        ValueError: if an exemplar on the data point carries a value that is
            neither an ``int`` nor a ``float``.
    """
    pt = JSONNumberDataPoint(
        attributes=_encode_attributes(data_point.attributes),
        start_time_unix_nano=data_point.start_time_unix_nano,
        time_unix_nano=data_point.time_unix_nano,
        exemplars=_encode_exemplars(data_point.exemplars),
    )
    if isinstance(data_point.value, int):
        pt.as_int = data_point.value
    else:
        pt.as_double = data_point.value
    return pt


def _encode_histogram_data_point(
    data_point: HistogramDataPoint,
) -> JSONHistogramDataPoint:
    """Encode one data point of an explicit bucket histogram.

    Args:
        data_point: the data point to encode.

    Returns:
        A ``HistogramDataPoint`` carrying the count, the sum, the bucket counts
        and the explicit bounds, plus the minimum and the maximum, which are
        ``None`` when the aggregation was configured not to record them. The
        bucket counts and the explicit bounds are copied into new lists, so a
        later change to the SDK data point does not reach the encoded one.

    Raises:
        ValueError: if an exemplar on the data point carries a value that is
            neither an ``int`` nor a ``float``.
    """
    return JSONHistogramDataPoint(
        attributes=_encode_attributes(data_point.attributes),
        time_unix_nano=data_point.time_unix_nano,
        start_time_unix_nano=data_point.start_time_unix_nano,
        exemplars=_encode_exemplars(data_point.exemplars),
        count=data_point.count,
        sum=data_point.sum,
        bucket_counts=list(data_point.bucket_counts),
        explicit_bounds=list(data_point.explicit_bounds),
        max=data_point.max,
        min=data_point.min,
    )


def _encode_exponential_histogram_data_point(
    data_point: ExponentialHistogramDataPoint,
) -> JSONExponentialHistogramDataPoint:
    """Encode one data point of an exponential bucket histogram.

    Args:
        data_point: the data point to encode.

    Returns:
        An ``ExponentialHistogramDataPoint`` carrying the count, the sum, the
        scale, the count of values that fell in the zero bucket and the flags,
        plus the minimum and the maximum, which are ``None`` when the
        aggregation was configured not to record them. The positive and the
        negative bucket sets are each left unset only when the list of bucket
        counts is empty, which a data point the SDK produced never has: a fresh
        set of buckets already holds the single count zero, so a histogram of
        only positive values still encodes a negative bucket set.

    Raises:
        ValueError: if an exemplar on the data point carries a value that is
            neither an ``int`` nor a ``float``.
    """
    return JSONExponentialHistogramDataPoint(
        attributes=_encode_attributes(data_point.attributes),
        time_unix_nano=data_point.time_unix_nano,
        start_time_unix_nano=data_point.start_time_unix_nano,
        exemplars=_encode_exemplars(data_point.exemplars),
        count=data_point.count,
        sum=data_point.sum,
        scale=data_point.scale,
        zero_count=data_point.zero_count,
        positive=(
            JSONExponentialHistogramDataPoint.Buckets(
                offset=data_point.positive.offset,
                bucket_counts=list(data_point.positive.bucket_counts),
            )
            if data_point.positive.bucket_counts
            else None
        ),
        negative=(
            JSONExponentialHistogramDataPoint.Buckets(
                offset=data_point.negative.offset,
                bucket_counts=list(data_point.negative.bucket_counts),
            )
            if data_point.negative.bucket_counts
            else None
        ),
        flags=data_point.flags,
        max=data_point.max,
        min=data_point.min,
    )


def _encode_exemplars(
    sdk_exemplars: Collection[Exemplar],
) -> list[JSONExemplar]:
    """Encode the exemplars attached to one metric data point.

    An exemplar links a recorded measurement back to the trace that was active
    when it was taken. The trace and span identifiers are encoded only when the
    exemplar carries both, so an exemplar recorded outside any span is still
    exported, with its timestamp, its value and its filtered attributes but no
    trace link.

    Args:
        sdk_exemplars: the exemplars of one data point, in the order the
            aggregation holds them.

    Returns:
        One ``Exemplar`` per exemplar, with the value in ``as_double`` for a
        ``float`` and in ``as_int`` for an ``int``.

    Raises:
        ValueError: if an exemplar carries a value that is neither an ``int``
            nor a ``float``.
    """
    json_exemplars = []
    for sdk_exemplar in sdk_exemplars:
        if sdk_exemplar.span_id is not None and sdk_exemplar.trace_id is not None:
            json_exemplar = JSONExemplar(
                time_unix_nano=sdk_exemplar.time_unix_nano,
                span_id=_encode_span_id(sdk_exemplar.span_id),
                trace_id=_encode_trace_id(sdk_exemplar.trace_id),
                filtered_attributes=_encode_attributes(sdk_exemplar.filtered_attributes),
            )
        else:
            json_exemplar = JSONExemplar(
                time_unix_nano=sdk_exemplar.time_unix_nano,
                filtered_attributes=_encode_attributes(sdk_exemplar.filtered_attributes),
            )

        # Assign the value based on its type in the SDK exemplar
        if isinstance(sdk_exemplar.value, float):
            json_exemplar.as_double = sdk_exemplar.value
        elif isinstance(sdk_exemplar.value, int):
            json_exemplar.as_int = sdk_exemplar.value
        else:
            if TYPE_CHECKING:
                assert_never(sdk_exemplar.value)
            raise ValueError("Exemplar value must be an int or float")
        json_exemplars.append(json_exemplar)

    return json_exemplars
