# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Log record exporter that writes OTLP JSON to a file, to a stream or to standard output.

The logger of this module carries ``opentelemetry.sdk._shared_internal.DuplicateFilter``, which
compares a record against the one before it on the logging module, the level and the message
template rather than on the formatted text, and drops the record when all three match inside the
same twenty second window. A second failure from the same call site is therefore dropped even
when its exception type and message differ from the first. An application that routes its own
logging through OpenTelemetry would otherwise turn each failed export into another log record to
export, and the failures would then feed themselves.
"""

import logging
import os
from collections.abc import Sequence
from typing import IO, Any, overload

from opentelemetry.exporter.otlp.json.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.json.file._internal import _FileExporter
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)
from opentelemetry.sdk._shared_internal import DuplicateFilter

_logger = logging.getLogger(__name__)
_logger.addFilter(DuplicateFilter())


def _encode_logs_to_dict(
    batch: Sequence[ReadableLogRecord],
) -> dict[str, Any] | None:
    """Encode a batch of log records as an OTLP export request.

    Args:
        batch: Log records handed over by a log record processor.

    Returns:
        The ``ExportLogsServiceRequest`` as a JSON serialisable dictionary, or ``None`` when the
        batch produced no resource logs, so that an empty batch writes no line at all.
    """
    data = encode_logs(batch)
    return data.to_dict() if data.resource_logs else None


class FileLogExporter(LogRecordExporter):
    """Writes log records to a file, to a stream or to ``sys.stdout`` as OTLP JSON Lines.

    A line written by this exporter always holds one whole ``ExportLogsServiceRequest``, so the
    output can be read back a line at a time and a batch is never split across lines. A batch that
    encodes to nothing writes no line at all. Register
    this exporter with a log record processor, such as
    ``opentelemetry.sdk._logs.export.BatchLogRecordProcessor``, for the log records to reach it.

    Args:
        path: File to append the log records to, opened with UTF-8 encoding. The exporter closes
            this file on shutdown. Mutually exclusive with ``stream``.
        stream: Open text stream to write the log records to. The caller keeps responsibility for
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
        self._exporter: _FileExporter[Sequence[ReadableLogRecord]] = _FileExporter(
            encode=_encode_logs_to_dict,
            kind="logs",
            logger=_logger,
            path=path,
            stream=stream,
        )

    def export(self, batch: Sequence[ReadableLogRecord]) -> LogRecordExportResult:
        """Append the batch to the destination as one line of OTLP JSON, then flush.

        A failure is logged with its traceback and reported through the return value. This
        exporter raises nothing, so the caller does not need the exception handling that
        ``opentelemetry.sdk._logs.export.LogRecordExporter`` warns other implementations may
        require.

        Args:
            batch: Log records to write.

        Returns:
            ``LogRecordExportResult.SUCCESS`` once the line has been written and flushed, and also
            when the batch encoded to nothing and no line was written.
            ``LogRecordExportResult.FAILURE`` when this exporter has been shut down, when the
            stream was closed by whoever owns it, or when encoding or writing raised.
        """
        return LogRecordExportResult.SUCCESS if self._exporter.export(batch) else LogRecordExportResult.FAILURE

    def shutdown(self) -> None:
        """Refuse further exports, and close the file when this exporter opened one.

        A stream supplied by the caller is left open, and so is ``sys.stdout``. A later call to
        :meth:`export` logs a warning and returns ``LogRecordExportResult.FAILURE``.
        """
        self._exporter.shutdown()

    # pylint: disable-next=no-self-use
    def force_flush(self, timeout_millis: int = 10_000) -> bool:
        """Report that no log records are being held back.

        Every call to :meth:`export` writes and flushes before it returns, so this exporter never
        buffers log records and has nothing to do here.

        Args:
            timeout_millis: Accepted for compatibility with the exporter interface and ignored.

        Returns:
            ``True`` always.
        """
        return True
