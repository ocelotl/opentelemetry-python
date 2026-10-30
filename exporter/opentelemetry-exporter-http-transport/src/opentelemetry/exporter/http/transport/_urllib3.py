# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""HTTP transport built on ``urllib3``.

Selected by the name ``"urllib3"``, and available only when the ``urllib3``
extra of this package is installed. ``urllib3`` is imported inside the
functions that need it rather than at module level, so importing this module
costs nothing when another transport is in use.

``urllib3`` reads no proxy configuration and picks no certificate bundle on
its own, so this module does both itself, following what ``requests`` does:
the proxy for a URL comes from ``_get_environ_proxy`` in
``opentelemetry.exporter.http.transport._proxy``, and the default certificate
bundle comes from ``certifi`` when it is installed.
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._base import (
    BaseHTTPResult,
    BaseHTTPTransport,
)

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._proxy import (
    _get_environ_proxy,
    _get_proxy_auth,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from urllib3 import BaseHTTPResponse, PoolManager


@functools.cache
def _get_connection_error_types() -> tuple[type[Exception], ...]:
    """Return the ``urllib3`` exception types that count as connection errors.

    The result is cached, so ``urllib3.exceptions`` is imported on the first
    call and the tuple is built once. ``NameResolutionError`` was added in
    ``urllib3`` 2.0 and is included only when the installed version has it,
    which is why the tuple is assembled at run time instead of being written
    out as a constant.

    Returns:
        A tuple suitable as the second argument of ``isinstance``, holding the
        connection, timeout, protocol and proxy errors of ``urllib3``. An HTTP
        error status is not in it, because a server that answers is reachable.
    """
    # pylint: disable-next=import-outside-toplevel
    import urllib3.exceptions  # noqa: PLC0415

    types: list[type[Exception]] = [
        urllib3.exceptions.ConnectionError,
        urllib3.exceptions.NewConnectionError,
        urllib3.exceptions.ConnectTimeoutError,
        urllib3.exceptions.MaxRetryError,
        urllib3.exceptions.ProtocolError,
        urllib3.exceptions.ProxyError,
        urllib3.exceptions.ReadTimeoutError,
    ]

    # NameResolutionError was added in urllib3 2.0
    name_resolution_error = getattr(urllib3.exceptions, "NameResolutionError", None)
    if name_resolution_error is not None:
        types.append(name_resolution_error)

    return tuple(types)


@dataclass(frozen=True, slots=True)
class Urllib3HTTPResult(BaseHTTPResult):
    """A :class:`BaseHTTPResult` backed by a ``urllib3`` response object.

    The body has already been downloaded by the time this object exists,
    because ``Urllib3HTTPTransport.request`` asks ``urllib3`` to preload the
    content.

    Unlike ``RequestsHTTPResult``, this class does not override
    :meth:`BaseHTTPResult.text`, so a body is decoded strictly as UTF-8 and the
    charset of the ``Content-Type`` header is ignored.

    Attributes:
        response: The ``urllib3.BaseHTTPResponse`` the request produced, or
            ``None`` when the request failed before a response arrived. It
            takes no part in equality or hashing, so two results compare by
            status code, reason and error alone.
    """

    response: BaseHTTPResponse | None = field(default=None, hash=False, compare=False)

    def content(self) -> bytes:
        """Return the raw response body.

        Returns:
            The undecoded body, or ``b""`` when the request failed or the
            response carried no body.
        """
        if self.response is None:
            return b""
        return self.response.data or b""

    def headers(self) -> Mapping[str, str]:
        """Return the response headers.

        Returns:
            The case-insensitive ``HTTPHeaderDict`` of ``urllib3``, which joins
            repeated headers into one comma separated value. An empty mapping
            when the request failed.
        """
        if self.response is None:
            return {}
        return self.response.headers

    def json(self) -> Any:
        """Return the response body parsed as JSON.

        The bytes are handed to :func:`json.loads` directly, which decodes
        UTF-8, UTF-16 and UTF-32 by inspecting the first bytes.

        Returns:
            The value the JSON document decodes to, which is whatever the
            server sent.

        Raises:
            ValueError: If the request failed, so that there is no response to
                parse, or if the body is not a valid JSON document.
        """
        if self.response is None:
            raise ValueError("No response available.")
        return json.loads(self.content())


class Urllib3HTTPTransport(BaseHTTPTransport):
    """A :class:`BaseHTTPTransport` that sends requests through ``urllib3``.

    One ``urllib3.PoolManager`` is held for direct connections, and one more
    is built per proxy URL as proxies are encountered. All of them are built
    from the same pool settings, which fix the retry count at zero, ask for
    redirect following to be off, and keep up to ten connections per host for
    reuse. Ten bounds how many connections are kept, leaving the number open
    at any moment unbounded: concurrent requests beyond ten open further
    connections, which are closed once they are done.

    The request for no redirect following reaches the connection pool, and on
    ``urllib3`` below 2.5.0 the pool manager above it follows redirects
    anyway. :meth:`request` describes what that means for a caller.

    Args:
        verify: TLS verification setting. ``True`` verifies against the
            ``certifi`` bundle when ``certifi`` is installed and against the
            system trust store otherwise, ``False`` disables verification, and
            a string is the path of a CA bundle file to verify against.
        cert: Client certificate for mutual TLS. A string is the path of a
            file holding both the certificate and its unencrypted private key,
            a pair of strings is the certificate path and the key path, and
            ``None`` sends no client certificate.
        **kwargs: Accepted and ignored, so that a caller can pass the options
            of another transport without the construction failing. In
            particular a ``session`` meant for ``RequestsHTTPTransport`` lands
            here and has no effect.
    """

    def __init__(
        self,
        *,
        verify: bool | str = True,
        cert: str | tuple[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Build the transport. The arguments are documented on the class."""
        # pylint: disable-next=import-outside-toplevel
        import urllib3  # noqa: PLC0415

        pool_kwargs: dict[str, Any] = {
            "retries": urllib3.Retry(0, redirect=False),
            # Match the connection pool size of requests
            "maxsize": 10,
        }
        if verify is False:
            pool_kwargs["cert_reqs"] = "CERT_NONE"
        else:
            pool_kwargs["cert_reqs"] = "CERT_REQUIRED"
            if isinstance(verify, str):
                pool_kwargs["ca_certs"] = verify
            else:
                # Prefer certifi's CA bundle, as requests does, falling back
                # to the system trust store when certifi is not installed.
                try:
                    # pylint: disable-next=import-outside-toplevel
                    import certifi  # noqa: PLC0415
                except ImportError:
                    pass
                else:
                    pool_kwargs["ca_certs"] = certifi.where()
        if isinstance(cert, tuple):
            pool_kwargs["cert_file"] = cert[0]
            pool_kwargs["key_file"] = cert[1]
        elif isinstance(cert, str):
            pool_kwargs["cert_file"] = cert

        self._pool_kwargs = pool_kwargs
        self._pool = urllib3.PoolManager(**pool_kwargs)  # type: ignore
        self._proxy_managers: dict[str, PoolManager] = {}
        self._get_proxy = functools.lru_cache(maxsize=32)(_get_environ_proxy)

    def _get_pool_manager(self, url: str) -> PoolManager:
        """Return the pool manager that should carry a request to a URL.

        The proxy lookup is memoized per URL on this transport, in a 32 entry
        cache that :meth:`close` empties, so the environment is read again
        only after an eviction or a close. The proxy managers themselves are
        kept in a dictionary that has no size limit, keyed by proxy URL, so
        two endpoints behind the same proxy share one pool.

        Args:
            url: The absolute URL the request is about to be sent to.

        Returns:
            The direct pool manager when no proxy applies, otherwise the pool
            manager for the proxy that does, building it on first use.
        """
        proxy = self._get_proxy(url)
        if proxy is None:
            return self._pool
        manager = self._proxy_managers.get(proxy)
        if manager is None:
            manager = self._proxy_managers.setdefault(proxy, self._new_proxy_manager(proxy))
        return manager

    def _new_proxy_manager(self, proxy: str) -> PoolManager:
        """Build a pool manager that sends every request through one proxy.

        The pool settings of the transport are reused, so a proxied connection
        gets the same TLS configuration and the same retry and redirect
        behaviour as a direct one. Credentials in the proxy URL become a
        ``Proxy-Authorization`` header for an HTTP proxy, and the username and
        password arguments of the SOCKS manager for a SOCKS proxy.

        Args:
            proxy: The proxy URL, including any ``user:password@`` part. A
                scheme starting with ``socks`` selects the SOCKS manager, any
                other scheme the HTTP one.

        Returns:
            A new pool manager for that proxy. The caller is responsible for
            storing it, since nothing is cached here.

        Raises:
            ImportError: If the proxy is a SOCKS proxy and PySocks is not
                installed, which is the dependency ``urllib3[socks]`` pulls in.
        """
        # pylint: disable-next=import-outside-toplevel
        import urllib3  # noqa: PLC0415

        username, password = _get_proxy_auth(proxy)
        if proxy.lower().startswith("socks"):
            try:
                # pylint: disable-next=import-outside-toplevel
                from urllib3.contrib.socks import (  # noqa: PLC0415
                    SOCKSProxyManager,
                )
            except ImportError as error:
                raise ImportError(
                    "SOCKS proxy support requires PySocks, install it with 'pip install urllib3[socks]'."
                ) from error
            return SOCKSProxyManager(
                proxy,
                username=username,
                password=password,
                **self._pool_kwargs,
            )
        proxy_headers = urllib3.make_headers(proxy_basic_auth=f"{username}:{password}") if username else None
        return urllib3.proxy_from_url(
            proxy,
            proxy_headers=proxy_headers,
            **self._pool_kwargs,
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        data: bytes | None = None,
    ) -> BaseHTTPResult:
        """Send an HTTP request through the right pool manager and return the result.

        The hop this method issues is never retried, and on ``urllib3`` 2.5.0
        and later a redirect is never followed, so a ``3xx`` status reaches the
        caller as the status of the request.

        An earlier ``urllib3``, which ``pyproject.toml`` still admits because
        it requires only ``urllib3 >= 1.26``, behaves differently in several
        ways that matter to an exporter. ``PoolManager.urlopen`` runs its own
        redirect handling and never sees the ``redirect=False`` that was put in
        the pool settings, so it follows up to three redirects and the caller
        gets the status of the last hop reached. A 301, 302, 307 or 308 to the
        same host re-sends the method, the body and the headers. A 303 turns
        the request into a bodiless ``GET``, so a ``303`` from a misconfigured
        endpoint gives the caller a ``200`` for an export whose payload was
        never delivered. A redirect to a different host drops the
        ``Authorization``, ``Cookie`` and ``Proxy-Authorization`` headers. A
        chain longer than three redirects comes back as a result whose
        ``error`` is a ``MaxRetryError``, which :meth:`is_connection_error`
        reports as retryable, so the exporter sends the batch again. The
        redirect target also gets a retry budget of its own, drawn from what
        is left of the ``urllib3`` default, in place of the zero this
        transport asked for.

        Every exception raised by ``urllib3`` is caught and placed in the
        result, including ones that are not connection errors, so this method
        does not raise. The ``ImportError`` for a missing PySocks is raised
        inside the same ``try``, so it too comes back as a result rather than
        as an exception.

        Args:
            method: HTTP method (e.g. ``"POST"``).
            url: Target URL. It also decides which proxy, if any, the request
                goes through.
            headers: Optional HTTP headers to include in the request. ``None``
                lets ``urllib3`` send only the headers it adds itself.
            timeout: Optional request timeout in seconds, applied as a total
                budget for the whole exchange rather than per socket
                operation. ``None`` is passed on to ``urllib3`` as an explicit
                absence of a timeout, which is not the same as leaving the
                default in place: the connect and read operations then block
                without a deadline, and the process-wide socket timeout that
                the default would have honoured does not apply.
            data: Optional request body, sent as given with no encoding step.

        Returns:
            A ``Urllib3HTTPResult`` carrying the response, with its body
            already read into memory, or one carrying only the exception when
            the request failed.
        """
        # pylint: disable-next=import-outside-toplevel
        import urllib3  # noqa: PLC0415

        try:
            response = self._get_pool_manager(url).request(
                method=method,
                url=url,
                headers=headers,
                body=data,
                timeout=urllib3.Timeout(total=timeout) if timeout is not None else None,
                preload_content=True,
            )
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            # pylint: disable-next=unexpected-keyword-arg
            return Urllib3HTTPResult(error=error)

        # pylint: disable-next=unexpected-keyword-arg
        return Urllib3HTTPResult(
            status_code=response.status,
            reason=response.reason,
            response=response,
        )

    # pylint: disable-next=no-self-use
    def is_connection_error(self, exception: Exception | None) -> bool:
        """Return whether a ``urllib3`` exception means the server was unreachable.

        Args:
            exception: The ``error`` field of a result, or ``None``.

        Returns:
            ``True`` when the exception is one of the ``urllib3`` connection,
            timeout, protocol or proxy errors, which makes the export worth
            retrying. ``False`` for any other exception and for ``None``.
        """
        return isinstance(exception, _get_connection_error_types())

    def close(self) -> None:
        """Drop every pooled connection and forget the proxy lookups.

        Clears the direct pool, clears and discards every proxy pool manager,
        and empties the per-URL proxy cache, so a later request would read the
        proxy environment variables again and open new connections. Results
        already returned keep working, because their bodies were read into
        memory before the result was built.
        """
        self._pool.clear()
        for manager in self._proxy_managers.values():
            manager.clear()
        self._proxy_managers.clear()
        self._get_proxy.cache_clear()
