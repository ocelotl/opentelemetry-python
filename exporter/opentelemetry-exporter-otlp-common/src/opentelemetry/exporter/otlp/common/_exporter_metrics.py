# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Self-observability instruments for the OTLP exporters.

An OTLP exporter wraps each export operation in the context manager returned
by ``ExporterMetricsT.export_operation`` and records three instruments defined
by the semantic conventions: an up-down counter of the telemetry handed to the
exporter but not yet exported, a counter of the telemetry whose export has
finished whether it succeeded or failed, and a histogram of how long the
operation took in seconds. An export operation is the delivery of one payload
to the server, from the moment the exporter starts that delivery to the moment
it succeeds or gives up, so an exporter that retries holds the ``with`` body
open across every retry and every backoff wait between them, and each
instrument is recorded once for the payload rather than once per request. What
else falls inside the ``with`` body is up to the exporter: the span and log
exporters serialize inside it, while ``OTLPMetricExporter`` of
``opentelemetry-exporter-otlp-proto-http`` encodes and splits first and then
opens one export operation per sub-batch. The instrument names depend on the
signal, so a span exporter records ``otel.sdk.exporter.span.inflight`` and
``otel.sdk.exporter.span.exported`` while a metric exporter records
``otel.sdk.exporter.metric_data_point.inflight`` and
``otel.sdk.exporter.metric_data_point.exported``. The duration histogram is
``otel.sdk.exporter.operation.duration`` for every signal.

The instruments stay off unless the exporter asks for them, which it does by
passing ``enabled=True`` to ``create_exporter_metrics``. When they are off the
exporter gets ``NoOpExporterMetrics``, whose context manager records nothing,
so the call sites in the exporters are written once and need no condition
around them.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlparse

from opentelemetry.metrics import MeterProvider, get_meter_provider
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OTEL_COMPONENT_NAME,
    OTEL_COMPONENT_TYPE,
    OtelComponentTypeValues,
)
from opentelemetry.semconv._incubating.metrics.otel_metrics import (
    create_otel_sdk_exporter_log_exported,
    create_otel_sdk_exporter_log_inflight,
    create_otel_sdk_exporter_metric_data_point_exported,
    create_otel_sdk_exporter_metric_data_point_inflight,
    create_otel_sdk_exporter_operation_duration,
    create_otel_sdk_exporter_span_exported,
    create_otel_sdk_exporter_span_inflight,
)
from opentelemetry.semconv.attributes.error_attributes import ERROR_TYPE
from opentelemetry.semconv.attributes.server_attributes import (
    SERVER_ADDRESS,
    SERVER_PORT,
)

if TYPE_CHECKING:
    from typing import Literal

    from opentelemetry.util.types import AnyValue, Attributes

_component_counter = Counter()

_GRPC_COMPONENT_TYPES = frozenset(
    {
        OtelComponentTypeValues.OTLP_GRPC_SPAN_EXPORTER,
        OtelComponentTypeValues.OTLP_GRPC_LOG_EXPORTER,
        OtelComponentTypeValues.OTLP_GRPC_METRIC_EXPORTER,
    }
)


@dataclass
class ExportResult:
    """How an export operation ended, as reported back by the exporter.

    ``export_operation`` yields a fresh instance with both fields left at their
    defaults, which means the export operation succeeded. An exporter that
    fails sets one or both fields before the ``with`` block ends, and the
    values are read once the block exits.

    Attributes:
        error: The exception that ended the export operation, or ``None`` when
            it succeeded. When it is set, the qualified name of its type is
            recorded as the ``error.type`` attribute on the exported counter
            and on the duration histogram.
        error_attrs: Extra attributes recorded on the duration histogram only,
            or ``None`` to add none. They are recorded whether or not ``error``
            is set: an HTTP exporter uses this field to report
            ``http.response.status_code``, and a response carrying a failing
            status code but no exception leaves ``error`` at ``None`` while
            this field is populated.
    """

    error: Exception | None = None
    error_attrs: Attributes = None


class ExporterMetricsT(Protocol):
    """What an OTLP exporter needs from its self-observability instruments.

    ``ExporterMetrics`` and ``NoOpExporterMetrics`` both satisfy this protocol,
    so an exporter holds one of the two behind this type and never asks which
    one it got.
    """

    def export_operation(self, num_items: int) -> AbstractContextManager[ExportResult]:
        """Return a context manager that covers one export operation.

        The exporter runs the whole export operation inside the ``with`` body,
        every retry and every backoff wait included, and reports the outcome by
        assigning to the fields of the ``ExportResult`` the context manager
        yields. The implementation reads those fields once the body has ended.

        Args:
            num_items: How many spans, log records or metric data points the
                export operation covers.

        Returns:
            A context manager yielding the ``ExportResult`` the exporter fills
            in.
        """
        ...  # pylint: disable=unnecessary-ellipsis


class NoOpExporterMetrics:
    """An ``ExporterMetricsT`` that records nothing.

    ``create_exporter_metrics`` returns this when self-observability is
    disabled. It creates no instruments and reaches no meter provider, so an
    exporter that is not being observed pays only the cost of entering and
    leaving a context manager.
    """

    @contextmanager
    # pylint: disable-next=no-self-use
    def export_operation(self, num_items: int) -> Iterator[ExportResult]:
        """Yield a discarded ``ExportResult`` around an export operation.

        Args:
            num_items: How many spans, log records or metric data points the
                export operation covers. It is accepted so that the signature
                matches ``ExporterMetricsT.export_operation`` and is otherwise
                unused.

        Yields:
            A fresh ``ExportResult``. Whatever the caller assigns to its fields
            is never read.
        """
        yield ExportResult()


class ExporterMetrics:
    """Records the self-observability instruments of one OTLP exporter.

    The instruments are created once, when the instance is, and every export
    operation reuses them. Each recording carries ``otel.component.type`` and
    ``otel.component.name``, plus ``server.address`` and ``server.port`` when
    the endpoint supplied enough information to determine them.

    ``otel.component.name`` has to be unique among the exporters of a process,
    so instances of this class share a module-level counter per component type
    and the name is the component type followed by ``/`` and the number of
    instances with that same component type created before this one. The
    counter is never reset, so an exporter created after another one is shut
    down still gets a name of its own.

    Args:
        component_type: The kind of exporter being observed, recorded as the
            ``otel.component.type`` attribute. ``None`` records the literal
            ``unknown_otlp_exporter`` instead, and the component name counter
            treats it as one more component type.
        signal: Which telemetry the exporter sends. ``"traces"`` and
            ``"logs"`` select the span and log record instruments, and any
            other value selects the metric data point instruments.
        endpoint: Where the exporter sends telemetry, parsed for the host and
            the port recorded as ``server.address`` and ``server.port``. A
            value that neither starts with ``//`` nor contains ``://`` is
            prefixed with ``//`` first so that ``urlparse`` reads its leading
            component as the host rather than as a scheme. A host with no port
            gets 443 when ``component_type`` is one of the gRPC exporters or
            the scheme is ``https``, and 80 when the scheme is ``http`` and
            ``component_type`` is not one of the gRPC exporters.
            ``server.port`` is left unrecorded in every other case, and
            ``server.address`` is left unrecorded when no host could be parsed.
            ``urlparse`` itself accepts a port that is not an integer in range,
            and reading the parsed port then raises ``ValueError`` out of the
            constructor, so enabling self-observability turns a malformed
            endpoint into an exception the exporter does not otherwise raise.
        meter_provider: Where to get the meter that creates the instruments,
            or ``None`` to use the global meter provider at the moment this
            instance is created. The meter is named ``opentelemetry-sdk``.
    """

    def __init__(
        self,
        component_type: OtelComponentTypeValues | None,
        signal: Literal["traces", "metrics", "logs"],
        endpoint: str,
        meter_provider: MeterProvider | None,
    ) -> None:
        """Create the instruments and the attributes every recording carries.

        The parameters are documented on the class.
        """
        if signal == "traces":
            create_exported = create_otel_sdk_exporter_span_exported
            create_inflight = create_otel_sdk_exporter_span_inflight
        elif signal == "logs":
            create_exported = create_otel_sdk_exporter_log_exported
            create_inflight = create_otel_sdk_exporter_log_inflight
        else:
            create_exported = create_otel_sdk_exporter_metric_data_point_exported
            create_inflight = create_otel_sdk_exporter_metric_data_point_inflight

        if not endpoint.startswith("//") and "://" not in endpoint:
            endpoint = f"//{endpoint}"
        parsed_endpoint = urlparse(endpoint)

        port = parsed_endpoint.port
        if port is None:
            if component_type in _GRPC_COMPONENT_TYPES or parsed_endpoint.scheme == "https":
                port = 443
            elif parsed_endpoint.scheme == "http":
                port = 80

        component_type_value = component_type.value if component_type else "unknown_otlp_exporter"
        count = _component_counter[component_type_value]
        _component_counter[component_type_value] = count + 1
        self._standard_attrs: dict[str, AnyValue] = {
            OTEL_COMPONENT_TYPE: component_type_value,
            OTEL_COMPONENT_NAME: f"{component_type_value}/{count}",
        }
        if parsed_endpoint.hostname:
            self._standard_attrs[SERVER_ADDRESS] = parsed_endpoint.hostname
        if port is not None:
            self._standard_attrs[SERVER_PORT] = port

        meter_provider = meter_provider or get_meter_provider()
        meter = meter_provider.get_meter("opentelemetry-sdk")
        self._inflight = create_inflight(meter)
        self._exported = create_exported(meter)
        self._duration = create_otel_sdk_exporter_operation_duration(meter)

    @contextmanager
    def export_operation(self, num_items: int) -> Iterator[ExportResult]:
        """Record one export operation across the three instruments.

        Entering the context manager adds ``num_items`` to the inflight
        up-down counter. Leaving it subtracts the same amount, adds
        ``num_items`` to the exported counter and records the elapsed
        ``time.perf_counter`` interval on the duration histogram. The recording
        happens in a ``finally`` block, so an exception that propagates out of
        the ``with`` body still leaves the inflight counter balanced.

        The exporter holds the ``with`` body open for the whole export
        operation, so a retried export stays in the inflight counter across
        every retry and every backoff wait, and reaches the exported counter
        only after the last retry has ended.

        An exception that propagates out of the ``with`` body is not inspected.
        The export operation counts as a failure only when the caller assigns
        to the ``error`` field of the yielded ``ExportResult``, so an exporter
        that lets an exception escape without assigning to that field records
        the export operation as a success.

        Args:
            num_items: How many spans, log records or metric data points the
                export operation covers. It is added to the inflight counter on
                entry, subtracted on exit and added to the exported counter, so
                the same number is counted as exported whether the export
                operation succeeded or failed.

        Yields:
            An ``ExportResult`` whose fields the caller sets to report a
            failure. The fields are read once the ``with`` body has ended, so
            assigning to them after that has no effect.
        """
        start_time = perf_counter()
        self._inflight.add(num_items, self._standard_attrs)

        result = ExportResult()
        try:
            yield result
        finally:
            error = result.error
            error_attrs = result.error_attrs

            end_time = perf_counter()
            self._inflight.add(-num_items, self._standard_attrs)
            exported_attrs = (
                {**self._standard_attrs, ERROR_TYPE: type(error).__qualname__} if error else self._standard_attrs
            )
            self._exported.add(num_items, exported_attrs)
            duration_attrs = {**exported_attrs, **error_attrs} if error_attrs else exported_attrs
            self._duration.record(end_time - start_time, duration_attrs)


def create_exporter_metrics(
    component_type: OtelComponentTypeValues | None,
    signal: Literal["traces", "metrics", "logs"],
    endpoint: str,
    meter_provider: MeterProvider | None,
    enabled: bool,
) -> ExporterMetricsT:
    """Build the self-observability instruments an OTLP exporter records.

    An exporter calls this from its constructor, and again whenever its meter
    provider is replaced, so that the instruments come from the new provider.
    The call creates no instruments and touches no meter provider while
    ``enabled`` is false.

    Every call with ``enabled`` true builds a new ``ExporterMetrics`` and so
    takes the next ``otel.component.name`` for its component type. One exporter
    that replaces its meter provider therefore reports one name before the
    replacement and the next name after it, and a backend grouping the
    ``otel.sdk.exporter.*`` series by that attribute sees two series rather
    than one.

    Args:
        component_type: The kind of exporter being observed. See
            ``ExporterMetrics``.
        signal: Which telemetry the exporter sends. See ``ExporterMetrics``.
        endpoint: Where the exporter sends telemetry. See ``ExporterMetrics``.
        meter_provider: Where to get the meter, or ``None`` for the global
            meter provider. See ``ExporterMetrics``.
        enabled: Whether to record anything. An OTLP exporter sets it from
            ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED``.

    Returns:
        An ``ExporterMetrics`` when ``enabled`` is true, and a
        ``NoOpExporterMetrics`` otherwise. The other four arguments are
        ignored in the second case.
    """
    if not enabled:
        return NoOpExporterMetrics()

    return ExporterMetrics(
        component_type,
        signal,
        endpoint,
        meter_provider,
    )
