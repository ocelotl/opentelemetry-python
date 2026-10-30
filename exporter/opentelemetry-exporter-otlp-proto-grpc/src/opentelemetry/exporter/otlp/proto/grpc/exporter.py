# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OTLP Exporter

This module provides a mixin class for OTLP exporters that send telemetry data
to an OTLP-compatible receiver via gRPC. It includes a configurable reconnection
logic to handle transient collector outages.

"""

import os
import random
import threading
from abc import ABC, abstractmethod
from collections.abc import (
    Callable,
    Iterable,
    Sequence,  # noqa: F401
)
from collections.abc import Sequence as TypingSequence
from logging import getLogger
from os import environ
from time import time
from typing import (  # noqa: F401
    Any,
    Generic,
    Literal,
    NewType,
    Optional,
    TypeVar,
)
from urllib.parse import urlparse

from google.rpc.error_details_pb2 import RetryInfo
from typing_extensions import deprecated

from grpc import (
    ChannelCredentials,
    Compression,
    RpcError,
    StatusCode,
    insecure_channel,
    secure_channel,
    ssl_channel_credentials,
)
from opentelemetry.exporter.otlp.common._exporter_metrics import (
    create_exporter_metrics,
)
from opentelemetry.exporter.otlp.proto.common._internal import (
    _get_resource_data,
)
from opentelemetry.exporter.otlp.proto.grpc import (
    _OTLP_GRPC_CHANNEL_OPTIONS,
    _timeout_from_env,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2_grpc import (
    LogsServiceStub,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2_grpc import (
    MetricsServiceStub,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    AnyValue,
    ArrayValue,
    KeyValue,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource  # noqa: F401
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import LogRecordExportResult
from opentelemetry.sdk._shared_internal import DuplicateFilter
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_GRPC_CREDENTIAL_PROVIDER,
    _OTEL_PYTHON_EXPORTER_OTLP_GRPC_RETRYABLE_ERROR_CODES,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_INSECURE,
    OTEL_EXPORTER_OTLP_TIMEOUT,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.metrics.export import MetricExportResult, MetricsData
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.semconv._incubating.attributes.rpc_attributes import (
    RPC_RESPONSE_STATUS_CODE,
)
from opentelemetry.util._importlib_metadata import entry_points
from opentelemetry.util.re import parse_env_headers

_RETRYABLE_ERROR_CODES = frozenset(
    [
        StatusCode.CANCELLED,
        StatusCode.DEADLINE_EXCEEDED,
        StatusCode.RESOURCE_EXHAUSTED,
        StatusCode.ABORTED,
        StatusCode.OUT_OF_RANGE,
        StatusCode.UNAVAILABLE,
        StatusCode.DATA_LOSS,
    ]
)
_MAX_RETRYS = 6
logger = getLogger(__name__)
# This prevents logs generated when a log fails to be written to generate another log which fails to be written etc. etc.
logger.addFilter(DuplicateFilter())
SDKDataT = TypeVar(
    "SDKDataT",
    TypingSequence[ReadableLogRecord],
    MetricsData,
    TypingSequence[ReadableSpan],
)
ResourceDataT = TypeVar("ResourceDataT")
TypingResourceT = TypeVar("TypingResourceT")
ExportServiceRequestT = TypeVar(
    "ExportServiceRequestT",
    ExportTraceServiceRequest,
    ExportMetricsServiceRequest,
    ExportLogsServiceRequest,
)
ExportResultT = TypeVar(
    "ExportResultT",
    LogRecordExportResult,
    MetricExportResult,
    SpanExportResult,
)
ExportStubT = TypeVar("ExportStubT", TraceServiceStub, MetricsServiceStub, LogsServiceStub)

_ENVIRON_TO_COMPRESSION = {
    None: None,
    "gzip": Compression.Gzip,
}


class InvalidCompressionValueException(Exception):
    """Raised when a compression environment variable holds a value gRPC cannot use.

    The only value this package accepts is ``gzip``. The exception message
    repeats both the variable name and the offending value, so the operator
    can find the misconfigured variable without reading the traceback.

    Args:
        environ_key: Name of the environment variable that was read.
        environ_value: Value found in that variable, already lowercased and
            stripped.
    """

    def __init__(self, environ_key: str, environ_value: str):
        """Build the exception message. The arguments are documented on the class."""
        super().__init__(f'Invalid value "{environ_value}" for compression envvar {environ_key}')


def environ_to_compression(environ_key: str) -> Compression | None:
    """Translate the value of a compression environment variable into a gRPC compression method.

    Args:
        environ_key: Name of the environment variable to read, for example
            ``OTEL_EXPORTER_OTLP_COMPRESSION``. The value is lowercased and
            stripped before it is compared.

    Returns:
        ``grpc.Compression.Gzip`` when the variable holds ``gzip``, and
        ``None`` when the variable is unset. ``None`` leaves the choice to the
        caller, and the callers in this package do two different things with
        it: ``OTLPExporterMixin`` falls back to
        ``grpc.Compression.NoCompression``, while the three exporter
        constructors pass the ``None`` on so that the generic compression
        variable is read next.

    Raises:
        InvalidCompressionValueException: When the variable is set to anything
            other than ``gzip``.
    """
    environ_value = environ[environ_key].lower().strip() if environ_key in environ else None
    if environ_value not in _ENVIRON_TO_COMPRESSION and environ_value is not None:
        raise InvalidCompressionValueException(environ_key, environ_value)
    return _ENVIRON_TO_COMPRESSION[environ_value]


@deprecated(
    "Use one of the encoders from opentelemetry-exporter-otlp-proto-common instead. Deprecated since version 1.18.0.",
)
def get_resource_data(
    sdk_resource_scope_data: dict[SDKResource, ResourceDataT],
    resource_class: Callable[..., TypingResourceT],
    name: str,
) -> list[TypingResourceT]:
    """Group SDK data by resource and wrap each group in a protobuf resource message.

    This is a thin forwarding wrapper kept for backwards compatibility. New
    code calls one of the encoders in
    ``opentelemetry-exporter-otlp-proto-common`` instead.

    Args:
        sdk_resource_scope_data: Mapping from an SDK resource to a mapping of
            already encoded scope data collected under that resource. Only the
            values of the inner mapping reach the protobuf message; its keys
            are the instrumentation scopes and are dropped here.
        resource_class: Protobuf message class to instantiate once per
            resource, for example ``ResourceSpans``. It is called with the
            encoded resource under the keyword ``resource`` and the scope data
            under the keyword built from ``name``.
        name: Signal part of the scope keyword, for example ``spans``, which
            is passed to ``resource_class`` as ``scope_spans``.

    Returns:
        One instance of ``resource_class`` per entry in
        ``sdk_resource_scope_data``, in iteration order of that mapping.
    """
    return _get_resource_data(sdk_resource_scope_data, resource_class, name)


def _read_file(file_path: str) -> bytes | None:
    """Read a certificate or key file from disk.

    Args:
        file_path: Path of the file to read.

    Returns:
        The bytes of the file, or ``None`` when the file does not exist. A
        path that does not exist is logged with its name rather than raised,
        so it degrades to the default TLS credentials instead of stopping the
        process.

    Raises:
        OSError: When the path exists and still cannot be read. Only
            ``FileNotFoundError`` is caught, so ``PermissionError`` for a file
            the process may not open and ``IsADirectoryError`` for a path that
            names a directory both reach the caller.
    """
    try:
        with open(file_path, "rb") as file:
            return file.read()
    except FileNotFoundError as e:
        logger.exception(
            "Failed to read file: %s. Please check if the file exists and is accessible.",
            e.filename,
        )
        return None


def _load_credentials(
    certificate_file: str | None,
    client_key_file: str | None,
    client_certificate_file: str | None,
) -> ChannelCredentials:
    """Build TLS channel credentials from certificate and key files on disk.

    Args:
        certificate_file: Path of the PEM file holding the root certificates
            used to verify the receiver. ``None`` falls back to the root
            certificates gRPC finds for itself.
        client_key_file: Path of the PEM file holding the client private key
            used for mutual TLS. ``None`` means no client key is sent.
        client_certificate_file: Path of the PEM file holding the client
            certificate chain used for mutual TLS. ``None`` means no client
            certificate is sent.

    Returns:
        Channel credentials built from whichever of the three files was read.
        A path that does not exist is logged and treated as if it had not been
        given, so the result can be weaker than the caller asked for.

    Raises:
        OSError: When one of the paths exists and still cannot be read,
            propagated from ``_read_file``.
    """
    root_certificates = _read_file(certificate_file) if certificate_file else None
    private_key = _read_file(client_key_file) if client_key_file else None
    certificate_chain = _read_file(client_certificate_file) if client_certificate_file else None

    return ssl_channel_credentials(
        root_certificates=root_certificates,
        private_key=private_key,
        certificate_chain=certificate_chain,
    )


def _get_credentials(
    creds: ChannelCredentials | None,
    credential_entry_point_env_key: str,
    certificate_file_env_key: str,
    client_key_file_env_key: str,
    client_certificate_file_env_key: str,
) -> ChannelCredentials:
    """Resolve the TLS channel credentials an exporter should use.

    Three sources are consulted in order: the credentials the caller passed,
    a credential provider named by an environment variable and loaded through
    the ``opentelemetry_otlp_credential_provider`` entry point group, and a
    set of certificate file paths read from environment variables.

    Args:
        creds: Credentials the caller built itself. When this is not ``None``
            it is returned unchanged and no environment variable is read.
        credential_entry_point_env_key: Name of the environment variable
            holding the name of a credential provider entry point.
        certificate_file_env_key: Name of the environment variable holding the
            path of the root certificate file. When this variable is unset,
            the two client file variables below are not read at all.
        client_key_file_env_key: Name of the environment variable holding the
            path of the client private key file, for mutual TLS.
        client_certificate_file_env_key: Name of the environment variable
            holding the path of the client certificate file, for mutual TLS.

    Returns:
        The credentials from the first source that yields any, and otherwise
        credentials built from the root certificates gRPC finds for itself.

    Raises:
        RuntimeError: When the credential provider environment variable names
            an entry point that is not installed, or names one whose return
            value is not a ``grpc.ChannelCredentials``.
        OSError: When one of the certificate file paths exists and still
            cannot be read, propagated from ``_load_credentials``.
    """
    if creds is not None:
        return creds
    _credential_env = environ.get(credential_entry_point_env_key)
    if _credential_env:
        try:
            maybe_channel_creds = next(
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
        if isinstance(maybe_channel_creds, ChannelCredentials):
            return maybe_channel_creds
        else:
            raise RuntimeError(
                f"Requested component '{_credential_env}' is of type {type(maybe_channel_creds)}"
                f" must be of type `grpc.ChannelCredentials`."
            )

    certificate_file = environ.get(certificate_file_env_key)
    if certificate_file:
        client_key_file = environ.get(client_key_file_env_key)
        client_certificate_file = environ.get(client_certificate_file_env_key)
        credentials = _load_credentials(certificate_file, client_key_file, client_certificate_file)
        if credentials is not None:
            return credentials
    return ssl_channel_credentials()


# pylint: disable=no-member
class OTLPExporterMixin(ABC, Generic[SDKDataT, ExportServiceRequestT, ExportResultT, ExportStubT]):
    """OTLP gRPC exporter mixin.

    This class provides the base functionality for OTLP exporters that send
    telemetry data (spans, metrics or log records) to an OTLP-compatible
    receiver via gRPC.
    It includes a configurable reconnection mechanism to handle transient
    receiver outages.

    Args:
        stub: gRPC service stub class for the signal being exported, for
            example ``TraceServiceStub``. It is instantiated with the channel
            every time the channel is created or recreated.
        result: Export result enumeration for the signal being exported, for
            example ``SpanExportResult``. Its ``SUCCESS`` and ``FAILURE``
            members are what ``_export`` returns.
        endpoint: OTLP-compatible receiver endpoint. Falls back to
            :envvar:`OTEL_EXPORTER_OTLP_ENDPOINT` and then to
            ``http://localhost:4317``. When the endpoint is written with a
            scheme, only the host and port are kept, because the gRPC exporter
            addresses a service rather than a URL path, and a path that holds
            more than slashes is dropped with a warning naming the HTTP
            exporter instead. The same happens for an endpoint that starts
            with ``//`` and no scheme, because the host and port are taken
            from the network location that ``urlparse`` reports rather than
            from the scheme. An endpoint that has neither a scheme nor a
            leading ``//`` has no network location, and is passed to gRPC
            unchanged, so a path in it is neither dropped nor reported.
        insecure: Connection type. ``True`` sends plain HTTP/2 with no TLS.
            ``None`` means the value is taken from
            :envvar:`OTEL_EXPORTER_OTLP_INSECURE`, or from the endpoint scheme
            when that variable is unset. Only an ``http`` scheme gives
            ``True`` that way, so an endpoint written without a scheme
            resolves to ``False`` and opens a TLS channel. An ``https`` scheme
            forces ``False`` whatever the argument and that variable say,
            because the scheme is tested before either of them is.
        credentials: ChannelCredentials object for server authentication. Used
            only when the connection is not insecure, and returned unchanged
            when it is not ``None``. ``None`` on a connection that is not
            insecure means the credentials are resolved from the environment
            instead: first the entry point named by
            ``OTEL_PYTHON_EXPORTER_OTLP_GRPC_CREDENTIAL_PROVIDER``, then
            :envvar:`OTEL_EXPORTER_OTLP_CERTIFICATE` with its client key and
            client certificate companions, then the root certificates gRPC
            finds for itself. An insecure connection resolves nothing and
            reads none of those variables.
        headers: Headers to send when exporting, as a mapping, as a sequence
            of pairs, or as the comma-separated string form used by
            :envvar:`OTEL_EXPORTER_OTLP_HEADERS`. ``None`` means that
            environment variable is read, and no headers are sent when it is
            unset too.
            An empty mapping, sequence or string is treated the same way
            as ``None``, so this argument cannot suppress the headers the
            environment configures.
        timeout: Backend request timeout in seconds. This is the deadline for
            the whole export including retries, not for one attempt. ``None``
            means the value is taken from
            :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT`, defaulting to 10 seconds. A
            timeout of ``0`` is treated the same way as ``None``.
        compression: gRPC compression method to use. ``None`` means the value
            is taken from :envvar:`OTEL_EXPORTER_OTLP_COMPRESSION`, and no
            compression is used when that variable is unset too. Any value of
            that variable other than ``gzip`` makes the constructor raise
            ``InvalidCompressionValueException``.
        channel_options: gRPC channel options, as a sequence of name and value
            pairs. They are merged over this package's own options, so an
            option given here overrides the default of the same name.
        retryable_error_codes: gRPC status codes that cause an export to be
            retried. ``None`` means the value is taken from
            ``OTEL_PYTHON_EXPORTER_OTLP_GRPC_RETRYABLE_ERROR_CODES``, parsed as
            a comma-separated list of status code names, and otherwise falls
            back to this module's own set.
            An empty iterable is treated the same way as ``None``, so this
            argument cannot ask for no retries at all.
        component_type: Semantic conventions component type recorded as an
            attribute on the exporter's own self-observability metrics.
            ``None`` records ``unknown_otlp_exporter`` instead, and does not
            stop those metrics from being recorded.
        signal: Signal name, which selects which self-observability
            instruments the exporter creates.
        meter_provider: Meter provider used to record the exporter's own
            self-observability metrics. ``None`` means the globally configured
            meter provider is used. Those metrics are recorded at all only
            when :envvar:`OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED` is set to
            ``true``.

    Raises:
        RuntimeError: When ``OTEL_PYTHON_EXPORTER_OTLP_GRPC_CREDENTIAL_PROVIDER``
            names an entry point that is not installed, or one whose return
            value is not a ``grpc.ChannelCredentials``. The constructor is
            where this surfaces.
        KeyError: When ``retryable_error_codes`` is ``None`` and
            ``OTEL_PYTHON_EXPORTER_OTLP_GRPC_RETRYABLE_ERROR_CODES`` holds a
            name that is not a ``grpc.StatusCode`` member. The key is that
            name, uppercased, and the message names neither the variable nor
            the rest of the list.
        OSError: When a certificate file path read from the environment exists
            and still cannot be opened.
    """

    def __init__(
        self,
        stub: ExportStubT,
        result: ExportResultT,
        endpoint: str | None = None,
        insecure: bool | None = None,
        credentials: ChannelCredentials | None = None,
        headers: TypingSequence[tuple[str, str]] | dict[str, str] | str | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        channel_options: tuple[tuple[str, str]] | None = None,
        retryable_error_codes: Iterable[StatusCode] | None = None,
        *,
        component_type: OtelComponentTypeValues | None = None,
        signal: Literal["traces", "metrics", "logs"] = "traces",
        meter_provider: MeterProvider | None = None,
    ):
        """Resolve the configuration and open the gRPC channel.

        The parameters are documented on the class.
        """
        super().__init__()
        self._result = result
        self._stub = stub
        self._endpoint = endpoint or environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, "http://localhost:4317")

        parsed_url = urlparse(self._endpoint)

        if parsed_url.scheme == "https":
            insecure = False
        insecure_exporter = environ.get(OTEL_EXPORTER_OTLP_INSECURE)
        if insecure is None:
            if insecure_exporter is not None:
                insecure = insecure_exporter.lower() == "true"
            else:
                insecure = parsed_url.scheme == "http"

        if parsed_url.netloc:
            self._endpoint = parsed_url.netloc
            if parsed_url.path and parsed_url.path.strip("/"):
                logger.warning(
                    "Endpoint path '%s' will be ignored. gRPC exporter uses '%s' without path. "
                    "If you intended to use HTTP, import from opentelemetry.exporter.otlp.proto.http instead.",
                    parsed_url.path,
                    self._endpoint,
                )

        self._insecure = insecure
        self._credentials = credentials
        self._headers = headers or environ.get(OTEL_EXPORTER_OTLP_HEADERS)
        if isinstance(self._headers, str):
            temp_headers = parse_env_headers(self._headers, liberal=True)
            self._headers = tuple(temp_headers.items())
        elif isinstance(self._headers, dict):
            self._headers = tuple(self._headers.items())
        if self._headers is None:
            self._headers = tuple()

        if channel_options:
            # merge the default channel options with the one passed as parameter
            overridden_options = {opt_name for (opt_name, _) in channel_options}
            default_options = tuple(
                (opt_name, opt_value)
                for opt_name, opt_value in _OTLP_GRPC_CHANNEL_OPTIONS
                if opt_name not in overridden_options
            )
            self._channel_options = default_options + channel_options
        else:
            self._channel_options = tuple(_OTLP_GRPC_CHANNEL_OPTIONS)

        self._timeout = timeout or _timeout_from_env(OTEL_EXPORTER_OTLP_TIMEOUT, default=10)
        self._collector_kwargs = None

        self._compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_COMPRESSION) if compression is None else compression
        ) or Compression.NoCompression

        self._retryable_error_codes = retryable_error_codes or os.environ.get(
            _OTEL_PYTHON_EXPORTER_OTLP_GRPC_RETRYABLE_ERROR_CODES
        )
        if isinstance(self._retryable_error_codes, str):
            self._retryable_error_codes = frozenset(
                StatusCode[code.strip().upper()] for code in self._retryable_error_codes.split(",") if code.strip()
            )
        elif self._retryable_error_codes is not None:
            self._retryable_error_codes = frozenset(self._retryable_error_codes)
        else:
            self._retryable_error_codes = _RETRYABLE_ERROR_CODES

        self._channel = None
        self._client = None

        self._shutdown_in_progress = threading.Event()
        self._shutdown = False

        if not self._insecure:
            self._credentials = _get_credentials(
                self._credentials,
                _OTEL_PYTHON_EXPORTER_OTLP_GRPC_CREDENTIAL_PROVIDER,
                OTEL_EXPORTER_OTLP_CERTIFICATE,
                OTEL_EXPORTER_OTLP_CLIENT_KEY,
                OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
            )

        self._component_type = component_type
        self._signal: Literal["traces", "metrics", "logs"] = signal
        self._metrics = create_exporter_metrics(
            self._component_type,
            signal,
            self._endpoint,
            meter_provider,
            os.environ.get(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED, "").strip().lower() == "true",
        )

        self._initialize_channel_and_stub()

    def _initialize_channel_and_stub(self):
        """
        Create a new gRPC channel and stub.

        This method is used during initialization and by the reconnection
        mechanism to reinitialize the channel on transient errors.
        """
        if self._insecure:
            self._channel = insecure_channel(
                self._endpoint,
                compression=self._compression,
                options=self._channel_options,
            )
        else:
            assert self._credentials is not None
            self._channel = secure_channel(
                self._endpoint,
                self._credentials,
                compression=self._compression,
                options=self._channel_options,
            )
        self._client = self._stub(self._channel)  # type: ignore [reportCallIssue]

    @abstractmethod
    def _translate_data(
        self,
        data: SDKDataT,
    ) -> ExportServiceRequestT:
        """Encode a batch of SDK data as the protobuf request for one signal.

        Implemented by each signal's exporter, because the encoder differs per
        signal. It is called once per export attempt, so a retry re-encodes
        the same batch.

        Args:
            data: Batch handed to the exporter by the SDK.

        Returns:
            The export service request to send over the gRPC channel.
        """

    @abstractmethod
    def _count_data(
        self,
        data: SDKDataT,
    ) -> int:
        """Count the individual items in a batch of SDK data.

        The count is recorded on the exporter's own self-observability
        metrics, and it is not the number of gRPC calls.

        Args:
            data: Batch handed to the exporter by the SDK.

        Returns:
            Number of spans, log records or metric data points in the batch.
        """

    def _export(
        self,
        data: SDKDataT,
    ) -> ExportResultT:
        """Send one batch over the gRPC channel, retrying transient failures.

        Up to six attempts are made within the configured timeout. The backoff
        doubles after each attempt and is jittered by up to 20 percent either
        way, unless the receiver sent a ``RetryInfo`` trailer, whose delay is
        used instead. An ``UNAVAILABLE`` failure on the first attempt also
        closes and recreates the channel, and an ``UNAVAILABLE`` failure on
        any later attempt does not. Retrying stops early when the next backoff
        would pass the deadline, when the status code is not in the retryable
        set, or when shutdown starts during a backoff.

        Args:
            data: Batch handed to the exporter by the SDK.

        Returns:
            The ``SUCCESS`` member of the signal's export result enumeration
            when the receiver accepted the batch, and the ``FAILURE`` member
            otherwise. Exporting after shutdown logs a warning and returns
            ``FAILURE`` without contacting the receiver.
        """
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring batch")
            return self._result.FAILURE  # type: ignore [reportReturnType]

        with self._metrics.export_operation(self._count_data(data)) as result:
            # FIXME remove this check if the export type for traces
            # gets updated to a class that represents the proto
            # TracesData and use the code below instead.
            deadline_sec = time() + self._timeout
            for retry_num in range(_MAX_RETRYS):
                try:
                    if self._client is None:
                        return self._result.FAILURE
                    self._client.Export(
                        request=self._translate_data(data),
                        metadata=self._headers,
                        timeout=deadline_sec - time(),
                    )
                    return self._result.SUCCESS  # type: ignore [reportReturnType]
                except RpcError as error:
                    retry_info_bin = dict(error.trailing_metadata()).get(  # type: ignore [reportAttributeAccessIssue]
                        "google.rpc.retryinfo-bin"  # type: ignore [reportArgumentType]
                    )
                    # multiplying by a random number between .8 and 1.2 introduces a +/20% jitter to each backoff.
                    backoff_seconds = 2**retry_num * random.uniform(0.8, 1.2)
                    if retry_info_bin is not None:
                        retry_info = RetryInfo()
                        retry_info.ParseFromString(retry_info_bin)
                        backoff_seconds = retry_info.retry_delay.seconds + retry_info.retry_delay.nanos / 1.0e9

                    # For UNAVAILABLE errors, reinitialize the channel to force reconnection
                    if error.code() == StatusCode.UNAVAILABLE and retry_num == 0:  # type: ignore
                        logger.debug(
                            "Reinitializing gRPC channel for %s exporter due to UNAVAILABLE error",
                            self._exporting,
                        )
                        try:
                            if self._channel:
                                self._channel.close()
                        except Exception as e:
                            logger.debug(
                                "Error closing channel for %s exporter to %s: %s",
                                self._exporting,
                                self._endpoint,
                                str(e),
                            )
                        # Enable channel reconnection for subsequent calls
                        self._initialize_channel_and_stub()

                    if (
                        error.code() not in self._retryable_error_codes  # type: ignore [reportAttributeAccessIssue]
                        or retry_num + 1 == _MAX_RETRYS
                        or backoff_seconds > (deadline_sec - time())
                        or self._shutdown
                    ):
                        logger.error(
                            "Failed to export %s to %s, error code: %s, error details: %s",
                            self._exporting,
                            self._endpoint,
                            error.code(),  # type: ignore [reportAttributeAccessIssue]
                            error.details(),
                            exc_info=error.code() == StatusCode.UNKNOWN,  # type: ignore [reportAttributeAccessIssue]
                        )
                        result.error = error
                        result.error_attrs = {RPC_RESPONSE_STATUS_CODE: error.code().name}
                        return self._result.FAILURE  # type: ignore [reportReturnType]
                    logger.warning(
                        "Transient error %s encountered while exporting %s to %s, retrying in %.2fs. Error details: %s",
                        error.code(),  # type: ignore [reportAttributeAccessIssue]
                        self._exporting,
                        self._endpoint,
                        backoff_seconds,
                        error.details(),
                    )
                shutdown = self._shutdown_in_progress.wait(backoff_seconds)
                if shutdown:
                    logger.warning("Shutdown in progress, aborting retry.")
                    break
            # Not possible to reach here but the linter is complaining.
            return self._result.FAILURE  # type: ignore [reportReturnType]

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """
        Shut down the exporter.

        An export that is waiting between retries is released by the same
        event that marks the shutdown, and then gives up rather than making a
        further attempt. The gRPC channel is closed afterwards. A second call
        logs a warning and does nothing.

        Args:
            timeout_millis: Timeout in milliseconds for shutting down the exporter.
                It is accepted for interface compatibility and is not used:
                closing a gRPC channel does not block.
            kwargs: Accepted and ignored, so that signal-specific subclasses
                can pass their own keyword arguments through.
        """
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_in_progress.set()
        if self._channel:
            self._channel.close()

    @property
    @abstractmethod
    def _exporting(self) -> str:
        """
        Returns a string that describes the overall exporter, to be used in
        warning messages.

        Returns:
            The plural signal name, for example ``traces``, as it appears in
            the retry and failure log messages of ``_export``.
        """

    def _set_meter_provider(self, meter_provider: MeterProvider) -> None:
        """Rebuild the exporter's own self-observability metrics against another meter provider.

        Call this when the meter provider to record those metrics with was not
        known at the time the exporter was constructed. The instruments
        created earlier are discarded, and new ones are created from
        ``meter_provider`` only when
        :envvar:`OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED` is set to ``true``.
        When it is not, no instrument is created, ``meter_provider`` is never
        asked for a meter, and the call leaves the exporter recording
        nothing.

        Args:
            meter_provider: Meter provider to record the exporter's own
                metrics with.
        """
        self._metrics = create_exporter_metrics(
            self._component_type,
            self._signal,
            self._endpoint,
            meter_provider,
            os.environ.get(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED, "").strip().lower() == "true",
        )
