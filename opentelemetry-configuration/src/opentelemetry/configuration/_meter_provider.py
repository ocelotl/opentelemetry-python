# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# pylint: disable=too-many-lines

"""MeterProvider construction from declarative configuration.

Only ``create_meter_provider`` and ``configure_meter_provider`` are
meant to be called from outside this module. The rest build one piece:
a metric reader, its exporter, a view, the exemplar filter, the
cardinality limits, or the experimental per-meter configurator.

No function here reads an environment variable. The temporality and
histogram aggregation preferences in particular are always passed to the
exporter as an explicit mapping, even when the configuration file
selects the default, so that
``OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE`` and
``OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION`` cannot
change what a configuration file asked for.

Metrics have two kinds of reader. A periodic reader owns a push
exporter and sends on a timer. A pull reader has no separate exporter
object: the thing the schema calls its exporter, Prometheus being the
only built-in one, is itself the reader, and constructing it starts an
HTTP listener.

Several fields the schema accepts are not supported by the Python SDK.
Five are ignored with a warning naming them: the excluded half of a
view's attribute keys, a pull reader's metric producers, the Prometheus
scope info and resource constant labels, and cardinality limits on a
plugin pull exporter. Three more of those are ignored with no warning at
all, so a configuration file that sets one looks as though it took
effect: ``periodic.producers``,
``periodic.max_export_batch_size/development`` and
``prometheus/development.translation_strategy``.

The ``tls`` block of the ``otlp_http`` and ``otlp_grpc`` exporters is a
separate case and is dropped just as quietly. The SDK exporters do
support TLS through their own parameters; this module simply never reads
the block, as the two exporter factories record.
"""

from __future__ import annotations

import logging

from opentelemetry import metrics
from opentelemetry.configuration._common import (
    _map_compression,
    _parse_headers,
    _parse_otlp_file_output_stream,
    _scope_name_matches_glob,
    load_entry_point,
)
from opentelemetry.configuration._exceptions import (
    ConfigurationError,
    MissingDependencyError,
)
from opentelemetry.configuration.models import (
    Aggregation as AggregationConfig,
)
from opentelemetry.configuration.models import (
    CardinalityLimits as CardinalityLimitsConfig,
)
from opentelemetry.configuration.models import (
    ConsoleMetricExporter as ConsoleMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    ExemplarFilter as ExemplarFilterConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalMeterConfig as MeterConfigConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalMeterConfigurator as MeterConfiguratorConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalOtlpFileMetricExporter as ExperimentalOtlpFileMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalPrometheusMetricExporter as PrometheusMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    ExporterDefaultHistogramAggregation,
    ExporterTemporalityPreference,
    InstrumentType,
    OtlpHttpEncoding,
)
from opentelemetry.configuration.models import (
    MeterProvider as MeterProviderConfig,
)
from opentelemetry.configuration.models import (
    MetricReader as MetricReaderConfig,
)
from opentelemetry.configuration.models import (
    OtlpGrpcMetricExporter as OtlpGrpcMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    OtlpHttpMetricExporter as OtlpHttpMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    PeriodicMetricReader as PeriodicMetricReaderConfig,
)
from opentelemetry.configuration.models import (
    PullMetricExporter as PullMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    PullMetricReader as PullMetricReaderConfig,
)
from opentelemetry.configuration.models import (
    PushMetricExporter as PushMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    View as ViewConfig,
)
from opentelemetry.sdk.metrics import (
    AlwaysOffExemplarFilter,
    AlwaysOnExemplarFilter,
    Counter,
    Histogram,
    MeterProvider,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    TraceBasedExemplarFilter,
    UpDownCounter,
    _Gauge,
)
from opentelemetry.sdk.metrics._internal import (
    _MeterConfig,
    _RuleBasedMeterConfigurator,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    CardinalityLimits,
    ConsoleMetricExporter,
    MetricExporter,
    MetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import (
    Aggregation,
    DefaultAggregation,
    DropAggregation,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
    LastValueAggregation,
    SumAggregation,
    View,
)
from opentelemetry.sdk.resources import Resource

_logger = logging.getLogger(__name__)


# Default interval/timeout per OTel spec (milliseconds).
_DEFAULT_EXPORT_INTERVAL_MILLIS = 60000
_DEFAULT_EXPORT_TIMEOUT_MILLIS = 30000

# Instrument type → SDK instrument class mapping (for View selectors).
_INSTRUMENT_TYPE_MAP: dict[InstrumentType, type] = {
    InstrumentType.counter: Counter,
    InstrumentType.up_down_counter: UpDownCounter,
    InstrumentType.histogram: Histogram,
    InstrumentType.gauge: _Gauge,
    InstrumentType.observable_counter: ObservableCounter,
    InstrumentType.observable_gauge: ObservableGauge,
    InstrumentType.observable_up_down_counter: ObservableUpDownCounter,
}


def _map_temporality(
    pref: ExporterTemporalityPreference | None,
) -> dict[type, AggregationTemporality]:
    """Map a temporality preference to an explicit preferred_temporality dict.

    Always returns an explicit dict to suppress OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE.
    Default (None or cumulative) → all instruments CUMULATIVE.

    Args:
        pref: The ``temporality_preference`` field of an exporter
            configuration block. ``None`` means the field was absent and is
            read as cumulative.

    Returns:
        Six entries, one per instrument class except the synchronous gauge,
        which is left out. Delta and low_memory differ only for the
        observable counter, which low_memory keeps cumulative; the
        observable gauge is pinned to cumulative in all three mappings.

    Raises:
        ConfigurationError: If ``pref`` is some other enum member.
    """
    if pref is None or pref == ExporterTemporalityPreference.cumulative:
        return {
            Counter: AggregationTemporality.CUMULATIVE,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.CUMULATIVE,
            ObservableCounter: AggregationTemporality.CUMULATIVE,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
    if pref == ExporterTemporalityPreference.delta:
        return {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.DELTA,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
    if pref == ExporterTemporalityPreference.low_memory:
        return {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.CUMULATIVE,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
    raise ConfigurationError(
        f"Unsupported temporality preference '{pref}'. Supported values: cumulative, delta, low_memory."
    )


def _map_histogram_aggregation(
    pref: ExporterDefaultHistogramAggregation | None,
) -> dict[type, Aggregation]:
    """Map a histogram aggregation preference to an explicit preferred_aggregation dict.

    Always returns an explicit dict to suppress
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION.
    Default (None or explicit_bucket_histogram) → ExplicitBucketHistogramAggregation.

    Args:
        pref: The ``default_histogram_aggregation`` field of an exporter
            configuration block. ``None`` means the field was absent.

    Returns:
        A single entry mapping the histogram instrument class to the chosen
        aggregation, constructed with its own defaults: the schema has no
        place to configure bucket boundaries or scale for the exporter-wide
        preference. A view is the way to set those.

    Raises:
        ConfigurationError: If ``pref`` is some other enum member.
    """
    if pref is None or pref == ExporterDefaultHistogramAggregation.explicit_bucket_histogram:
        return {Histogram: ExplicitBucketHistogramAggregation()}
    if pref == ExporterDefaultHistogramAggregation.base2_exponential_bucket_histogram:
        return {Histogram: ExponentialBucketHistogramAggregation()}
    raise ConfigurationError(
        f"Unsupported default histogram aggregation '{pref}'. "
        "Supported values: explicit_bucket_histogram, base2_exponential_bucket_histogram."
    )


def _create_aggregation(config: AggregationConfig) -> Aggregation:
    """Create an SDK Aggregation from config, passing through detail parameters.

    Args:
        config: The ``aggregation`` field of a view's stream. Exactly one of
            its fields is expected to be set; they are checked in the order
            default, drop, explicit_bucket_histogram,
            base2_exponential_bucket_histogram, last_value, sum.

    Returns:
        The aggregation the block selects. For the explicit bucket histogram
        an absent ``record_min_max`` becomes ``True``; for the exponential
        one an absent field is not passed at all, so the SDK default applies.

    Raises:
        ConfigurationError: If the block selects none of the six known
            types. The message carries the repr of the block.
    """
    if config.default is not None:
        return DefaultAggregation()
    if config.drop is not None:
        return DropAggregation()
    if config.explicit_bucket_histogram is not None:
        return ExplicitBucketHistogramAggregation(
            boundaries=config.explicit_bucket_histogram.boundaries,
            record_min_max=(
                config.explicit_bucket_histogram.record_min_max
                if config.explicit_bucket_histogram.record_min_max is not None
                else True
            ),
        )
    if config.base2_exponential_bucket_histogram is not None:
        kwargs = {}
        if config.base2_exponential_bucket_histogram.max_size is not None:
            kwargs["max_size"] = config.base2_exponential_bucket_histogram.max_size
        if config.base2_exponential_bucket_histogram.max_scale is not None:
            kwargs["max_scale"] = config.base2_exponential_bucket_histogram.max_scale
        if config.base2_exponential_bucket_histogram.record_min_max is not None:
            kwargs["record_min_max"] = config.base2_exponential_bucket_histogram.record_min_max
        return ExponentialBucketHistogramAggregation(**kwargs)
    if config.last_value is not None:
        return LastValueAggregation()
    if config.sum is not None:
        return SumAggregation()
    raise ConfigurationError(
        f"Unknown or unsupported aggregation type in config: {config!r}. "
        "Supported types: default, drop, explicit_bucket_histogram, "
        "base2_exponential_bucket_histogram, last_value, sum."
    )


def _create_view(config: ViewConfig) -> View:
    """Create an SDK View from config.

    The Python SDK's View matches an instrument by an include list only, so
    the ``excluded`` half of ``attribute_keys`` is ignored with a warning
    rather than applied.

    Args:
        config: One entry of the ``views`` list, carrying the ``selector``
            that chooses instruments and the ``stream`` that says what to do
            with them.

    Returns:
        A ``View``. A selector field left absent is passed as ``None``,
        which matches any instrument on that dimension.

    Raises:
        ConfigurationError: If ``selector.instrument_type`` names an
            instrument kind this module has no SDK class for, or if the
            stream's aggregation block selects nothing.
        Exception: Raised by the ``View`` constructor itself, as a bare
            ``Exception``, in three cases: the selector sets none of its
            six matching fields; the stream sets ``name`` while the
            selector leaves ``instrument_name`` absent; the stream sets
            ``name`` while ``instrument_name`` holds a wildcard character.
            None of the three is translated into a ConfigurationError, so
            each reaches the caller of ``configure_sdk`` as it is.
    """
    selector = config.selector
    stream = config.stream

    instrument_type = None
    if selector.instrument_type is not None:
        instrument_type = _INSTRUMENT_TYPE_MAP.get(selector.instrument_type)
        if instrument_type is None:
            raise ConfigurationError(f"Unknown instrument type: {selector.instrument_type!r}")

    attribute_keys: set[str] | None = None
    if stream.attribute_keys is not None:
        if stream.attribute_keys.excluded:
            _logger.warning(
                "attribute_keys.excluded is not supported by the Python SDK View; the exclusion list will be ignored."
            )
        if stream.attribute_keys.included is not None:
            attribute_keys = set(stream.attribute_keys.included)

    aggregation = None
    if stream.aggregation is not None:
        aggregation = _create_aggregation(stream.aggregation)

    return View(
        instrument_type=instrument_type,
        instrument_name=selector.instrument_name,
        meter_name=selector.meter_name,
        meter_version=selector.meter_version,
        meter_schema_url=selector.meter_schema_url,
        instrument_unit=selector.unit,
        name=stream.name,
        description=stream.description,
        attribute_keys=attribute_keys,
        aggregation=aggregation,
        aggregation_cardinality_limit=stream.aggregation_cardinality_limit,
    )


def _create_console_metric_exporter(
    config: ConsoleMetricExporterConfig,
) -> MetricExporter:
    """Create a ConsoleMetricExporter from config.

    Args:
        config: The ``console`` block of a push metric exporter
            configuration. Its only fields are the two preferences.

    Returns:
        A ``ConsoleMetricExporter`` writing to standard output.

    Raises:
        ConfigurationError: If a preference field names something
            unsupported.
    """
    preferred_temporality = _map_temporality(config.temporality_preference)
    preferred_aggregation = _map_histogram_aggregation(config.default_histogram_aggregation)
    return ConsoleMetricExporter(
        preferred_temporality=preferred_temporality,
        preferred_aggregation=preferred_aggregation,
    )


def _create_otlp_http_metric_exporter(
    config: OtlpHttpMetricExporterConfig,
) -> MetricExporter:
    """Create an OTLP HTTP metric exporter from config.

    Args:
        config: The ``otlp_http`` block of a push metric exporter
            configuration. Its ``timeout``, in milliseconds, is converted to
            the seconds the exporter expects. Its ``tls`` block is not read
            at all, so setting ``ca_file``, ``cert_file`` or ``key_file``
            has no effect.

    Returns:
        An ``OTLPMetricExporter`` from the protobuf or the JSON
        distribution, according to ``config.encoding``.

    Raises:
        MissingDependencyError: If the exporter distribution for the chosen
            encoding is not installed.
        ConfigurationError: If ``config.encoding`` is neither protobuf nor
            json, or if a compression or preference field names something
            unsupported.
    """
    headers = _parse_headers(config.headers, config.headers_list)
    timeout = (config.timeout / 1000.0) if config.timeout is not None else None
    preferred_temporality = _map_temporality(config.temporality_preference)
    preferred_aggregation = _map_histogram_aggregation(config.default_histogram_aggregation)

    match config.encoding:
        case None | OtlpHttpEncoding.protobuf:
            try:
                # pylint: disable=import-outside-toplevel,no-name-in-module
                from opentelemetry.exporter.otlp.proto.http import (  # noqa: PLC0415
                    Compression,
                )
                from opentelemetry.exporter.otlp.proto.http.metric_exporter import (  # noqa: PLC0415
                    OTLPMetricExporter,
                )
            except ImportError as exc:
                raise MissingDependencyError(
                    package="opentelemetry-exporter-otlp-proto-http",
                    feature="otlp_http metric exporter",
                ) from exc

            compression = _map_compression(config.compression, Compression, allow_deflate=True)
            return OTLPMetricExporter(
                endpoint=config.endpoint,
                headers=headers,
                timeout=timeout,
                compression=compression,
                preferred_temporality=preferred_temporality,
                preferred_aggregation=preferred_aggregation,
            )
        case OtlpHttpEncoding.json:
            try:
                # pylint: disable=import-outside-toplevel,no-name-in-module
                from opentelemetry.exporter.otlp.common.http import (  # noqa: PLC0415
                    Compression as JsonCompression,
                )
                from opentelemetry.exporter.otlp.json.http.metric_exporter import (  # noqa: PLC0415
                    OTLPMetricExporter as JsonOTLPMetricExporter,
                )
            except ImportError as exc:
                raise MissingDependencyError(
                    package="opentelemetry-exporter-otlp-json-http",
                    feature="otlp_http JSON metric exporter",
                ) from exc

            compression = _map_compression(config.compression, JsonCompression, allow_deflate=True)
            return JsonOTLPMetricExporter(
                endpoint=config.endpoint,
                headers=headers,
                timeout=timeout,
                compression=compression,
                preferred_temporality=preferred_temporality,
                preferred_aggregation=preferred_aggregation,
            )
        case _:
            raise ConfigurationError(
                f"Unsupported OTLP HTTP encoding '{config.encoding}'. Supported values: protobuf, json."
            )


def _create_otlp_grpc_metric_exporter(
    config: OtlpGrpcMetricExporterConfig,
) -> MetricExporter:
    """Create an OTLP gRPC metric exporter from config.

    Args:
        config: The ``otlp_grpc`` block of a push metric exporter
            configuration. Its ``timeout``, in milliseconds, is converted to
            the seconds the exporter expects. Its ``tls`` block is not read
            at all, so ``ca_file``, ``cert_file``, ``key_file`` and
            ``insecure`` have no effect.

    Returns:
        An ``OTLPMetricExporter`` from the gRPC distribution.

    Raises:
        MissingDependencyError: If ``opentelemetry-exporter-otlp-proto-grpc``
            or ``grpc`` is not installed.
        ConfigurationError: If ``config.compression`` is anything other than
            gzip or none, or if a preference field names something
            unsupported.
    """
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        import grpc  # noqa: PLC0415  # type: ignore[import-untyped]

        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (  # noqa: PLC0415  # type: ignore[import-untyped]
            OTLPMetricExporter,
        )
    except ImportError as exc:
        raise MissingDependencyError(
            package="opentelemetry-exporter-otlp-proto-grpc",
            feature="otlp_grpc metric exporter",
        ) from exc

    compression = _map_compression(config.compression, grpc.Compression)
    headers = _parse_headers(config.headers, config.headers_list)
    timeout = (config.timeout / 1000.0) if config.timeout is not None else None
    preferred_temporality = _map_temporality(config.temporality_preference)
    preferred_aggregation = _map_histogram_aggregation(config.default_histogram_aggregation)

    return OTLPMetricExporter(  # type: ignore[return-value]
        endpoint=config.endpoint,
        headers=headers,
        timeout=timeout,
        compression=compression,  # type: ignore[arg-type]
        preferred_temporality=preferred_temporality,
        preferred_aggregation=preferred_aggregation,
    )


def _create_otlp_file_development_metric_exporter(
    config: ExperimentalOtlpFileMetricExporterConfig,
) -> MetricExporter:
    """Create an OTLP file (JSON Lines) metric exporter from config.

    Args:
        config: The ``otlp_file/development`` block of a push metric
            exporter configuration, carrying ``output_stream`` and the two
            preferences.

    Returns:
        A ``FileMetricExporter`` writing to the configured path, or one
        writing to standard output when ``output_stream`` is absent or
        ``"stdout"``.

    Raises:
        ConfigurationError: If ``opentelemetry-exporter-otlp-json-file`` is
            not installed, if ``output_stream`` is neither ``"stdout"`` nor
            a local ``file://`` URI with an absolute path, or if a
            preference field names something unsupported. The missing
            distribution is reported as a plain ConfigurationError here,
            unlike the OTLP HTTP and gRPC exporters.
    """
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        from opentelemetry.exporter.otlp.json.file.metric_exporter import (  # noqa: PLC0415  # type: ignore[import-untyped]
            FileMetricExporter,
        )
    except ImportError as exc:
        raise ConfigurationError(
            "otlp_file_development metric exporter requires 'opentelemetry-exporter-otlp-json-file'. "
            "Install it with: pip install opentelemetry-exporter-otlp-json-file"
        ) from exc

    path = _parse_otlp_file_output_stream(config.output_stream)
    preferred_temporality = _map_temporality(config.temporality_preference)
    preferred_aggregation = _map_histogram_aggregation(config.default_histogram_aggregation)
    return (
        FileMetricExporter(
            path,
            preferred_temporality=preferred_temporality,
            preferred_aggregation=preferred_aggregation,
        )
        if path is not None
        else FileMetricExporter(
            preferred_temporality=preferred_temporality,
            preferred_aggregation=preferred_aggregation,
        )
    )


def _create_push_metric_exporter(
    config: PushMetricExporterConfig,
) -> MetricExporter:
    """Create a push metric exporter from config.

    Known exporter types are checked via typed fields on the PushMetricExporter
    dataclass. Unknown exporter names captured in additional_properties
    by the @_additional_properties decorator are loaded via the
    ``opentelemetry_metrics_exporter`` entry point group.

    The schema permits one exporter per block. If several fields are set,
    which is possible only when schema validation was bypassed, the first
    match in the order otlp_http, otlp_grpc, console, otlp_file_development
    wins and the rest are ignored.

    Args:
        config: The ``exporter`` block of a periodic metric reader
            configuration.

    Returns:
        The exporter the block selects. A plugin exporter is constructed
        with its nested configuration mapping splatted as keyword
        arguments, with no preference translation, so whatever keys the
        mapping holds reach its constructor unchanged.

    Raises:
        ConfigurationError: If the block selects no exporter, or if the
            selected one cannot be built.
        MissingDependencyError: If the selected exporter's distribution is
            not installed.
        TypeError: If a plugin exporter's constructor does not accept the
            keys of the nested configuration mapping splatted into it.
    """
    match config:
        case PushMetricExporterConfig(otlp_http=exporter_config) if exporter_config is not None:
            return _create_otlp_http_metric_exporter(exporter_config)
        case PushMetricExporterConfig(otlp_grpc=exporter_config) if exporter_config is not None:
            return _create_otlp_grpc_metric_exporter(exporter_config)
        case PushMetricExporterConfig(console=exporter_config) if exporter_config is not None:
            return _create_console_metric_exporter(exporter_config)
        case PushMetricExporterConfig(otlp_file_development=exporter_config) if exporter_config is not None:
            return _create_otlp_file_development_metric_exporter(exporter_config)
        case PushMetricExporterConfig(additional_properties=additional_properties) if additional_properties:
            name, plugin_config = next(iter(additional_properties.items()))
            return load_entry_point("opentelemetry_metrics_exporter", name)(**(plugin_config or {}))
        case _:
            raise ConfigurationError(
                "No exporter type specified in push metric exporter config. "
                "Supported types: console, otlp_http, otlp_grpc, otlp_file_development."
            )


def _create_cardinality_limits(config: CardinalityLimitsConfig | None) -> CardinalityLimits | None:
    """Create the SDK per-instrument cardinality limits from config.

    Each instrument type uses its own limit and falls back to ``default``.
    Instrument types left out of the result use the SDK default limit.

    Args:
        config: The ``cardinality_limits`` block of a metric reader
            configuration. ``None`` means the field was absent.

    Returns:
        A mapping from instrument class to limit, holding only the
        instrument types that ended up with one. ``None`` for a ``None``
        config, and an empty mapping for a block that set neither
        ``default`` nor any per-instrument field; both leave every
        instrument on the SDK default.
    """
    if config is None:
        return None
    limits: CardinalityLimits = {}
    for instrument_class, limit in (
        (Counter, config.counter),
        (UpDownCounter, config.up_down_counter),
        (Histogram, config.histogram),
        (_Gauge, config.gauge),
        (ObservableCounter, config.observable_counter),
        (ObservableUpDownCounter, config.observable_up_down_counter),
        (ObservableGauge, config.observable_gauge),
    ):
        limit = limit if limit is not None else config.default
        if limit is not None:
            limits[instrument_class] = limit
    return limits


def _create_periodic_metric_reader(
    config: PeriodicMetricReaderConfig,
) -> PeriodicExportingMetricReader:
    """Create a PeriodicExportingMetricReader from config.

    Passes explicit interval/timeout defaults to suppress env var reading.

    Constructing the reader starts its background export thread, so a
    failure later in ``create_meter_provider`` leaves that thread running.

    Args:
        config: One ``periodic`` block from the ``readers`` list. Its
            ``interval`` and ``timeout`` are in milliseconds; an absent one
            becomes the specification default, 60000 and 30000. Its
            ``producers`` and ``max_export_batch_size/development`` fields
            are read by nothing and no warning names them, so setting
            either has no effect and leaves no trace in the log.

    Returns:
        A ``PeriodicExportingMetricReader`` owning the configured exporter.

    Raises:
        ConfigurationError: If the exporter block selects nothing or cannot
            be built.
        MissingDependencyError: If the exporter's distribution is not
            installed.
    """
    exporter = _create_push_metric_exporter(config.exporter)
    interval = config.interval if config.interval is not None else _DEFAULT_EXPORT_INTERVAL_MILLIS
    timeout = config.timeout if config.timeout is not None else _DEFAULT_EXPORT_TIMEOUT_MILLIS
    return PeriodicExportingMetricReader(
        exporter=exporter,
        export_interval_millis=float(interval),
        export_timeout_millis=float(timeout),
        cardinality_limits=_create_cardinality_limits(config.cardinality_limits),
    )


def _create_prometheus_metric_reader(
    config: PrometheusMetricExporterConfig,
    cardinality_limits: CardinalityLimits | None = None,
) -> MetricReader:
    """Create a PrometheusMetricReader from config.

    Dynamically imports the prometheus exporter package to avoid a hard
    dependency. Maps config fields to constructor parameters and starts
    the HTTP server.

    The listener is started here and never stopped, so building a provider
    that is then discarded leaves the port bound for the life of the
    process, and a second reader on the same port fails to bind.
    ``scope_info_enabled`` and ``resource_constant_labels`` are ignored
    with a warning naming each; ``translation_strategy`` is ignored with
    no warning.

    Args:
        config: The ``prometheus/development`` block of a pull metric
            exporter configuration. An absent ``port`` becomes 9464 and an
            absent ``host`` becomes ``"localhost"``.
        cardinality_limits: Per-instrument limits to hand to the reader.
            ``None`` leaves the SDK defaults in place.

    Returns:
        A ``PrometheusMetricReader``, with the HTTP listener already
        accepting scrapes. Target info is emitted unless
        ``target_info_enabled/development`` is explicitly false.

    Raises:
        MissingDependencyError: If ``opentelemetry-exporter-prometheus`` is
            not installed.
        OSError: If the configured port cannot be bound.
    """
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        from opentelemetry.exporter.prometheus import (  # noqa: PLC0415  # type: ignore[import-untyped]
            PrometheusMetricReader,
            start_http_server,
        )
    except ImportError as exc:
        raise MissingDependencyError(
            package="opentelemetry-exporter-prometheus",
            feature="prometheus pull metric exporter",
        ) from exc

    disable_target_info = (
        config.target_info_enabled_development is not None and not config.target_info_enabled_development
    )

    if config.scope_info_enabled is not None:
        _logger.warning("scope_info_enabled is not yet supported for Prometheus metric exporter and will be ignored.")
    if config.resource_constant_labels is not None:
        _logger.warning(
            "resource_constant_labels is not yet supported for Prometheus metric exporter and will be ignored."
        )

    reader = PrometheusMetricReader(
        disable_target_info=disable_target_info,
        cardinality_limits=cardinality_limits,
    )

    port = config.port if config.port is not None else 9464
    host = config.host if config.host is not None else "localhost"
    start_http_server(port=port, addr=host)

    return reader


def _create_pull_metric_exporter(
    config: PullMetricExporterConfig,
    cardinality_limits: CardinalityLimits | None = None,
) -> MetricReader:
    """Create a pull metric exporter (which is itself a MetricReader) from config.

    Pull metric exporters like Prometheus are combined reader+exporter objects:
    the "exporter" IS the reader. The config schema models them as separate
    exporter configs, but the factory returns a MetricReader.

    Plugin pull exporters are loaded via the ``opentelemetry_pull_metric_exporter``
    entry point group.

    Args:
        config: The ``exporter`` block of a pull metric reader
            configuration.
        cardinality_limits: Per-instrument limits from the reader. They
            reach the Prometheus reader. For a plugin they are ignored, and
            a warning is logged only when they are not ``None``.

    Returns:
        The reader the block selects.

    Raises:
        ConfigurationError: If the block names neither
            ``prometheus/development`` nor a plugin, or if the plugin name
            is not registered.
        MissingDependencyError: If the Prometheus exporter distribution is
            not installed.
        OSError: If the Prometheus listener cannot bind the configured
            port. ``_create_prometheus_metric_reader`` starts it before
            returning, so the failure reaches this caller.
    """
    if config.prometheus_development is not None:
        return _create_prometheus_metric_reader(config.prometheus_development, cardinality_limits)
    if config.additional_properties:
        name, plugin_config = next(iter(config.additional_properties.items()))
        if cardinality_limits is not None:
            _logger.warning(
                "cardinality_limits is not yet supported for pull metric exporter plugins and will be ignored."
            )
        return load_entry_point("opentelemetry_pull_metric_exporter", name)(**(plugin_config or {}))
    raise ConfigurationError(
        "No exporter type specified in pull metric exporter config. Supported types: prometheus_development."
    )


def _create_pull_metric_reader(
    config: PullMetricReaderConfig,
) -> MetricReader:
    """Create a pull MetricReader from config.

    The pull reader's exporter is itself a MetricReader (combined reader+exporter).
    producers are not yet supported.

    Args:
        config: One ``pull`` block from the ``readers`` list. Its
            ``producers`` field is ignored with a warning, because the
            Python SDK has no metric producer plugin point.

    Returns:
        The reader its exporter block names. A Prometheus reader carries
        the reader's cardinality limits; a plugin reader does not, because
        ``_create_pull_metric_exporter`` drops them.

    Raises:
        ConfigurationError: If the exporter block selects nothing or cannot
            be built.
        MissingDependencyError: If the Prometheus exporter distribution is
            not installed.
        OSError: If the exporter block is ``prometheus/development`` and
            its listener cannot bind the configured port.
    """
    if config.producers:
        _logger.warning(
            "MetricProducer configuration is not yet supported for pull metric readers and will be ignored."
        )
    return _create_pull_metric_exporter(config.exporter, _create_cardinality_limits(config.cardinality_limits))


def _create_metric_reader(config: MetricReaderConfig) -> MetricReader:
    """Create a MetricReader from config.

    Args:
        config: One entry of the ``readers`` list. Exactly one of its
            ``periodic`` and ``pull`` fields is expected to be set;
            ``periodic`` is checked first.

    Returns:
        A ``PeriodicExportingMetricReader`` or the pull reader the block
        names.

    Raises:
        ConfigurationError: If neither field is set, or if the reader
            cannot be built.
        MissingDependencyError: If the selected exporter's distribution is
            not installed.
        OSError: If the reader is a ``pull`` reader on
            ``prometheus/development`` and its listener cannot bind the
            configured port.
    """
    if config.periodic is not None:
        return _create_periodic_metric_reader(config.periodic)
    if config.pull is not None:
        return _create_pull_metric_reader(config.pull)
    raise ConfigurationError("No reader type specified in metric reader config. Supported types: periodic, pull.")


def _create_exemplar_filter(
    value: ExemplarFilterConfig,
) -> object:
    """Create an SDK exemplar filter from config enum value.

    Args:
        value: The ``exemplar_filter`` field of the meter provider
            configuration.

    Returns:
        The filter instance for that value. It is annotated as ``object``
        rather than as the SDK's ``ExemplarFilter``, which is why
        ``create_meter_provider`` has to silence the type checker where it
        passes the result on.

    Raises:
        ConfigurationError: If ``value`` is some other enum member.
    """
    if value == ExemplarFilterConfig.always_on:
        return AlwaysOnExemplarFilter()
    if value == ExemplarFilterConfig.always_off:
        return AlwaysOffExemplarFilter()
    if value == ExemplarFilterConfig.trace_based:
        return TraceBasedExemplarFilter()
    raise ConfigurationError(
        f"Unknown exemplar filter value: {value!r}. Supported values: always_on, always_off, trace_based."
    )


def _to_meter_config(config: MeterConfigConfig | None) -> _MeterConfig:
    """Map an experimental per-meter config to an SDK ``_MeterConfig``.

    Only ``enabled`` is honored — it is the sole field the SDK
    ``_MeterConfig`` exposes. An absent ``enabled`` leaves the meter enabled.

    Args:
        config: The ``config`` field of one meter matcher, or the
            ``default_config`` of the configurator. ``None`` means the
            field was absent.

    Returns:
        A ``_MeterConfig``. The SDK default, which is enabled, for a
        ``None`` config and for one whose ``enabled`` is absent.
    """
    if config is None or config.enabled is None:
        return _MeterConfig.default()
    return _MeterConfig(is_enabled=config.enabled)


def _create_meter_configurator(
    config: MeterConfiguratorConfig,
) -> _RuleBasedMeterConfigurator:
    """Build a rule-based meter configurator from experimental config.

    Each entry in ``meters`` maps an instrumentation-scope name glob to a
    per-meter config; ``default_config`` applies to scopes matching no glob.
    Rules are evaluated in order, so earlier entries take precedence.

    Args:
        config: The ``meter_configurator/development`` block of the meter
            provider configuration.

    Returns:
        A ``_RuleBasedMeterConfigurator``. An absent ``meters`` field gives
        no rules, so every meter takes ``default_config``.
    """
    rules = [
        (
            _scope_name_matches_glob(matcher.name),
            _to_meter_config(matcher.config),
        )
        for matcher in (config.meters or [])
    ]
    return _RuleBasedMeterConfigurator(
        rules=rules,
        default_config=_to_meter_config(config.default_config),
    )


def create_meter_provider(
    config: MeterProviderConfig | None,
    resource: Resource | None = None,
) -> MeterProvider:
    """Create an SDK MeterProvider from declarative config.

    Does NOT read OTEL_METRIC_EXPORT_INTERVAL, OTEL_METRICS_EXEMPLAR_FILTER,
    or any other env vars for values explicitly controlled by the config.
    Absent config values use OTel spec defaults, matching Java SDK behavior.

    Args:
        config: MeterProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.

    Returns:
        A configured MeterProvider.
    """
    # Always pass an explicit exemplar filter to suppress env var reading.
    # Spec default is trace_based.
    exemplar_filter: object = TraceBasedExemplarFilter()
    if config is not None and config.exemplar_filter is not None:
        exemplar_filter = _create_exemplar_filter(config.exemplar_filter)

    readers: list[MetricReader] = []
    views: list[View] = []

    if config is not None:
        for reader_config in config.readers:
            readers.append(_create_metric_reader(reader_config))
        if config.views:
            for view_config in config.views:
                views.append(_create_view(view_config))

    meter_configurator = (
        _create_meter_configurator(config.meter_configurator_development)
        if config is not None and config.meter_configurator_development is not None
        else None
    )

    return MeterProvider(
        resource=resource,
        metric_readers=readers,
        exemplar_filter=exemplar_filter,  # type: ignore[arg-type]
        views=views,
        _meter_configurator=meter_configurator,
    )


def configure_meter_provider(
    config: MeterProviderConfig | None,
    resource: Resource | None = None,
) -> None:
    """Configure the global MeterProvider from declarative config.

    When config is None (meter_provider section absent from config file),
    the global is not set — matching Java/JS SDK behavior.

    Args:
        config: MeterProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.
    """
    if config is None:
        return
    metrics.set_meter_provider(create_meter_provider(config, resource))
