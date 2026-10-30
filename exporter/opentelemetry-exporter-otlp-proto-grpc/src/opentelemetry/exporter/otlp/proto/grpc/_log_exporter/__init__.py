# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OTLP Log Record Exporter

This module holds the log record exporter that sends log records to an
OTLP-compatible receiver over gRPC. The module name starts with an underscore
because the logs signal of this package is still unstable, so the import path
can change without a major version bump.
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

    Sends log records to an OTLP receiver over gRPC. Each argument that is
    left as ``None`` is read from the logs-specific environment variable first
    and from the generic OTLP variable second, so a deployment can configure
    logs apart from the other signals.

    Args:
        endpoint: OTLP-compatible receiver endpoint. Falls back to
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_ENDPOINT`, then to
            :envvar:`OTEL_EXPORTER_OTLP_ENDPOINT`, then to
            ``http://localhost:4317``.
        insecure: Connection type. ``True`` sends plain HTTP/2 with no TLS.
            ``None`` means the value is taken from
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_INSECURE`, then from
            :envvar:`OTEL_EXPORTER_OTLP_INSECURE`, and finally from the scheme
            of the endpoint.
        credentials: Credentials object for server authentication. ``None``
            means credentials are built from
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE` and its client key
            and client certificate companions when that variable is set, and
            resolved from the generic OTLP variables otherwise.
        headers: Headers to send when exporting, as a mapping, as a sequence
            of pairs, or as the comma-separated string form used by
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_HEADERS`. ``None`` means that
            variable is read, then :envvar:`OTEL_EXPORTER_OTLP_HEADERS`.
        timeout: Backend request timeout in seconds, covering the whole export
            including retries. ``None`` means the value is taken from
            :envvar:`OTEL_EXPORTER_OTLP_LOGS_TIMEOUT`, then from
            :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT`, defaulting to 10 seconds.
        compression: gRPC compression method to use. ``None`` means the value
            is taken from :envvar:`OTEL_EXPORTER_OTLP_LOGS_COMPRESSION`, then
            from :envvar:`OTEL_EXPORTER_OTLP_COMPRESSION`, and no compression
            is used when neither is set.
        channel_options: gRPC channel options, as a sequence of name and value
            pairs, merged over this package's own options.
        retryable_error_codes: gRPC status codes that cause an export to be
            retried, overriding the default set.
        meter_provider: Meter provider used to record the exporter's own
            self-observability metrics. ``None`` means the globally configured
            meter provider is used.
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
