# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Sequence
from gzip import GzipFile
from io import BytesIO
from logging import getLogger
from os import environ
from random import uniform
from threading import Event
from time import time
from zlib import compress

from requests import Session
from requests.exceptions import ConnectionError, RequestException

from opentelemetry.exporter.otlp.pyproto.common._internal._log_encoder import (
    encode_logs,
)
from opentelemetry.exporter.otlp.pyproto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.exporter.otlp.pyproto.http._common import (
    _is_retryable,
    _load_session_from_envvar,
)
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.util.re import parse_env_headers

_logger = getLogger(__name__)

DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_LOGS_EXPORT_PATH = "v1/logs"
DEFAULT_TIMEOUT = 10
_MAX_RETRYS = 6


class OTLPLogExporter(LogRecordExporter):
    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        session: Session | None = None,
    ):
        self._shutdown_is_occuring = Event()
        self._endpoint = endpoint or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
            _append_logs_path(
                environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, DEFAULT_ENDPOINT)
            ),
        )
        self._certificate_file = certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, True),
        )
        self._client_key_file = client_key_file or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY, None),
        )
        self._client_certificate_file = client_certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE, None),
        )
        self._client_cert = (
            (self._client_certificate_file, self._client_key_file)
            if self._client_certificate_file and self._client_key_file
            else self._client_certificate_file
        )
        headers_string = environ.get(
            OTEL_EXPORTER_OTLP_LOGS_HEADERS,
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = headers or parse_env_headers(headers_string, liberal=True)
        self._timeout = timeout or float(
            environ.get(
                OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env()
        self._session = (
            session
            or _load_session_from_envvar(
                _OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER
            )
            or Session()
        )
        self._session.headers.update(self._headers)
        self._session.headers.update(_OTLP_HTTP_HEADERS)
        self._session.headers.update(self._headers)
        if self._compression is not Compression.NoCompression:
            self._session.headers.update(
                {"Content-Encoding": self._compression.value}
            )
        self._shutdown = False

    def _export(self, serialized_data: bytes, timeout_sec: float | None = None):
        data = serialized_data
        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                gzip_stream.write(serialized_data)
            data = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            data = compress(serialized_data)
        if timeout_sec is None:
            timeout_sec = self._timeout
        try:
            resp = self._session.post(
                url=self._endpoint,
                data=data,
                verify=self._certificate_file,
                timeout=timeout_sec,
                cert=self._client_cert,
            )
        except ConnectionError:
            resp = self._session.post(
                url=self._endpoint,
                data=data,
                verify=self._certificate_file,
                timeout=timeout_sec,
                cert=self._client_cert,
            )
        return resp

    def export(self, batch: Sequence[ReadableLogRecord]) -> LogRecordExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return LogRecordExportResult.FAILURE

        serialized_data = encode_logs(batch).SerializeToString()
        deadline_sec = time() + self._timeout
        for retry_num in range(_MAX_RETRYS):
            backoff_seconds = 2**retry_num * uniform(0.8, 1.2)
            export_error: Exception | None = None
            try:
                resp = self._export(serialized_data, deadline_sec - time())
                if resp.ok:
                    return LogRecordExportResult.SUCCESS
            except RequestException as error:
                reason = error
                export_error = error
                retryable = isinstance(error, ConnectionError)
                status_code = None
            else:
                reason = resp.reason
                retryable = _is_retryable(resp)
                status_code = resp.status_code

            if not retryable:
                _logger.error(
                    "Failed to export logs batch code: %s, reason: %s",
                    status_code,
                    reason,
                )
                return LogRecordExportResult.FAILURE

            if (
                retry_num + 1 == _MAX_RETRYS
                or backoff_seconds > (deadline_sec - time())
                or self._shutdown
            ):
                _logger.error(
                    "Failed to export logs batch due to timeout, max retries or shutdown."
                )
                return LogRecordExportResult.FAILURE

            _logger.warning(
                "Transient error %s encountered while exporting logs batch, retrying in %.2fs.",
                reason,
                backoff_seconds,
            )
            if self._shutdown_is_occuring.wait(backoff_seconds):
                _logger.warning("Shutdown in progress, aborting retry.")
                break
        return LogRecordExportResult.FAILURE

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True

    def shutdown(self):
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_is_occuring.set()
        self._session.close()


def _compression_from_env() -> Compression:
    return Compression(
        environ.get(
            OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
            environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )


def _append_logs_path(endpoint: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + DEFAULT_LOGS_EXPORT_PATH
    return endpoint + f"/{DEFAULT_LOGS_EXPORT_PATH}"
