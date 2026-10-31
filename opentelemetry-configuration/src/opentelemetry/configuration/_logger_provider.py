# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""LoggerProvider construction from declarative configuration.

Only ``create_logger_provider`` and ``configure_logger_provider`` are
meant to be called from outside this module. The rest build one piece: a
log record processor, its exporter, the record limits, or the
experimental per-logger configurator.

No function here reads an environment variable. The record limits and
the batch processor tuning values are passed to the SDK explicitly, with
the constant the specification gives standing in for an absent
configuration field, so ``OTEL_BLRP_*`` and
``OTEL_LOGRECORD_ATTRIBUTE_*`` have no effect once a configuration file
is in use. That is the difference from the span processor on the tracer
path, which passes an absent batch field through as ``None`` and does
let the SDK read ``OTEL_BSP_*``.

The exporter fields are the other way round on both paths. An absent
endpoint, header set, timeout or compression is passed through as
``None``, so the exporter still reads the ``OTEL_EXPORTER_OTLP_*``
family for whatever the configuration file leaves out.

The logger configurator block accepts two fields the Python SDK's
``_LoggerConfig`` has no place for, ``minimum_severity`` and
``trace_based``. Setting either is ignored with a warning naming it.
"""

from __future__ import annotations

import logging

from opentelemetry._logs import set_logger_provider
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
    AttributeLimits,
    OtlpHttpEncoding,
)
from opentelemetry.configuration.models import (
    BatchLogRecordProcessor as BatchLogRecordProcessorConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalLoggerConfig as LoggerConfigConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalLoggerConfigurator as LoggerConfiguratorConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalOtlpFileExporter as ExperimentalOtlpFileExporterConfig,
)
from opentelemetry.configuration.models import (
    LoggerProvider as LoggerProviderConfig,
)
from opentelemetry.configuration.models import (
    LogRecordExporter as LogRecordExporterConfig,
)
from opentelemetry.configuration.models import (
    LogRecordLimits as LogRecordLimitsConfig,
)
from opentelemetry.configuration.models import (
    LogRecordProcessor as LogRecordProcessorConfig,
)
from opentelemetry.configuration.models import (
    OtlpGrpcExporter as OtlpGrpcExporterConfig,
)
from opentelemetry.configuration.models import (
    OtlpHttpExporter as OtlpHttpExporterConfig,
)
from opentelemetry.configuration.models import (
    SimpleLogRecordProcessor as SimpleLogRecordProcessorConfig,
)
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs._internal import (
    LogRecordLimits,
    _LoggerConfig,
    _RuleBasedLoggerConfigurator,
)
from opentelemetry.sdk._logs._internal.export import (
    BatchLogRecordProcessor,
    ConsoleLogRecordExporter,
    LogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.resources import Resource

_logger = logging.getLogger(__name__)

_DEFAULT_OTEL_LOG_ATTRIBUTE_COUNT_LIMIT = 128

# BatchLogRecordProcessor defaults per OTel spec (milliseconds).
_DEFAULT_SCHEDULE_DELAY_MILLIS = 1000
_DEFAULT_EXPORT_TIMEOUT_MILLIS = 30000
_DEFAULT_MAX_QUEUE_SIZE = 2048
_DEFAULT_MAX_EXPORT_BATCH_SIZE = 512


def _create_console_log_exporter() -> ConsoleLogRecordExporter:
    """Create a ConsoleLogRecordExporter.

    The ``console`` block of a log record exporter configuration has no
    fields, so nothing is read from it and this function takes no argument.
    ``_create_log_record_exporter`` constructs the exporter directly rather
    than calling this, so nothing in the package reaches it today.

    Returns:
        A ``ConsoleLogRecordExporter`` writing to standard output.
    """
    return ConsoleLogRecordExporter()


def _create_otlp_http_log_exporter(
    config: OtlpHttpExporterConfig,
) -> LogRecordExporter:
    """Create an OTLP HTTP log exporter from config.

    Args:
        config: The ``otlp_http`` block of a log record exporter
            configuration. Its ``timeout``, in milliseconds, is converted to
            the seconds the exporter expects. Its ``tls`` block is not read
            at all, so setting ``ca_file``, ``cert_file`` or ``key_file``
            has no effect.

    Returns:
        An ``OTLPLogExporter`` from the protobuf or the JSON distribution,
        according to ``config.encoding``.

    Raises:
        MissingDependencyError: If the exporter distribution for the chosen
            encoding is not installed.
        ConfigurationError: If ``config.encoding`` is neither protobuf nor
            json, or if ``config.compression`` names something the exporter
            does not support.
    """
    headers = _parse_headers(config.headers, config.headers_list)
    timeout = (config.timeout / 1000.0) if config.timeout is not None else None

    match config.encoding:
        case None | OtlpHttpEncoding.protobuf:
            try:
                # pylint: disable=import-outside-toplevel,no-name-in-module
                from opentelemetry.exporter.otlp.proto.http import (  # noqa: PLC0415
                    Compression,
                )
                from opentelemetry.exporter.otlp.proto.http._log_exporter import (  # noqa: PLC0415
                    OTLPLogExporter,
                )
            except ImportError as exc:
                raise MissingDependencyError(
                    package="opentelemetry-exporter-otlp-proto-http",
                    feature="otlp_http log exporter",
                ) from exc

            compression = _map_compression(config.compression, Compression, allow_deflate=True)
            return OTLPLogExporter(
                endpoint=config.endpoint,
                headers=headers,
                timeout=timeout,
                compression=compression,
            )
        case OtlpHttpEncoding.json:
            try:
                # pylint: disable=import-outside-toplevel,no-name-in-module
                from opentelemetry.exporter.otlp.common.http import (  # noqa: PLC0415
                    Compression as JsonCompression,
                )
                from opentelemetry.exporter.otlp.json.http._log_exporter import (  # noqa: PLC0415
                    OTLPLogExporter as JsonOTLPLogExporter,
                )
            except ImportError as exc:
                raise MissingDependencyError(
                    package="opentelemetry-exporter-otlp-json-http",
                    feature="otlp_http JSON log exporter",
                ) from exc

            compression = _map_compression(config.compression, JsonCompression, allow_deflate=True)
            return JsonOTLPLogExporter(
                endpoint=config.endpoint,
                headers=headers,
                timeout=timeout,
                compression=compression,
            )
        case _:
            raise ConfigurationError(
                f"Unsupported OTLP HTTP encoding '{config.encoding}'. Supported values: protobuf, json."
            )


def _create_otlp_grpc_log_exporter(
    config: OtlpGrpcExporterConfig,
) -> LogRecordExporter:
    """Create an OTLP gRPC log exporter from config.

    Args:
        config: The ``otlp_grpc`` block of a log record exporter
            configuration. Its ``timeout``, in milliseconds, is converted to
            the seconds the exporter expects. Its ``tls`` block is not read
            at all, so ``ca_file``, ``cert_file``, ``key_file`` and
            ``insecure`` have no effect.

    Returns:
        An ``OTLPLogExporter`` from the gRPC distribution.

    Raises:
        MissingDependencyError: If ``opentelemetry-exporter-otlp-proto-grpc``
            or ``grpc`` is not installed.
        ConfigurationError: If ``config.compression`` is anything other than
            gzip or none. Deflate is rejected here, unlike on the HTTP path.
    """
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        import grpc  # noqa: PLC0415  # type: ignore[import-untyped]

        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (  # noqa: PLC0415  # type: ignore[import-untyped]
            OTLPLogExporter,
        )
    except ImportError as exc:
        raise MissingDependencyError(
            package="opentelemetry-exporter-otlp-proto-grpc",
            feature="otlp_grpc log exporter",
        ) from exc

    compression = _map_compression(config.compression, grpc.Compression)
    headers = _parse_headers(config.headers, config.headers_list)
    timeout = (config.timeout / 1000.0) if config.timeout is not None else None

    return OTLPLogExporter(  # type: ignore[return-value]
        endpoint=config.endpoint,
        headers=headers,
        timeout=timeout,
        compression=compression,  # type: ignore[arg-type]
    )


def _create_otlp_file_development_log_exporter(
    config: ExperimentalOtlpFileExporterConfig,
) -> LogRecordExporter:
    """Create an OTLP file (JSON Lines) log exporter from config.

    Args:
        config: The ``otlp_file/development`` block of a log record exporter
            configuration, whose only field is ``output_stream``.

    Returns:
        A ``FileLogExporter`` writing to the configured path, or one writing
        to standard output when ``output_stream`` is absent or ``"stdout"``.

    Raises:
        ConfigurationError: If ``opentelemetry-exporter-otlp-json-file`` is
            not installed, or if ``output_stream`` is neither ``"stdout"``
            nor a local ``file://`` URI with an absolute path. The missing
            distribution is reported as a plain ConfigurationError here,
            unlike the OTLP HTTP and gRPC exporters.
    """
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        from opentelemetry.exporter.otlp.json.file._log_exporter import (  # noqa: PLC0415  # type: ignore[import-untyped]
            FileLogExporter,
        )
    except ImportError as exc:
        raise ConfigurationError(
            "otlp_file_development log exporter requires 'opentelemetry-exporter-otlp-json-file'. "
            "Install it with: pip install opentelemetry-exporter-otlp-json-file"
        ) from exc

    path = _parse_otlp_file_output_stream(config.output_stream)
    return FileLogExporter(path) if path is not None else FileLogExporter()


def _create_log_record_exporter(
    config: LogRecordExporterConfig,
) -> LogRecordExporter:
    """Create a log record exporter from config.

    Known exporter types are checked via typed fields on the LogRecordExporter
    dataclass. Unknown exporter names captured in additional_properties
    by the @_additional_properties decorator are loaded via the
    ``opentelemetry_logs_exporter`` entry point group.

    The schema permits one exporter per block. If several fields are set,
    which is possible only when schema validation was bypassed, the first
    match in the order otlp_http, otlp_grpc, console, otlp_file_development
    wins and the rest are ignored.

    Args:
        config: The ``exporter`` block of a log record processor
            configuration.

    Returns:
        The exporter the block selects. A plugin exporter is constructed
        with its nested configuration mapping splatted as keyword
        arguments, so a plugin that does not accept them raises
        ``TypeError``.

    Raises:
        ConfigurationError: If the block selects no exporter, or if the
            selected one cannot be built.
        MissingDependencyError: If the selected exporter's distribution is
            not installed.
        TypeError: If a plugin exporter's constructor does not accept the
            keys of the nested configuration mapping splatted into it.
    """
    match config:
        case LogRecordExporterConfig(otlp_http=exporter_config) if exporter_config is not None:
            return _create_otlp_http_log_exporter(exporter_config)
        case LogRecordExporterConfig(otlp_grpc=exporter_config) if exporter_config is not None:
            return _create_otlp_grpc_log_exporter(exporter_config)
        case LogRecordExporterConfig(console=exporter_config) if exporter_config is not None:
            return ConsoleLogRecordExporter()
        case LogRecordExporterConfig(otlp_file_development=exporter_config) if exporter_config is not None:
            return _create_otlp_file_development_log_exporter(exporter_config)
        case LogRecordExporterConfig(additional_properties=additional_properties) if additional_properties:
            name, plugin_config = next(iter(additional_properties.items()))
            return load_entry_point("opentelemetry_logs_exporter", name)(**(plugin_config or {}))
        case _:
            raise ConfigurationError(
                "No exporter type specified in log record exporter config. "
                "Supported types: console, otlp_http, otlp_grpc, otlp_file_development."
            )


def _create_batch_log_record_processor(
    config: BatchLogRecordProcessorConfig,
) -> BatchLogRecordProcessor:
    """Create a BatchLogRecordProcessor from config.

    Passes explicit defaults to suppress OTEL_BLRP_* env var reading.

    Args:
        config: One ``batch`` block from the ``processors`` list. Its
            ``schedule_delay`` and ``export_timeout`` are in milliseconds.
            An absent field becomes the specification default: 1000 ms
            delay, 30000 ms timeout, 2048 queued records, 512 per batch.

    Returns:
        A ``BatchLogRecordProcessor`` owning the configured exporter, with
        all four tuning values set explicitly.

    Raises:
        ConfigurationError: If the exporter block selects nothing or cannot
            be built.
        MissingDependencyError: If the exporter's distribution is not
            installed.
        TypeError: If a plugin exporter's constructor does not accept the
            keys of the nested configuration mapping splatted into it.
    """
    exporter = _create_log_record_exporter(config.exporter)
    schedule_delay = config.schedule_delay if config.schedule_delay is not None else _DEFAULT_SCHEDULE_DELAY_MILLIS
    export_timeout = config.export_timeout if config.export_timeout is not None else _DEFAULT_EXPORT_TIMEOUT_MILLIS
    max_queue_size = config.max_queue_size if config.max_queue_size is not None else _DEFAULT_MAX_QUEUE_SIZE
    max_export_batch_size = (
        config.max_export_batch_size if config.max_export_batch_size is not None else _DEFAULT_MAX_EXPORT_BATCH_SIZE
    )
    return BatchLogRecordProcessor(
        exporter=exporter,
        schedule_delay_millis=float(schedule_delay),
        export_timeout_millis=float(export_timeout),
        max_queue_size=max_queue_size,
        max_export_batch_size=max_export_batch_size,
    )


def _create_simple_log_record_processor(
    config: SimpleLogRecordProcessorConfig,
) -> SimpleLogRecordProcessor:
    """Create a SimpleLogRecordProcessor from config.

    Args:
        config: One ``simple`` block from the ``processors`` list. Its only
            field is the exporter.

    Returns:
        A ``SimpleLogRecordProcessor``, which exports each record as it is
        emitted rather than batching.

    Raises:
        ConfigurationError: If the exporter block selects nothing or cannot
            be built.
        MissingDependencyError: If the exporter's distribution is not
            installed.
        TypeError: If a plugin exporter's constructor does not accept the
            keys of the nested configuration mapping splatted into it.
    """
    exporter = _create_log_record_exporter(config.exporter)
    return SimpleLogRecordProcessor(exporter)


def _create_log_record_processor(
    config: LogRecordProcessorConfig,
) -> BatchLogRecordProcessor | SimpleLogRecordProcessor:
    """Create a log record processor from config.

    Args:
        config: One entry of the ``processors`` list. Exactly one of its
            ``batch`` and ``simple`` fields is expected to be set;
            ``batch`` is checked first.

    Returns:
        A ``BatchLogRecordProcessor`` or a ``SimpleLogRecordProcessor``
        wrapping the exporter the block names.

    Raises:
        ConfigurationError: If neither field is set, or if the processor
            cannot be built.
        MissingDependencyError: If the selected exporter's distribution is
            not installed.
        TypeError: If a plugin exporter's constructor does not accept the
            keys of the nested configuration mapping splatted into it.
    """
    if config.batch is not None:
        return _create_batch_log_record_processor(config.batch)
    if config.simple is not None:
        return _create_simple_log_record_processor(config.simple)
    raise ConfigurationError(
        "No processor type specified in log record processor config. Supported types: batch, simple."
    )


def _to_logger_config(config: LoggerConfigConfig | None) -> _LoggerConfig:
    """Map an experimental per-logger config to an SDK ``_LoggerConfig``.

    Only ``enabled`` is honored. ``minimum_severity`` and ``trace_based`` are
    accepted by the config schema but not supported by the Python SDK
    ``_LoggerConfig``; the ones that are set are ignored with a warning naming
    them. An absent ``enabled`` leaves the logger enabled.

    Args:
        config: The ``config`` field of one logger matcher, or the
            ``default_config`` of the configurator. ``None`` means the
            field was absent.

    Returns:
        A ``_LoggerConfig``. The SDK default, which is enabled, for a
        ``None`` config and for one whose ``enabled`` is absent. The
        warning about unsupported fields is emitted before that check, so
        it is reached even when ``enabled`` is absent.
    """
    if config is None:
        return _LoggerConfig.default()
    unsupported_fields = [
        field_name for field_name in ("minimum_severity", "trace_based") if getattr(config, field_name) is not None
    ]
    if unsupported_fields:
        _logger.warning(
            "Ignoring logger_configurator fields that are not supported by the Python SDK LoggerProvider: %s",
            ", ".join(unsupported_fields),
        )
    if config.enabled is None:
        return _LoggerConfig.default()
    return _LoggerConfig(is_enabled=config.enabled)


def _create_logger_configurator(
    config: LoggerConfiguratorConfig,
) -> _RuleBasedLoggerConfigurator:
    """Build a rule-based logger configurator from experimental config.

    Each entry in ``loggers`` maps an instrumentation-scope name glob to a
    per-logger config; ``default_config`` applies to scopes matching no glob.
    Rules are evaluated in order, so earlier entries take precedence.

    Args:
        config: The ``logger_configurator/development`` block of the logger
            provider configuration.

    Returns:
        A ``_RuleBasedLoggerConfigurator``. An absent ``loggers`` field
        gives no rules, so every logger takes ``default_config``.
    """
    rules = [
        (
            _scope_name_matches_glob(matcher.name),
            _to_logger_config(matcher.config),
        )
        for matcher in (config.loggers or [])
    ]
    return _RuleBasedLoggerConfigurator(
        rules=rules,
        default_config=_to_logger_config(config.default_config),
    )


def _create_log_record_limits(
    config: LogRecordLimitsConfig,
    global_limits: AttributeLimits | None = None,
) -> LogRecordLimits:
    """Create LogRecordLimits from config.

    Absent fields fall back to global_limits (if provided), then to OTel spec
    defaults (128 for counts, unlimited for lengths).
    Explicit values suppress env-var reading — matching Java SDK behavior.

    Args:
        config: The ``limits`` block of the logger provider configuration.
            ``create_logger_provider`` passes an empty block rather than
            ``None`` when the configuration has no limits section, so every
            field falls back.
        global_limits: The top-level ``attribute_limits`` block, consulted
            only for a field the log record limits leave absent. ``None``
            means the configuration has no top-level block.

    Returns:
        ``LogRecordLimits`` with every field set, so the SDK reads none of
        the ``OTEL_LOGRECORD_ATTRIBUTE_*`` environment variables. Each
        resolved value is written to both the generic and the
        log-record-specific field, because the SDK enforces the
        log-record-specific pair and leaving it absent would let the
        environment variable override the configured value.
    """
    attribute_count_limit = config.attribute_count_limit
    if attribute_count_limit is None and global_limits is not None:
        attribute_count_limit = global_limits.attribute_count_limit

    attribute_value_length_limit = config.attribute_value_length_limit
    if attribute_value_length_limit is None and global_limits is not None:
        attribute_value_length_limit = global_limits.attribute_value_length_limit

    max_attributes = (
        attribute_count_limit if attribute_count_limit is not None else _DEFAULT_OTEL_LOG_ATTRIBUTE_COUNT_LIMIT
    )
    max_attribute_length = (
        attribute_value_length_limit if attribute_value_length_limit is not None else LogRecordLimits.UNSET
    )

    # The log-record-specific fields are the ones the SDK enforces, so they are
    # set explicitly too. Leaving them absent would let OTEL_LOGRECORD_ATTRIBUTE_*
    # override the configured values.
    return LogRecordLimits(
        max_attributes=max_attributes,
        max_attribute_length=max_attribute_length,
        max_log_record_attributes=max_attributes,
        max_log_record_attribute_length=max_attribute_length,
    )


def create_logger_provider(
    config: LoggerProviderConfig | None,
    resource: Resource | None = None,
    global_attribute_limits: AttributeLimits | None = None,
) -> LoggerProvider:
    """Create an SDK LoggerProvider from declarative config.

    Does NOT read OTEL_BLRP_* or other env vars for values explicitly
    controlled by the config. Absent config values use OTel spec defaults.

    Args:
        config: LoggerProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.
        global_attribute_limits: Top-level attribute_limits from the root config,
            used as a fallback when per-signal limits are not specified.

    Returns:
        A configured LoggerProvider.

    Raises:
        ConfigurationError: If a log record processor names a component
            that cannot be built.
        MissingDependencyError: If a log record exporter's distribution is
            not installed.
        TypeError: If a plugin component's constructor does not accept the
            keys of the nested configuration mapping splatted into it.
    """
    logger_configurator = (
        _create_logger_configurator(config.logger_configurator_development)
        if config is not None and config.logger_configurator_development is not None
        else None
    )

    if config is not None and config.limits is not None:
        limits = config.limits

    else:
        limits = LogRecordLimitsConfig()

    log_record_limits = _create_log_record_limits(limits, global_attribute_limits)

    provider = LoggerProvider(
        resource=resource,
        log_record_limits=log_record_limits,
        _logger_configurator=logger_configurator,
    )

    if config is None:
        return provider

    for processor_config in config.processors:
        provider.add_log_record_processor(_create_log_record_processor(processor_config))

    return provider


def configure_logger_provider(
    config: LoggerProviderConfig | None,
    resource: Resource | None = None,
    global_attribute_limits: AttributeLimits | None = None,
) -> None:
    """Configure the global LoggerProvider from declarative config.

    When config is None (logger_provider section absent from config file),
    the global is not set — matching Java/JS SDK behavior.

    Args:
        config: LoggerProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.
        global_attribute_limits: Top-level attribute_limits from the root config,
            used as a fallback when per-signal limits are not specified.

    Raises:
        ConfigurationError: If any component the configuration names cannot
            be built.
        MissingDependencyError: If a log record exporter's distribution is
            not installed.
        TypeError: If a plugin component's constructor does not accept the
            keys of the nested configuration mapping splatted into it.
            The global is left as it was for every one of these, because
            ``create_logger_provider`` builds the provider before it is
            set.
    """
    if config is None:
        return
    set_logger_provider(create_logger_provider(config, resource, global_attribute_limits))
