# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Span exporter that writes OTLP JSON to a file, to a stream or to standard output."""

import logging
import os
from collections.abc import Sequence
from typing import IO, Any, overload

from opentelemetry.exporter.otlp.json.common.trace_encoder import encode_spans
from opentelemetry.exporter.otlp.json.file._internal import _FileExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

_logger = logging.getLogger(__name__)


def _encode_spans_to_dict(
    spans: Sequence[ReadableSpan],
) -> dict[str, Any] | None:
    """Encode a batch of spans as an OTLP export request.

    Args:
        spans: Finished spans handed over by a span processor.

    Returns:
        The ``ExportTraceServiceRequest`` as a JSON serialisable dictionary, or ``None`` when the
        batch produced no resource spans, so that an empty batch writes no line at all.
    """
    data = encode_spans(spans)
    return data.to_dict() if data.resource_spans else None


class FileSpanExporter(SpanExporter):
    """Writes finished spans to a file, to a stream or to ``sys.stdout`` as OTLP JSON Lines.

    A line written by this exporter always holds one whole ``ExportTraceServiceRequest``, so the
    output can be read back a line at a time and a batch is never split across lines. A batch
    that encodes to nothing writes no line at all.
    Register this exporter with ``opentelemetry.sdk.trace.export.BatchSpanProcessor`` or
    ``opentelemetry.sdk.trace.export.SimpleSpanProcessor`` for the spans to reach it.

    Args:
        path: File to append the spans to, opened with UTF-8 encoding. The exporter closes this
            file on shutdown. Mutually exclusive with ``stream``.
        stream: Open text stream to write the spans to. The caller keeps responsibility for
            closing it. Mutually exclusive with ``path``.

    Raises:
        ValueError: Both ``path`` and ``stream`` were given. Leaving both out selects
            ``sys.stdout``.
        OSError: ``path`` could not be opened for appending, because its directory does not
            exist, because the process may not write there, or for any other reason ``open``
            reports.
    """

    @overload
    def __init__(
        self,
        path: str | os.PathLike[str],
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        stream: IO[str],
    ) -> None: ...

    @overload
    def __init__(
        self,
    ) -> None: ...

    def __init__(
        self,
        path: str | os.PathLike[str] | None = None,
        *,
        stream: IO[str] | None = None,
    ) -> None:
        """Open the destination. The parameters are documented on the class."""
        self._exporter: _FileExporter[Sequence[ReadableSpan]] = _FileExporter(
            encode=_encode_spans_to_dict,
            kind="spans",
            logger=_logger,
            path=path,
            stream=stream,
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Append the batch to the destination as one line of OTLP JSON, then flush.

        A failure is logged with its traceback and reported through the return value. Nothing is
        raised, so a span processor calling this never has to guard the call.

        Args:
            spans: Finished spans to write.

        Returns:
            ``SpanExportResult.SUCCESS`` once the line has been written and flushed, and also when
            the batch encoded to nothing and no line was written. ``SpanExportResult.FAILURE``
            when this exporter has been shut down, when the stream was closed by whoever owns it,
            or when encoding or writing raised.
        """
        return SpanExportResult.SUCCESS if self._exporter.export(spans) else SpanExportResult.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Refuse further exports, and close the file when this exporter opened one.

        A stream supplied by the caller is left open, and so is ``sys.stdout``. A later call to
        :meth:`export` logs a warning and returns ``SpanExportResult.FAILURE``.

        Args:
            timeout_millis: What is left of the shutdown budget.
                ``opentelemetry.sdk.trace.export.BatchSpanProcessor`` passes it because this
                signature accepts it, and it is ignored here because closing a local file does
                not block. ``opentelemetry.sdk.trace.export.SpanExporter`` declares this method
                with no parameters at all, so a caller holding the base type must not rely on
                this one.
            kwargs: Absorbs any further keyword a span processor passes, and is ignored.
        """
        self._exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Report that no spans are being held back.

        Every call to :meth:`export` writes and flushes before it returns, so this exporter never
        buffers spans and has nothing to do here.

        Args:
            timeout_millis: Accepted for compatibility with the exporter interface and ignored.

        Returns:
            ``True`` always.
        """
        return True
