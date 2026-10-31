# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Log record exporter for the OTLP JSON over HTTP wire format.

:class:`~opentelemetry.exporter.otlp.json.http._log_exporter.OTLPLogExporter`
serializes log records to OTLP JSON and posts them to an OTLP/HTTP endpoint.
Register it with a log record processor such as ``BatchLogRecordProcessor``
instead of calling it directly.

The logger this module reports its own failures through carries a
``DuplicateFilter``. It compares a record against the previous one by module,
level and format string, the format string being the template before the
arguments are substituted, and drops the record when all three match within the
same twenty second window. Without it, a logging setup that exports its own log
records through this exporter would turn one export failure into an endless
stream of records describing that failure. The cost is that two different
failures reported through one template, a 400 response followed by a 500, are
collapsed into a single record.
"""

import logging
from collections.abc import Mapping, Sequence
from typing import overload

from opentelemetry.exporter.http.transport._base import BaseHTTPTransport
from opentelemetry.exporter.otlp.common.http import (
    Compression,
    _OTLPHTTPClient,
)
from opentelemetry.exporter.otlp.json.common._internal._log_encoder import (
    encode_logs,
)
from opentelemetry.exporter.otlp.json.http._internal import (
    _build_transport,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
)
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)
from opentelemetry.sdk._shared_internal import DuplicateFilter
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
)

_DEFAULT_LOGS_EXPORT_PATH = "v1/logs"

_logger = logging.getLogger(__name__)
_logger.addFilter(DuplicateFilter())


class OTLPLogExporter(LogRecordExporter):
    """Exports log records as OTLP JSON over HTTP.

    Each call to :meth:`export` encodes the batch it is handed as one JSON
    document and posts it to a single endpoint. A transient failure is retried
    over at most six attempts and for no longer than the timeout. An attempt
    that ends in a connection error is re-sent once immediately before the next
    attempt is counted, so the batch can leave this process up to twelve times.
    The wait between attempts doubles each time and is then multiplied by a
    random factor between 0.8 and 1.2; a retryable response carrying a
    ``Retry-After`` header the client can read, as a number of seconds or as an
    HTTP date, replaces that wait with the header's value. A wait longer than
    the time left in the timeout ends the export rather than being served. A
    permanent failure is logged and reported to the caller, which drops the
    batch.

    Every argument may be left as ``None``. Each one is then taken from the
    per-signal ``OTEL_EXPORTER_OTLP_LOGS_*`` environment variable, then from
    the generic ``OTEL_EXPORTER_OTLP_*`` variable, then from a default, with the
    exception of ``_transport``, which has no environment variable at all. All
    settings are resolved once, when the exporter is constructed; changing the
    environment afterwards has no effect.

    Args:
        endpoint: Full URL of the OTLP/HTTP signal endpoint, including the signal
            path. Example: ``http://collector:4318/v1/logs``. For a base URL without a
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
        timeout: Seconds one export may take in total, retries included. The
            default is 10 seconds.
        compression: Compression applied to the request body. The default is
            ``Compression.NONE``, which sends the JSON uncompressed.
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
        *,
        _transport: BaseHTTPTransport | None = None,
    ) -> None:
        """Resolve the exporter settings and open the HTTP transport.

        The parameters are documented on the class, which is what the API
        reference renders.
        """
        transport = _transport or _build_transport(
            certificate_file,
            client_key_file,
            client_certificate_file,
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
        )
        self._client = _OTLPHTTPClient(
            transport=transport,
            endpoint=endpoint or _resolve_endpoint(OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, _DEFAULT_LOGS_EXPORT_PATH),
            kind="logs",
            timeout=timeout if timeout is not None else _resolve_timeout(OTEL_EXPORTER_OTLP_LOGS_TIMEOUT),
            compression=compression
            if compression is not None
            else _resolve_compression(OTEL_EXPORTER_OTLP_LOGS_COMPRESSION),
            headers=_resolve_headers(headers, OTEL_EXPORTER_OTLP_LOGS_HEADERS),
            logger=_logger,
        )
        self._shutdown = False

    def export(self, batch: Sequence[ReadableLogRecord]) -> LogRecordExportResult:
        """Encode a batch of log records and post it to the endpoint.

        The whole batch becomes one JSON document and one request, whatever its
        size, so the caller is responsible for keeping batches small enough for
        the collector to accept. The call blocks until the export succeeds, is
        refused, runs out of attempts, or exhausts the timeout.

        A record that cannot be encoded fails the whole batch: the error is
        logged and nothing is sent. The same applies after :meth:`shutdown`
        has been called, when the batch is dropped with a warning instead of
        being exported.

        Args:
            batch: The log records to export, in the order the log record
                processor collected them. An empty sequence is still encoded
                and posted.

        Returns:
            ``LogRecordExportResult.SUCCESS`` when the collector answered with
            a 2xx or 3xx status, and ``LogRecordExportResult.FAILURE``
            otherwise. Failure is final: this method does not ask the caller to
            retry, because the retries have already happened inside it.
        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return LogRecordExportResult.FAILURE
        try:
            body = encode_logs(batch).to_json().encode()
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            _logger.error("Failed to encode logs: %s", error)
            return LogRecordExportResult.FAILURE
        export_result = self._client.export(body)
        return LogRecordExportResult.SUCCESS if export_result.success else LogRecordExportResult.FAILURE

    def shutdown(self) -> None:
        """Close the HTTP transport and refuse any further export.

        An export already in progress stops retrying as soon as it notices the
        shutdown, and reports failure. A second call logs a warning and does
        nothing, so the method is safe to call from more than one place.
        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._client.shutdown()

    # pylint: disable-next=no-self-use
    def force_flush(self, timeout_millis: int = 10_000) -> bool:
        """Report that there is nothing left to flush.

        :meth:`export` sends its batch before it returns, so this exporter
        holds no queue of its own. Flushing pending log records is the job of
        the log record processor that owns the exporter.

        Args:
            timeout_millis: Accepted for compatibility with the
                ``LogRecordExporter`` interface and ignored.

        Returns:
            ``True``, always.
        """
        return True
