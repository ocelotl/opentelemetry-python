# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Selection of the HTTP client library an HTTP exporter sends through.

An exporter names a transport by a string, ``_load_http_transport_factory``
turns that string into a factory, and calling the factory with ``verify`` and
``cert`` gives a ``BaseHTTPTransport`` in
``opentelemetry.exporter.http.transport._base``.

Two names are built in: ``"requests"`` and ``"urllib3"``. Each needs the
matching extra of this package to be installed, since neither client library
is a hard dependency. A third party registers another name under the
``opentelemetry_http_transport`` entry point group.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport as _RequestsHTTPTransport,
)

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport as _Urllib3HTTPTransport,
)

if TYPE_CHECKING:
    from typing import Any, Protocol

    from opentelemetry.exporter.http.transport._base import BaseHTTPTransport

    class BaseHTTPTransportFactory(Protocol):
        """What a registered transport has to be callable as.

        Any callable with this signature qualifies. A class qualifies through
        its constructor, which is what the two built-in entries are, and a
        factory function qualifies just as well: ``_load_http_transport_factory``
        checks only that the loaded entry point is callable. Any keyword
        argument beyond ``verify`` and ``cert`` is optional for the caller and
        has to be tolerated by the callee, so an exporter can pass the same
        keyword arguments whichever transport is selected.
        """

        def __call__(
            self,
            *,
            verify: bool | str,
            cert: str | tuple[str, str] | None,
            **kwargs: Any,
        ) -> BaseHTTPTransport:
            """Build a transport that carries the given TLS settings.

            Both arguments are keyword only, so a factory is free to name its
            remaining parameters as it likes.

            Args:
                verify: TLS verification setting. ``True`` verifies against
                    the default certificate bundle of the factory, ``False``
                    disables verification, and a string is the path of a CA
                    bundle to verify against.
                cert: Client certificate for mutual TLS. A string is the path
                    of a file holding both the certificate and its unencrypted
                    private key, a pair of strings is the certificate path and
                    the key path, and ``None`` sends no client certificate.
                **kwargs: Options that only some transports understand. A
                    factory accepts them and ignores the ones it has no use
                    for, so an exporter can pass one set of options whichever
                    transport is selected.

            Returns:
                A transport ready to send requests. An exporter holds on to it
                and calls :meth:`BaseHTTPTransport.close` when it shuts down.
            """
            ...  # pylint: disable=unnecessary-ellipsis


_KNOWN_TRANSPORTS: dict[str, BaseHTTPTransportFactory] = {
    "requests": _RequestsHTTPTransport,
    "urllib3": _Urllib3HTTPTransport,
}


def _load_http_transport_factory(name: str) -> BaseHTTPTransportFactory:
    """Return the transport factory registered under *name*.

    Checks the built-in transport registry first to avoid the overhead of an
    entry-point scan for built-in transports. Falls back to standard entry-point
    discovery for user supplied transports registered under the
    ``opentelemetry_http_transport`` group.

    The factory is returned, not called, so the client library behind a
    built-in name is still not imported when this returns. Nothing is cached:
    an entry point lookup is repeated on every call for a name that is not
    built in.

    Args:
        name: Entry point name, e.g. ``"requests"`` or ``"urllib3"``.

    Returns:
        A callable with signature
        ``(*, verify, cert, **kwargs) -> BaseHTTPTransport``. For a built-in
        name this is the transport class itself.

    Raises:
        ValueError: If no transport is registered under ``name``. A built-in
            name is found whether or not its extra is installed, so a missing
            client library surfaces later as an ``ImportError`` raised by the
            factory rather than here.
        TypeError: If the loaded entry point is not callable.
    """
    if name in _KNOWN_TRANSPORTS:
        return _KNOWN_TRANSPORTS[name]
    # pylint: disable-next=import-outside-toplevel,import-error
    from opentelemetry.util._importlib_metadata import (  # noqa: PLC0415
        entry_points,
    )

    ep = next(
        iter(entry_points(group="opentelemetry_http_transport", name=name)),
        None,
    )
    if not ep:
        raise ValueError(
            f"No HTTP transport registered under name {name!r}. "
            "Install the corresponding extra or register an entry point "
            "under the 'opentelemetry_http_transport' group."
        )
    factory = ep.load()
    if not callable(factory):
        raise TypeError(f"Transport {name!r} loaded from entry point is not callable (got {factory!r}).")
    return cast("BaseHTTPTransportFactory", factory)
