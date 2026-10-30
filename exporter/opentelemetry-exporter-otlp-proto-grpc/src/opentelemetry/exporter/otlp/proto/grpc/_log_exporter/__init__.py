# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OTLP Log Record Exporter

This module holds the log record exporter that sends log records to an
OTLP-compatible receiver over gRPC. It reads the records that
``opentelemetry.sdk._logs`` produces, and it carries the same leading
underscore that module does.
"""

from collections.abc import Iterable, Sequence
from collections.abc import Sequence as TypingSequence
from os import environ
from typing import Literal

from grpc import ChannelCredentials, Compression, StatusCode
from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.proto.grpc import _timeout_from_env
from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    OTLPExporterMixin,
    _get_credentials,
    environ_to_compression,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2_grpc import (
    LogsServiceStub,
)
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_GRPC_LOGS_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_INSECURE,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
)
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)


class OTLPLogExporter(
    LogRecordExporter,
    OTLPExporterMixin[
        Sequence[ReadableLogRecord],
        ExportLogsServiceRequest,
        LogRecordExportResult,
        LogsServiceStub,
    ],
):
    """OTLP log record exporter

    Sends log records to an OTLP receiver over gRPC. The ``endpoint``,
    ``insecure``, ``credentials``, ``headers``, ``timeout`` and ``compression``
    arguments, when left as ``None``, are read from the logs-specific
    environment variable first and from the generic OTLP variable second, so a
    deployment can configure logs apart from the other signals. The remaining
    arguments have no logs-specific variable, and each entry below says what it
    does read.

    Args:
        endpoint: OTLP-compatible receiver endpoint. Falls back to
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_ENDPOINT`, then to
            :envvar:`OTEL_EXPORTER_OTLP_ENDPOINT`, then to
            ``http://localhost:4317``.
        insecure: Connection type. ``True`` sends plain HTTP/2 with no TLS.
            ``None`` means the value is taken from
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_INSECURE`, then from
            :envvar:`OTEL_EXPORTER_OTLP_INSECURE`, and finally from the scheme
            of the endpoint. An ``https`` scheme forces ``False`` whatever the
            argument and the two variables say, and an endpoint written
            without a scheme matches neither ``http`` nor ``https``, so it
            too resolves to ``False`` and opens a TLS channel.
        credentials: Credentials object for server authentication. ``None``
            means they are resolved from the environment. The logs-specific
            sources are consulted when
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE` is set and neither
            the ``insecure`` argument nor
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_INSECURE` says the connection is
            insecure: the entry point named by
            ``OTEL_PYTHON_EXPORTER_OTLP_GRPC_LOGS_CREDENTIAL_PROVIDER`` takes
            precedence, and the logs-specific certificate, client key and
            client certificate files are read when that variable is unset. The
            generic sources are consulted when nothing has been resolved yet
            and the connection ends up secure:
            ``OTEL_PYTHON_EXPORTER_OTLP_GRPC_CREDENTIAL_PROVIDER``, then
            :envvar:`OTEL_EXPORTER_OTLP_CERTIFICATE` with its own companions,
            then the root certificates gRPC finds for itself. An ``http``
            endpoint and :envvar:`OTEL_EXPORTER_OTLP_INSECURE` do not stop the
            logs-specific variables from being read and their files from being
            opened, because the first condition tests only the argument and
            the logs-specific insecure variable, and the credentials built
            that way are then never used. An ``https`` endpoint combined with
            an insecure setting makes a TLS connection that skips the
            logs-specific variables and uses the generic ones.
        headers: Headers to send when exporting, as a mapping, as a sequence
            of pairs, or as the comma-separated string form used by
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_HEADERS`. ``None`` means that
            variable is read, then :envvar:`OTEL_EXPORTER_OTLP_HEADERS`.
        timeout: Backend request timeout in seconds, covering the whole export
            including retries. ``None`` means the value is taken from
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_TIMEOUT`, then from
            :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT`, defaulting to 10 seconds. A
            ``0`` in the argument or in
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_TIMEOUT` is treated the same way
            as ``None`` and the next source is used, while a ``0`` in
            :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT` is kept and makes every
            export fail on its first attempt.
        compression: gRPC compression method to use. ``None`` means the value
            is taken from :envvar:`OTEL_EXPORTER_OTLP_LOGS_COMPRESSION`, then
            from :envvar:`OTEL_EXPORTER_OTLP_COMPRESSION`, and no compression
            is used when neither is set. Only one of the two is ever read: a
            value of ``gzip`` in
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_COMPRESSION` settles the choice
            and :envvar:`OTEL_EXPORTER_OTLP_COMPRESSION` is then left unread,
            whatever it holds. A value other than ``gzip`` in whichever
            variable is read makes the constructor raise
            ``InvalidCompressionValueException``.
        channel_options: gRPC channel options, as a sequence of name and value
            pairs, merged over this package's own options. No environment
            variable is read for this.
        retryable_error_codes: gRPC status codes that cause an export to be
            retried. ``None`` means the set is read from
            ``OTEL_PYTHON_EXPORTER_OTLP_GRPC_RETRYABLE_ERROR_CODES``, which
            applies to all three signals and has no logs-specific form, and
            otherwise falls back to the default set.
        meter_provider: Meter provider used to record the exporter's own
            self-observability metrics. ``None`` means the globally configured
            meter provider is used. Those metrics are recorded at all only
            when :envvar:`OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED` is set to
            ``true``.

    Raises:
        RuntimeError: When either credential provider environment variable
            names an entry point that is not installed, or one whose return
            value is not a ``grpc.ChannelCredentials``. The constructor is
            where this surfaces.
        InvalidCompressionValueException: When ``compression`` is ``None`` and
            the compression variable that is read holds anything other than
            ``gzip``.
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
        endpoint: str | None = None,
        insecure: bool | None = None,
        credentials: ChannelCredentials | None = None,
        headers: TypingSequence[tuple[str, str]] | dict[str, str] | str | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        channel_options: tuple[tuple[str, str]] | None = None,
        retryable_error_codes: Iterable[StatusCode] | None = None,
        *,
        meter_provider: MeterProvider | None = None,
    ):
        """Resolve the logs-specific configuration and open the gRPC channel.

        The parameters are documented on the class.
        """
        insecure_logs = environ.get(OTEL_EXPORTER_OTLP_LOGS_INSECURE)
        if insecure is None and insecure_logs is not None:
            insecure = insecure_logs.lower() == "true"

        if not insecure and environ.get(OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE) is not None:
            credentials = _get_credentials(
                credentials,
                _OTEL_PYTHON_EXPORTER_OTLP_GRPC_LOGS_CREDENTIAL_PROVIDER,
                OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
                OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
                OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
            )

        environ_timeout = _timeout_from_env(OTEL_EXPORTER_OTLP_LOGS_TIMEOUT)

        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_LOGS_COMPRESSION) if compression is None else compression
        )

        OTLPExporterMixin.__init__(
            self,
            endpoint=endpoint or environ.get(OTEL_EXPORTER_OTLP_LOGS_ENDPOINT),
            insecure=insecure,
            credentials=credentials,
            headers=headers or environ.get(OTEL_EXPORTER_OTLP_LOGS_HEADERS),
            timeout=timeout or environ_timeout,
            compression=compression,
            stub=LogsServiceStub,
            result=LogRecordExportResult,
            channel_options=channel_options,
            retryable_error_codes=retryable_error_codes,
            component_type=OtelComponentTypeValues.OTLP_GRPC_LOG_EXPORTER,
            signal="logs",
            meter_provider=meter_provider,
        )

    def _translate_data(self, data: Sequence[ReadableLogRecord]) -> ExportLogsServiceRequest:
        """Encode log records as an OTLP logs export request.

        Args:
            data: Log records to encode.

        Returns:
            The export request, with the log records grouped by resource and
            then by instrumentation scope.
        """
        return encode_logs(data)

    def _count_data(self, data: Sequence[ReadableLogRecord]):
        """Count the log records in a batch, for the exporter's own metrics.

        Args:
            data: Log records about to be exported.

        Returns:
            The number of log records in the batch.
        """
        return len(data)

    def export(  # type: ignore [reportIncompatibleMethodOverride]
        self,
        batch: Sequence[ReadableLogRecord],
    ) -> Literal[LogRecordExportResult.SUCCESS, LogRecordExportResult.FAILURE]:
        """Send a batch of log records to the receiver.

        Called by the log record processor the exporter is installed in.
        Transient failures are retried inside the configured timeout.

        Args:
            batch: Log records to export.

        Returns:
            ``LogRecordExportResult.SUCCESS`` when the receiver accepted the
            batch, and ``LogRecordExportResult.FAILURE`` otherwise, which
            includes the case where the exporter has already been shut down.
        """
        return OTLPExporterMixin._export(self, batch)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Shut down the exporter and close its gRPC channel.

        Args:
            timeout_millis: Timeout in milliseconds, accepted for interface
                compatibility and not used.
            kwargs: Accepted and ignored.
        """
        OTLPExporterMixin.shutdown(self, timeout_millis=timeout_millis)

    def force_flush(self, timeout_millis: int = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing.

        Args:
            timeout_millis: Timeout in milliseconds, accepted for interface
                compatibility and not used.

        Returns:
            ``True``, always, since there is never anything left to flush.
        """
        return True

    @property
    def _exporting(self) -> str:
        """Name of the signal, used in the retry and failure log messages.

        Returns:
            The string ``logs``.
        """
        return "logs"
