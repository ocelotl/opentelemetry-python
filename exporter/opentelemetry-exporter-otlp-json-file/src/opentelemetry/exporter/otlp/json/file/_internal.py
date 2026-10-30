# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Shared machinery behind the three OTLP JSON file exporters.

Nothing in this module is public API. The span, metric and log exporters of this package each own
a ``_FileExporter``, which holds the destination stream, serialises one encoded batch per line and
turns every failure on the export path into a logged message and a ``False`` return value. The
export path is the only one that works that way: building a ``_FileExporter`` raises when the
destination cannot be opened, and shutting one down raises when the file it opened cannot be
closed.
"""

import json
import logging
import sys
import threading
from collections.abc import Callable
from os import PathLike
from typing import IO, Generic, Literal, TypeVar

_logger = logging.getLogger(__name__)

T = TypeVar("T")


class _FileExporter(Generic[T]):
    """Writes encoded telemetry batches to a text stream, one JSON object per line.

    The destination is chosen once, when the exporter is built, and never changes afterwards.
    Giving ``path`` opens that file and makes this object responsible for closing it again on
    shutdown. Giving ``stream`` hands over a stream that the caller keeps responsible for. Giving
    neither captures ``sys.stdout`` as it is at that moment, so replacing ``sys.stdout``
    afterwards does not redirect the output.

    Concurrent calls to ``export`` on one instance are serialised with a lock, so two exporting
    threads cannot interleave halves of their lines. The lock belongs to the instance, so two
    instances pointed at the same file, or both left on ``sys.stdout``, do not coordinate with
    each other.

    Args:
        encode: Turns one batch of telemetry into a JSON serialisable dictionary. Returning
            ``None`` means the batch held nothing worth writing, and the export then flushes
            without appending a line.
        kind: Names the telemetry this exporter carries. It is interpolated into the warning
            logged when the stream turns out to be closed and into the message logged when an
            export fails, so that a reader of the logs can tell which of the three exporters
            emitted them. The two warnings about an exporter that is already shut down do not
            carry it.
        logger: Receives the warnings and the export failures. ``None`` selects the logger of this
            module, which is what a caller with no logger of its own wants.
        path: File to append to, opened with UTF-8 encoding. The file is created when it does not
            exist, and content already in it is kept.
        stream: Open text stream to write to.

    Raises:
        ValueError: Both ``path`` and ``stream`` were given, which names two destinations at once.
        OSError: ``path`` could not be opened for appending, because its directory does not
            exist, because the process may not write there, or for any other reason ``open``
            reports.
    """

    def __init__(
        self,
        encode: Callable[[T], dict | None],
        kind: Literal["spans", "logs", "metrics"],
        logger: logging.Logger | None = None,
        path: str | PathLike[str] | None = None,
        stream: IO[str] | None = None,
    ) -> None:
        """Open the destination. The parameters are documented on the class."""
        if path is not None and stream is not None:
            raise ValueError("Cannot specify both 'path' and 'stream'")
        if path is not None:
            self._stream: IO[str] = open(  # pylint: disable=consider-using-with
                path, "a", encoding="utf-8"
            )
            self._owns_stream = True
        elif stream is not None:
            self._stream = stream
            self._owns_stream = False
        else:
            self._stream = sys.stdout
            self._owns_stream = False
        self._shutdown = False
        self._encode = encode
        self._kind = kind
        self._logger = logger if logger is not None else _logger
        self._lock = threading.Lock()

    def export(self, data: T) -> bool:
        """Encode one batch and append it to the stream as a single line.

        The stream is flushed before the call returns, so a reader following the file sees the
        batch straight away. Nothing propagates to the caller: an exception raised by the encoder
        or by the write is logged with its traceback and reported as ``False``.

        Args:
            data: One batch of telemetry, of whatever type the ``encode`` callable accepts.

        Returns:
            ``True`` when the batch reached the stream, which includes the case where the encoder
            returned ``None`` and no line was appended. ``False`` when this exporter has already
            been shut down, when the stream was closed by whoever owns it, or when encoding or
            writing raised.
        """
        if self._shutdown:
            self._logger.warning("Exporter already shutdown, ignoring call")
            return False
        try:
            encoded = self._encode(data)
            with self._lock:
                if self._stream.closed:
                    self._logger.warning("Stream is closed, ignoring %s export call", self._kind)
                    return False
                if encoded is not None:
                    self._stream.write(_format_line(encoded))
                self._stream.flush()
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            self._logger.exception(
                "Failed to write %s batch to stream: %s: %s",
                self._kind,
                type(error).__name__,
                error,
            )
            return False
        return True

    def shutdown(self) -> None:
        """Refuse further exports, and close the stream when this exporter opened it.

        A stream supplied by the caller is left open, and so is ``sys.stdout``. Calling this a
        second time logs a warning and does nothing else.

        Raises:
            OSError: Closing the file this exporter opened failed, which is where the buffered
                bytes of the last write are reported when the write itself was buffered and
                the flush succeeded. A caller-supplied stream and ``sys.stdout`` are never
                closed, so neither of those destinations can raise here.
        """
        if self._shutdown:
            self._logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        if self._owns_stream:
            with self._lock:
                self._stream.close()


def _format_line(entry: dict) -> str:
    """Serialise one encoded batch as a JSON Lines record.

    The separators carry no spaces, so the record is the compact form that JSON Lines readers
    expect, and it ends in the newline that terminates the record.

    Args:
        entry: JSON serialisable dictionary produced by one of the encoders.

    Returns:
        The serialised entry followed by a newline.
    """
    return json.dumps(entry, separators=(",", ":")) + "\n"
