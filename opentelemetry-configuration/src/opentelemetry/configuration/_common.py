# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Helpers shared by the per-signal configuration factories.

Four kinds of helper live here. The glob matchers implement the
restricted wildcard syntax the configuration schema uses, which is not
``fnmatch`` and not a regular expression. ``load_entry_point`` turns a
component name from the configuration file into the class an entry
point group registers under that name, and ``_resolve_component`` goes
one step further and returns a constructed component, built-in or
plugin. Of those two, only ``load_entry_point`` is called from anywhere
in the package; the glob matchers, ``_additional_properties`` and the
value translators all have callers. ``_additional_properties`` is the decorator the code generator
puts on a model that accepts a plugin component name; it rewrites the
generated ``__init__`` so an undeclared key is captured rather than
rejected. The value translators turn one configuration field into the
shape an SDK exporter constructor expects: a headers dict, a
``Compression`` enum member, or a file path.

The component resolvers and the value translators raise
``ConfigurationError`` on bad input rather than falling back to a
default, because a value that reached them came from a configuration
file the user wrote on purpose. ``_parse_headers`` is the exception: a
malformed pair is dropped with a warning so that one typo does not
discard the rest of the header set.

``_resolve_component`` has no caller in the package. Each signal factory
open-codes the same dispatch with a ``match`` statement instead, so a
reader following a component name from the configuration file should
read one of those rather than this.
"""

from __future__ import annotations

import dataclasses
import inspect
import logging
from collections.abc import Callable
from fnmatch import fnmatchcase
from typing import Any, Protocol, TypeVar
from urllib.parse import urlparse

from opentelemetry.configuration._exceptions import ConfigurationError
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util._importlib_metadata import entry_points

_logger = logging.getLogger(__name__)

_CompressionT = TypeVar("_CompressionT")


def _matches_glob(value: str, pattern: str) -> bool:
    """Match exactly or using the configuration schema's case-sensitive wildcards.

    Only ``*`` (zero or more characters) and ``?`` (one character) are
    wildcards. All other characters, including brackets and backslashes,
    are literal.

    The exact-equality test runs first, so a pattern that is itself made of
    literal wildcard characters still matches the identical value.

    Args:
        value: The string being tested, for example an instrumentation scope
            name or a resource attribute key.
        pattern: The pattern from the configuration file.

    Returns:
        ``True`` when ``value`` equals ``pattern`` or the wildcards in
        ``pattern`` cover the whole of ``value``.
    """
    # Escape opening brackets to disable fnmatch's character classes while
    # retaining its wildcard implementation and compiled-pattern cache.
    return value == pattern or fnmatchcase(value, pattern.replace("[", "[[]"))


def _scope_name_matches_glob(pattern: str) -> Callable[[InstrumentationScope], bool]:
    """Match scope names using the configuration schema's wildcard semantics.

    The tracer, meter and logger configurators each hold a list of
    (predicate, config) rules, where the predicate takes a whole
    ``InstrumentationScope``. This builds such a predicate from a pattern
    that applies to the scope name alone, ignoring the scope's version,
    schema URL and attributes.

    Args:
        pattern: The scope-name pattern from the configuration file, with
            the wildcard syntax ``_matches_glob`` implements.

    Returns:
        A predicate that takes an ``InstrumentationScope`` and reports
        whether its name matches ``pattern``.
    """

    def matches(scope: InstrumentationScope) -> bool:
        """Report whether the name of ``scope`` matches the captured pattern.

        Args:
            scope: The instrumentation scope a tracer, meter or logger was
                created with. Only its ``name`` is read.

        Returns:
            ``True`` when the scope name matches ``pattern``.
        """
        return _matches_glob(scope.name, pattern)

    return matches


def _additional_properties(cls):
    """Decorator for dataclasses whose JSON Schema sets additionalProperties.

    Wraps the dataclass-generated ``__init__`` so that extra keyword
    arguments are captured into an ``additional_properties`` instance
    attribute instead of raising ``TypeError``.  This lets user-defined
    component names flow through the config pipeline without modifying
    the codegen output for built-in fields.

    Applied automatically by ``opentelemetry-configuration/codegen/dataclass.jinja2``
    when ``datamodel-codegen`` puts either ``additionalPropertiesType`` or a
    non-false ``additionalProperties`` in the template context, which happens
    for every schema type that accepts a plugin component name.

    The wrapped ``__init__`` accepts only keyword arguments, so a positional
    call that the generated ``__init__`` would have taken raises ``TypeError``
    once the decorator is applied.

    Args:
        cls: The generated dataclass to wrap. It is modified in place.

    Returns:
        ``cls`` itself, so the result can be used as a decorator.
    """
    original_init = cls.__init__
    original_sig = inspect.signature(original_init)
    known_fields = frozenset(f.name for f in dataclasses.fields(cls) if f.init)

    def _init(self, **kwargs):
        """Split the keyword arguments into declared fields and extras.

        Args:
            kwargs: Every keyword argument the caller passed. Names that are
                init fields of the dataclass go to the generated
                ``__init__``; all the others become the
                ``additional_properties`` dict.
        """
        known = {k: v for k, v in kwargs.items() if k in known_fields}
        extra = {k: v for k, v in kwargs.items() if k not in known_fields}
        original_init(self, **known)
        self.additional_properties = extra

    # Preserve the original parameter list for IDE autocompletion and
    # inspect.signature(), adding **kwargs to signal extras are accepted.
    # setattr used because pyright rejects direct __signature__ assignment.
    params = list(original_sig.parameters.values())
    params.append(inspect.Parameter("kwargs", inspect.Parameter.VAR_KEYWORD))
    setattr(_init, "__signature__", original_sig.replace(parameters=params))  # noqa: B010

    cls.__init__ = _init
    return cls


def load_entry_point(group: str, name: str) -> type:
    """Load a plugin class from an entry point group by name.

    Nothing is instantiated here. Each caller constructs the class with
    whatever arguments its own configuration block carries, which differs by
    component type: a sampler takes none, a plugin exporter takes the nested
    configuration mapping splatted as keyword arguments.

    When several distributions register the same name in the same group, the
    first entry point ``importlib.metadata`` reports is used and the rest are
    ignored silently.

    Args:
        group: Entry point group to search, for example
            ``"opentelemetry_traces_exporter"``.
        name: Entry point name, taken verbatim from the key the user wrote in
            the configuration file.

    Returns:
        The object the entry point resolves to. It is annotated as a class
        because every group this package reads registers classes, and it is
        returned unverified, so a group that registers a function returns
        that function.

    Raises:
        ConfigurationError: If no entry point in ``group`` is named ``name``,
            in which case the message names the plugin and tells the user to
            install the package that provides it. Also if loading a
            registered entry point raises, for instance when its module
            fails to import, in which case the message names the plugin and
            quotes the underlying exception instead, with no install hint.
    """
    try:
        ep = next(iter(entry_points(group=group, name=name)), None)
        if ep is None:
            raise ConfigurationError(
                f"Plugin '{name}' not found in group '{group}'. "
                "Make sure the package providing this plugin is installed."
            )
        return ep.load()
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(f"Failed to load plugin '{name}' from group '{group}': {exc}") from exc


class _ComponentConfig(Protocol):
    """Protocol for config dataclasses decorated with @_additional_properties.

    Values in ``additional_properties`` are nested config dicts (suitable
    for ``**kwargs`` splatting to the user-defined component class) or
    ``None`` (when the YAML uses ``my_plugin:`` or ``my_plugin: null``).

    The generated models declare ``additional_properties`` as an instance
    field to match the decorator's runtime assignment.
    """

    additional_properties: dict[str, dict[str, Any] | None]


def _resolve_component(
    config: _ComponentConfig,
    registry: dict[str, Callable[[Any], Any]],
    entry_point_group: str,
    component_type: str,
) -> Any:
    """Resolve a config dataclass to a component instance.

    Checks built-in factories in ``registry`` first (by matching typed
    field names on ``config``), then falls back to entry point loading
    for plugin components found in ``config.additional_properties``.

    The JSON schema enforces exactly one component per config block
    (``minProperties: 1, maxProperties: 1``). If multiple typed fields or
    ``additional_properties`` entries are set (e.g. when schema validation
    is bypassed), the first registry match wins.

    Nothing in the package calls this. Each signal factory open-codes the
    same dispatch with a ``match`` statement, so the only callers today are
    in ``opentelemetry-configuration/tests/test_common.py``.

    Args:
        config: A dataclass with ``additional_properties`` (from the
            ``@_additional_properties`` decorator).
        registry: Mapping of built-in component names to factory
            callables. Each factory receives the field value from config.
        entry_point_group: The entry point group name for plugin loading.
        component_type: Human-readable name for error messages
            (e.g. "span exporter").

    Returns:
        The resolved component instance.

    Raises:
        ConfigurationError: If no component type is specified in config.
    """
    for name, factory in registry.items():
        value = getattr(config, name, None)
        if value is not None:
            return factory(value)
    if config.additional_properties:
        name, plugin_config = next(iter(config.additional_properties.items()))
        return load_entry_point(entry_point_group, name)(**(plugin_config or {}))
    raise ConfigurationError(f"No {component_type} type specified in config.")


def _parse_headers(
    headers: list | None,
    headers_list: str | None,
) -> dict[str, str] | None:
    """Merge headers struct and headers_list into a dict.

    An entry of ``headers_list`` with no ``=`` is dropped with a warning
    rather than raising, so one malformed pair does not discard the rest of
    the header set. An entry whose value is absent or empty becomes the empty
    string, because the SDK exporters expect ``dict[str, str]`` and reject
    ``None``.

    Neither the name nor the value is stripped of quotes or URL-decoded,
    unlike the resource ``attributes_list`` handling in
    ``opentelemetry.configuration._resource``, which does unquote values.

    Args:
        headers: The ``headers`` field of an exporter configuration block, a
            list of name/value pairs. Each element is either a
            ``NameStringValuePair`` dataclass or, when schema conversion was
            bypassed, a plain dict with ``name`` and ``value`` keys. ``None``
            means the field was absent.
        headers_list: The ``headers_list`` field, one string of
            comma-separated ``name=value`` pairs. ``None`` means the field
            was absent.

    Returns:
        The merged headers, with an entry from ``headers`` overwriting one of
        the same name from ``headers_list``. ``None`` when both arguments are
        ``None``, and an empty dict when a field was present but contributed
        no usable pair.

        Neither result suppresses ``OTEL_EXPORTER_OTLP_HEADERS``. The gRPC
        exporter falls back to the variable whenever what it is given is
        falsy, which an empty dict is, and the HTTP exporters always read
        the variable first and then overlay what they are given, so a
        header set only in the environment is sent either way.
    """
    if headers is None and headers_list is None:
        return None
    result: dict[str, str] = {}
    if headers_list:
        for item in headers_list.split(","):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                result[key.strip()] = value.strip()
            elif item:
                _logger.warning(
                    "Invalid header pair in headers_list (missing '='): %s",
                    item,
                )
    if headers:
        for pair in headers:
            if isinstance(pair, dict):
                result[pair["name"]] = pair.get("value") or ""
            else:
                result[pair.name] = pair.value or ""
    return result


def _map_compression(
    value: str | None,
    compression_enum: type[_CompressionT],
    *,
    allow_deflate: bool = False,
) -> _CompressionT | None:
    """Map a compression string to the given Compression enum value.

    Each OTLP exporter package defines its own ``Compression`` enum, and the
    member names differ between them: ``Gzip`` in
    ``opentelemetry.exporter.otlp.proto.http`` and in ``grpc``, and ``GZIP``
    in ``opentelemetry.exporter.otlp.common.http``, which is the enum the
    JSON encoding of the OTLP HTTP exporters uses. The member is therefore
    looked up by trying both spellings rather than imported.

    Args:
        value: The ``compression`` field of an exporter configuration block.
            ``None`` means the field was absent.
        compression_enum: The ``Compression`` enum of the exporter package
            that will receive the result.
        allow_deflate: Whether ``"deflate"`` is an accepted value. The HTTP
            exporter factories pass ``True`` and the gRPC ones leave it
            ``False``, so a configuration file asking for deflate over gRPC
            fails rather than silently sending gzip. That is this package's
            choice rather than a limit of the exporter: ``grpc.Compression``
            carries a ``Deflate`` member, which the ``supports_deflate``
            test below finds.

    Returns:
        The enum member for ``value``, or ``None`` when ``value`` is ``None``
        or ``"none"``. The two cases are indistinguishable to the exporter,
        which reads ``None`` as "consult the environment", so an explicit
        ``compression: none`` disables compression unless
        ``OTEL_EXPORTER_OTLP_COMPRESSION`` or its signal-specific variant
        names one.

    Raises:
        ConfigurationError: If ``value`` is anything else, including
            ``"deflate"`` when ``allow_deflate`` is ``False`` or when
            ``compression_enum`` has no deflate member. The message lists the
            values that this call would have accepted.
    """
    if value is None:
        return None

    value_lower = value.lower()
    supports_deflate = hasattr(compression_enum, "Deflate") or hasattr(compression_enum, "DEFLATE")

    if value_lower == "none":
        return None
    if value_lower == "gzip":
        for member_name in ("Gzip", "GZIP"):
            if member := getattr(compression_enum, member_name, None):
                return member
    if value_lower == "deflate" and allow_deflate and supports_deflate:
        for member_name in ("Deflate", "DEFLATE"):
            if member := getattr(compression_enum, member_name, None):
                return member

    supported_values = ["'gzip'", "'none'"]
    if allow_deflate and supports_deflate:
        supported_values.insert(1, "'deflate'")

    raise ConfigurationError(
        f"Unsupported compression value '{value}'. Supported values: {', '.join(supported_values)}."
    )


def _parse_otlp_file_output_stream(output_stream: str | None) -> str | None:
    """Resolve an output_stream value to a file path, or None for stdout.

    Per the OTel file exporter spec, output_stream is "stdout" (or
    None, which means the same), or a "file://" URI giving a path.

    The URI must have an empty host or ``localhost``, an absolute path, and
    no parameters, query or fragment. A URI naming a remote host is rejected
    rather than treated as a local path, so a typo cannot quietly write
    telemetry to the wrong file.

    Args:
        output_stream: The ``output_stream`` field of an
            ``otlp_file/development`` exporter configuration block. ``None``
            means the field was absent.

    Returns:
        The absolute filesystem path the URI names, or ``None`` when the
        exporter should write to standard output. The caller distinguishes
        the two by calling the exporter constructor with or without a path
        argument.

    Raises:
        ConfigurationError: If the value is neither ``"stdout"`` nor a local
            ``file://`` URI, if it cannot be parsed as a URI at all, or if
            its path is relative or ends in ``/``. The last two get their own
            messages naming which rule the path broke.
    """
    if output_stream is None or output_stream == "stdout":
        return None
    try:
        parsed = urlparse(output_stream)
    except ValueError as exc:
        raise ConfigurationError(
            f"Failed to parse output_stream '{output_stream}' for otlp_file_development exporter: {exc}"
        ) from exc
    is_local_file_uri = parsed.scheme == "file" and parsed.netloc in ("", "localhost") and bool(parsed.path)
    has_extra_components = parsed.params or parsed.query or parsed.fragment
    if is_local_file_uri and not has_extra_components:
        path = parsed.path
        if not path.startswith("/"):
            raise ConfigurationError(
                f"Unsupported output_stream '{output_stream}' for "
                "otlp_file_development exporter. Path must be absolute."
            )
        if path.endswith("/"):
            raise ConfigurationError(
                f"Unsupported output_stream '{output_stream}' for "
                "otlp_file_development exporter. Path must be a file, "
                "not a directory."
            )
        return path
    raise ConfigurationError(
        f"Unsupported output_stream '{output_stream}' for otlp_file_development "
        "exporter. Supported values: stdout, file://<path>."
    )
