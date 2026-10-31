# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Log record exporter that sends OTLP over HTTP with a protobuf body.

:class:`OTLPLogExporter` encodes a batch of log records as an
``ExportLogsServiceRequest`` and posts it to a collector. It performs no
batching of its own, so it is normally registered with
:class:`~opentelemetry.sdk._logs.export.BatchLogRecordProcessor`, which decides
when a batch is complete and calls :meth:`OTLPLogExporter.export` with it.

The logger this module reports failures through carries a duplicate filter, so
that a log record emitted about a failed export cannot itself fail and emit a
further one without end.

``DEFAULT_LOGS_EXPORT_PATH`` is the path appended to a base endpoint that
carries no signal path of its own. The other module-level ``DEFAULT_`` names
are kept for callers that import them. The resolution code reads its own
fallbacks from ``opentelemetry.exporter.otlp.proto.http._common``, so rebinding
one of those other three names does not change what an exporter does.
Rebinding ``DEFAULT_LOGS_EXPORT_PATH`` does, because the constructor passes
that name itself to the resolution code every time an exporter is built.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, overload

from opentelemetry.exporter.otlp.common import http as _http
from opentelemetry.exporter.otlp.common._exporter_metrics import (
    create_exporter_metrics,
)
from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
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
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)
from opentelemetry.sdk._shared_internal import DuplicateFilter
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
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
# This prevents logs generated when a log fails to be written to generate another log which fails to be written etc. etc.
_logger.addFilter(DuplicateFilter())


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_LOGS_EXPORT_PATH = "v1/logs"
DEFAULT_TIMEOUT = 10  # in seconds


class OTLPLogExporter(LogRecordExporter):
    """OTLP HTTP log exporter.

    ``endpoint``, the three TLS file paths, ``timeout`` and ``compression`` may
    each be left unset, in which case the value is resolved from the
    environment: first the per-signal ``OTEL_EXPORTER_OTLP_LOGS_*`` variable,
    then the signal-independent ``OTEL_EXPORTER_OTLP_*`` one, then a built-in
    fallback. An argument given here overrides both variables. ``headers`` is
    merged key by key over the headers of whichever one of the two variables is
    used, but the two variables do not merge with each other: the per-signal one
    replaces the signal-independent one entirely when it is set.

    ``max_request_size`` and ``meter_provider`` have no environment variable of
    either kind, so they can only be set here. ``session`` reverses the
    precedence above, as its entry explains.

    Args:
        endpoint: Full URL of the OTLP/HTTP signal endpoint, including the signal
            path. Example: ``http://collector:4318/v1/logs``. For a base URL without a
            signal path, set the ``OTEL_EXPORTER_OTLP_ENDPOINT`` environment variable.
        certificate_file: Path to the CA certificate file for TLS.
        client_key_file: Path to the client key file for mTLS. It is used only
            together with ``client_certificate_file``.
        client_certificate_file: Path to the client certificate file for mTLS.
        headers: Headers to send with each export request. They are merged key
            by key over the headers parsed from the environment, which are in
            turn merged over the ``Content-Type`` and ``User-Agent`` this
            exporter always sets. A header the environment supplies and this
            argument does not is therefore still sent. Keys are lowercased
            before merging, so a key given in a different case replaces the
            earlier value rather than adding a second header.
        timeout: Timeout in seconds for each export request. It covers the
            retries and the waits between them, not one HTTP attempt.
        compression: Compression to use; one of none, gzip, deflate.
        session: Requests session to use at export. When it is not given and a
            credential provider is configured, the session that provider
            returns is used instead. The provider is named by the
            signal-independent
            ``OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER``, and only if
            that is unset by the per-signal
            ``OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER``, which
            is the reverse of the precedence every other setting follows.
        max_request_size: Maximum size in bytes of a serialized request,
            measured before compression. A request exceeding this size is
            dropped before being sent. Defaults to 64 MiB; a value of 0 (or
            any non-positive value) disables the limit. Batch processors
            group log records by count rather than serialized size, so a
            batch whose serialized request exceeds this limit is dropped as
            a whole and recorded as a failed export; reduce the processor's
            ``max_export_batch_size`` (or raise/disable this limit) if
            batches may approach it.
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
        *,
        max_request_size: int | None = None,
        meter_provider: MeterProvider | None = None,
        _transport: BaseHTTPTransport | None = None,
    ) -> None:
        """Resolve the configuration and open the HTTP client.

        The parameters are documented on the class. ``_transport`` is private:
        it replaces the transport that would otherwise be built, and the tests
        use it to intercept requests. When it is given, the three TLS file
        paths, ``session`` and the credential provider are all unused, which is
        why the overload that accepts it types the TLS paths as None.
        """
        self._endpoint = endpoint or _resolve_endpoint(OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, DEFAULT_LOGS_EXPORT_PATH)
        self._compression = _normalize_compression(compression) or _resolve_compression(
            OTEL_EXPORTER_OTLP_LOGS_COMPRESSION
        )
        transport = _transport or _build_transport(
            certificate_file,
            client_key_file,
            client_certificate_file,
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
            session=session or _load_session_from_envvar(_OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER),
        )
        self._max_request_size = _DEFAULT_MAX_REQUEST_SIZE if max_request_size is None else max_request_size
        self._client = _http._OTLPHTTPClient(
            transport=transport,
            endpoint=self._endpoint,
            kind="logs",
            timeout=timeout if timeout is not None else _resolve_timeout(OTEL_EXPORTER_OTLP_LOGS_TIMEOUT),
            compression=self._compression,
            headers=_resolve_headers(headers, OTEL_EXPORTER_OTLP_LOGS_HEADERS),
            logger=_logger,
        )
        self._shutdown = False

        self._metrics = create_exporter_metrics(
            OtelComponentTypeValues.OTLP_HTTP_LOG_EXPORTER,
            "logs",
            self._endpoint,
            meter_provider,
            os.environ.get(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED, "").strip().lower() == "true",
        )

    def export(self, batch: Sequence[ReadableLogRecord]) -> LogRecordExportResult:
        """Encode a batch of log records and post it to the collector.

        The call blocks until the collector answers, the configured timeout
        expires or the retries are exhausted. Transient failures are retried
        inside the HTTP client, so a single call may issue several requests.

        Args:
            batch: The log records to send. They are sent as one request,
                whatever their number, since this exporter does no batching of
                its own.

        Returns:
            ``LogRecordExportResult.SUCCESS`` when the collector accepted the
            request. ``LogRecordExportResult.FAILURE`` when the exporter has
            already been shut down, when the batch could not be encoded, when
            its serialized size exceeds ``max_request_size``, or when the
            request failed and could not be retried within the timeout. The
            batch is dropped in every failure case; nothing is kept for a later
            attempt. No exception is raised, because a log record processor
            calls this on its own thread.
        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return LogRecordExportResult.FAILURE

        with self._metrics.export_operation(len(batch)) as result:
            try:
                serialized_data = encode_logs(batch).SerializeToString()
            # pylint: disable-next=broad-exception-caught
            except Exception as error:
                _logger.error("Failed to encode logs batch: %s", error)
                result.error = error
                return LogRecordExportResult.FAILURE

            if _is_request_too_large(serialized_data, self._max_request_size):
                _logger.warning(
                    "Dropping logs batch: serialized size %d bytes exceeds max_request_size %d bytes.",
                    len(serialized_data),
                    self._max_request_size,
                )
                result.error = RequestPayloadTooLargeError(
                    f"Serialized logs request size {len(serialized_data)} "
                    f"bytes exceeds max_request_size "
                    f"{self._max_request_size} bytes."
                )
                return LogRecordExportResult.FAILURE

            export_result = self._client.export(serialized_data)
            if not export_result.success:
                result.error = export_result.error
                result.error_attrs = (
                    {HTTP_RESPONSE_STATUS_CODE: export_result.status_code}
                    if export_result.status_code is not None
                    else None
                )
                return LogRecordExportResult.FAILURE
        return LogRecordExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing.

        Args:
            timeout_millis: Accepted because :class:`~opentelemetry.sdk._logs.export.LogRecordExporter`
                declares it, and ignored, since there is nothing to wait for.

        Returns:
            True, always.
        """
        return True

    def shutdown(self):
        """Close the HTTP client and reject any further export.

        An export already in progress on another thread is interrupted at its
        next retry, which abandons the batch it was sending. A second call logs
        a warning and does nothing, so shutting down twice is harmless.
        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._client.shutdown()
