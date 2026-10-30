# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OTLP Span Exporter"""

import logging
from collections.abc import Iterable, Sequence
from collections.abc import Sequence as TypingSequence
from os import environ

from grpc import ChannelCredentials, Compression, StatusCode
from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.proto.grpc import _timeout_from_env
from opentelemetry.exporter.otlp.proto.grpc.exporter import (  # noqa: F401
    OTLPExporterMixin,
    _get_credentials,
    environ_to_compression,
    get_resource_data,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    InstrumentationScope,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (  # noqa: F401
    ResourceSpans,
    ScopeSpans,
    Status,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (  # noqa: F401
    Span as CollectorSpan,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_GRPC_TRACES_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_INSECURE,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
)
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)

logger = logging.getLogger(__name__)


# pylint: disable=no-member
class OTLPSpanExporter(
    SpanExporter,
    OTLPExporterMixin[
        Sequence[ReadableSpan],
        ExportTraceServiceRequest,
        SpanExportResult,
        TraceServiceStub,
    ],
):
    # pylint: disable=unsubscriptable-object
    """OTLP span exporter

    Sends finished spans to an OTLP receiver over gRPC. The ``endpoint``,
    ``insecure``, ``credentials``, ``headers``, ``timeout`` and ``compression``
    arguments, when left as ``None``, are read from the traces-specific
    environment variable first and from the generic OTLP variable second, so a
    deployment can configure traces apart from the other signals. The
    remaining arguments have no traces-specific variable, and each entry below
    says what it does read.

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint. Falls back to
            :envvar:`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, then to
            :envvar:`OTEL_EXPORTER_OTLP_ENDPOINT`, then to
            ``http://localhost:4317``.
        insecure: Connection type. ``True`` sends plain HTTP/2 with no TLS.
            ``None`` means the value is taken from
            :envvar:`OTEL_EXPORTER_OTLP_TRACES_INSECURE`, then from
            :envvar:`OTEL_EXPORTER_OTLP_INSECURE`, and finally from the scheme
            of the endpoint. An ``https`` scheme forces ``False`` whatever the
            argument and the two variables say, and an endpoint written
            without a scheme matches neither ``http`` nor ``https``, so it
            too resolves to ``False`` and opens a TLS channel.
        credentials: Credentials object for server authentication. ``None``
            means they are resolved from the environment. The traces-specific
            sources are consulted when
            :envvar:`OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE` is set and neither
            the ``insecure`` argument nor
            :envvar:`OTEL_EXPORTER_OTLP_TRACES_INSECURE` says the connection
            is insecure: the entry point named by
            ``OTEL_PYTHON_EXPORTER_OTLP_GRPC_TRACES_CREDENTIAL_PROVIDER`` takes
            precedence, and the traces-specific certificate, client key and
            client certificate files are read when that variable is unset. The
            generic sources are consulted when nothing has been resolved yet
            and the connection ends up secure:
            ``OTEL_PYTHON_EXPORTER_OTLP_GRPC_CREDENTIAL_PROVIDER``, then
            :envvar:`OTEL_EXPORTER_OTLP_CERTIFICATE` with its own companions,
            then the root certificates gRPC finds for itself. An ``http``
            endpoint and :envvar:`OTEL_EXPORTER_OTLP_INSECURE` do not stop the
            traces-specific variables from being read and their files from
            being opened, because the first condition tests only the argument
            and the traces-specific insecure variable, and the credentials
            built that way are then never used. An ``https`` endpoint combined
            with an insecure setting makes a TLS connection that skips the
            traces-specific variables and uses the generic ones.
        headers: Headers to send when exporting, as a mapping, as a sequence
            of pairs, or as the comma-separated string form used by
            :envvar:`OTEL_EXPORTER_OTLP_TRACES_HEADERS`. ``None`` means that
            variable is read, then :envvar:`OTEL_EXPORTER_OTLP_HEADERS`.
        timeout: Backend request timeout in seconds, covering the whole export
            including retries. ``None`` means the value is taken from
            :envvar:`OTEL_EXPORTER_OTLP_TRACES_TIMEOUT`, then from
            :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT`, defaulting to 10 seconds. A
            ``0`` in the argument or in
            :envvar:`OTEL_EXPORTER_OTLP_TRACES_TIMEOUT` is treated the same
            way as ``None`` and the next source is used, while a ``0`` in
            :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT` is kept and makes every
            export fail on its first attempt.
        compression: gRPC compression method to use. ``None`` means the value
            is taken from :envvar:`OTEL_EXPORTER_OTLP_TRACES_COMPRESSION`,
            then from :envvar:`OTEL_EXPORTER_OTLP_COMPRESSION`, and no
            compression is used when neither is set. Only one of the two is
            ever read: a value of ``gzip`` in
            :envvar:`OTEL_EXPORTER_OTLP_TRACES_COMPRESSION` settles the choice
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
            applies to all three signals and has no traces-specific form, and
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
        """Resolve the traces-specific configuration and open the gRPC channel.

        The parameters are documented on the class.
        """
        insecure_spans = environ.get(OTEL_EXPORTER_OTLP_TRACES_INSECURE)
        if insecure is None and insecure_spans is not None:
            insecure = insecure_spans.lower() == "true"

        if not insecure and environ.get(OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE) is not None:
            credentials = _get_credentials(
                credentials,
                _OTEL_PYTHON_EXPORTER_OTLP_GRPC_TRACES_CREDENTIAL_PROVIDER,
                OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
                OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
                OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
            )

        environ_timeout = _timeout_from_env(OTEL_EXPORTER_OTLP_TRACES_TIMEOUT)

        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_TRACES_COMPRESSION) if compression is None else compression
        )

        OTLPExporterMixin.__init__(
            self,
            stub=TraceServiceStub,
            result=SpanExportResult,
            endpoint=endpoint or environ.get(OTEL_EXPORTER_OTLP_TRACES_ENDPOINT),
            insecure=insecure,
            credentials=credentials,
            headers=headers or environ.get(OTEL_EXPORTER_OTLP_TRACES_HEADERS),
            timeout=timeout or environ_timeout,
            compression=compression,
            channel_options=channel_options,
            retryable_error_codes=retryable_error_codes,
            component_type=OtelComponentTypeValues.OTLP_GRPC_SPAN_EXPORTER,
            signal="traces",
            meter_provider=meter_provider,
        )

    def _translate_data(self, data: Sequence[ReadableSpan]) -> ExportTraceServiceRequest:
        """Encode finished spans as an OTLP trace export request.

        Args:
            data: Finished spans to encode.

        Returns:
            The export request, with the spans grouped by resource and then by
            instrumentation scope.
        """
        return encode_spans(data)

    def _count_data(self, data: Sequence[ReadableSpan]):
        """Count the spans in a batch, for the exporter's own metrics.

        Args:
            data: Finished spans about to be exported.

        Returns:
            The number of spans in the batch.
        """
        return len(data)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Send a batch of finished spans to the receiver.

        Called by the span processor the exporter is installed in. Transient
        failures are retried inside the configured timeout.

        Args:
            spans: Finished spans to export.

        Returns:
            ``SpanExportResult.SUCCESS`` when the receiver accepted the batch,
            and ``SpanExportResult.FAILURE`` otherwise, which includes the
            case where the exporter has already been shut down.
        """
        return self._export(spans)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Shut down the exporter and close its gRPC channel.

        Args:
            timeout_millis: Timeout in milliseconds, accepted for interface
                compatibility and not used.
            kwargs: Accepted and ignored.
        """
        OTLPExporterMixin.shutdown(self, timeout_millis=timeout_millis)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing.

        Args:
            timeout_millis: Timeout in milliseconds, accepted for interface
                compatibility and not used.

        Returns:
            ``True``, always, since there is never anything left to flush.
        """
        return True

    @property
    def _exporting(self):
        """Name of the signal, used in the retry and failure log messages.

        Returns:
            The string ``traces``.
        """
        return "traces"
