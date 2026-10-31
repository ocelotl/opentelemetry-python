# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Metric exporter for the OTLP JSON over HTTP wire format.

:class:`~opentelemetry.exporter.otlp.json.http.metric_exporter.OTLPMetricExporter`
serializes the metrics a metric reader collected to OTLP JSON and posts them to
an OTLP/HTTP endpoint. Register it with ``PeriodicExportingMetricReader``
instead of calling it directly.

The exporter also decides, for the metric reader that holds it, which
aggregation temporality and which default histogram aggregation apply to each
instrument kind. A second reader on the same meter provider, holding a
different exporter, keeps its own preferences. Both preferences come from the
constructor arguments and from the
``OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE`` and
``OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION`` environment
variables.
"""

import logging
from collections.abc import Mapping
from typing import overload

from opentelemetry.exporter.http.transport._base import BaseHTTPTransport
from opentelemetry.exporter.otlp.common._aggregation import (
    _get_aggregation,
    _get_temporality,
)
from opentelemetry.exporter.otlp.common.http import (
    Compression,
    _OTLPHTTPClient,
)
from opentelemetry.exporter.otlp.json.common._internal.metrics_encoder import (
    encode_metrics,
    split_metrics_data,
)
from opentelemetry.exporter.otlp.json.http._internal import (
    _build_transport,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExporter,
    MetricExportResult,
    MetricsData,
)
from opentelemetry.sdk.metrics.view import Aggregation

_DEFAULT_METRICS_EXPORT_PATH = "v1/metrics"

_logger = logging.getLogger(__name__)


class OTLPMetricExporter(MetricExporter):
    """Exports metrics as OTLP JSON over HTTP.

    Each call to :meth:`export` encodes the collection it is handed and posts
    it, as one request or as several when ``max_export_batch_size`` is set. A
    transient failure is retried over at most six attempts and for no longer
    than the timeout. An attempt that ends in a connection error is re-sent
    once immediately before the next attempt is counted, so one request can
    leave this process up to twelve times. The wait between attempts doubles
    each time and is then multiplied by a random factor between 0.8 and 1.2; a
    retryable response carrying a ``Retry-After`` header the client can read,
    as a number of seconds or as an HTTP date, replaces that wait with the
    header's value. A wait longer than the time left in the timeout ends the
    request rather than being served. A permanent failure is logged and
    reported to the caller, which drops the collection.

    Every argument may be left as ``None``, but the fallback that follows is
    not the same for all of them. ``endpoint``, ``certificate_file``,
    ``client_key_file``, ``client_certificate_file``, ``headers``, ``timeout``
    and ``compression`` are taken from the per-signal
    ``OTEL_EXPORTER_OTLP_METRICS_*`` environment variable, then from the generic
    ``OTEL_EXPORTER_OTLP_*`` variable, then from a default.
    ``preferred_temporality`` and ``preferred_aggregation`` have a per-signal
    environment variable and no generic one. ``max_export_batch_size`` and
    ``_transport`` have no environment variable at all. All settings are
    resolved once, when the exporter is constructed; changing the environment
    afterwards has no effect.

    Args:
        endpoint: Full URL of the OTLP/HTTP signal endpoint, including the signal
            path. Example: ``http://collector:4318/v1/metrics``. For a base URL without a
            signal path, set the ``OTEL_EXPORTER_OTLP_ENDPOINT`` environment variable.
        certificate_file: Path to the certificate authority bundle used to
            verify the server. When none is configured, the server is still
            verified, against the default trust store.
        client_key_file: Path to the private key of the client certificate,
            for mutual TLS. Ignored unless ``client_certificate_file`` is
            configured as well.
        client_certificate_file: Path to the client certificate presented for
            mutual TLS.
        headers: Headers added to every request. They are merged over the
            headers parsed from the environment, and their names are lowercased
            so that a name already present is replaced rather than sent twice.
            The ``content-type`` and ``user-agent`` headers this exporter sets
            can be overridden this way.
        timeout: Seconds one request may take, the retries of that request
            included. When ``max_export_batch_size`` splits a collection into
            several requests, each of them is given this budget afresh, so a
            whole export can take this long multiplied by the number of
            requests. The default is 10 seconds.
        compression: Compression applied to the request body. The default is
            ``Compression.NONE``, which sends the JSON uncompressed.
        preferred_temporality: Aggregation temporality per instrument class,
            overriding the preference read from
            ``OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE``. An instrument
            class left out of the mapping keeps the temporality that preference
            gives it, so a partial mapping is enough to change one instrument
            class.
        preferred_aggregation: Aggregation per instrument class, overriding the
            histogram aggregation read from
            ``OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION``. Only
            ``Histogram`` has a default to override; any other instrument class
            named here adds an aggregation that would otherwise come from the
            SDK.
        max_export_batch_size: Largest number of data points to put in one
            request. The collection is split across as many requests as that
            takes, and the first failing request abandons the rest. ``None``,
            the default, sends the whole collection as a single request.
        _transport: Pre-built HTTP transport to send requests through. It
            replaces the transport that the certificate and key arguments would
            otherwise configure, and exists so that tests can observe requests
            without opening a socket.
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
        compression: Compression | None = None,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
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
        compression: Compression | None = None,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
        *,
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
        compression: Compression | None = None,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
        *,
        _transport: BaseHTTPTransport | None = None,
    ) -> None:
        """Resolve the exporter settings and open the HTTP transport.

        The parameters are documented on the class, which is what the API
        reference renders.
        """
        MetricExporter.__init__(
            self,
            preferred_temporality=_get_temporality(preferred_temporality),
            preferred_aggregation=_get_aggregation(preferred_aggregation),
        )
        transport = _transport or _build_transport(
            certificate_file,
            client_key_file,
            client_certificate_file,
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
        )
        self._client = _OTLPHTTPClient(
            transport=transport,
            endpoint=endpoint
            or _resolve_endpoint(
                OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
                _DEFAULT_METRICS_EXPORT_PATH,
            ),
            kind="metrics",
            timeout=timeout if timeout is not None else _resolve_timeout(OTEL_EXPORTER_OTLP_METRICS_TIMEOUT),
            compression=compression
            if compression is not None
            else _resolve_compression(OTEL_EXPORTER_OTLP_METRICS_COMPRESSION),
            headers=_resolve_headers(headers, OTEL_EXPORTER_OTLP_METRICS_HEADERS),
            logger=_logger,
        )
        self._max_export_batch_size = max_export_batch_size
        self._shutdown = False

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        """Encode one metric collection and post it to the endpoint.

        The collection is encoded once and then split into requests of at most
        ``max_export_batch_size`` data points each. The requests are sent one
        after another, and the first one that fails ends the call, leaving the
        data points after it unsent. The call blocks until every request has
        been answered or has exhausted its own timeout.

        A collection that cannot be encoded fails as a whole: the error is
        logged, nothing is sent, and the call reports failure. That guard
        covers the encoding step alone. An error raised afterwards, while the
        encoded collection is split and each request serialized to JSON, is
        not caught here: it propagates to the caller, and the requests already
        sent are not retracted. After :meth:`shutdown` has been called the
        collection is dropped with a warning instead of being exported.

        Args:
            metrics_data: The metrics collected by the metric reader that owns
                this exporter.
            timeout_millis: Accepted for compatibility with the
                ``MetricExporter`` interface and ignored. The timeout that
                applies is the one resolved when the exporter was constructed.
            **kwargs: Accepted for compatibility with the ``MetricExporter``
                interface and ignored.

        Returns:
            ``MetricExportResult.SUCCESS`` when every request was answered with
            a 2xx or 3xx status, and ``MetricExportResult.FAILURE`` otherwise.
            Failure is final: this method does not ask the caller to retry,
            because the retries have already happened inside it.
        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return MetricExportResult.FAILURE
        try:
            export_request = encode_metrics(metrics_data)
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            _logger.error("Failed to encode metrics: %s", error)
            return MetricExportResult.FAILURE
        for request in split_metrics_data(export_request, self._max_export_batch_size):
            export_result = self._client.export(request.to_json().encode())
            if not export_result.success:
                return MetricExportResult.FAILURE
        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Close the HTTP transport and refuse any further export.

        An export already in progress stops retrying as soon as it notices the
        shutdown, and reports failure. A second call logs a warning and does
        nothing, so the method is safe to call from more than one place.

        Args:
            timeout_millis: Accepted for compatibility with the
                ``MetricExporter`` interface and ignored.
            **kwargs: Accepted for compatibility with the ``MetricExporter``
                interface and ignored.
        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._client.shutdown()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Report that there is nothing left to flush.

        :meth:`export` sends every request before it returns, so this exporter
        holds no queue of its own. Collecting and exporting on demand is the
        job of the metric reader that owns the exporter.

        Args:
            timeout_millis: Accepted for compatibility with the
                ``MetricExporter`` interface and ignored.

        Returns:
            ``True``, always.
        """
        return True
