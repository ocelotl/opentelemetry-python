# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from os import environ
from typing import Literal

import requests

from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
)
from opentelemetry.util._importlib_metadata import entry_points

_logger = logging.getLogger(__name__)


def _log_partial_success(response_bytes: bytes, response_class) -> None:
    """Deserialize an OTLP export response and log a warning if it reports a
    partial success.

    A partial success is signalled by the collector either rejecting some
    items (``rejected_spans`` / ``rejected_data_points`` / ``rejected_log_records``
    != 0) or by returning a non-empty ``error_message``. The request itself was
    still accepted, so this only logs; it does not change the export result.
    """
    try:
        response = response_class.FromString(response_bytes)
    except Exception:  # pylint: disable=broad-except
        # An unparseable body must not turn a successful export into a failure.
        return
    if not response.HasField("partial_success"):
        return
    partial_success = response.partial_success
    rejected = 0
    for field_name in (
        "rejected_spans",
        "rejected_data_points",
        "rejected_log_records",
    ):
        if hasattr(partial_success, field_name):
            rejected = getattr(partial_success, field_name)
            break
    error_message = partial_success.error_message
    if rejected != 0 or error_message:
        _logger.warning(
            "Partial success received from collector: %s items rejected. %s",
            rejected,
            error_message,
        )


def _is_retryable(resp: requests.Response) -> bool:
    if resp.status_code == 408:
        return True
    if resp.status_code >= 500 and resp.status_code <= 599:
        return True
    return False


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
