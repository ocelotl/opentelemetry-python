# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""HTTP transport built on ``requests``.

Selected by the name ``"requests"``, and available only when the ``requests``
extra of this package is installed. ``requests`` is imported inside the
functions that need it rather than at module level, so importing this module
costs nothing when another transport is in use.

Proxy configuration and certificate bundle selection are left to ``requests``
itself, which is what makes this transport the reference the ``urllib3``
transport is written to match.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._base import (
    BaseHTTPResult,
    BaseHTTPTransport,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    import requests
    from requests import Response


@functools.cache
def _get_connection_error_types() -> tuple[type[Exception], ...]:
    """Return the ``requests`` exception types that count as connection errors.

    The result is cached, so ``requests.exceptions`` is imported on the first
    call and the tuple is built once.

    Returns:
        A tuple suitable as the second argument of ``isinstance``, holding the
        connection, timeout, TLS and proxy errors of ``requests``. An HTTP
        error status is not in it, because a server that answers is reachable.
    """
    # pylint: disable-next=import-outside-toplevel
    import requests.exceptions  # noqa: PLC0415

    return (
        requests.exceptions.ConnectionError,
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ReadTimeout,
        requests.exceptions.Timeout,
        requests.exceptions.SSLError,
        requests.exceptions.ProxyError,
    )


@dataclass(frozen=True, slots=True)
class RequestsHTTPResult(BaseHTTPResult):
    """A :class:`BaseHTTPResult` backed by a ``requests`` response object.

    The body and the headers are read back out of the response on demand, so
    the response is kept alive for as long as the result is. The body has
    already been downloaded by the time this object exists, because
    ``RequestsHTTPTransport.request`` does not stream.

    Attributes:
        response: The ``requests.Response`` the request produced, or ``None``
            when the request failed before a response arrived. It takes no
            part in equality or hashing, so two results compare by status code,
            reason and error alone.
    """

    response: Response | None = field(default=None, hash=False, compare=False)

    def content(self) -> bytes:
        """Return the raw response body.

        Returns:
            The undecoded body, or ``b""`` when the request failed or the
            response carried no body.
        """
        if self.response is None:
            return b""
        return self.response.content or b""

    def text(self) -> str:
        """Return the response body as text.

        This overrides the UTF-8 decoding of :meth:`BaseHTTPResult.text` and
        hands the work to ``requests``, which decodes with the charset of the
        ``Content-Type`` header, falls back to a guess when the header gives
        none, and replaces undecodable bytes instead of raising.

        Returns:
            The decoded body, or ``""`` when the request failed or the
            response carried no body.
        """
        if self.response is None:
            return ""
        return self.response.text or ""

    def json(self) -> Any:
        """Return the response body parsed as JSON.

        Returns:
            The value the JSON document decodes to, which is whatever the
            server sent.

        Raises:
            ValueError: If the request failed, so that there is no response to
                parse, or if the body is not a valid JSON document.
        """
        if self.response is None:
            raise ValueError("No response available.")
        return self.response.json()

    def headers(self) -> Mapping[str, str]:
        """Return the response headers.

        Returns:
            The case-insensitive header mapping of ``requests``, which joins
            repeated headers into one comma separated value. An empty mapping
            when the request failed.
        """
        if self.response is None:
            return {}
        return self.response.headers


class RequestsHTTPTransport(BaseHTTPTransport):
    """A :class:`BaseHTTPTransport` that sends requests through ``requests``.

    One ``requests.Session`` is held for the lifetime of the transport, which
    is what keeps connections to the endpoint alive between exports. The
    session also supplies the proxy handling, so this transport does not
    consult the proxy environment variables itself.

    Args:
        verify: TLS verification setting, passed straight to the session.
            ``True`` verifies against the default certificate bundle,
            ``False`` disables verification, and a string is the path of a CA
            bundle file or directory to verify against.
        cert: Client certificate for mutual TLS. A string is the path of a
            file holding both the certificate and its unencrypted private key,
            a pair of strings is the certificate path and the key path, and
            ``None`` sends no client certificate.
        session: An existing ``requests.Session`` to send through. Its
            ``verify`` attribute is always overwritten by ``verify``, and its
            ``cert`` attribute is overwritten only when ``cert`` is not
            ``None``, so a certificate already configured on the session
            survives. The session is closed by :meth:`close` even though the
            caller created it. ``None`` builds a new session.
        **kwargs: Accepted and ignored, so that a caller can pass the options
            of another transport without the construction failing.
    """

    def __init__(
        self,
        *,
        verify: bool | str = True,
        cert: str | tuple[str, str] | None = None,
        session: requests.Session | None = None,
        **kwargs: Any,
    ) -> None:
        """Build the transport. The arguments are documented on the class."""
        # pylint: disable-next=import-outside-toplevel
        import requests  # noqa: PLC0415

        self._session = session if session is not None else requests.Session()
        self._session.verify = verify
        if cert is not None:
            self._session.cert = cert

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        data: bytes | None = None,
    ) -> BaseHTTPResult:
        """Send an HTTP request through the session and return the result.

        Redirects are not followed, so a ``3xx`` status reaches the caller as
        the status of the request. Every exception raised by ``requests`` is
        caught and placed in the result, including ones that are not connection
        errors, so this method does not raise.

        Args:
            method: HTTP method (e.g. ``"POST"``).
            url: Target URL.
            headers: Optional HTTP headers to include in the request, merged
                by ``requests`` with the headers already on the session.
            timeout: Optional request timeout in seconds, applied by
                ``requests`` to the connect phase and to the read phase
                separately rather than to the exchange as a whole.
            data: Optional request body, sent as given with no encoding step.

        Returns:
            A ``RequestsHTTPResult`` carrying the response, or one carrying
            only the exception when the request failed.
        """
        try:
            response = self._session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                timeout=timeout,
                allow_redirects=False,
            )
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            # pylint: disable-next=unexpected-keyword-arg
            return RequestsHTTPResult(error=error)

        # pylint: disable-next=unexpected-keyword-arg
        return RequestsHTTPResult(
            status_code=response.status_code,
            reason=response.reason,
            response=response,
        )

    # pylint: disable-next=no-self-use
    def is_connection_error(self, exception: Exception | None) -> bool:
        """Return whether a ``requests`` exception means the server was unreachable.

        Args:
            exception: The ``error`` field of a result, or ``None``.

        Returns:
            ``True`` when the exception is one of the ``requests`` connection,
            timeout, TLS or proxy errors, which makes the export worth
            retrying. ``False`` for any other exception and for ``None``.
        """
        return isinstance(exception, _get_connection_error_types())

    def close(self) -> None:
        """Close the session and the connections it is pooling.

        A session passed in by the caller is closed too. Results already
        returned keep working, because their bodies were downloaded before the
        result was built.
        """
        self._session.close()
