# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from os import environ
from typing import Literal

import requests

from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
)
from opentelemetry.util._importlib_metadata import entry_points

# Upper bound (in seconds) applied to the exponential backoff between retries so
# it cannot grow without limit. This mirrors the behavior of the Go and Java
# OTLP exporters, which both cap the backoff interval.
_MAX_BACKOFF = 32


def _is_retryable(resp: requests.Response) -> bool:
    if resp.status_code == 408:
        return True
    if resp.status_code == 429:
        return True
    if resp.status_code >= 500 and resp.status_code <= 599:
        return True
    return False


def _parse_retry_after_header(resp: requests.Response) -> float | None:
    """Return the ``Retry-After`` delay in seconds, or ``None`` if absent/invalid.

    The ``Retry-After`` header can be either an integer number of seconds
    (delay-seconds form) or an HTTP-date. Both forms are defined by RFC 9110
    and the OpenTelemetry OTLP specification requires that the exporter honor
    the value when present on a retryable response (e.g. 429 or 503).
    """
    retry_after = resp.headers.get("Retry-After")
    if retry_after is None:
        return None
    retry_after = retry_after.strip()
    if not retry_after:
        return None
    try:
        # delay-seconds form, e.g. "Retry-After: 120"
        return float(int(retry_after))
    except ValueError:
        pass
    try:
        # HTTP-date form, e.g. "Retry-After: Wed, 21 Oct 2015 07:28:00 GMT"
        retry_date = parsedate_to_datetime(retry_after)
    except (TypeError, ValueError):
        return None
    if retry_date is None:
        return None
    if retry_date.tzinfo is None:
        retry_date = retry_date.replace(tzinfo=timezone.utc)
    delay = (retry_date - datetime.now(timezone.utc)).total_seconds()
    if delay < 0:
        return 0.0
    return delay


def _load_session_from_envvar(
    cred_envvar: Literal[
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER",
    ],
) -> requests.Session | None:
    _credential_env = environ.get(
        _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER
    ) or environ.get(cred_envvar)
    if _credential_env:
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
