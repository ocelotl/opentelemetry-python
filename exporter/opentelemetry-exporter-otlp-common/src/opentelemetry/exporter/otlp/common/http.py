# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""HTTP delivery shared by the OTLP exporters.

``_OTLPHTTPClient`` takes an OTLP payload that the caller has already
serialized, compresses it when asked to, posts it through a transport from the
``opentelemetry-exporter-http-transport`` distribution and retries while the
failure looks transient. The OTLP exporters for protobuf over HTTP and for JSON
over HTTP both send through it, so the retry policy, the reading of the
``Retry-After`` header and the response to shutdown are written once.

``Compression`` is defined here too, because an exporter has to turn the value
of ``OTEL_EXPORTER_OTLP_COMPRESSION`` into something it can hand to
``_OTLPHTTPClient``.

The transport is imported only while type checking, so this module can be
imported by a distribution that did not install the ``http`` extra of
``opentelemetry-exporter-otlp-common``.
"""

from __future__ import annotations

import enum
import gzip
import logging
import math
import random
import threading
import time
import zlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timezone
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from io import BytesIO
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from opentelemetry.exporter.http.transport._base import (
        BaseHTTPResult,
        BaseHTTPTransport,
    )

_logger = logging.getLogger(__name__)

_MAX_RETRIES: Final[int] = 6
_DEFAULT_TIMEOUT: Final[float] = 10.0
_DEFAULT_JITTER: Final[float] = 0.2


_RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset(
    {
        HTTPStatus.TOO_MANY_REQUESTS.value,
        HTTPStatus.BAD_GATEWAY.value,
        HTTPStatus.SERVICE_UNAVAILABLE.value,
        HTTPStatus.GATEWAY_TIMEOUT.value,
    }
)


def _is_retryable(status_code: int | None) -> bool:
    """Report whether a status code is one the OTLP specification retries.

    Args:
        status_code: The status code of the response, or ``None`` when the
            request produced no response at all.

    Returns:
        ``True`` for 429, 502, 503 and 504. ``False`` for every other status
        code and for ``None``, since a request with no response is judged by
        asking the transport whether its error was a connection error.
    """
    return status_code in _RETRYABLE_STATUS_CODES


def _extract_retry_after(result: BaseHTTPResult) -> float | None:
    """Parse the ``Retry-After`` header (RFC 7231).

    The header carries either a count of seconds or an HTTP date. A date with
    no timezone is read as UTC, and a date already in the past yields ``0.0``
    rather than a negative wait.

    Args:
        result: The response to read the ``Retry-After`` header from. Any
            exception raised while reading its headers is caught and treated
            the same as a missing header.

    Returns:
        The number of seconds to wait before retrying, never negative. ``None``
        when the header is absent, when reading the headers raised, when the
        value parses as neither a number of seconds nor an HTTP date, or when
        it parses as a non-finite number such as ``inf`` or ``nan``.
    """
    try:
        value = result.headers().get("retry-after")
    # pylint: disable-next=broad-exception-caught
    except Exception:
        return None
    if value is None:
        return None
    value = value.strip()

    # delay-seconds: a non-negative decimal integer.
    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        return max(seconds, 0.0) if math.isfinite(seconds) else None

    # HTTP-date: wait until the indicated absolute time.
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(retry_at.timestamp() - time.time(), 0.0)


class Compression(enum.Enum):
    """How an OTLP HTTP client compresses a payload before sending it.

    The value of each member is the token the OTLP specification uses for it in
    ``OTEL_EXPORTER_OTLP_COMPRESSION``. For every member other than ``NONE`` it
    is also the value ``_OTLPHTTPClient`` writes into the ``Content-Encoding``
    request header, unless the caller already supplied that header, as the
    ``compression`` entry of ``_OTLPHTTPClient`` describes.
    """

    NONE = "none"
    DEFLATE = "deflate"
    GZIP = "gzip"

    @staticmethod
    def from_str(value: str) -> Compression:
        """Parse one of the compression tokens of the OTLP specification.

        Args:
            value: The token to parse. It is stripped of surrounding whitespace
                and lowercased first, so ``" GZIP "`` is accepted.

        Returns:
            The member whose value matches ``value``.

        Raises:
            ValueError: When ``value`` is none of ``none``, ``deflate`` and
                ``gzip``. The caller decides what to do about it: the OTLP
                exporters log a warning and fall back to ``NONE``.
        """
        match value.strip().lower():
            case "none":
                return Compression.NONE
            case "deflate":
                return Compression.DEFLATE
            case "gzip":
                return Compression.GZIP
            case _:
                raise ValueError(f"Invalid compression type: {value!r}. Expected one of: 'none', 'deflate', 'gzip'.")


@dataclass(slots=True, frozen=True)
class _ExportResult:
    """Outcome of one ``_OTLPHTTPClient.export`` call, retries included.

    Attributes:
        success: Whether the server answered with a status code in the range
            200 to 399. Every other ending, including a run of retries that
            reached the deadline and a shutdown that interrupted the retries,
            is a failure.
        status_code: The status code of the last response received, or ``None``
            when no response was received at all or when shutdown interrupted a
            wait between attempts. Shutdown noticed before a wait begins is the
            other case, and that one does carry the status code of the attempt
            that had just failed.
        reason: The reason phrase the transport reported alongside
            ``status_code``, or ``None`` on the same conditions.
        error: The exception that ended the export, either the one raised
            while submitting the request or the one the transport attached to
            the last response, and ``None`` when there was neither. It is
            ``None`` as well when shutdown interrupted a wait between attempts,
            even though the attempt before the wait may have produced one. An
            OTLP exporter copies it onto the ``ExportResult`` of its
            self-observability metrics, so an export abandoned that way is
            counted with no ``error.type`` attribute.
    """

    success: bool
    status_code: int | None
    reason: str | None
    error: Exception | None


class _OTLPHTTPClient:
    """Sends serialized OTLP payloads over HTTP with retry logic.

    Compression, backoff, and connection-error recovery are handled internally.
    Callers interact through the ``export`` and ``shutdown`` methods.

    An instance sends to a single endpoint and is reused for every batch, so
    the transport keeps its connection pool between exports. It is not tied to
    one signal beyond the wording of the messages it logs.

    Args:
        transport: What performs the request. The client also asks it whether a
            given exception was a connection error, and closes it on shutdown.
        endpoint: The full URL to post to, used unchanged for every attempt.
        kind: Which telemetry the payloads carry. It appears in the log
            messages only, so that an operator reading the log can tell the
            exporters of a process apart.
        timeout: How many seconds the whole export may take, retries included.
            The deadline starts once ``export`` has compressed the payload, so
            the time compression takes is not counted against it, and each
            attempt is given whatever is left of it.
        compression: How to compress the payload. Anything other than
            ``Compression.NONE`` also adds a ``Content-Encoding`` header,
            unless ``headers`` already carries one under any capitalisation.
        headers: Headers to send with every request, or ``None`` for none. The
            mapping is copied, so later changes to it are not picked up.
        jitter: How far the backoff may stray from its nominal value, as a
            fraction. A value of 0.2 multiplies each backoff by a random number
            between 0.8 and 1.2. The value is clamped to the range 0 to 1, so
            the factor never exceeds 2, and at the clamp of 1 it can be as low
            as 0.
        logger: Where to send the warning and error messages, or ``None`` to
            use the logger of this module. An exporter passes its own logger so
            that the messages are attributed to the exporter rather than to
            this shared module.
    """

    def __init__(
        self,
        transport: BaseHTTPTransport,
        endpoint: str,
        kind: Literal["spans", "logs", "metrics"],
        timeout: float = _DEFAULT_TIMEOUT,
        compression: Compression = Compression.NONE,
        headers: Mapping[str, str] | None = None,
        jitter: float = _DEFAULT_JITTER,
        logger: logging.Logger | None = None,
    ) -> None:
        """Store the request settings and prepare the shutdown signal.

        The parameters are documented on the class.
        """
        self._transport = transport
        self._endpoint = endpoint
        self._timeout = timeout
        self._compression = compression
        self._headers = dict(headers) if headers is not None else {}
        if self._compression is not Compression.NONE and not any(
            key.lower() == "content-encoding" for key in self._headers
        ):
            self._headers["Content-Encoding"] = self._compression.value
        self._kind = kind
        self._jitter = min(max(jitter, 0.0), 1.0)
        self._logger = logger if logger is not None else _logger
        self._shutdown = False
        self._shutdown_event = threading.Event()

    def _compute_backoff(self, retry: int) -> float:
        """Compute the wait that follows one attempt.

        The nominal wait doubles with each attempt, starting at one second for
        ``retry`` of 0, and is then multiplied by a random factor drawn
        uniformly from the jitter range, so that many exporters failing at once
        do not retry in step.

        Args:
            retry: The zero-based index of the attempt that is about to be
                made. ``export`` calls this at the head of each iteration,
                before the attempt the index names.

        Returns:
            The wait in seconds, to be spent after that attempt fails. A
            ``Retry-After`` header overrides it only when the response carried
            a status code and ``_extract_retry_after`` could parse the header,
            so a header this module does not understand leaves this value in
            place.
        """
        return 2**retry * random.uniform(1 - self._jitter, 1 + self._jitter)

    def _compress(self, serialized_data: bytes) -> bytes:
        """Compress a payload with the scheme this client was configured with.

        The payload is compressed once, before the first attempt, and the same
        compressed bytes are sent again on every retry.

        Args:
            serialized_data: The payload as the caller serialized it.

        Returns:
            The gzip or zlib compressed payload, or ``serialized_data`` itself
            when the compression is ``Compression.NONE``.
        """
        if self._compression is Compression.GZIP:
            buf = BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="w") as gz:
                gz.write(serialized_data)
            return buf.getvalue()
        if self._compression is Compression.DEFLATE:
            return zlib.compress(serialized_data)
        return serialized_data

    def _submit(self, data: bytes, timeout: float) -> BaseHTTPResult:
        """Post the payload once, repeating it immediately after a connection error.

        The repeat costs no backoff and happens only when time is left within
        ``timeout``, which is why it is here rather than in the retry loop of
        ``export``.

        Args:
            data: The already compressed payload to post.
            timeout: How many seconds both attempts together may take. The
                second attempt is given whatever is left.

        Returns:
            The result of the second attempt when one was made, and the result
            of the first attempt otherwise. The transport reports most failures
            in the result rather than by raising, so the caller inspects the
            ``error`` of the result as well as its status code.
        """
        deadline = time.time() + timeout
        result = self._transport.request(
            "POST",
            self._endpoint,
            headers=self._headers,
            data=data,
            timeout=timeout,
        )
        if (
            result.error is not None
            and self._transport.is_connection_error(result.error)
            and (remaining := deadline - time.time()) > 0
        ):
            # Immediately retry connection errors once without backoff. These
            # usually indicate a stale pooled connection that the transport will
            # reestablish on the next attempt.
            result = self._transport.request(
                "POST",
                self._endpoint,
                headers=self._headers,
                data=data,
                timeout=remaining,
            )
        return result

    def export(self, data: bytes) -> _ExportResult:
        """Export a serialized payload, retrying on transient failures.

        The payload is compressed once and a deadline of ``timeout`` seconds is
        then set, counted from the end of the compression rather than from the
        start of this call. At most six attempts are made, and each attempt may
        repeat its request once after a connection error, so up to twelve
        requests can be sent. A status code in the range 200 to 399 ends
        the export as a success. A status code of 429, 502, 503 or 504 is
        retried, and so is a response that carried no status code at all and
        whose error the transport recognises as a connection error. Anything
        else, including an exception raised while submitting, ends the export as
        a failure without another attempt.

        The wait between attempts doubles each time, starting at one second and
        jittered by the fraction given to the constructor. A ``Retry-After``
        header on a retryable response that carried a status code replaces that
        wait. The export gives up and logs an error when the sixth attempt has
        been made, when the next wait would run past the deadline, or when
        shutdown was already requested before the wait began. Shutdown that
        arrives during the wait also gives up, logging a warning rather than an
        error.

        The call blocks for the wait between attempts, so an export can occupy
        the calling thread for close to ``timeout`` seconds on top of whatever
        the compression took. ``shutdown`` wakes it early.

        A failure of the request, whether the transport reported it in a
        response or raised it, is reported in the value returned rather than
        raised. Compression runs before the first attempt and is not guarded, so
        a payload that ``gzip`` or ``zlib`` cannot compress raises out of here.

        Args:
            data: The serialized payload to send, before compression.

        Returns:
            An ``_ExportResult``. Its ``success`` is true only for a status
            code in the range 200 to 399. On failure its ``status_code``,
            ``reason`` and ``error`` carry what the last attempt produced,
            except when shutdown interrupted a wait, in which case all three
            are ``None``.
        """
        data = self._compress(data)
        deadline = time.time() + self._timeout

        for retry in range(_MAX_RETRIES):
            backoff = self._compute_backoff(retry)
            status_code: int | None = None
            reason: str | None = None
            export_error: Exception | None
            retryable: bool

            try:
                result = self._submit(data, max(deadline - time.time(), 0.0))
            # pylint: disable-next=broad-exception-caught
            except Exception as error:
                export_error = error
                retryable = False
            else:
                status_code = result.status_code
                reason = result.reason
                if status_code is not None and 200 <= status_code < 400:
                    return _ExportResult(True, status_code, reason, None)
                export_error = result.error
                retryable = (
                    _is_retryable(status_code) if status_code else self._transport.is_connection_error(result.error)
                )
                if retryable and status_code is not None and (retry_after := _extract_retry_after(result)) is not None:
                    backoff = retry_after

            if not retryable:
                self._logger.error(
                    "Failed to export %s batch code: %s, reason: %s",
                    self._kind,
                    status_code,
                    reason or export_error or "unknown",
                )
                return _ExportResult(False, status_code, reason, export_error)

            if retry + 1 == _MAX_RETRIES or backoff > (deadline - time.time()) or self._shutdown_event.is_set():
                self._logger.error(
                    "Failed to export %s batch due to timeout, max retries or shutdown.",
                    self._kind,
                )
                return _ExportResult(False, status_code, reason, export_error)

            self._logger.warning(
                "Transient error %s encountered while exporting %s batch, retrying in %.2fs.",
                reason or export_error,
                self._kind,
                backoff,
            )
            shutdown = self._shutdown_event.wait(backoff)
            if shutdown:
                self._logger.warning("Shutdown in progress, aborting retry.")
                break

        return _ExportResult(False, None, None, None)

    def shutdown(self) -> None:
        """Shutdown the client.

        An ``export`` already waiting between two attempts wakes up at once and
        gives up. An ``export`` started afterwards still makes its first
        attempt, and gives up rather than retrying if that attempt fails, so it
        succeeds whenever the first attempt succeeds. Neither is cancelled part
        way through a request, so a request already in flight runs to its own
        timeout.

        The transport is closed, which releases its connection pool. A second
        call logs a warning and does nothing else. The flag it reads is set
        without a lock, so two threads calling this at the same time can both
        pass the check and close the transport twice.
        """
        if self._shutdown:
            self._logger.warning("OTLP client already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_event.set()
        self._transport.close()
