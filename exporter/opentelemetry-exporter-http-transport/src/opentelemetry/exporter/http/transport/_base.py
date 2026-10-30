# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Abstract HTTP transport interface shared by the HTTP exporters.

An exporter sends a request by calling :meth:`BaseHTTPTransport.request` and
reads the outcome from the :class:`BaseHTTPResult` it returns. Neither class is
instantiable on its own. The transports shipped with this package implement
them on top of ``requests`` and ``urllib3``, and a third party transport is
registered under the ``opentelemetry_http_transport`` entry point group.

A failed request is reported as a result carrying an ``error``, never as an
exception raised out of ``request``, so an exporter handles a connection
failure and an HTTP error status through the same return value.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any


@dataclass(frozen=True, slots=True)
class BaseHTTPResult(ABC):
    """Outcome of a single HTTP request made by a :class:`BaseHTTPTransport`.

    Either ``status_code`` and ``reason`` are populated (server responded),
    or ``error`` is set (request failed before a response was received).

    The class holds only the fields an exporter needs to decide whether to
    retry. A subclass keeps the underlying library response alongside them and
    reads the body and the headers back out of it, so the body is not copied
    into this object.

    Attributes:
        status_code: HTTP status line code of the response, or ``None`` when no
            response was received.
        reason: HTTP status line reason phrase, or ``None`` when no response
            was received. A server is free to send an empty reason phrase, so
            an empty string does not mean the request failed.
        error: The exception that ended the request before a response arrived,
            or ``None`` when a response was received. Pass it to
            :meth:`BaseHTTPTransport.is_connection_error` to find out whether
            retrying is worthwhile.
    """

    status_code: int | None = None
    reason: str | None = None
    error: Exception | None = None

    @abstractmethod
    def content(self) -> bytes:
        """Return the raw response body.

        Implementations may raise an exception if the returned content is malformed.

        Returns:
            The undecoded response body. An implementation returns ``b""``
            rather than raising when no response was received.
        """

    @abstractmethod
    def headers(self) -> Mapping[str, str]:
        """Return the response headers.

        The returned mapping MUST be case-insensitive with respect to header
        keys. Headers with multiple values are represented as a single string
        of comma separated values.

        Implementations may raise an exception if the returned headers are malformed.

        Returns:
            The response headers. An implementation returns an empty mapping
            rather than raising when no response was received.
        """

    def text(self) -> str:
        """Return the response body decoded as UTF-8.

        Implementations may raise an exception if the returned string is malformed.

        The charset declared by the ``Content-Type`` header is ignored, and
        decoding is strict, so a body in any other encoding raises instead of
        coming back with replacement characters. A subclass is free to
        override this with the charset handling of its own library, and
        ``RequestsHTTPResult`` does.

        Returns:
            The body of :meth:`content` decoded as UTF-8.

        Raises:
            UnicodeDecodeError: If the body is not valid UTF-8.
        """
        return self.content().decode("utf-8")

    def json(self) -> Any:
        """Return the response body parsed as JSON.

        Implementations may raise an exception if no response content
        is available or the returned JSON is malformed.

        Returns:
            The value the JSON document decodes to, which is whatever the
            server sent: usually a ``dict``, but any JSON value is possible.

        Raises:
            json.JSONDecodeError: If the body is not a valid JSON document.
        """
        return json.loads(self.text())


class BaseHTTPTransport(ABC):
    """Abstract HTTP transport interface used by HTTP exporters.

    A transport owns the connection pool and the TLS settings for one exporter
    and is used for every request that exporter makes. An instance comes from
    the factory that ``_load_http_transport_factory`` returns, called with the
    keyword arguments ``verify`` and ``cert``.

    Both transports shipped with this package turn redirect following off, so
    a request to an endpoint that answers ``3xx`` gives back that status rather
    than sending the telemetry on to the redirect target.
    """

    @abstractmethod
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        data: bytes | None = None,
    ) -> BaseHTTPResult:
        """Send an HTTP request and return the result.

        An implementation reports a failure through the ``error`` field of the
        returned result rather than by raising, so a caller does not need an
        exception handler around this call.

        Args:
            method: HTTP method (e.g. ``"POST"``).
            url: Target URL.
            headers: Optional HTTP headers to include in the request. ``None``
                sends only the headers the underlying library adds itself.
            timeout: Optional request timeout in seconds. Whether it bounds
                the whole exchange or each socket operation separately is left
                to the implementation, and the two transports shipped here
                differ on it. ``None`` leaves the implementation to pick.
            data: Optional request body, serialized and encoded by the caller
                and sent as given. ``None`` sends no body.

        Returns:
            A :class:`BaseHTTPResult` describing the outcome. It carries
            ``status_code`` and ``reason`` when the server responded, and
            ``error`` when the request failed first.
        """

    @abstractmethod
    def close(self) -> None:
        """Release any resources held by the transport.

        Closes the connection pool, so an in-flight request on another thread
        may fail. Calling it twice is harmless, and the transport is not
        expected to be usable afterwards.
        """

    @abstractmethod
    def is_connection_error(self, exception: Exception | None) -> bool:
        """Return ``True`` if the exception is a transport-level connection error.

        The exporters call this with the ``error`` field of a result to decide
        whether a failed export is worth retrying. A connection error means the
        request never reached the server or its response never arrived, so the
        same payload can be sent again.

        Args:
            exception: The exception that ended the request, normally the
                ``error`` field of a :class:`BaseHTTPResult`. ``None`` means
                the request did not fail and gives ``False``.

        Returns:
            ``True`` when the exception belongs to the set of connection and
            timeout errors of the underlying library, ``False`` for any other
            exception and for ``None``.
        """
