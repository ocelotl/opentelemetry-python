# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Metric exporter that sends OTLP over HTTP with a protobuf body.

:class:`OTLPMetricExporter` encodes the metrics a reader collected as an
``ExportMetricsServiceRequest`` and posts it to a collector. It is registered
with :class:`~opentelemetry.sdk.metrics.export.PeriodicExportingMetricReader`,
which decides how often a collection happens and calls
:meth:`OTLPMetricExporter.export` with the result.

Unlike the span and log exporters, this one can split a single collection
across several requests: setting ``max_export_batch_size`` to a positive number
caps the number of data points in one request, and the remaining data points go
into further requests sent one after another. A value of 0 or a negative value
is not a disabled limit, and the ``max_export_batch_size`` entry on
:class:`OTLPMetricExporter` records what each of those does instead.

``DEFAULT_METRICS_EXPORT_PATH`` is the path appended to a base endpoint that
carries no signal path of its own. The other module-level ``DEFAULT_`` names
are kept for callers that import them. The resolution code reads its own
fallbacks from ``opentelemetry.exporter.otlp.proto.http._common``, so rebinding
one of those other three names does not change what an exporter does.
Rebinding ``DEFAULT_METRICS_EXPORT_PATH`` does, because the constructor passes
that name itself to the resolution code every time an exporter is built.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterable, Mapping
from typing import (  # noqa: F401
    TYPE_CHECKING,
    Any,
    Optional,
    overload,
)

from typing_extensions import deprecated

from opentelemetry.exporter.otlp.common import http as _http
from opentelemetry.exporter.otlp.common._aggregation import (
    _get_aggregation,
    _get_temporality,
)
from opentelemetry.exporter.otlp.common._exporter_metrics import (
    create_exporter_metrics,
)
from opentelemetry.exporter.otlp.proto.common._internal import (
    _get_resource_data,
)
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._common import (
    _DEFAULT_MAX_REQUEST_SIZE,
    RequestPayloadTooLargeError,
    _build_transport,
    _is_request_too_large,
    _load_session_from_envvar,
    _normalize_compression,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    AnyValue,
    ArrayValue,
    InstrumentationScope,
    KeyValue,
    KeyValueList,
)
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2
from opentelemetry.proto.resource.v1.resource_pb2 import Resource  # noqa: F401
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as PB2Resource,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation
from opentelemetry.sdk.metrics.export import (  # noqa: F401
    AggregationTemporality,
    Gauge,
    MetricExporter,
    MetricExportResult,
    MetricsData,
    Sum,
)
from opentelemetry.sdk.metrics.export import (  # noqa: F401
    Histogram as HistogramType,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.semconv.attributes.http_attributes import (
    HTTP_RESPONSE_STATUS_CODE,
)

if TYPE_CHECKING:
    import requests

    from opentelemetry.exporter.http.transport._base import BaseHTTPTransport

_logger = logging.getLogger(__name__)


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_METRICS_EXPORT_PATH = "v1/metrics"
DEFAULT_TIMEOUT = 10  # in seconds


class OTLPMetricExporter(MetricExporter):
    """OTLP HTTP metrics exporter.

    ``endpoint``, the three TLS file paths, ``timeout`` and ``compression`` may
    each be left unset, in which case the value is resolved from the
    environment: first the per-signal ``OTEL_EXPORTER_OTLP_METRICS_*`` variable,
    then the signal-independent ``OTEL_EXPORTER_OTLP_*`` one, then a built-in
    fallback. An argument given here overrides both variables. ``headers`` is
    merged key by key over the headers of whichever one of the two variables is
    used, but the two variables do not merge with each other: the per-signal one
    replaces the signal-independent one entirely when it is set.

    ``max_export_batch_size``, ``max_request_size`` and ``meter_provider`` have
    no environment variable of either kind, so they can only be set here.
    ``preferred_temporality``, ``preferred_aggregation`` and ``session`` each
    follow a rule of their own, given in their entries below.

    Args:
        endpoint: Full URL of the OTLP/HTTP signal endpoint, including the signal
            path. Example: ``http://collector:4318/v1/metrics``. For a base URL without a
            signal path, set the ``OTEL_EXPORTER_OTLP_ENDPOINT`` environment variable.
        certificate_file: Path to the certificate file to use for any TLS
        client_key_file: Path to the client key file to use for any TLS. It is
            used only together with ``client_certificate_file``.
        client_certificate_file: Path to the client certificate file to use for any TLS
        headers: Headers to be sent with HTTP requests at export. They are
            merged key by key over the headers parsed from the environment,
            which are in turn merged over the ``Content-Type`` and
            ``User-Agent`` this exporter always sets. A header the environment
            supplies and this argument does not is therefore still sent. Keys
            are lowercased before merging, so a key given in a different case
            replaces the earlier value rather than adding a second header.
        timeout: Timeout in seconds for export. It covers the retries and the
            waits between them, not one HTTP attempt, and it applies to each
            request separately when a collection is split into several.
        compression: Compression to use; one of none, gzip, deflate
        session: Requests session to use at export. When it is not given and a
            credential provider is configured, the session that provider
            returns is used instead. The provider is named by the
            signal-independent
            ``OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER``, and only if
            that is unset by the per-signal
            ``OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER``,
            which is the reverse of the precedence every other setting follows.
        preferred_temporality: Map of preferred temporality for each metric type.
            See `opentelemetry.sdk.metrics.export.MetricReader` for more details on what
            preferred temporality is. This does not replace the map that
            ``OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE`` selects, it is
            merged over it entry by entry, and that variable has no
            signal-independent counterpart.
        preferred_aggregation: Map of preferred aggregation for each metric type.
            See `opentelemetry.sdk.metrics.export.MetricReader` for more details on what
            preferred aggregation is. It is merged the same way over the map
            that ``OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION``
            selects, which likewise has no signal-independent counterpart.
        max_export_batch_size: Maximum number of data points to export in a single request.
            If not set there is no limit to the number of data points in a request.
            If it is set and the number of data points exceeds the max, the request will be split.
            A non-positive value is not a way to disable the limit. Setting it
            to 0 makes every export drop its data points and report success,
            and a negative value puts one data point in each request. Leave it
            unset to send a collection as one request.
        max_request_size: Maximum size in bytes of a serialized request, measured before
            compression. A request exceeding this size is dropped before being sent. Defaults
            to 64 MiB; a value of 0 (or any non-positive value) disables the limit. Requests
            are sized after any ``max_export_batch_size`` splitting; a batch whose serialized
            request still exceeds this limit is dropped as a whole and recorded as a failed
            export. Reduce ``max_export_batch_size`` (or raise/disable this limit) if batches
            may approach it.
        meter_provider: MeterProvider used for the exporter's own metrics.
            Those metrics are only recorded when
            ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED`` is set to ``true``.
        _transport: Private, and shown here only because it appears in the
            second overload above. It replaces the transport that would
            otherwise be built, which leaves the three TLS file paths,
            ``session`` and the credential provider unused. The tests pass it
            to intercept requests. It is not part of the public API.
    """

    @overload
    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | _http.Compression | None = None,
        session: requests.Session | None = None,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
        *,
        max_request_size: int | None = None,
        meter_provider: MeterProvider | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: None = None,
        client_key_file: None = None,
        client_certificate_file: None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | _http.Compression | None = None,
        session: requests.Session | None = None,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
        *,
        max_request_size: int | None = None,
        meter_provider: MeterProvider | None = None,
        _transport: BaseHTTPTransport,
    ) -> None: ...

    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | _http.Compression | None = None,
        session: requests.Session | None = None,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
        *,
        max_request_size: int | None = None,
        meter_provider: MeterProvider | None = None,
        _transport: BaseHTTPTransport | None = None,
    ) -> None:
        """Resolve the configuration and open the HTTP client.

        The parameters are documented on the class.
        """
        MetricExporter.__init__(
            self,
            preferred_temporality=_get_temporality(preferred_temporality),
            preferred_aggregation=_get_aggregation(preferred_aggregation),
        )
        self._endpoint = endpoint or _resolve_endpoint(OTEL_EXPORTER_OTLP_METRICS_ENDPOINT, DEFAULT_METRICS_EXPORT_PATH)
        self._compression = _normalize_compression(compression) or _resolve_compression(
            OTEL_EXPORTER_OTLP_METRICS_COMPRESSION
        )
        transport = _transport or _build_transport(
            certificate_file,
            client_key_file,
            client_certificate_file,
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
            session=session or _load_session_from_envvar(_OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER),
        )
        self._client = _http._OTLPHTTPClient(
            transport=transport,
            endpoint=self._endpoint,
            kind="metrics",
            timeout=timeout if timeout is not None else _resolve_timeout(OTEL_EXPORTER_OTLP_METRICS_TIMEOUT),
            compression=self._compression,
            headers=_resolve_headers(headers, OTEL_EXPORTER_OTLP_METRICS_HEADERS),
            logger=_logger,
        )
        self._max_export_batch_size: int | None = max_export_batch_size
        self._max_request_size = _DEFAULT_MAX_REQUEST_SIZE if max_request_size is None else max_request_size
        self._shutdown = False

        self._metrics = create_exporter_metrics(
            OtelComponentTypeValues.OTLP_HTTP_METRIC_EXPORTER,
            "metrics",
            self._endpoint,
            meter_provider,
            os.environ.get(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED, "").strip().lower() == "true",
        )

    def _export_batch(
        self,
        export_request: ExportMetricsServiceRequest,
    ) -> MetricExportResult:
        """Serialize one already-encoded request and post it.

        This is the single place where the exporter's own metrics are recorded,
        so a collection split into several requests records one operation per
        request rather than one for the whole collection.

        Args:
            export_request: One request, already encoded from metrics data and
                already split if ``max_export_batch_size`` called for it.

        Returns:
            ``MetricExportResult.SUCCESS`` when the collector accepted the
            request. ``MetricExportResult.FAILURE`` when the serialized request
            exceeds ``max_request_size``, or when the request failed and could
            not be retried within the timeout. The data points in the request
            are dropped in either failure case.
        """
        with self._metrics.export_operation(_count_data_points(export_request)) as result:
            serialized_data = export_request.SerializeToString()
            if _is_request_too_large(serialized_data, self._max_request_size):
                _logger.warning(
                    "Dropping metrics batch: serialized size %d bytes exceeds max_request_size %d bytes.",
                    len(serialized_data),
                    self._max_request_size,
                )
                result.error = RequestPayloadTooLargeError(
                    f"Serialized metrics request size {len(serialized_data)} "
                    f"bytes exceeds max_request_size "
                    f"{self._max_request_size} bytes."
                )
                return MetricExportResult.FAILURE
            export_result = self._client.export(serialized_data)
            if not export_result.success:
                result.error = export_result.error
                result.error_attrs = (
                    {HTTP_RESPONSE_STATUS_CODE: export_result.status_code}
                    if export_result.status_code is not None
                    else None
                )
                return MetricExportResult.FAILURE
        return MetricExportResult.SUCCESS

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float | None = 10000,
        **kwargs,
    ) -> MetricExportResult:
        """Encode a collection of metrics and post it to the collector.

        When ``max_export_batch_size`` is set, the encoded request is split and
        the resulting requests are sent one after another, stopping at the
        first one that fails. The data points of the requests that had already
        succeeded stay exported, so a partial failure leaves the collector
        holding part of the collection.

        Args:
            metrics_data: The metrics a reader collected.
            timeout_millis: Accepted because
                :class:`~opentelemetry.sdk.metrics.export.MetricExporter` declares it, and
                ignored. The deadline that is actually applied is the
                ``timeout`` the exporter was constructed with.
            **kwargs: Accepted for the same reason and ignored.

        Returns:
            ``MetricExportResult.SUCCESS`` when every request was accepted.
            ``MetricExportResult.FAILURE`` when the exporter has already been
            shut down, when the metrics could not be encoded, or when any one
            request failed. No exception is raised, because a metric reader
            calls this on its own thread.
        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return MetricExportResult.FAILURE

        try:
            export_request = encode_metrics(metrics_data)
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            _logger.error("Failed to encode metrics batch: %s", error)
            return MetricExportResult.FAILURE

        # If no batch size configured, export as single batch with retries as configured
        if self._max_export_batch_size is None:
            return self._export_batch(export_request)

        for batch in _split_metrics_data(export_request, self._max_export_batch_size):
            export_result = self._export_batch(batch)
            if export_result != MetricExportResult.SUCCESS:
                return MetricExportResult.FAILURE

        # Only returns SUCCESS if all batches succeeded
        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Close the HTTP client and reject any further export.

        An export already in progress on another thread is interrupted at its
        next retry, which abandons the request it was sending and every request
        the split had not reached yet. A second call logs a warning and does
        nothing, so shutting down twice is harmless.

        Args:
            timeout_millis: Accepted because
                :class:`~opentelemetry.sdk.metrics.export.MetricExporter` declares it, and
                ignored, since closing the client does not wait.
            **kwargs: Accepted for the same reason and ignored.
        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._client.shutdown()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing.

        Args:
            timeout_millis: Accepted because :class:`~opentelemetry.sdk.metrics.export.MetricExporter`
                declares it, and ignored, since there is nothing to wait for.

        Returns:
            True, always.
        """
        return True

    def set_meter_provider(self, meter_provider: MeterProvider) -> None:
        """Rebuild the exporter's own metrics against another meter provider.

        The instruments created when the exporter was constructed are
        discarded and new ones are created from ``meter_provider``, which
        resets the in-flight count they were tracking. Whether anything is
        recorded at all still depends on
        ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED``, which is read again here.

        No code path inside the SDK reaches this method. A meter provider calls
        ``MetricReader._set_meter_provider`` on the readers registered with it
        and nothing on the exporter behind them, and
        :class:`~opentelemetry.sdk.metrics.export.MetricExporter` declares no
        method of this name for this one to override. It is here so that a
        caller that built the exporter before its meter provider existed can
        point the exporter at that provider afterwards, instead of leaving it
        on the global one.

        Args:
            meter_provider: The provider the new instruments are created from.
        """
        self._metrics = create_exporter_metrics(
            OtelComponentTypeValues.OTLP_HTTP_METRIC_EXPORTER,
            "metrics",
            self._endpoint,
            meter_provider,
            os.environ.get(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED, "").strip().lower() == "true",
        )


def _count_data_points(export_request: ExportMetricsServiceRequest) -> int:
    """Count the number of data points in an encoded metrics export request.

    This is the number the exporter's own metrics report as exported or
    in flight, which is why it counts data points rather than metrics: a single
    metric carries one data point per attribute combination.

    Args:
        export_request: An encoded request to walk.

    Returns:
        The total across every resource, scope and metric in the request. A
        metric whose ``data`` oneof is unset contributes nothing and is skipped
        silently, since it carries no data points to count.
    """
    count = 0
    for resource_metrics in export_request.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                field_name = metric.WhichOneof("data")
                if field_name:
                    count += len(getattr(metric, field_name).data_points)
    return count


def _split_metrics_data(
    metrics_data: ExportMetricsServiceRequest,
    max_export_batch_size: int | None = None,
) -> Iterable[ExportMetricsServiceRequest]:
    """Splits metrics data into several ExportMetricsServiceRequest (copies protobuf originals),
    based on configured data point max export batch size.

    The split counts data points, not metrics, and the count runs across the
    whole request rather than restarting per metric, so a single metric with
    more data points than the limit is itself divided across several requests.
    The resource, the scope and the metric's name, description and unit are
    repeated in every request that carries part of that metric, so each request
    stands on its own.

    This is a generator, so the splitting happens as the caller consumes it and
    the whole split is never held in memory at once.

    Args:
        metrics_data: metrics object based on HTTP protocol buffer definition
        max_export_batch_size: Largest number of data points to put in one
            request. A request holding at least one data point and fewer than
            this is yielded as a single rebuilt copy, carrying the resource,
            the scope and each metric's name, description, unit and data
            points, and nothing else the original metric held. A request
            holding no data point at all yields nothing. Passing 0 or None
            yields nothing at all either, because the generator returns before
            its first ``yield``.

    Yields:
        One ``ExportMetricsServiceRequest`` per batch, each built from new
        ``pb2.ResourceMetrics``, ``pb2.ScopeMetrics`` and ``pb2.Metric``
        objects rather than from the ones in ``metrics_data``. A metric whose
        ``data`` oneof is unset is reported with a warning and left out, so the
        yielded requests may hold fewer metrics than the original. It carries
        no data points, so no data point is lost with it.
    """
    if not max_export_batch_size:
        return metrics_data

    batch_size: int = 0
    # Stores split metrics data as editable references
    # used to write batched pb2 objects for export when finalized
    split_resource_metrics = []

    for resource_metrics in metrics_data.resource_metrics:
        split_scope_metrics = []
        split_resource_metrics.append(
            {
                "resource": resource_metrics.resource,
                "schema_url": resource_metrics.schema_url,
                "scope_metrics": split_scope_metrics,
            }
        )

        for scope_metrics in resource_metrics.scope_metrics:
            split_metrics = []
            split_scope_metrics.append(
                {
                    "scope": scope_metrics.scope,
                    "schema_url": scope_metrics.schema_url,
                    "metrics": split_metrics,
                }
            )

            for metric in scope_metrics.metrics:
                split_data_points = []
                field_name = metric.WhichOneof("data")
                if not field_name:
                    _logger.warning("Tried to split and export an unsupported metric type. Skipping.")
                    continue

                # Get data container using field name
                # and build metric dictionary dynamically for conciseness
                data_container = getattr(metric, field_name)
                metric_dict = {
                    "name": metric.name,
                    "description": metric.description,
                    "unit": metric.unit,
                    field_name: {
                        "data_points": split_data_points,
                    },
                }
                if hasattr(data_container, "aggregation_temporality"):
                    metric_dict[field_name]["aggregation_temporality"] = data_container.aggregation_temporality
                if hasattr(data_container, "is_monotonic"):
                    metric_dict[field_name]["is_monotonic"] = data_container.is_monotonic
                split_metrics.append(metric_dict)

                current_data_points = data_container.data_points
                for data_point in current_data_points:
                    split_data_points.append(data_point)
                    batch_size += 1

                    if batch_size >= max_export_batch_size:
                        yield ExportMetricsServiceRequest(
                            resource_metrics=_get_split_resource_metrics_pb2(split_resource_metrics)
                        )

                        # Reset all the reference variables with current metrics_data position
                        # minus yielded data_points. Need to clear data_points and keep metric
                        # to avoid duplicate data_point export
                        batch_size = 0
                        split_data_points = []

                        # Rebuild metric dict generically using same approach as initial creation
                        field_name = metric.WhichOneof("data")
                        if field_name is None:
                            _logger.warning("Tried to split and export an unsupported metric type. Skipping.")
                            continue
                        data_container = getattr(metric, field_name)
                        metric_dict = {
                            "name": metric.name,
                            "description": metric.description,
                            "unit": metric.unit,
                            field_name: {
                                "data_points": split_data_points,
                            },
                        }
                        if hasattr(data_container, "aggregation_temporality"):
                            metric_dict[field_name]["aggregation_temporality"] = data_container.aggregation_temporality
                        if hasattr(data_container, "is_monotonic"):
                            metric_dict[field_name]["is_monotonic"] = data_container.is_monotonic

                        split_metrics = [metric_dict]
                        split_scope_metrics = [
                            {
                                "scope": scope_metrics.scope,
                                "schema_url": scope_metrics.schema_url,
                                "metrics": split_metrics,
                            }
                        ]
                        split_resource_metrics = [
                            {
                                "resource": resource_metrics.resource,
                                "schema_url": resource_metrics.schema_url,
                                "scope_metrics": split_scope_metrics,
                            }
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
        yield ExportMetricsServiceRequest(resource_metrics=_get_split_resource_metrics_pb2(split_resource_metrics))


def _get_split_resource_metrics_pb2(
    split_resource_metrics: list[dict],
) -> list[pb2.ResourceMetrics]:
    """Helper that returns a list of pb2.ResourceMetrics objects based on split_resource_metrics.
    Example input:

    ```python
    [
        {
            "resource": <opentelemetry.proto.resource.v1.resource_pb2.Resource>,
            "schema_url": "http://foo-bar",
            "scope_metrics": [
                "scope": <opentelemetry.proto.common.v1.InstrumentationScope>,
                "schema_url": "http://foo-baz",
                "metrics": [
                    {
                        "name": "apples",
                        "description": "number of apples purchased",
                        "sum": {
                            "aggregation_temporality": 1,
                            "is_monotonic": "false",
                            "data_points": [
                                {
                                    start_time_unix_nano: 1000
                                    time_unix_nano: 1001
                                    exemplars {
                                        time_unix_nano: 1002
                                        span_id: "foo-span"
                                        trace_id: "foo-trace"
                                        as_int: 5
                                    }
                                    as_int: 5
                                }
                            ]
                        }
                    },
                ],
            ],
        },
    ]
    ```

    Args:
        split_resource_metrics: A list of dict representations of ResourceMetrics,
            ScopeMetrics, Metric, and data points.

    Returns:
        List[pb2.ResourceMetrics]: A list of pb2.ResourceMetrics objects containing
            pb2.ScopeMetrics, pb2.Metric, and data points
    """
    split_resource_metrics_pb = []
    for resource_metrics in split_resource_metrics:
        new_resource_metrics = pb2.ResourceMetrics(
            resource=resource_metrics.get("resource"),
            scope_metrics=[],
            schema_url=resource_metrics.get("schema_url") or "",
        )
        for scope_metrics in resource_metrics.get("scope_metrics", []):
            new_scope_metrics = pb2.ScopeMetrics(
                scope=scope_metrics.get("scope"),
                metrics=[],
                schema_url=scope_metrics.get("schema_url") or "",
            )

            for metric in scope_metrics.get("metrics", []):
                new_metric = None
                data_points = []

                if "sum" in metric:
                    new_metric = pb2.Metric(
                        name=metric.get("name"),
                        description=metric.get("description"),
                        unit=metric.get("unit"),
                        sum=pb2.Sum(
                            data_points=[],
                            aggregation_temporality=metric.get("sum").get("aggregation_temporality"),
                            is_monotonic=metric.get("sum").get("is_monotonic"),
                        ),
                    )
                    data_points = metric.get("sum").get("data_points")
                elif "histogram" in metric:
                    new_metric = pb2.Metric(
                        name=metric.get("name"),
                        description=metric.get("description"),
                        unit=metric.get("unit"),
                        histogram=pb2.Histogram(
                            data_points=[],
                            aggregation_temporality=metric.get("histogram").get("aggregation_temporality"),
                        ),
                    )
                    data_points = metric.get("histogram").get("data_points")
                elif "exponential_histogram" in metric:
                    new_metric = pb2.Metric(
                        name=metric.get("name"),
                        description=metric.get("description"),
                        unit=metric.get("unit"),
                        exponential_histogram=pb2.ExponentialHistogram(
                            data_points=[],
                            aggregation_temporality=metric.get("exponential_histogram").get("aggregation_temporality"),
                        ),
                    )
                    data_points = metric.get("exponential_histogram").get("data_points")
                elif "gauge" in metric:
                    new_metric = pb2.Metric(
                        name=metric.get("name"),
                        description=metric.get("description"),
                        unit=metric.get("unit"),
                        gauge=pb2.Gauge(
                            data_points=[],
                        ),
                    )
                    data_points = metric.get("gauge").get("data_points")
                elif "summary" in metric:
                    new_metric = pb2.Metric(
                        name=metric.get("name"),
                        description=metric.get("description"),
                        unit=metric.get("unit"),
                        summary=pb2.Summary(
                            data_points=[],
                        ),
                    )
                    data_points = metric.get("summary").get("data_points")
                else:
                    _logger.warning("Tried to split and export an unsupported metric type. Skipping.")
                    continue

                # Append data points generically using the field name from the metric dict
                for field_name in [
                    "sum",
                    "histogram",
                    "exponential_histogram",
                    "gauge",
                    "summary",
                ]:
                    if field_name in metric:
                        metric_data_container = getattr(new_metric, field_name)
                        for data_point in data_points:
                            metric_data_container.data_points.append(data_point)
                        break

                new_scope_metrics.metrics.append(new_metric)
            new_resource_metrics.scope_metrics.append(new_scope_metrics)
        split_resource_metrics_pb.append(new_resource_metrics)
    return split_resource_metrics_pb


@deprecated(
    "Use one of the encoders from opentelemetry-exporter-otlp-proto-common instead. Deprecated since version 1.18.0.",
)
def get_resource_data(
    sdk_resource_scope_data: dict[SDKResource, Any],  # ResourceDataT?
    resource_class: Callable[..., PB2Resource],
    name: str,
) -> list[PB2Resource]:
    """Group SDK data by resource and wrap each group in a protobuf message.

    Deprecated since version 1.18.0. The encoders in
    ``opentelemetry-exporter-otlp-proto-common`` do this as part of encoding a
    whole signal, so there is no reason to call this directly. It stays here
    only so that code written against the old import path keeps working, and it
    forwards to ``opentelemetry.exporter.otlp.proto.common._internal._get_resource_data``
    without adding anything.

    Args:
        sdk_resource_scope_data: Maps each SDK resource to a dictionary of the
            already-encoded scope data collected under it. Only the values of
            that dictionary are used, so its keys may be anything.
        resource_class: The protobuf message class to build, one of
            ``ResourceSpans``, ``ResourceMetrics`` or ``ResourceLogs``. It is
            called with a ``resource`` keyword and one named after ``name``.
        name: Suffix of that second keyword. Passing ``metrics`` makes the call
            use ``scope_metrics``.

    Returns:
        One message per entry in ``sdk_resource_scope_data``, in iteration
        order. Each carries the resource's encoded attributes, and no schema
        URL, since this function does not pass one on.
    """
    return _get_resource_data(sdk_resource_scope_data, resource_class, name)
