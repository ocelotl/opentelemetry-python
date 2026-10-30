# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Metric exporter that writes OTLP JSON to a file, to a stream or to standard output."""

import logging
import os
from typing import IO, Any, overload

from opentelemetry.exporter.otlp.common._aggregation import (
    _get_aggregation,
    _get_temporality,
)
from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.json.file._internal import _FileExporter
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExporter,
    MetricExportResult,
    MetricsData,
)
from opentelemetry.sdk.metrics.view import Aggregation

_logger = logging.getLogger(__name__)


def _encode_metrics_to_dict(
    metrics_data: MetricsData,
) -> dict[str, Any] | None:
    """Encode one metric collection as an OTLP export request.

    Args:
        metrics_data: Metrics collected by a metric reader.

    Returns:
        The ``ExportMetricsServiceRequest`` as a JSON serialisable dictionary, or ``None`` when the
        collection produced no resource metrics, so that an empty collection writes no line at all.
    """
    data = encode_metrics(metrics_data)
    return data.to_dict() if data.resource_metrics else None


class FileMetricExporter(MetricExporter):
    """Writes collected metrics to a file, to a stream or to ``sys.stdout`` as OTLP JSON Lines.

    A line written by this exporter always holds one whole ``ExportMetricsServiceRequest``, so the
    output can be read back a line at a time and a collection is never split across lines. A
    collection that encodes to nothing writes no line at all.
    Register this exporter with ``opentelemetry.sdk.metrics.export.PeriodicExportingMetricReader``
    for the metrics to reach it.

    Args:
        path: File to append the metrics to, opened with UTF-8 encoding. The exporter closes this
            file on shutdown. Mutually exclusive with ``stream``.
        stream: Open text stream to write the metrics to. The caller keeps responsibility for
            closing it. Mutually exclusive with ``path``.
        preferred_temporality: Temporality this exporter asks the metric reader for, per
            instrument class. An entry here overrides, for that one instrument class, the choice
            that :envvar:`OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE` makes. That variable
            names one of three presets: ``CUMULATIVE``, which is the default and what an
            unrecognised value falls back to after a warning; ``DELTA``, which makes the counter,
            the histogram and the observable counter delta; and ``LOWMEMORY``, which makes the
            counter and the histogram delta. Every preset leaves the up-down counters and the
            gauges cumulative. ``None`` overrides nothing.
        preferred_aggregation: Aggregation this exporter asks the metric reader for, per
            instrument class. The only entry this exporter contributes on its own is the one for
            ``Histogram``, chosen by
            :envvar:`OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION`: the explicit
            bucket histogram by default, and also after a warning for an unrecognised value, or
            the base-2 exponential bucket histogram when that variable is set to
            ``BASE2_EXPONENTIAL_BUCKET_HISTOGRAM``. An entry here for ``Histogram`` overrides
            that choice, and an entry for any of the other instrument classes is handed to the
            metric reader as it stands. An instrument class with no entry here, ``Histogram``
            aside, is left on the default aggregation the metric reader picks, since neither
            this exporter nor that variable names one for it. ``None`` overrides nothing.

    Raises:
        ValueError: Both ``path`` and ``stream`` were given. Leaving both out selects
            ``sys.stdout``.
    """

    @overload
    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        stream: IO[str],
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None: ...

    def __init__(
        self,
        path: str | os.PathLike[str] | None = None,
        *,
        stream: IO[str] | None = None,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None:
        """Read the two environment variables and open the destination.

        The parameters are documented on the class.
        """
        MetricExporter.__init__(
            self,
            preferred_temporality=_get_temporality(preferred_temporality),
            preferred_aggregation=_get_aggregation(preferred_aggregation),
        )
        self._exporter: _FileExporter[MetricsData] = _FileExporter(
            encode=_encode_metrics_to_dict,
            kind="metrics",
            logger=_logger,
            path=path,
            stream=stream,
        )

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        """Append the collection to the destination as one line of OTLP JSON, then flush.

        A failure is logged with its traceback and reported through the return value. Nothing is
        raised, so a metric reader calling this never has to guard the call.

        Args:
            metrics_data: Metrics to write.
            timeout_millis: Accepted for compatibility with the exporter interface and ignored,
                because the write goes to a local stream.
            kwargs: Accepted for compatibility with the exporter interface and ignored.

        Returns:
            ``MetricExportResult.SUCCESS`` once the line has been written and flushed, and also
            when the collection encoded to nothing and no line was written.
            ``MetricExportResult.FAILURE`` when this exporter has been shut down, when the stream
            was closed by whoever owns it, or when encoding or writing raised.
        """
        return MetricExportResult.SUCCESS if self._exporter.export(metrics_data) else MetricExportResult.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Refuse further exports, and close the file when this exporter opened one.

        A stream supplied by the caller is left open, and so is ``sys.stdout``. A later call to
        :meth:`export` logs a warning and returns ``MetricExportResult.FAILURE``.

        Args:
            timeout_millis: Accepted for compatibility with the exporter interface and ignored,
                because closing a local file does not block.
            kwargs: Accepted for compatibility with the exporter interface and ignored.
        """
        self._exporter.shutdown()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Report that no metrics are being held back.

        Every call to :meth:`export` writes and flushes before it returns, so this exporter never
        buffers metrics and has nothing to do here.

        Args:
            timeout_millis: Accepted for compatibility with the exporter interface and ignored.

        Returns:
            ``True`` always.
        """
        return True
