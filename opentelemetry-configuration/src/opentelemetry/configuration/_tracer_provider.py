# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""TracerProvider construction from declarative configuration.

Only ``create_tracer_provider`` and ``configure_tracer_provider`` are
meant to be called from outside this module. Everything else builds one
piece of the provider: a sampler, an id generator, the span limits, a
span processor and its exporter, or the experimental per-tracer
configurator.

No function here reads an environment variable. The sampler, the id
generator and most of the span limits are passed to the SDK explicitly,
with the constant the specification gives standing in for an absent
configuration field, so ``OTEL_TRACES_SAMPLER`` and the
``OTEL_SPAN_*_LIMIT`` family have no effect once a configuration file is
in use.

Three things are left to the SDK and so still follow the environment.
``_create_span_processor`` passes an absent batch field through as
``None``, which lets the SDK read ``OTEL_BSP_SCHEDULE_DELAY`` and its
siblings. ``_create_span_limits`` never passes ``max_attributes``, so
``OTEL_ATTRIBUTE_COUNT_LIMIT`` is still read for it. The OTLP exporter
factories pass an absent endpoint, header set, timeout or compression
through as ``None``, so the exporter still reads the
``OTEL_EXPORTER_OTLP_*`` family for whatever the configuration file
leaves out. The logger provider passes its batch values and its
``max_attributes`` explicitly, which is why ``OTEL_BLRP_*`` is dead
there and ``OTEL_BSP_*`` is not dead here; its exporter fields behave
exactly as the ones here do.

The SDK's experimental composable samplers are reachable through the
``composite/development`` field. They are a separate sampler hierarchy
from the stable one: a composable sampler returns a threshold rather
than a decision, and only ``composite_sampler`` turns the outermost one
back into a ``Sampler`` the provider accepts.
"""

from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.configuration._common import (
    _map_compression,
    _matches_glob,
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
    ExperimentalComposableRuleBasedSampler as RuleBasedSamplerConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalComposableRuleBasedSamplerRule as RuleBasedSamplerRuleConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalComposableSampler as ComposableSamplerConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalOtlpFileExporter as ExperimentalOtlpFileExporterConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalTracerConfig as TracerConfigConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalTracerConfigurator as TracerConfiguratorConfig,
)
from opentelemetry.configuration.models import (
    IdGenerator as IdGeneratorConfig,
)
from opentelemetry.configuration.models import (
    OtlpGrpcExporter as OtlpGrpcExporterConfig,
)
from opentelemetry.configuration.models import (
    OtlpHttpExporter as OtlpHttpExporterConfig,
)
from opentelemetry.configuration.models import (
    ParentBasedSampler as ParentBasedSamplerConfig,
)
from opentelemetry.configuration.models import (
    Sampler as SamplerConfig,
)
from opentelemetry.configuration.models import (
    SpanExporter as SpanExporterConfig,
)
from opentelemetry.configuration.models import (
    SpanLimits as SpanLimitsConfig,
)
from opentelemetry.configuration.models import (
    SpanProcessor as SpanProcessorConfig,
)
from opentelemetry.configuration.models import (
    TracerProvider as TracerProviderConfig,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import (
    _DEFAULT_OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT,
    _DEFAULT_OTEL_LINK_ATTRIBUTE_COUNT_LIMIT,
    _DEFAULT_OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT,
    _DEFAULT_OTEL_SPAN_EVENT_COUNT_LIMIT,
    _DEFAULT_OTEL_SPAN_LINK_COUNT_LIMIT,
    SpanLimits,
    TracerProvider,
    _RuleBasedTracerConfigurator,
    _TracerConfig,
)
from opentelemetry.sdk.trace._sampling_experimental import (
    ComposableSampler,
    composable_always_off,
    composable_always_on,
    composable_parent_threshold,
    composable_rule_based,
    composable_traceid_ratio_based,
    composite_sampler,
)
from opentelemetry.sdk.trace._sampling_experimental._rule_based import (
    AllPredicate,
    AlwaysMatchPredicate,
    AttributePatternsPredicate,
    AttributeValuesPredicate,
    ParentPredicate,
    PredicateT,
    RulesT,
    SpanKindPredicate,
)
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.id_generator import IdGenerator, RandomIdGenerator
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    ParentBased,
    Sampler,
    TraceIdRatioBased,
)
from opentelemetry.trace import SpanKind as TraceSpanKind

_logger = logging.getLogger(__name__)

# Default sampler per the OTel spec: parent_based with always_on root.
_DEFAULT_SAMPLER = ParentBased(root=ALWAYS_ON)


def _create_otlp_http_span_exporter(
    config: OtlpHttpExporterConfig,
) -> SpanExporter:
    """Create an OTLP HTTP span exporter from config.

    The exporter class comes from a different distribution for each
    encoding, so both are imported inside the function and a missing one is
    reported as a configuration error instead of an import failure at module
    load.

    Args:
        config: The ``otlp_http`` block of a span exporter configuration.
            Its ``timeout``, in milliseconds, is converted to the seconds
            the exporter expects. Its ``tls`` block is not read at all, so
            setting ``ca_file``, ``cert_file`` or ``key_file`` has no
            effect.

    Returns:
        An ``OTLPSpanExporter`` from the protobuf or the JSON distribution,
        according to ``config.encoding``. Any field left absent is passed as
        ``None``, which lets the exporter fall back to its own default or to
        ``OTEL_EXPORTER_OTLP_*``.

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
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # noqa: PLC0415
                    OTLPSpanExporter,
                )
            except ImportError as exc:
                raise MissingDependencyError(
                    package="opentelemetry-exporter-otlp-proto-http",
                    feature="otlp_http span exporter",
                ) from exc

            compression = _map_compression(config.compression, Compression, allow_deflate=True)
            return OTLPSpanExporter(
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
                from opentelemetry.exporter.otlp.json.http.trace_exporter import (  # noqa: PLC0415
                    OTLPSpanExporter as JsonOTLPSpanExporter,
                )
            except ImportError as exc:
                raise MissingDependencyError(
                    package="opentelemetry-exporter-otlp-json-http",
                    feature="otlp_http JSON span exporter",
                ) from exc

            compression = _map_compression(config.compression, JsonCompression, allow_deflate=True)
            return JsonOTLPSpanExporter(
                endpoint=config.endpoint,
                headers=headers,
                timeout=timeout,
                compression=compression,
            )
        case _:
            raise ConfigurationError(
                f"Unsupported OTLP HTTP encoding '{config.encoding}'. Supported values: protobuf, json."
            )


def _create_otlp_grpc_span_exporter(
    config: OtlpGrpcExporterConfig,
) -> SpanExporter:
    """Create an OTLP gRPC span exporter from config.

    Args:
        config: The ``otlp_grpc`` block of a span exporter configuration.
            Its ``timeout``, in milliseconds, is converted to the seconds
            the exporter expects. Its ``tls`` block is not read at all, so a
            configuration that sets ``ca_file``, ``cert_file``, ``key_file``
            or ``insecure`` gets no effect from them. The exporter
            decides for itself: ``OTEL_EXPORTER_OTLP_TRACES_INSECURE``, then
            ``OTEL_EXPORTER_OTLP_INSECURE``, then the endpoint scheme for
            the channel, and the
            ``OTEL_EXPORTER_OTLP_[TRACES_]CERTIFICATE``, ``..._CLIENT_KEY``
            and ``..._CLIENT_CERTIFICATE`` family for the three file
            fields.

    Returns:
        An ``OTLPSpanExporter`` from the gRPC distribution.

    Raises:
        MissingDependencyError: If ``opentelemetry-exporter-otlp-proto-grpc``
            or ``grpc`` is not installed.
        ConfigurationError: If ``config.compression`` is anything other than
            gzip or none. Deflate is rejected here, unlike on the HTTP path.
    """
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        import grpc  # noqa: PLC0415  # type: ignore[import-untyped]

        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: PLC0415  # type: ignore[import-untyped]
            OTLPSpanExporter,
        )
    except ImportError as exc:
        raise MissingDependencyError(
            package="opentelemetry-exporter-otlp-proto-grpc",
            feature="otlp_grpc span exporter",
        ) from exc

    compression = _map_compression(config.compression, grpc.Compression)
    headers = _parse_headers(config.headers, config.headers_list)
    timeout = (config.timeout / 1000.0) if config.timeout is not None else None

    return OTLPSpanExporter(  # type: ignore[return-value]
        endpoint=config.endpoint,
        headers=headers,
        timeout=timeout,
        compression=compression,  # type: ignore[arg-type]
    )


def _create_otlp_file_development_span_exporter(
    config: ExperimentalOtlpFileExporterConfig,
) -> SpanExporter:
    """Create an OTLP file (JSON Lines) span exporter from config.

    Args:
        config: The ``otlp_file/development`` block of a span exporter
            configuration, whose only field is ``output_stream``.

    Returns:
        A ``FileSpanExporter`` writing to the configured path, or one
        writing to standard output when ``output_stream`` is absent or
        ``"stdout"``.

    Raises:
        ConfigurationError: If ``opentelemetry-exporter-otlp-json-file`` is
            not installed, or if ``output_stream`` is neither ``"stdout"``
            nor a local ``file://`` URI with an absolute path. The missing
            distribution is reported as a plain ConfigurationError here,
            unlike the OTLP HTTP and gRPC exporters, which raise
            MissingDependencyError.
    """
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        from opentelemetry.exporter.otlp.json.file.trace_exporter import (  # noqa: PLC0415  # type: ignore[import-untyped]
            FileSpanExporter,
        )
    except ImportError as exc:
        raise ConfigurationError(
            "otlp_file_development span exporter requires 'opentelemetry-exporter-otlp-json-file'. "
            "Install it with: pip install opentelemetry-exporter-otlp-json-file"
        ) from exc

    path = _parse_otlp_file_output_stream(config.output_stream)
    return FileSpanExporter(path) if path is not None else FileSpanExporter()


def _create_span_exporter(config: SpanExporterConfig) -> SpanExporter:
    """Create a span exporter from config.

    Known exporter types are checked via typed fields on the SpanExporter
    dataclass. Unknown exporter names captured in additional_properties
    by the @_additional_properties decorator are loaded via the
    ``opentelemetry_traces_exporter`` entry point group.

    The schema permits one exporter per block. If several fields are set,
    which is possible only when schema validation was bypassed, the first
    match in the order otlp_http, otlp_grpc, console, otlp_file_development
    wins and the rest are ignored.

    Args:
        config: One ``exporter`` block from a span processor configuration.

    Returns:
        The exporter the block selects. A plugin exporter is constructed
        with its nested configuration mapping splatted as keyword
        arguments, so a plugin that does not accept them raises ``TypeError``.

    Raises:
        ConfigurationError: If the block selects no exporter at all, or if
            the selected one cannot be built.
        MissingDependencyError: If the selected exporter's distribution is
            not installed.
        TypeError: If a plugin exporter's constructor does not accept the
            keys of the nested configuration mapping splatted into it.
    """
    match config:
        case SpanExporterConfig(otlp_http=exporter_config) if exporter_config is not None:
            return _create_otlp_http_span_exporter(exporter_config)
        case SpanExporterConfig(otlp_grpc=exporter_config) if exporter_config is not None:
            return _create_otlp_grpc_span_exporter(exporter_config)
        case SpanExporterConfig(console=exporter_config) if exporter_config is not None:
            return ConsoleSpanExporter()
        case SpanExporterConfig(otlp_file_development=exporter_config) if exporter_config is not None:
            return _create_otlp_file_development_span_exporter(exporter_config)
        case SpanExporterConfig(additional_properties=additional_properties) if additional_properties:
            name, plugin_config = next(iter(additional_properties.items()))
            return load_entry_point("opentelemetry_traces_exporter", name)(**(plugin_config or {}))
        case _:
            raise ConfigurationError(
                "No exporter type specified in span exporter config. "
                "Supported types: otlp_http, otlp_grpc, console, otlp_file_development."
            )


def _create_span_processor(
    config: SpanProcessorConfig,
) -> BatchSpanProcessor | SimpleSpanProcessor:
    """Create a span processor from config.

    Unlike the log record batch processor, the batch fields are passed
    through as they are, including ``None`` for an absent one, so the SDK
    reads ``OTEL_BSP_SCHEDULE_DELAY`` and its siblings for whatever the
    configuration file leaves out.

    Args:
        config: One entry of the ``processors`` list. Exactly one of its
            ``batch`` and ``simple`` fields is expected to be set; ``batch``
            is checked first.

    Returns:
        A ``BatchSpanProcessor`` or a ``SimpleSpanProcessor`` wrapping the
        exporter the block names.

    Raises:
        ConfigurationError: If neither ``batch`` nor ``simple`` is set, or
            if the exporter cannot be built.
        MissingDependencyError: If the selected exporter's distribution is
            not installed.
    """
    if config.batch is not None:
        exporter = _create_span_exporter(config.batch.exporter)
        return BatchSpanProcessor(
            exporter,
            max_queue_size=config.batch.max_queue_size,
            schedule_delay_millis=config.batch.schedule_delay,
            max_export_batch_size=config.batch.max_export_batch_size,
            export_timeout_millis=config.batch.export_timeout,
        )
    if config.simple is not None:
        return SimpleSpanProcessor(_create_span_exporter(config.simple.exporter))
    raise ConfigurationError("No processor type specified in span processor config. Supported types: batch, simple.")


def _create_experimental_composable_sampler(
    config: ComposableSamplerConfig,
) -> ComposableSampler:
    """Create an experimental composable sampler from config.

    A composable sampler reports a sampling threshold rather than a
    decision, which is what lets ``parent_threshold`` and ``rule_based``
    nest other composable samplers inside themselves. This function recurses
    for both of those, so the whole tree under ``composite/development`` is
    built by one call on its root.

    Args:
        config: A composable sampler block. Exactly one of its fields is
            expected to be set; they are checked in the order always_on,
            always_off, parent_threshold, probability, rule_based.

    Returns:
        The composable sampler the block selects. ``probability`` with no
        ``ratio`` samples everything, matching the ratio 1.0.

    Raises:
        ConfigurationError: If the block selects none of the five known
            types. A plugin composable sampler is not supported, so an
            entry point name reaches this branch and fails. The message
            carries the repr of the block.
    """
    if config.always_on is not None:
        return composable_always_on()
    if config.always_off is not None:
        return composable_always_off()
    if config.parent_threshold is not None:
        return composable_parent_threshold(_create_experimental_composable_sampler(config.parent_threshold.root))
    if config.probability is not None:
        ratio = config.probability.ratio
        return composable_traceid_ratio_based(ratio if ratio is not None else 1.0)
    if config.rule_based is not None:
        return composable_rule_based(_create_rule_based_sampler_rules(config.rule_based))
    raise ConfigurationError(
        f"Unknown or unsupported experimental composable sampler type in config: {config!r}. "
        "Supported types: always_on, always_off, parent_threshold, probability, rule_based."
    )


def _create_rule_based_sampler_rules(
    config: RuleBasedSamplerConfig,
) -> RulesT:
    """Build the (predicate, sampler) rule list of a rule-based sampler.

    Args:
        config: The ``rule_based`` block, whose ``rules`` field holds the
            rules in the order they will be evaluated.

    Returns:
        One pair per rule, in the configured order, so the first rule whose
        predicate matches decides. An absent ``rules`` field gives an empty
        list, which makes the sampler drop every span, since no rule can
        match.

    Raises:
        ConfigurationError: If any rule's nested sampler block selects no
            known composable sampler type.
    """
    if config.rules is None:
        return []
    return [
        (
            _create_rule_based_sampler_rule_predicate(rule),
            _create_experimental_composable_sampler(rule.sampler),
        )
        for rule in config.rules
    ]


def _create_rule_based_sampler_rule_predicate(
    config: RuleBasedSamplerRuleConfig,
) -> PredicateT:
    """Build the predicate of one rule-based sampler rule.

    A rule may carry several conditions. They are combined with "and", so a
    span has to satisfy every one of them for the rule to apply.

    Args:
        config: One entry of the ``rules`` list. Its ``attribute_values``,
            ``attribute_patterns``, ``span_kinds`` and ``parent`` fields are
            each optional and each contribute one condition.

    Returns:
        The single condition when the rule carries exactly one, an "and"
        over them when it carries several, and a predicate matching every
        span when it carries none. The attribute pattern condition uses the
        configuration schema's wildcard syntax rather than ``fnmatch``.
    """
    predicates: list[PredicateT] = []
    if config.attribute_values is not None:
        predicates.append(
            AttributeValuesPredicate(
                config.attribute_values.key,
                config.attribute_values.values,
            )
        )
    if config.attribute_patterns is not None:
        predicates.append(
            AttributePatternsPredicate(
                config.attribute_patterns.key,
                config.attribute_patterns.included,
                config.attribute_patterns.excluded,
                matcher=_matches_glob,
            )
        )
    if config.span_kinds is not None:
        predicates.append(
            SpanKindPredicate([TraceSpanKind[span_kind.value.upper()] for span_kind in config.span_kinds])
        )
    if config.parent is not None:
        predicates.append(ParentPredicate([parent.value for parent in config.parent]))
    if not predicates:
        return AlwaysMatchPredicate()
    if len(predicates) == 1:
        return predicates[0]
    return AllPredicate(predicates)


def _create_sampler(config: SamplerConfig) -> Sampler:
    """Create a sampler from config.

    Built-in sampler types are checked via typed fields on the Sampler
    dataclass. User-defined sampler names captured in additional_properties
    by the @_additional_properties decorator are loaded via the
    ``opentelemetry_sampler`` entry point group.

    Args:
        config: A sampler block, from the provider's ``sampler`` field or
            from one of the delegate fields of a parent-based sampler. The
            built-in fields are checked in the order always_on, always_off,
            trace_id_ratio_based, composite_development, parent_based.

    Returns:
        The sampler the block selects. ``trace_id_ratio_based`` with no
        ``ratio`` samples everything, matching the ratio 1.0. A plugin
        sampler is constructed with no arguments, so the nested
        configuration mapping a user wrote under its name is discarded
        rather than passed to it.

    Raises:
        ConfigurationError: If the block selects no sampler type this
            function implements, in which case the message carries the repr
            of the block. The schema declares two sampler fields that are
            not implemented here, ``probability/development`` and
            ``jaeger_remote/development``, so a block that sets either one
            reaches that same error. It is raised as well when a plugin
            sampler name is not registered in the entry point group, in
            which case ``load_entry_point`` raises and the message names the
            plugin and the group instead.
    """
    if config.always_on is not None:
        return ALWAYS_ON
    if config.always_off is not None:
        return ALWAYS_OFF
    if config.trace_id_ratio_based is not None:
        ratio = config.trace_id_ratio_based.ratio
        return TraceIdRatioBased(ratio if ratio is not None else 1.0)
    if config.composite_development is not None:
        return composite_sampler(_create_experimental_composable_sampler(config.composite_development))
    if config.parent_based is not None:
        return _create_parent_based_sampler(config.parent_based)
    if config.additional_properties:
        name = next(iter(config.additional_properties))
        return load_entry_point("opentelemetry_sampler", name)()
    raise ConfigurationError(
        f"Unsupported sampler type in config: {config!r}. "
        "Supported types: always_on, always_off, composite_development, "
        "trace_id_ratio_based, parent_based."
    )


def _create_id_generator(config: IdGeneratorConfig) -> IdGenerator:
    """Create an IdGenerator from config.

    Built-in ``random`` resolves to ``RandomIdGenerator``; unknown names
    load from the ``opentelemetry_id_generator`` entry point group (the
    same group ``OTEL_PYTHON_ID_GENERATOR`` uses today).

    Args:
        config: The ``id_generator`` block of the tracer provider
            configuration.

    Returns:
        A ``RandomIdGenerator`` for the built-in name, or an instance of the
        plugin class constructed with its nested configuration mapping
        splatted as keyword arguments.

    Raises:
        ConfigurationError: If the block names neither ``random`` nor a
            plugin, or if the plugin name is not registered.
    """
    if config.random is not None:
        return RandomIdGenerator()
    if config.additional_properties:
        name, plugin_config = next(iter(config.additional_properties.items()))
        return load_entry_point("opentelemetry_id_generator", name)(**(plugin_config or {}))
    raise ConfigurationError("No id_generator type specified in config. Supported built-in types: random.")


def _create_parent_based_sampler(config: ParentBasedSamplerConfig) -> Sampler:
    """Create a ParentBased sampler from config, applying SDK defaults for absent delegates.

    Args:
        config: The ``parent_based`` block. Its ``root`` and its four
            delegate fields are each optional.

    Returns:
        A ``ParentBased`` sampler. An absent ``root`` becomes always-on. An
        absent delegate is not passed at all, so it keeps the SDK's own
        default: follow the parent's sampled flag.

    Raises:
        ConfigurationError: If the root or any delegate block selects no
            sampler. Nesting is unbounded, so a parent-based sampler may
            carry another one as a delegate.
    """
    root = _create_sampler(config.root) if config.root is not None else ALWAYS_ON
    kwargs: dict = {"root": root}
    if config.remote_parent_sampled is not None:
        kwargs["remote_parent_sampled"] = _create_sampler(config.remote_parent_sampled)
    if config.remote_parent_not_sampled is not None:
        kwargs["remote_parent_not_sampled"] = _create_sampler(config.remote_parent_not_sampled)
    if config.local_parent_sampled is not None:
        kwargs["local_parent_sampled"] = _create_sampler(config.local_parent_sampled)
    if config.local_parent_not_sampled is not None:
        kwargs["local_parent_not_sampled"] = _create_sampler(config.local_parent_not_sampled)
    return ParentBased(**kwargs)


def _create_span_limits(
    config: SpanLimitsConfig,
    global_limits: AttributeLimits | None = None,
) -> SpanLimits:
    """Create SpanLimits from config.

    Absent fields fall back to global_limits (if provided), then to OTel spec
    defaults (128 for counts, unlimited for lengths).
    Explicit values suppress env-var reading — matching Java SDK behavior.

    Only the two attribute limits fall back to ``global_limits``. The event
    and link limits have no counterpart at the top level, so they take the
    specification default when the span limits block leaves them out.

    Args:
        config: The ``limits`` block of the tracer provider configuration.
            ``create_tracer_provider`` passes an empty block rather than
            ``None`` when the configuration has no limits section, so every
            field falls back.
        global_limits: The top-level ``attribute_limits`` block, consulted
            only for a field the span limits leave absent. ``None`` means
            the configuration has no top-level block.

    Returns:
        ``SpanLimits`` with seven of its eight parameters set, so the SDK
        reads none of the ``OTEL_SPAN_*`` environment variables. The
        value-length limit is applied to both the generic and the
        span-specific field, which is what makes it reach span attributes.
        The generic ``max_attributes`` is the one parameter not passed, so
        ``OTEL_ATTRIBUTE_COUNT_LIMIT`` is still read for it, and a value
        that is not a non-negative integer raises ``ValueError`` from the
        ``SpanLimits`` constructor.
    """
    attribute_count_limit = config.attribute_count_limit
    if attribute_count_limit is None and global_limits is not None:
        attribute_count_limit = global_limits.attribute_count_limit

    attribute_value_length_limit = config.attribute_value_length_limit
    if attribute_value_length_limit is None and global_limits is not None:
        attribute_value_length_limit = global_limits.attribute_value_length_limit

    return SpanLimits(
        max_span_attributes=(
            attribute_count_limit if attribute_count_limit is not None else _DEFAULT_OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT
        ),
        max_events=(
            config.event_count_limit if config.event_count_limit is not None else _DEFAULT_OTEL_SPAN_EVENT_COUNT_LIMIT
        ),
        max_links=(
            config.link_count_limit if config.link_count_limit is not None else _DEFAULT_OTEL_SPAN_LINK_COUNT_LIMIT
        ),
        max_event_attributes=(
            config.event_attribute_count_limit
            if config.event_attribute_count_limit is not None
            else _DEFAULT_OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT
        ),
        max_link_attributes=(
            config.link_attribute_count_limit
            if config.link_attribute_count_limit is not None
            else _DEFAULT_OTEL_LINK_ATTRIBUTE_COUNT_LIMIT
        ),
        max_attribute_length=(
            attribute_value_length_limit if attribute_value_length_limit is not None else SpanLimits.UNSET
        ),
        max_span_attribute_length=(
            attribute_value_length_limit if attribute_value_length_limit is not None else SpanLimits.UNSET
        ),
    )


def _to_tracer_config(config: TracerConfigConfig | None) -> _TracerConfig:
    """Map an experimental per-tracer config to an SDK ``_TracerConfig``.

    Only ``enabled`` is honored — it is the sole field the SDK
    ``_TracerConfig`` exposes. An absent ``enabled`` leaves the tracer enabled.

    Args:
        config: The ``config`` field of one tracer matcher, or the
            ``default_config`` of the configurator. ``None`` means the field
            was absent.

    Returns:
        A ``_TracerConfig``. The SDK default, which is enabled, for a
        ``None`` config and for one whose ``enabled`` is absent.
    """
    if config is None or config.enabled is None:
        return _TracerConfig.default()
    return _TracerConfig(is_enabled=config.enabled)


def _create_tracer_configurator(
    config: TracerConfiguratorConfig,
) -> _RuleBasedTracerConfigurator:
    """Build a rule-based tracer configurator from experimental config.

    Each entry in ``tracers`` maps an instrumentation-scope name glob to a
    per-tracer config; ``default_config`` applies to scopes matching no glob.
    Rules are evaluated in order, so earlier entries take precedence.

    Args:
        config: The ``tracer_configurator/development`` block of the tracer
            provider configuration.

    Returns:
        A ``_RuleBasedTracerConfigurator``. An absent ``tracers`` field
        gives no rules, so every tracer takes ``default_config``.
    """
    rules = [
        (
            _scope_name_matches_glob(matcher.name),
            _to_tracer_config(matcher.config),
        )
        for matcher in (config.tracers or [])
    ]
    return _RuleBasedTracerConfigurator(
        rules=rules,
        default_config=_to_tracer_config(config.default_config),
    )


def create_tracer_provider(
    config: TracerProviderConfig | None,
    resource: Resource | None = None,
    global_attribute_limits: AttributeLimits | None = None,
) -> TracerProvider:
    """Create an SDK TracerProvider from declarative config.

    Does NOT read OTEL_TRACES_SAMPLER, OTEL_SPAN_*_LIMIT, or any other env vars
    for values that are explicitly controlled by the config. Absent config values
    use OTel spec defaults (not env vars), matching Java SDK behavior.

    Args:
        config: TracerProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.
        global_attribute_limits: Top-level attribute_limits from the root config,
            used as a fallback when per-signal limits are not specified.

    Returns:
        A configured TracerProvider.
    """
    sampler = _create_sampler(config.sampler) if config is not None and config.sampler is not None else _DEFAULT_SAMPLER
    id_generator = (
        _create_id_generator(config.id_generator) if config is not None and config.id_generator is not None else None
    )
    if config is not None and config.limits is not None:
        limits = config.limits

    else:
        limits = SpanLimitsConfig()

    span_limits = _create_span_limits(limits, global_attribute_limits)

    tracer_configurator = (
        _create_tracer_configurator(config.tracer_configurator_development)
        if config is not None and config.tracer_configurator_development is not None
        else None
    )

    provider = TracerProvider(
        resource=resource,
        sampler=sampler,
        span_limits=span_limits,
        id_generator=id_generator,
        _tracer_configurator=tracer_configurator,
    )

    if config is not None:
        for proc_config in config.processors:
            provider.add_span_processor(_create_span_processor(proc_config))

    return provider


def configure_tracer_provider(
    config: TracerProviderConfig | None,
    resource: Resource | None = None,
    global_attribute_limits: AttributeLimits | None = None,
) -> None:
    """Configure the global TracerProvider from declarative config.

    When config is None (tracer_provider section absent from config file),
    the global is not set — matching Java/JS SDK behavior and the spec's
    "a noop tracer provider is used" default.

    Args:
        config: TracerProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.
        global_attribute_limits: Top-level attribute_limits from the root config,
            used as a fallback when per-signal limits are not specified.
    """
    if config is None:
        return
    trace.set_tracer_provider(create_tracer_provider(config, resource, global_attribute_limits))
