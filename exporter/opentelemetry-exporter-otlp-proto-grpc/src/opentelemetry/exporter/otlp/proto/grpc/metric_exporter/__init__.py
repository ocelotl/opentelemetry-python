# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OTLP Metric Exporter

This module holds the metric exporter that sends metrics to an
OTLP-compatible receiver over gRPC. It adds two things to the behaviour the
other signals share: the temporality and aggregation preferences the SDK asks
the exporter for, and an optional split of one collection into several
requests so that no request exceeds the message size the receiver accepts.
"""

from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Sequence as TypingSequence
from dataclasses import replace
from logging import getLogger
from os import environ

from grpc import ChannelCredentials, Compression, StatusCode
from opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder import (
    OTLPMetricExporterMixin,
)
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.proto.grpc import _timeout_from_env
from opentelemetry.exporter.otlp.proto.grpc.exporter import (  # noqa: F401
    OTLPExporterMixin,
    _get_credentials,
    environ_to_compression,
    get_resource_data,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2_grpc import (
    MetricsServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    InstrumentationScope,
)
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2  # noqa: F401
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_GRPC_METRICS_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_INSECURE,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
)
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation
from opentelemetry.sdk.metrics.export import (  # noqa: F401
    AggregationTemporality,
    DataPointT,
    Gauge,
    Metric,
    MetricExporter,
    MetricExportResult,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.metrics.export import (  # noqa: F401
    ExponentialHistogram as ExponentialHistogramType,
)
from opentelemetry.sdk.metrics.export import (  # noqa: F401
    Histogram as HistogramType,
)
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)

_logger = getLogger(__name__)


class OTLPMetricExporter(
    MetricExporter,
    OTLPExporterMixin[
        MetricsData,
        ExportMetricsServiceRequest,
        MetricExportResult,
        MetricsServiceStub,
    ],
    OTLPMetricExporterMixin,
):
    """OTLP metric exporter

    Sends collected metrics to an OTLP receiver over gRPC. The ``endpoint``,
    ``insecure``, ``credentials``, ``headers``, ``timeout`` and ``compression``
    arguments, when left as ``None``, are read from the metrics-specific
    environment variable first and from the generic OTLP variable second, so a
    deployment can configure metrics apart from the other signals. The
    remaining arguments do not follow that pattern, and each entry below says
    what it does read.

    Args:
        endpoint: Target URL to which the exporter is going to send metrics.
            Falls back to :envvar:`OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`, then
            to :envvar:`OTEL_EXPORTER_OTLP_ENDPOINT`, then to
            ``http://localhost:4317``.
        insecure: Connection type. ``True`` sends plain HTTP/2 with no TLS.
            ``None`` means the value is taken from
            :envvar:`OTEL_EXPORTER_OTLP_METRICS_INSECURE`, then from
            :envvar:`OTEL_EXPORTER_OTLP_INSECURE`, and finally from the scheme
            of the endpoint. An ``https`` scheme forces ``False`` whatever the
            argument and the two variables say.
        credentials: Credentials object for server authentication. ``None``
            means credentials are built from
            :envvar:`OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE` and its client
            key and client certificate companions when that variable is set
            and neither the ``insecure`` argument nor
            :envvar:`OTEL_EXPORTER_OTLP_METRICS_INSECURE` says the connection
            is insecure, and resolved from the generic OTLP variables
            otherwise. An ``https`` endpoint combined with an insecure setting
            therefore makes a TLS connection that ignores the
            metrics-specific certificate variables.
        headers: Headers to send when exporting, as a mapping, as a sequence
            of pairs, or as the comma-separated string form used by
            :envvar:`OTEL_EXPORTER_OTLP_METRICS_HEADERS`. ``None`` means that
            variable is read, then :envvar:`OTEL_EXPORTER_OTLP_HEADERS`.
        timeout: Backend request timeout in seconds, covering the whole export
            including retries. ``None`` means the value is taken from
            :envvar:`OTEL_EXPORTER_OTLP_METRICS_TIMEOUT`, then from
            :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT`, defaulting to 10 seconds.
            When the collection is split, the timeout applies to each request
            separately.
        compression: gRPC compression method to use. ``None`` means the value
            is taken from :envvar:`OTEL_EXPORTER_OTLP_METRICS_COMPRESSION`,
            then from :envvar:`OTEL_EXPORTER_OTLP_COMPRESSION`, and no
            compression is used when neither is set.
        preferred_temporality: Aggregation temporality the SDK should use, per
            instrument class. Entries given here are applied over the full set
            of per-instrument defaults that
            :envvar:`OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE`
            selects, so an instrument class left out keeps the default from
            that variable.
        preferred_aggregation: Aggregation the SDK should use, per instrument
            class. Entries given here are applied over the histogram default
            that
            :envvar:`OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION`
            selects.
        max_export_batch_size: Maximum number of data points to export in a single request. This is to deal with
            gRPC's 4MB message size limit. If not set there is no limit to the number of data points in a request.
            If it is set and the number of data points exceeds the max, the request will be split.
            No environment variable is read for this.
        channel_options: gRPC channel options, as a sequence of name and value
            pairs, merged over this package's own options. No environment
            variable is read for this.
        retryable_error_codes: gRPC status codes that cause an export to be
            retried. ``None`` means the set is read from
            ``OTEL_PYTHON_EXPORTER_OTLP_GRPC_RETRYABLE_ERROR_CODES``, which
            applies to all three signals and has no metrics-specific form, and
            otherwise falls back to the default set.
        meter_provider: Meter provider used to record the exporter's own
            self-observability metrics. ``None`` means the globally configured
            meter provider is used. Those metrics are recorded at all only
            when :envvar:`OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED` is set to
            ``true``.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        insecure: bool | None = None,
        credentials: ChannelCredentials | None = None,
        headers: TypingSequence[tuple[str, str]] | dict[str, str] | str | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
        channel_options: tuple[tuple[str, str]] | None = None,
        retryable_error_codes: Iterable[StatusCode] | None = None,
        *,
        meter_provider: MeterProvider | None = None,
    ):
        """Resolve the metrics-specific configuration and open the gRPC channel.

        The parameters are documented on the class.
        """
        insecure_metrics = environ.get(OTEL_EXPORTER_OTLP_METRICS_INSECURE)
        if insecure is None and insecure_metrics is not None:
            insecure = insecure_metrics.lower() == "true"

        if not insecure and environ.get(OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE) is not None:
            credentials = _get_credentials(
                credentials,
                _OTEL_PYTHON_EXPORTER_OTLP_GRPC_METRICS_CREDENTIAL_PROVIDER,
                OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
                OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
                OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
            )

        environ_timeout = _timeout_from_env(OTEL_EXPORTER_OTLP_METRICS_TIMEOUT)

        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_METRICS_COMPRESSION) if compression is None else compression
        )

        self._common_configuration(preferred_temporality, preferred_aggregation)

        OTLPExporterMixin.__init__(
            self,
            stub=MetricsServiceStub,
            result=MetricExportResult,
            endpoint=endpoint or environ.get(OTEL_EXPORTER_OTLP_METRICS_ENDPOINT),
            insecure=insecure,
            credentials=credentials,
            headers=headers or environ.get(OTEL_EXPORTER_OTLP_METRICS_HEADERS),
            timeout=timeout or environ_timeout,
            compression=compression,
            channel_options=channel_options,
            retryable_error_codes=retryable_error_codes,
            component_type=OtelComponentTypeValues.OTLP_GRPC_METRIC_EXPORTER,
            signal="metrics",
            meter_provider=meter_provider,
        )

        self._max_export_batch_size: int | None = max_export_batch_size

    def _translate_data(  # type: ignore [reportIncompatibleMethodOverride]
        self, data: MetricsData
    ) -> ExportMetricsServiceRequest:
        """Encode collected metrics as an OTLP metrics export request.

        Args:
            data: Metrics collected by the SDK, already grouped by resource
                and instrumentation scope.

        Returns:
            The export request to send over the gRPC channel.
        """
        return encode_metrics(data)

    def _count_data(self, data: MetricsData):
        """Count the data points in a collection, for the exporter's own metrics.

        Args:
            data: Metrics collected by the SDK.

        Returns:
            The total number of data points across every metric of every
            instrumentation scope of every resource, which is not the number
            of metrics.
        """
        num_items = 0

        for resource_metrics in data.resource_metrics:
            for scope_metrics in resource_metrics.scope_metrics:
                for metric in scope_metrics.metrics:
                    num_items += len(metric.data.data_points)

        return num_items

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        """Send a collection of metrics to the receiver.

        Called by the metric reader the exporter is installed in. When
        ``max_export_batch_size`` was given to the constructor, the collection
        is split into several requests, each sent separately, and one failed
        request does not stop the remaining ones from being sent.

        Args:
            metrics_data: Metrics collected by the SDK.
            timeout_millis: Timeout in milliseconds. It is accepted for
                interface compatibility and is not used: the deadline comes
                from the ``timeout`` given to the constructor.
            kwargs: Accepted and ignored.

        Returns:
            ``MetricExportResult.SUCCESS`` when every request was accepted,
            and ``MetricExportResult.FAILURE`` when any of them was not.
        """
        # TODO(#2663): OTLPExporterMixin should pass timeout to gRPC
        if self._max_export_batch_size is None:
            return self._export(data=metrics_data)

        export_result = MetricExportResult.SUCCESS

        for split_metrics_data in self._split_metrics_data(metrics_data):
            split_export_result = self._export(data=split_metrics_data)

            if split_export_result is MetricExportResult.FAILURE:
                export_result = MetricExportResult.FAILURE
        return export_result

    def _split_metrics_data(
        self,
        metrics_data: MetricsData,
    ) -> Iterable[MetricsData]:
        """Split a collection into chunks of at most ``max_export_batch_size`` data points.

        The resource and scope grouping is rebuilt in every chunk, so a metric
        whose data points fall on both sides of a chunk boundary appears in
        both chunks, each time carrying only the data points of that chunk. A
        resource, scope or metric left with no data points is dropped rather
        than emitted empty.

        Args:
            metrics_data: Metrics collected by the SDK.

        Yields:
            One collection per chunk, in the order the data points were
            visited. Nothing is yielded when the input holds no data points.
        """
        assert self._max_export_batch_size is not None
        batch_size: int = 0
        split_resource_metrics: list[ResourceMetrics] = []

        for resource_metrics in metrics_data.resource_metrics:
            split_scope_metrics: list[ScopeMetrics] = []
            split_resource_metrics.append(
                replace(
                    resource_metrics,
                    scope_metrics=split_scope_metrics,
                )
            )
            for scope_metrics in resource_metrics.scope_metrics:
                split_metrics: list[Metric] = []
                split_scope_metrics.append(
                    replace(
                        scope_metrics,
                        metrics=split_metrics,
                    )
                )
                for metric in scope_metrics.metrics:
                    split_data_points: list[DataPointT] = []
                    split_metrics.append(
                        replace(
                            metric,
                            data=replace(
                                metric.data,
                                data_points=split_data_points,
                            ),
                        )
                    )

                    for data_point in metric.data.data_points:
                        split_data_points.append(data_point)
                        batch_size += 1

                        if batch_size >= self._max_export_batch_size:
                            yield MetricsData(resource_metrics=split_resource_metrics)
                            # Reset all the variables
                            batch_size = 0
                            split_data_points = []
                            split_metrics = [
                                replace(
                                    metric,
                                    data=replace(
                                        metric.data,
                                        data_points=split_data_points,
                                    ),
                                )
                            ]
                            split_scope_metrics = [
                                replace(
                                    scope_metrics,
                                    metrics=split_metrics,
                                )
                            ]
                            split_resource_metrics = [
                                replace(
                                    resource_metrics,
                                    scope_metrics=split_scope_metrics,
                                )
                            ]

                    if not split_data_points:
                        # If data_points is empty remove the whole metric
                        split_metrics.pop()

                if not split_metrics:
                    # If metrics is empty remove the whole scope_metrics
                    split_scope_metrics.pop()

            if not split_scope_metrics:
                # If scope_metrics is empty remove the whole resource_metrics
                split_resource_metrics.pop()

        if batch_size > 0:
            yield MetricsData(resource_metrics=split_resource_metrics)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Shut down the exporter and close its gRPC channel.

        Args:
            timeout_millis: Timeout in milliseconds, accepted for interface
                compatibility and not used.
            kwargs: Accepted and ignored.
        """
        OTLPExporterMixin.shutdown(self, timeout_millis=timeout_millis)

    def set_meter_provider(self, meter_provider: MeterProvider):
        """Rebuild the exporter's own self-observability metrics against another meter provider.

        Call this when the meter provider to record those metrics with was not
        known at the time the exporter was constructed. This does not change
        where the exported metrics go, only where the exporter's own metrics
        are recorded.

        Args:
            meter_provider: Meter provider to record the exporter's own
                metrics with.
        """
        return self._set_meter_provider(meter_provider)

    @property
    def _exporting(self) -> str:
        """Name of the signal, used in the retry and failure log messages.

        Returns:
            The string ``metrics``.
        """
        return "metrics"

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing.

        Args:
            timeout_millis: Timeout in milliseconds, accepted for interface
                compatibility and not used.

        Returns:
            ``True``, always, since there is never anything left to flush.
        """
        return True
