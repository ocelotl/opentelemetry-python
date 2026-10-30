# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Conversion of SDK metrics into the protobuf metrics export request.

``encode_metrics`` is the only name the OTLP exporters import from here by way of
``opentelemetry.exporter.otlp.proto.common.metrics_encoder``. The gRPC and HTTP
metric exporters additionally import ``OTLPMetricExporterMixin`` from this module
directly, to share the reading of the two environment variables that decide
aggregation temporality and the default histogram aggregation.

The SDK has already grouped metrics by resource and by instrumentation scope
before they reach this module, so the encoding copies that structure rather than
rebuilding it, which is where it differs from the span and log record encoders.
"""

from __future__ import annotations

import logging
from os import environ

from opentelemetry.exporter.otlp.proto.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as PB2Resource,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Exemplar,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge,
    MetricExporter,
    MetricsData,
    Sum,
)
from opentelemetry.sdk.metrics.export import (
    ExponentialHistogram as ExponentialHistogramType,
)
from opentelemetry.sdk.metrics.export import (
    Histogram as HistogramType,
)
from opentelemetry.sdk.metrics.view import (
    Aggregation,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)

_logger = logging.getLogger(__name__)


class OTLPMetricExporterMixin:
    """Shared configuration for the gRPC and HTTP OTLP metric exporters.

    Both exporters subclass this mixin together with
    :class:`opentelemetry.sdk.metrics.export.MetricExporter`, and call
    ``_common_configuration`` from their own constructors. The mixin reads the
    two OTLP environment variables that select a temporality and a default
    histogram aggregation per instrument class, so that the two exporters cannot
    disagree about what those variables mean.

    The mixin defines no state of its own and takes no constructor arguments.
    """

    def _common_configuration(
        self,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None:
        """Initialise the ``MetricExporter`` half of the exporter.

        Calls ``MetricExporter.__init__`` explicitly rather than through
        ``super()``, so the exporter gets the temporality and aggregation
        mappings that the environment and the arguments produce together.

        Args:
            preferred_temporality: Per instrument class, the aggregation
                temporality the caller wants, overriding what the environment
                selects. ``None`` and an empty mapping both leave the environment
                in charge. An instrument class absent from the mapping keeps the
                environment's choice.
            preferred_aggregation: Per instrument class, the aggregation the
                caller wants. Same ``None`` and absence handling as
                ``preferred_temporality``.
        """
        MetricExporter.__init__(
            self,
            preferred_temporality=self._get_temporality(preferred_temporality),
            preferred_aggregation=self._get_aggregation(preferred_aggregation),
        )

    def _get_temporality(
        self, preferred_temporality: dict[type, AggregationTemporality]
    ) -> dict[type, AggregationTemporality]:
        """Decide the aggregation temporality of each instrument class.

        Reads ``OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE``, upper-cased
        and stripped of surrounding whitespace, so ``delta`` and ``" DELTA "``
        are both accepted. ``CUMULATIVE`` is the default and makes every
        instrument class cumulative. ``DELTA`` makes counters, histograms and
        observable counters delta. ``LOWMEMORY`` differs from ``DELTA`` only in
        keeping observable counters cumulative, which lets the SDK avoid storing
        the previous value for them. Any other value is logged at ``WARNING`` and
        treated as ``CUMULATIVE``.

        Args:
            preferred_temporality: Per instrument class, the temporality that
                overrides the environment's choice. ``None`` leaves the
                environment's choice untouched. The mapping is not mutated.

        Returns:
            One entry per instrument class the exporter supports, suitable for
            the ``preferred_temporality`` argument of ``MetricExporter``.
        """
        otel_exporter_otlp_metrics_temporality_preference = (
            environ.get(
                OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
                "CUMULATIVE",
            )
            .upper()
            .strip()
        )

        if otel_exporter_otlp_metrics_temporality_preference == "DELTA":
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.DELTA,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

        elif otel_exporter_otlp_metrics_temporality_preference == "LOWMEMORY":
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

        else:
            if otel_exporter_otlp_metrics_temporality_preference != ("CUMULATIVE"):
                _logger.warning(
                    "Unrecognized OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE value found: %s, using CUMULATIVE",
                    otel_exporter_otlp_metrics_temporality_preference,
                )
            instrument_class_temporality = {
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

        instrument_class_temporality.update(preferred_temporality or {})

        return instrument_class_temporality

    def _get_aggregation(
        self,
        preferred_aggregation: dict[type, Aggregation],
    ) -> dict[type, Aggregation]:
        """Decide the default aggregation of each instrument class.

        Reads ``OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION``, which
        only ever affects :class:`opentelemetry.sdk.metrics.Histogram`.
        ``explicit_bucket_histogram`` is the default and selects
        :class:`opentelemetry.sdk.metrics.view.ExplicitBucketHistogramAggregation`;
        ``base2_exponential_bucket_histogram`` selects
        :class:`opentelemetry.sdk.metrics.view.ExponentialBucketHistogramAggregation`.
        The comparison is exact, with no case folding and no stripping, so
        ``Explicit_Bucket_Histogram`` is logged at ``WARNING`` and falls back to
        explicit buckets. Every instrument class other than ``Histogram`` is left
        out of the result, which leaves the SDK's own default in place for it.

        Args:
            preferred_aggregation: Per instrument class, the aggregation that
                overrides the environment's choice, and the only way to set an
                aggregation for an instrument class that is not ``Histogram``.
                ``None`` leaves the environment's choice untouched. The mapping is
                not mutated.

        Returns:
            The aggregation for ``Histogram`` plus every entry of
            ``preferred_aggregation``, suitable for the
            ``preferred_aggregation`` argument of ``MetricExporter``.
        """
        otel_exporter_otlp_metrics_default_histogram_aggregation = environ.get(
            OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
            "explicit_bucket_histogram",
        )

        if otel_exporter_otlp_metrics_default_histogram_aggregation == ("base2_exponential_bucket_histogram"):
            instrument_class_aggregation = {
                Histogram: ExponentialBucketHistogramAggregation(),
            }

        else:
            if otel_exporter_otlp_metrics_default_histogram_aggregation != ("explicit_bucket_histogram"):
                _logger.warning(
                    ("Invalid value for %s: %s, using explicit bucket histogram aggregation"),
                    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
                    otel_exporter_otlp_metrics_default_histogram_aggregation,
                )

            instrument_class_aggregation = {
                Histogram: ExplicitBucketHistogramAggregation(),
            }

        instrument_class_aggregation.update(preferred_aggregation or {})

        return instrument_class_aggregation


class EncodingException(Exception):
    """
    Raised by encode_metrics() when an exception is caught during encoding. Contains the problematic metric so
    the misbehaving metric name and details can be logged during exception handling.

    It is raised with ``from None``, so the traceback does not show the original
    exception as the cause. The original exception is kept as an attribute
    instead, and is included in the string form.

    Args:
        original_exception: The exception raised while encoding ``metric``.
            Available afterwards as the ``original_exception`` attribute.
        metric: The SDK metric that failed to encode, carrying its name,
            description, unit and data points. Available afterwards as the
            ``metric`` attribute. A caller that logs it should keep in mind that
            the data points include attribute values, which may be sensitive.
    """

    def __init__(self, original_exception, metric):
        """Store the failing metric and the exception it caused.

        The arguments are documented on the class.
        """
        super().__init__()
        self.original_exception = original_exception
        self.metric = metric

    def __str__(self):
        """Render the failing metric and the original exception.

        Returns:
            The metric on its own line, then the original exception on the next.
            ``Exception.__init__`` was called with no arguments, so this is the
            only place the two values appear in the formatted traceback.
        """
        return f"{self.metric}\n{self.original_exception}"


def encode_metrics(data: MetricsData) -> ExportMetricsServiceRequest:
    """Encode collected metrics as the protobuf request body of an OTLP metrics export.

    Unlike the span and log record encoders, this one does not regroup anything:
    the SDK hands over one ``ResourceMetrics`` per resource already, each holding
    its scopes, and the encoding mirrors that structure. A metric whose data type
    the protocol has no message for is logged at ``WARNING`` and encoded as a
    ``Metric`` with a name, a description and a unit but no data points.

    Args:
        data: The metrics the SDK's reader collected.

    Returns:
        The ``ExportMetricsServiceRequest`` to send over gRPC or, serialized, as
        the body of an HTTP request.

    Raises:
        EncodingException: If encoding a single metric fails. The exception
            carries that metric and the exception it caused, so the caller can
            name the offending instrument. Nothing is exported in that case: the
            whole batch is lost, not only the one metric.
    """
    resource_metrics_dict = {}

    for resource_metrics in data.resource_metrics:
        _encode_resource_metrics(resource_metrics, resource_metrics_dict)

    resource_data = []
    for (
        sdk_resource,
        scope_data,
    ) in resource_metrics_dict.items():
        resource_data.append(
            pb2.ResourceMetrics(
                resource=PB2Resource(attributes=_encode_attributes(sdk_resource.attributes)),
                scope_metrics=scope_data.values(),
                schema_url=sdk_resource.schema_url,
            )
        )
    return ExportMetricsServiceRequest(resource_metrics=resource_data)


def _encode_resource_metrics(resource_metrics, resource_metrics_dict):
    """Encode every scope and metric under one resource into an accumulator.

    Nothing is returned: the encoded messages are added to
    ``resource_metrics_dict``, which ``encode_metrics`` then turns into
    ``ResourceMetrics`` messages. The entry for the resource is assigned rather
    than merged, so calling this twice with the same resource discards what the
    first call produced.

    Args:
        resource_metrics: One ``ResourceMetrics`` as the SDK's reader produced
            it, holding the resource and its scope metrics.
        resource_metrics_dict: The accumulator, mapping each SDK resource to a
            mapping from instrumentation scope to the protobuf ``ScopeMetrics``
            being filled. Mutated in place.

    Raises:
        EncodingException: If encoding one metric fails, wrapping the original
            exception and naming the metric. The scope metrics encoded before it
            stay in the accumulator, but ``encode_metrics`` does not return, so
            they are never exported.
    """
    resource = resource_metrics.resource
    # It is safe to assume that each entry in data.resource_metrics is
    # associated with an unique resource.
    scope_metrics_dict = {}
    resource_metrics_dict[resource] = scope_metrics_dict
    for scope_metrics in resource_metrics.scope_metrics:
        instrumentation_scope = scope_metrics.scope

        # The SDK groups metrics in instrumentation scopes already so
        # there is no need to check for existing instrumentation scopes
        # here.
        pb2_scope_metrics = pb2.ScopeMetrics(
            scope=_encode_instrumentation_scope(instrumentation_scope),
            schema_url=instrumentation_scope.schema_url,
        )

        scope_metrics_dict[instrumentation_scope] = pb2_scope_metrics

        for metric in scope_metrics.metrics:
            pb2_metric = pb2.Metric(
                name=metric.name,
                description=metric.description,
                unit=metric.unit,
            )

            try:
                _encode_metric(metric, pb2_metric)
            except Exception as ex:
                # `from None` so we don't get "During handling of the above exception, another exception occurred:"
                raise EncodingException(ex, metric) from None

            pb2_scope_metrics.metrics.append(pb2_metric)


def _encode_metric(metric, pb2_metric):
    """Fill in the data points of a protobuf ``Metric`` from an SDK metric.

    Nothing is returned: ``pb2_metric`` is mutated, and which of its ``gauge``,
    ``histogram``, ``sum`` and ``exponential_histogram`` fields gets set is
    decided by the runtime type of ``metric.data``. A numeric data point is
    written to ``as_int`` when its value is an ``int`` and to ``as_double``
    otherwise.

    An exponential histogram data point whose positive or negative bucket counts
    are empty leaves that side of the point unset rather than writing an empty
    ``Buckets`` message.

    Args:
        metric: The SDK metric, whose ``data`` attribute holds the data points.
            A ``data`` of a type this function does not recognise is logged at
            ``WARNING`` by class name and leaves ``pb2_metric`` without data
            points, so the metric is exported as an empty one rather than
            dropped.
        pb2_metric: The protobuf ``Metric`` to fill in. Its name, description and
            unit are expected to be set already, and are not touched here.
    """
    if isinstance(metric.data, Gauge):
        for data_point in metric.data.data_points:
            pt = pb2.NumberDataPoint(
                attributes=_encode_attributes(data_point.attributes),
                time_unix_nano=data_point.time_unix_nano,
                exemplars=_encode_exemplars(data_point.exemplars),
            )
            if isinstance(data_point.value, int):
                pt.as_int = data_point.value
            else:
                pt.as_double = data_point.value
            pb2_metric.gauge.data_points.append(pt)

    elif isinstance(metric.data, HistogramType):
        for data_point in metric.data.data_points:
            pt = pb2.HistogramDataPoint(
                attributes=_encode_attributes(data_point.attributes),
                time_unix_nano=data_point.time_unix_nano,
                start_time_unix_nano=data_point.start_time_unix_nano,
                exemplars=_encode_exemplars(data_point.exemplars),
                count=data_point.count,
                sum=data_point.sum,
                bucket_counts=data_point.bucket_counts,
                explicit_bounds=data_point.explicit_bounds,
                max=data_point.max,
                min=data_point.min,
            )
            pb2_metric.histogram.aggregation_temporality = metric.data.aggregation_temporality
            pb2_metric.histogram.data_points.append(pt)

    elif isinstance(metric.data, Sum):
        for data_point in metric.data.data_points:
            pt = pb2.NumberDataPoint(
                attributes=_encode_attributes(data_point.attributes),
                start_time_unix_nano=data_point.start_time_unix_nano,
                time_unix_nano=data_point.time_unix_nano,
                exemplars=_encode_exemplars(data_point.exemplars),
            )
            if isinstance(data_point.value, int):
                pt.as_int = data_point.value
            else:
                pt.as_double = data_point.value
            # note that because sum is a message type, the
            # fields must be set individually rather than
            # instantiating a pb2.Sum and setting it once
            pb2_metric.sum.aggregation_temporality = metric.data.aggregation_temporality
            pb2_metric.sum.is_monotonic = metric.data.is_monotonic
            pb2_metric.sum.data_points.append(pt)

    elif isinstance(metric.data, ExponentialHistogramType):
        for data_point in metric.data.data_points:
            if data_point.positive.bucket_counts:
                positive = pb2.ExponentialHistogramDataPoint.Buckets(
                    offset=data_point.positive.offset,
                    bucket_counts=data_point.positive.bucket_counts,
                )
            else:
                positive = None

            if data_point.negative.bucket_counts:
                negative = pb2.ExponentialHistogramDataPoint.Buckets(
                    offset=data_point.negative.offset,
                    bucket_counts=data_point.negative.bucket_counts,
                )
            else:
                negative = None

            pt = pb2.ExponentialHistogramDataPoint(
                attributes=_encode_attributes(data_point.attributes),
                time_unix_nano=data_point.time_unix_nano,
                start_time_unix_nano=data_point.start_time_unix_nano,
                exemplars=_encode_exemplars(data_point.exemplars),
                count=data_point.count,
                sum=data_point.sum,
                scale=data_point.scale,
                zero_count=data_point.zero_count,
                positive=positive,
                negative=negative,
                flags=data_point.flags,
                max=data_point.max,
                min=data_point.min,
            )
            pb2_metric.exponential_histogram.aggregation_temporality = metric.data.aggregation_temporality
            pb2_metric.exponential_histogram.data_points.append(pt)

    else:
        _logger.warning(
            "unsupported data type %s",
            metric.data.__class__.__name__,
        )


def _encode_exemplars(sdk_exemplars: list[Exemplar]) -> list[pb2.Exemplar]:
    """
    Converts a list of SDK Exemplars into a list of protobuf Exemplars.

    Args:
        sdk_exemplars (list): The list of exemplars from the OpenTelemetry SDK.

    Returns:
        list: A list of protobuf exemplars.
    """
    pb_exemplars = []
    for sdk_exemplar in sdk_exemplars:
        if sdk_exemplar.span_id is not None and sdk_exemplar.trace_id is not None:
            pb_exemplar = pb2.Exemplar(
                time_unix_nano=sdk_exemplar.time_unix_nano,
                span_id=_encode_span_id(sdk_exemplar.span_id),
                trace_id=_encode_trace_id(sdk_exemplar.trace_id),
                filtered_attributes=_encode_attributes(sdk_exemplar.filtered_attributes),
            )
        else:
            pb_exemplar = pb2.Exemplar(
                time_unix_nano=sdk_exemplar.time_unix_nano,
                filtered_attributes=_encode_attributes(sdk_exemplar.filtered_attributes),
            )

        # Assign the value based on its type in the SDK exemplar
        if isinstance(sdk_exemplar.value, float):
            pb_exemplar.as_double = sdk_exemplar.value
        elif isinstance(sdk_exemplar.value, int):
            pb_exemplar.as_int = sdk_exemplar.value
        else:
            raise ValueError("Exemplar value must be an int or float")
        pb_exemplars.append(pb_exemplar)

    return pb_exemplars
