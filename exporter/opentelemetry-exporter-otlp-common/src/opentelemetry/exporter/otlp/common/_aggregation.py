# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Default metric temporality and aggregation for the OTLP metric exporters.

The OTLP specification lets a user pick, through two environment variables, how
the OTLP metric exporters aggregate the instruments the SDK collects.
``OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE`` picks the aggregation
temporality per instrument type and
``OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION`` picks the
aggregation applied to histograms. The two functions here read those variables
and return the mappings an OTLP metric exporter reports to the SDK as its
preferences.

Both functions take a preference expressed in code as their argument and let it
win over the environment, so a value passed to the constructor of an exporter
overrides what the environment asked for.
"""

from __future__ import annotations

import logging
import os

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import AggregationTemporality
from opentelemetry.sdk.metrics.view import (
    Aggregation,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)

_logger = logging.getLogger(__name__)


def _get_temporality(
    preferred_temporality: dict[type, AggregationTemporality] | None,
) -> dict[type, AggregationTemporality]:
    """Resolve the aggregation temporality of each instrument type.

    The value of ``OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE`` is
    stripped and uppercased before it is matched, so ``delta`` and ``" Delta "``
    both select the same preference.

    ``DELTA`` asks for delta temporality on ``Counter``, ``Histogram`` and
    ``ObservableCounter``. ``LOWMEMORY`` asks for delta temporality on
    ``Counter`` and ``Histogram`` only, leaving every asynchronous instrument
    cumulative. ``CUMULATIVE`` asks for cumulative temporality on all six
    instrument types and is what an unset variable means. Any
    other value is also treated as ``CUMULATIVE``, after a warning naming the
    variable and the rejected value is logged.

    Args:
        preferred_temporality: Temporality per instrument type chosen in code,
            or ``None`` when the caller states no preference. Each entry
            replaces the entry the environment variable produced for the same
            instrument type, and an instrument type absent from it keeps the
            temporality the environment variable produced.

    Returns:
        A mapping from instrument type to ``AggregationTemporality``, covering
        the six SDK instrument types and anything extra that
        ``preferred_temporality`` named. An OTLP metric exporter passes it to
        ``MetricExporter.__init__`` as its ``preferred_temporality`` argument.
    """
    temporality_preference = (
        os.environ.get(
            OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
            "CUMULATIVE",
        )
        .upper()
        .strip()
    )

    instrument_class_temporality: dict[type, AggregationTemporality]
    match temporality_preference:
        case "DELTA":
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.DELTA,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        case "LOWMEMORY":
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        case _:
            if temporality_preference != "CUMULATIVE":
                _logger.warning(
                    ("Invalid value for %s: %s, using cumulative temporality aggregation"),
                    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
                    temporality_preference,
                )
            instrument_class_temporality = {
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

    return instrument_class_temporality | (preferred_temporality or {})


def _get_aggregation(
    preferred_aggregation: dict[type, Aggregation] | None,
) -> dict[type, Aggregation]:
    """Resolve the aggregation applied to histogram instruments.

    The value of ``OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION`` is
    stripped and uppercased before it is matched.
    ``BASE2_EXPONENTIAL_BUCKET_HISTOGRAM`` selects
    ``ExponentialBucketHistogramAggregation``. ``EXPLICIT_BUCKET_HISTOGRAM``
    selects ``ExplicitBucketHistogramAggregation`` and is what an unset
    variable means. Any other value selects
    ``ExplicitBucketHistogramAggregation`` as well, after a warning naming the
    variable and the rejected value is logged.

    ``Histogram`` is the only instrument type the environment variable can
    reach. Every other instrument type keeps the default aggregation the SDK
    applies unless ``preferred_aggregation`` names it.

    Args:
        preferred_aggregation: Aggregation per instrument type chosen in code,
            or ``None`` when the caller states no preference. An entry for
            ``Histogram`` replaces the aggregation the environment variable
            selected, and entries for other instrument types are passed
            through.

    Returns:
        A mapping from instrument type to ``Aggregation``. An OTLP metric
        exporter passes it to ``MetricExporter.__init__`` as its
        ``preferred_aggregation`` argument.
    """
    default_histogram_aggregation = (
        os.environ.get(
            OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
            "explicit_bucket_histogram",
        )
        .upper()
        .strip()
    )

    instrument_class_aggregation: dict[type, Aggregation]
    match default_histogram_aggregation:
        case "BASE2_EXPONENTIAL_BUCKET_HISTOGRAM":
            instrument_class_aggregation = {
                Histogram: ExponentialBucketHistogramAggregation(),
            }
        case _:
            if default_histogram_aggregation != "EXPLICIT_BUCKET_HISTOGRAM":
                _logger.warning(
                    ("Invalid value for %s: %s, using explicit bucket histogram aggregation"),
                    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
                    default_histogram_aggregation,
                )

            instrument_class_aggregation = {
                Histogram: ExplicitBucketHistogramAggregation(),
            }

    return instrument_class_aggregation | (preferred_aggregation or {})
