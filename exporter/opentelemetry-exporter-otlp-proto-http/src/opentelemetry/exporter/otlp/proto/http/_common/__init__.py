# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Configuration resolution shared by the three OTLP/HTTP exporters.

The span, metric and log exporters resolve their endpoint, TLS file paths,
headers, timeout and compression the same way, differing only in which
per-signal variable they consult and which path they append to a base endpoint.
The ``_resolve_*`` functions here take that per-signal variable as an argument
and apply one precedence rule to all three signals: a value passed to the
constructor wins over the per-signal environment variable, which wins over the
signal-independent ``OTEL_EXPORTER_OTLP_*`` variable, which wins over the
default built into this module. ``_resolve_headers`` merges the headers passed
to the constructor key by key over the headers of whichever one of the two
variables it used, but the two variables do not merge with each other: the
per-signal one replaces the signal-independent one entirely when it is set.
``_load_session_from_envvar`` reads the signal-independent variable first.

The metric exporter takes ``preferred_temporality``, ``preferred_aggregation``
and ``max_export_batch_size`` on top of that set, and none of the three is
resolved here.

Everything in this module is private. The names are imported by the exporter
modules and are not part of the public API.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from os import environ
from typing import TYPE_CHECKING, Literal

from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.otlp.common import http as _http
from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.util._importlib_metadata import entry_points
from opentelemetry.util.re import parse_env_headers

if TYPE_CHECKING:
    import requests

    from opentelemetry.exporter.http.transport._base import BaseHTTPTransport

    _CredentialEnvVar = Literal[
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER",
    ]

_logger = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = "http://localhost:4318"
_DEFAULT_TIMEOUT = 10

# 64 MiB, in bytes.
_DEFAULT_MAX_REQUEST_SIZE = 64 * 1024 * 1024


class RequestPayloadTooLargeError(Exception):
    """A serialized OTLP request exceeded the configured ``max_request_size``.

    The class name is emitted as the ``error.type`` attribute on the exporter's
    failed-export metric, so renaming it changes observable telemetry.
    """


def _is_request_too_large(serialized_data: bytes, max_request_size: int) -> bool:
    """Return True if the serialized request exceeds a positive size limit.

    The size is measured on the uncompressed serialized request, matching the
    OTLP specification's "before compression" request-size limit. A
    ``max_request_size`` of ``0`` (or any non-positive value) disables the
    check.

    Args:
        serialized_data: The protobuf-serialized export request, before any
            content encoding is applied to it.
        max_request_size: The limit in bytes. A non-positive value means no
            limit.

    Returns:
        True when the limit is positive and ``serialized_data`` is strictly
        longer than it, which is the case in which the caller drops the batch
        rather than sending it. False otherwise, including whenever the limit
        is disabled.
    """
    return 0 < max_request_size < len(serialized_data)


def _load_session_from_envvar(
    cred_envvar: _CredentialEnvVar,
) -> requests.Session | None:
    """Build the ``requests`` session named by a credential provider variable.

    A credential provider is an entry point in the
    ``opentelemetry_otlp_credential_provider`` group. This function requires
    the one it loads to return a ``requests.Session`` carrying whatever
    authentication the backend needs. The group is shared with the gRPC
    exporters, whose providers return a ``grpc.ChannelCredentials`` instead, so
    a distribution that supports both signalling protocols registers one entry
    point of each kind and the name given here has to be the HTTP one.
    The signal-independent
    ``OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER`` variable is read
    first and ``cred_envvar`` only if it is unset or empty, which is the
    reverse of the precedence the ``_resolve_*`` functions use.

    The session is built once, when the exporter is constructed, so a provider
    that mints a short-lived credential has to refresh it itself.

    Args:
        cred_envvar: Name of the per-signal environment variable to fall back
            to. Its value, or the value of the signal-independent variable, is
            the name of the entry point to load.

    Returns:
        The session the entry point returned, or None when neither variable is
        set to a non-empty value, in which case the transport creates its own
        session. Every call site reaches this function only when the exporter
        was given no session, so a None return cannot fall back to one.

    Raises:
        ImportError: ``requests`` is not importable. It is imported here rather
            than at module scope so that an installation missing it fails only
            when a credential provider is actually configured.
        RuntimeError: No entry point in the group carries the requested name,
            or the callable returned something that is not a
            ``requests.Session``.
    """
    _credential_env = environ.get(_OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER) or environ.get(cred_envvar)
    if _credential_env:
        try:
            # pylint: disable-next=import-outside-toplevel
            import requests  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "The 'requests' package is required to load a credential "
                "provider session but is not installed. Install it with "
                "`pip install requests`."
            ) from exc

        try:
            maybe_session = next(
                iter(
                    entry_points(
                        group="opentelemetry_otlp_credential_provider",
                        name=_credential_env,
                    )
                )
            ).load()()
        except StopIteration:
            raise RuntimeError(
                f"Requested component '{_credential_env}' not found in "
                f"entry point 'opentelemetry_otlp_credential_provider'"
            )
        if isinstance(maybe_session, requests.Session):
            return maybe_session
        else:
            raise RuntimeError(
                f"Requested component '{_credential_env}' is of type {type(maybe_session)}"
                f" must be of type `requests.Session`."
            )
    return None


def _normalize_compression(
    compression: Compression | _http.Compression | None,
) -> _http.Compression | None:
    """Translate this package's ``Compression`` enum into the shared one.

    The exporters accept either
    :class:`~opentelemetry.exporter.otlp.proto.http.Compression`, which they
    have accepted since before the HTTP client was factored out, or the
    ``Compression`` enum of ``opentelemetry.exporter.otlp.common.http``, which
    is what the client itself takes. The two carry the same three encodings
    under different member names.

    Args:
        compression: A member of either enum, or None.

    Returns:
        The member of the shared enum that denotes the same encoding. A value
        that is already a member of the shared enum is returned unchanged, and
        None is returned as None, which tells the caller to fall back to the
        environment variables.
    """
    match compression:
        case Compression.NoCompression:
            return _http.Compression.NONE
        case Compression.Deflate:
            return _http.Compression.DEFLATE
        case Compression.Gzip:
            return _http.Compression.GZIP
        case _:
            return compression


def _resolve_endpoint(
    endpoint_env_var: str,
    default_path: Literal["v1/traces", "v1/metrics", "v1/logs"],
) -> str:
    """Resolve the full URL an exporter posts its requests to.

    A per-signal endpoint is used exactly as given, because the OTLP
    specification requires it to already name the signal path. A
    signal-independent endpoint is a base URL instead, so ``default_path`` is
    appended to it, after exactly one trailing slash is removed. A base URL
    ending in more than one slash therefore still produces a doubled separator.

    Args:
        endpoint_env_var: Name of the per-signal endpoint variable, such as
            ``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT``.
        default_path: Path segment for this signal, appended only to a base
            URL.

    Returns:
        The value of the per-signal variable when it is set to a non-empty
        string. Otherwise ``OTEL_EXPORTER_OTLP_ENDPOINT``, or
        ``http://localhost:4318`` when that is unset, with ``default_path``
        appended.
    """
    if endpoint := os.environ.get(endpoint_env_var):
        return endpoint

    base_endpoint = os.environ.get(OTEL_EXPORTER_OTLP_ENDPOINT) or _DEFAULT_ENDPOINT

    return f"{base_endpoint.removesuffix('/')}/{default_path}"


def _resolve_headers(
    headers: Mapping[str, str] | None,
    headers_env_var: str,
) -> dict[str, str]:
    """Merge the header sources into the headers sent with every request.

    Three sources are applied in order, each overwriting a key the previous one
    set: the ``Content-Type`` and ``User-Agent`` this package always sends,
    then the headers parsed out of an environment variable, then ``headers``.
    Every key is lowercased first, so a header given in a different case still
    replaces rather than duplicates the earlier value.

    The environment variables do not merge with each other. The per-signal one
    replaces the signal-independent one entirely when it is set to a non-empty
    string.

    Args:
        headers: Headers passed to the exporter constructor, or None for none.
            These take precedence over both environment variables.
        headers_env_var: Name of the per-signal headers variable, such as
            ``OTEL_EXPORTER_OTLP_TRACES_HEADERS``. Its value, or that of
            ``OTEL_EXPORTER_OTLP_HEADERS``, is parsed as the comma-separated
            ``key=value`` list the OTLP specification defines. Parsing is
            liberal, so a pair whose name or value is not URL-encoded is still
            accepted, and a pair that cannot be parsed at all is dropped with a
            warning instead of raising.

    Returns:
        A new dictionary whose keys are all lowercase, ready to be handed to
        the HTTP client.
    """
    headers_ = {k.lower(): v for k, v in _OTLP_HTTP_HEADERS.items()}
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
    """Resolve the deadline, in seconds, for one export request.

    The deadline covers the whole export, including the retries and the
    backoff waits between them, not a single HTTP attempt.

    Args:
        timeout_env_var: Name of the per-signal timeout variable, such as
            ``OTEL_EXPORTER_OTLP_TRACES_TIMEOUT``.

    Returns:
        The value of the per-signal variable when it is set to a non-empty
        string, otherwise ``OTEL_EXPORTER_OTLP_TIMEOUT``, otherwise 10. A value
        that does not parse as a float is reported with a warning and replaced
        by 10 rather than raising, so a typo degrades the timeout instead of
        preventing the exporter from being constructed.
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


def _resolve_compression(compression_env_var: str) -> _http.Compression:
    """Resolve the content encoding from the environment.

    This is consulted only when the exporter was constructed without an
    explicit compression, because a constructor argument overrides both
    variables.

    Args:
        compression_env_var: Name of the per-signal compression variable, such
            as ``OTEL_EXPORTER_OTLP_TRACES_COMPRESSION``.

    Returns:
        The encoding named by the per-signal variable when it is set to a
        non-empty string, otherwise by ``OTEL_EXPORTER_OTLP_COMPRESSION``,
        otherwise no compression. The value is lowercased and stripped before
        it is matched, and a value naming no known encoding is reported with a
        warning and treated as no compression.
    """
    value = (
        (os.environ.get(compression_env_var) or os.environ.get(OTEL_EXPORTER_OTLP_COMPRESSION) or "none")
        .lower()
        .strip()
    )

    try:
        return _http.Compression.from_str(value)
    except ValueError:
        _logger.warning("Unsupported compression type: %s", value)
        return _http.Compression.NONE


def _build_transport(
    certificate_file: str | None,
    client_key_file: str | None,
    client_certificate_file: str | None,
    certificate_env_var: str,
    client_key_env_var: str,
    client_certificate_env_var: str,
    session: requests.Session | None,
) -> BaseHTTPTransport:
    """Build the transport the exporter sends its requests through.

    The three TLS file paths follow the same precedence as every other setting:
    the constructor argument, then the per-signal variable, then the
    signal-independent one.

    A client certificate and a client key are only passed to ``requests`` as a
    pair when both resolve to a path. A key that resolves on its own is
    discarded and no client credential is sent. A certificate that resolves on
    its own is passed as a combined certificate-and-key file, so client
    authentication still happens when that one file carries the key too.

    Args:
        certificate_file: Path to the CA certificate bundle used to verify the
            server, or None to resolve it from the environment. When nothing
            resolves, the default certificate store is used and verification
            stays on.
        client_key_file: Path to the client private key, or None to resolve it
            from the environment.
        client_certificate_file: Path to the client certificate, or None to
            resolve it from the environment.
        certificate_env_var: Name of the per-signal CA certificate variable,
            such as ``OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE``.
        client_key_env_var: Name of the per-signal client key variable.
        client_certificate_env_var: Name of the per-signal client certificate
            variable.
        session: A ``requests`` session the transport should reuse, typically
            one a credential provider built, or None to let the transport
            create its own.

    Returns:
        A transport backed by ``requests``, configured with the resolved
        verification setting and client credentials.
    """
    verify: bool | str = (
        certificate_file
        or os.environ.get(certificate_env_var)
        or os.environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE)
        or True
    )
    client_key_file = (
        client_key_file or os.environ.get(client_key_env_var) or os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY)
    )
    client_certificate_file = (
        client_certificate_file
        or os.environ.get(client_certificate_env_var)
        or os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE)
    )
    cert = (
        (client_certificate_file, client_key_file)
        if client_certificate_file and client_key_file
        else client_certificate_file
    )

    return RequestsHTTPTransport(verify=verify, cert=cert, session=session)
