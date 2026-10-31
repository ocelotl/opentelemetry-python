# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Settings resolution shared by the three OTLP JSON over HTTP exporters.

The span, metric and log exporters in this package take the same connection
settings, and each one resolves them the same way: the value passed to the
exporter constructor wins, then the per-signal environment variable, then the
generic ``OTEL_EXPORTER_OTLP_*`` variable, then a built-in default.

``_resolve_endpoint``, ``_resolve_timeout`` and ``_resolve_compression`` cover
the environment and default steps only; the exporter applies its own
constructor argument before it calls them. ``_resolve_headers`` and
``_build_transport`` take the constructor values as arguments and apply the
whole precedence themselves. ``_build_transport`` does so because it resolves
three file paths, each falling back through its own chain.
``_resolve_headers`` does so because it merges the constructor headers over the
environment ones entry by entry instead of replacing them wholesale. The choice
between the per-signal and the generic headers variable is still made once, for
the whole variable rather than per entry, so one entry in the per-signal
variable suppresses every entry of the generic one.

Every helper takes the names of the per-signal environment variables it reads
as arguments, since those are the names that differ between the three
exporters, and hard-codes the name of the generic variable it falls back to.
``_resolve_endpoint`` takes the signal path to append as well, and
``_build_transport`` takes three per-signal names rather than one.

None of these helpers raises on bad input, so a typo in the environment
degrades the configuration instead of preventing the exporter from being
constructed. ``_resolve_timeout`` and ``_resolve_compression`` report the bad
value through this module's logger and fall back to the default. A malformed
entry in a headers variable is dropped by
``opentelemetry.util.re.parse_env_headers``, which reports it through its own
logger, so raising the level of this module's logger alone does not surface it.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal

from opentelemetry.exporter.http.transport._urllib3 import Urllib3HTTPTransport
from opentelemetry.exporter.otlp.common.http import Compression
from opentelemetry.exporter.otlp.json.http.version import __version__
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.util.re import parse_env_headers

if TYPE_CHECKING:
    from opentelemetry.exporter.http.transport import BaseHTTPTransportFactory
    from opentelemetry.exporter.http.transport._base import BaseHTTPTransport

_DEFAULT_ENDPOINT = "http://localhost:4318"
_DEFAULT_TIMEOUT = 10

_logger = logging.getLogger(__name__)


def _resolve_endpoint(
    endpoint_env_var: str,
    default_path: Literal["v1/traces", "v1/metrics", "v1/logs"],
) -> str:
    """Resolve the URL one signal is posted to, signal path included.

    The per-signal environment variable is taken as a complete URL and used
    unchanged, because the OpenTelemetry specification defines it as already
    naming the signal. When it is unset or empty, ``default_path`` is appended
    to ``OTEL_EXPORTER_OTLP_ENDPOINT``, or to ``http://localhost:4318`` when
    that variable is unset or empty as well. One trailing slash is removed from
    the base before the path is appended, so a base written as
    ``http://collector:4318/`` does not produce a doubled slash in front of the
    signal path. A base ending in more than one slash keeps the rest of them.

    Args:
        endpoint_env_var: Name of the per-signal endpoint environment variable,
            for example ``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT``.
        default_path: Path appended to the generic endpoint for this signal.

    Returns:
        An absolute URL to post to.
    """
    if endpoint := os.environ.get(endpoint_env_var):
        return endpoint

    base_endpoint = os.environ.get(OTEL_EXPORTER_OTLP_ENDPOINT) or _DEFAULT_ENDPOINT

    return f"{base_endpoint.removesuffix('/')}/{default_path}"


def _resolve_headers(
    headers: Mapping[str, str] | None,
    headers_env_var: str,
) -> dict[str, str]:
    """Merge the request headers sent with every export of one signal.

    Three sources are combined, each one overriding the previous: the headers
    this package always sends (``content-type: application/json`` and a
    ``user-agent`` naming the exporter and its version), then the headers
    parsed from the per-signal environment variable or, when that is unset or
    empty, from ``OTEL_EXPORTER_OTLP_HEADERS``, then ``headers``. The
    environment is parsed liberally, which widens the accepted value syntax by
    the space character alone, so ``authorization=Bearer tok en`` is kept
    rather than dropped with a warning. A value holding any other character the
    specification requires to be percent encoded, ``;`` and ``"`` among them,
    is still dropped with a warning. A value is percent decoded only when it
    matches the strict syntax, so ``x-a=a%20b`` arrives as ``a b`` while
    ``x-a=a%20b c`` arrives as ``a%20b c``.

    Args:
        headers: Headers passed to the exporter constructor, or ``None`` to
            take headers from the environment alone. Names are lowercased so
            that they replace an entry of the same name that came from the
            environment instead of being sent alongside it.
        headers_env_var: Name of the per-signal headers environment variable,
            for example ``OTEL_EXPORTER_OTLP_TRACES_HEADERS``.

    Returns:
        A new dictionary with lowercased header names. ``headers`` is not
        modified.
    """
    headers_ = {
        "content-type": "application/json",
        "user-agent": "OTel-OTLP-JSON-Exporter-Python/" + __version__,
    }
    env_headers = parse_env_headers(
        os.environ.get(headers_env_var) or os.environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        liberal=True,
    )
    headers_.update(env_headers)
    if headers:
        headers_.update({key.lower(): value for key, value in headers.items()})
    return headers_


def _resolve_timeout(
    timeout_env_var: str,
) -> float:
    """Resolve the timeout given to the OTLP HTTP client of one signal, in seconds.

    The resolved value is handed to the OTLP HTTP client, where it bounds one
    call into that client together with the retries of that call. The span and
    log exporters make one such call per export, so for them it bounds the
    whole export. The metric exporter makes one call per request when
    ``max_export_batch_size`` splits a collection, and each of those calls gets
    the value afresh. The per-signal environment variable is read first, then
    ``OTEL_EXPORTER_OTLP_TIMEOUT``, then a default of 10 seconds. A value that
    ``float`` cannot parse is logged at warning level and replaced by that same
    default, so the exporter is still constructed.

    Args:
        timeout_env_var: Name of the per-signal timeout environment variable,
            for example ``OTEL_EXPORTER_OTLP_TRACES_TIMEOUT``.

    Returns:
        The timeout in seconds.
    """
    raw = os.environ.get(timeout_env_var) or os.environ.get(OTEL_EXPORTER_OTLP_TIMEOUT) or _DEFAULT_TIMEOUT

    try:
        return float(raw)
    except ValueError:
        _logger.warning(
            "Invalid timeout value %r, using default of %s seconds",
            raw,
            _DEFAULT_TIMEOUT,
        )
        return float(_DEFAULT_TIMEOUT)


def _resolve_compression(compression_env_var: str) -> Compression:
    """Resolve the compression applied to the request body of one signal.

    The per-signal environment variable is read first, then
    ``OTEL_EXPORTER_OTLP_COMPRESSION``, then the literal ``"none"``. The value
    is lowercased and stripped of surrounding whitespace before it is matched,
    so ``" GZIP "`` is accepted. A value naming no known compression is logged
    at warning level and the body is sent uncompressed.

    Args:
        compression_env_var: Name of the per-signal compression environment
            variable, for example ``OTEL_EXPORTER_OTLP_TRACES_COMPRESSION``.

    Returns:
        One of the ``Compression`` members ``NONE``, ``DEFLATE`` or ``GZIP``.
    """
    val = (
        (
            os.environ.get(
                compression_env_var,
            )
            or os.environ.get(OTEL_EXPORTER_OTLP_COMPRESSION)
            or "none"
        )
        .lower()
        .strip()
    )

    try:
        return Compression.from_str(val)
    except ValueError:
        _logger.warning("Unsupported compression type: %s", val)
        return Compression.NONE


def _build_transport(
    certificate_file: str | None,
    client_key_file: str | None,
    client_certificate_file: str | None,
    certificate_env_var: str,
    client_key_env_var: str,
    client_certificate_env_var: str,
    transport_factory: BaseHTTPTransportFactory = Urllib3HTTPTransport,
) -> BaseHTTPTransport:
    """Construct the HTTP transport one exporter sends its requests through.

    Each of the three TLS settings is taken from its argument, then from the
    per-signal environment variable, then from the generic
    ``OTEL_EXPORTER_OTLP_*`` variable. When no certificate authority bundle is
    named by any of the three, the transport verifies the server against the
    default trust store rather than skipping verification.

    A client certificate is passed on its own unless a client key is also
    configured, in which case the certificate and the key are passed as a pair.
    A client key configured without a client certificate is ignored, because
    the transport has no way to present a key alone.

    Args:
        certificate_file: Path to the certificate authority bundle used to
            verify the server, or ``None`` to fall back to the environment.
        client_key_file: Path to the private key of the client certificate, or
            ``None`` to fall back to the environment.
        client_certificate_file: Path to the client certificate presented for
            mutual TLS, or ``None`` to fall back to the environment.
        certificate_env_var: Name of the per-signal certificate authority
            environment variable, for example
            ``OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE``.
        client_key_env_var: Name of the per-signal client key environment
            variable, for example ``OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY``.
        client_certificate_env_var: Name of the per-signal client certificate
            environment variable, for example
            ``OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE``.
        transport_factory: Callable invoked with the resolved ``verify`` and
            ``cert`` keyword arguments to build the transport. It defaults to
            ``Urllib3HTTPTransport``.

    Returns:
        A transport ready to be handed to the OTLP HTTP client.
    """
    verify: bool | str = (
        certificate_file
        or os.environ.get(
            certificate_env_var,
        )
        or os.environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE)
        or True
    )
    client_key_file = (
        client_key_file
        or os.environ.get(
            client_key_env_var,
        )
        or os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY)
    )
    client_certificate_file = (
        client_certificate_file
        or os.environ.get(
            client_certificate_env_var,
        )
        or os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE)
    )
    return transport_factory(
        verify=verify,
        cert=(client_certificate_file, client_key_file)
        if client_certificate_file and client_key_file
        else client_certificate_file,
    )
