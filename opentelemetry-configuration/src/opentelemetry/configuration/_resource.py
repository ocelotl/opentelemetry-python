# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Resource construction from declarative configuration.

The resource is the one part of the configuration that is shared, so it
is built once by ``configure_sdk`` and handed to all three providers.

Declarative configuration does not read ``OTEL_RESOURCE_ATTRIBUTES``,
and it runs no resource detector unless the configuration file lists it
under ``detection/development``. That is the difference a reader coming
from the environment-variable path has to know about: a file that sets
no resource attributes produces the SDK defaults plus a ``service.name``
derived from the interpreter name, and nothing else.

Attributes reach the resource from three places, each overriding the one
before it: the SDK telemetry defaults, then whatever the configured
detectors reported (after the include/exclude filter), then the
attributes written in the configuration file.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import sys
from collections.abc import Callable
from typing import Any
from urllib import parse

from opentelemetry.configuration._common import _matches_glob, load_entry_point
from opentelemetry.configuration._exceptions import ConfigurationError
from opentelemetry.configuration.models import (
    AttributeNameValue,
    AttributeType,
    ExperimentalResourceDetector,
    IncludeExclude,
)
from opentelemetry.configuration.models import Resource as ResourceConfig
from opentelemetry.sdk.environment_variables import OTEL_SERVICE_NAME
from opentelemetry.sdk.resources import (
    _DEFAULT_RESOURCE,
    SERVICE_NAME,
    OsResourceDetector,
    ProcessResourceDetector,
    Resource,
    ServiceInstanceIdResourceDetector,
    _HostResourceDetector,
)
from opentelemetry.util.types import AnyValue

_logger = logging.getLogger(__name__)


def _coerce_bool(value: object) -> bool:
    """Read an attribute value declared as ``bool`` in the configuration file.

    A string is false only when it is ``"false"`` in any case, ``"0"`` or
    empty. Every other string, including ``"no"`` and ``"off"``, is true. Any
    non-string is passed to ``bool``, so ``0``, ``0.0`` and an empty list are
    false.

    Args:
        value: The raw attribute value, as the YAML or JSON parser produced
            it.

    Returns:
        The boolean the value stands for.
    """
    if isinstance(value, str):
        return value.lower() not in ("false", "0", "")
    return bool(value)


def _array(coerce: Callable) -> Callable:
    """Lift a single-value coercion into one that maps over a sequence.

    Args:
        coerce: The coercion for one element, for example ``str`` or
            ``_coerce_bool``.

    Returns:
        A callable that applies ``coerce`` to every item of its argument and
        returns a list. It raises ``TypeError`` when handed something that
        is not iterable, which happens when the configuration file declares
        an array type but gives a scalar value.
    """
    return lambda value: [coerce(item) for item in value]


# Dispatch table mapping AttributeType to its coercion callable
_COERCIONS = {
    AttributeType.string: str,
    AttributeType.int: int,
    AttributeType.double: float,
    AttributeType.bool: _coerce_bool,
    AttributeType.string_array: _array(str),
    AttributeType.int_array: _array(int),
    AttributeType.double_array: _array(float),
    AttributeType.bool_array: _array(_coerce_bool),
}


def _coerce_attribute_value(attr: AttributeNameValue) -> object:
    """Coerce an attribute value to the correct Python type based on AttributeType.

    Args:
        attr: One entry of the ``attributes`` list in the resource
            configuration, carrying a name, a value and an optional type.

    Returns:
        The value coerced to the declared type. The value is returned
        unchanged when ``attr.type`` is absent, which is how the schema
        spells "it is already a string", and also when the type is one the
        coercion table does not cover.

    Raises:
        ValueError: If the value cannot be read as the declared type, for
            example ``type: int`` on a value of ``"abc"``.
        TypeError: If an array type is declared on a value that is not
            iterable.
    """
    coerce = _COERCIONS.get(attr.type)  # type: ignore[arg-type]
    return coerce(attr.value) if coerce is not None else attr.value  # type: ignore[operator]


def _parse_attributes_list(attributes_list: str) -> dict[str, str]:
    """Parse a comma-separated key=value string into a dict.

    Format is the same as OTEL_RESOURCE_ATTRIBUTES: key=value,key=value
    Values are always strings (no type coercion).

    An entry with no ``=`` is dropped with a warning rather than raising, so
    one malformed pair does not discard the rest. An empty entry, which a
    trailing or doubled comma produces, is skipped without a warning. A
    value is percent-decoded, matching the handling of
    ``OTEL_RESOURCE_ATTRIBUTES``; a name is not.

    Args:
        attributes_list: The ``attributes_list`` field of the resource
            configuration.

    Returns:
        The parsed pairs. A name that appears more than once keeps the value
        of its last occurrence.
    """
    result: dict[str, str] = {}
    for item in attributes_list.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            _logger.warning(
                "Invalid resource attribute pair in attributes_list: %s",
                item,
            )
            continue
        key, value = item.split("=", maxsplit=1)
        result[key.strip()] = parse.unquote(value.strip())
    return result


def create_resource(config: ResourceConfig | None) -> Resource:
    """Create an SDK Resource from declarative config.

    Does NOT read OTEL_RESOURCE_ATTRIBUTES. Resource detectors are only run
    when explicitly listed under detection_development.detectors in the config.
    Starts from SDK telemetry defaults (telemetry.sdk.*), merges any detected
    attributes, then merges explicit config attributes on top (highest priority).

    ``service.name`` is always present. It defaults to
    ``unknown_service:<interpreter>``, which a detector or an explicit
    attribute can override.

    An attribute whose value is ``None`` is dropped with a warning instead of
    being written as a null or coerced into the string ``"None"``. A
    reference to an environment variable that is unset and has no default
    substitutes an empty value, which the YAML parser reads as null, so this
    is the normal outcome of a missing variable rather than an unusual one.

    Args:
        config: Resource config from the parsed config file, or None.

    Returns:
        A Resource with SDK defaults, optional detector attributes, and any
        config-specified attributes merged in priority order. Its schema URL
        is the one the config gives, or empty when the config gives none or
        is ``None``.

    Raises:
        ValueError: If an attribute value cannot be read as its declared
            type, for example ``type: int`` on a value of ``"abc"``.
            ``_coerce_attribute_value`` raises it.
        TypeError: If an array attribute type is declared on a value that
            is not iterable, or if a plugin detector's constructor does not
            accept the keys of the nested configuration mapping splatted
            into it.
    """
    # Spec requires service.name to always be present; detectors and explicit
    # config attributes can override this default.
    executable_name = os.path.basename(sys.executable) if sys.executable else None
    default_service_name = f"unknown_service:{executable_name}" if executable_name else "unknown_service"
    base = _DEFAULT_RESOURCE.merge(Resource({SERVICE_NAME: default_service_name}))

    if config is None:
        return base

    # attributes_list is lower priority; explicit attributes overwrite conflicts.
    config_attrs: dict[str, object] = {}
    if config.attributes_list:
        config_attrs.update(_parse_attributes_list(config.attributes_list))

    if config.attributes:
        for attr in config.attributes:
            # An unset ${VAR} with no default substitutes an empty value that
            # the YAML parser reads as null. Skip such attributes rather than
            # inserting a None (or coercing it into garbage like "None"/0).
            if attr.value is None:
                _logger.warning(
                    "Ignoring resource attribute '%s' with empty value",
                    attr.name,
                )
                continue
            config_attrs[attr.name] = _coerce_attribute_value(attr)

    schema_url = config.schema_url

    # Run detectors only if detection_development is configured. Collect all
    # detected attributes, apply the include/exclude filter, then merge before
    # config attributes so explicit values always win.
    result = base
    if config.detection_development:
        detected_attrs: dict[str, object] = {}
        if config.detection_development.detectors:
            for detector_config in config.detection_development.detectors:
                _run_detectors(detector_config, detected_attrs)

        filtered = _filter_attributes(detected_attrs, config.detection_development.attributes)
        if filtered:
            result = result.merge(Resource(filtered))  # type: ignore[arg-type]

    config_resource = Resource(config_attrs, schema_url)  # type: ignore[arg-type]
    return result.merge(config_resource)


def _detect_service(_config: Any) -> dict[str, AnyValue]:
    """Service detector: generates instance ID and reads OTEL_SERVICE_NAME.

    This is the one detector that reads an environment variable, which the
    rest of this module does not do. The declarative configuration
    specification defines the service detector that way.

    Args:
        _config: The value written under ``service:`` in the detectors list.
            It is ignored: the detector takes no options, and the key is
            present only to select it.

    Returns:
        ``service.instance.id``, always, and ``service.name`` when
        ``OTEL_SERVICE_NAME`` is set to a non-empty value.
    """
    attrs: dict[str, AnyValue] = dict(ServiceInstanceIdResourceDetector().detect().attributes)
    if service_name := os.environ.get(OTEL_SERVICE_NAME):
        attrs[SERVICE_NAME] = service_name
    return attrs


_RESOURCE_DETECTOR_REGISTRY: dict[str, Callable[[Any], dict[str, AnyValue]]] = {
    "service": _detect_service,
    "host": lambda _: dict(_HostResourceDetector().detect().merge(OsResourceDetector().detect()).attributes),
    "process": lambda _: dict(ProcessResourceDetector().detect().attributes),
}

# Schema detector names whose providers register under a different entry point name.
_DETECTOR_ENTRY_POINT_NAMES: dict[str, str] = {
    "container": "containerid",
}


def _load_detector(name: str) -> type | None:
    """Load a resource detector class by its config name.

    Returns None, after logging a warning, when the detector cannot be loaded,
    so that an unrecognized detector does not fail SDK construction.

    A few schema detector names differ from the entry point name their
    provider registers, so the name is translated through
    ``_DETECTOR_ENTRY_POINT_NAMES`` first. ``container`` is registered as
    ``containerid``.

    Args:
        name: The detector name as written in the configuration file, which
            is either a field of the detectors block or a key the schema did
            not declare.

    Returns:
        The detector class, or ``None`` when no installed package registers
        it. The caller is expected to skip a ``None`` rather than treat it
        as a detector that found nothing.
    """
    try:
        return load_entry_point(
            "opentelemetry_resource_detector",
            _DETECTOR_ENTRY_POINT_NAMES.get(name, name),
        )
    except ConfigurationError as exc:
        _logger.warning(
            "Resource detector '%s' could not be loaded and will be ignored: %s",
            name,
            exc,
        )
        return None


def _run_detectors(
    detector_config: ExperimentalResourceDetector,
    detected_attrs: dict[str, object],
) -> None:
    """Run detectors present in a single detector config entry.

    Known detectors (service, host, process) are handled directly via
    _RESOURCE_DETECTOR_REGISTRY. All other detectors — including known
    schema fields like container that require contrib packages, and
    unknown plugin detectors captured in additional_properties — are
    loaded via the ``opentelemetry_resource_detector`` entry point group.
    Detectors that cannot be loaded are skipped with a warning.

    The detected_attrs dict is updated in-place; later detectors overwrite
    earlier ones for the same key.

    The declared fields run before the plugin detectors, and within each
    group the order is the order the fields were declared or the keys were
    written. A detector whose ``detect()`` raises is not caught here, so it
    aborts the whole resource construction, unlike a detector that could not
    be loaded at all.

    Args:
        detector_config: One entry of the ``detectors`` list. Its declared
            fields name the detectors the schema knows; its
            ``additional_properties`` hold the plugin names it does not.
        detected_attrs: The accumulator every detector in this entry writes
            into. It is modified in place and nothing is returned.

    Raises:
        TypeError: If a plugin detector's constructor does not accept the
            keys of the nested configuration mapping splatted into it.
            A detector that cannot be loaded at all is skipped with a
            warning instead, so this covers only one that was found.
    """
    for field in dataclasses.fields(detector_config):
        if not field.init:
            continue

        value = getattr(detector_config, field.name, None)
        if value is None:
            continue
        if field.name in _RESOURCE_DETECTOR_REGISTRY:
            detected_attrs.update(_RESOURCE_DETECTOR_REGISTRY[field.name](value))
        elif (cls := _load_detector(field.name)) is not None:
            detected_attrs.update(cls(**(value or {})).detect().attributes)

    for name, plugin_config in detector_config.additional_properties.items():
        if (cls := _load_detector(name)) is not None:
            detected_attrs.update(cls(**(plugin_config or {})).detect().attributes)


def _filter_attributes(attrs: dict[str, object], filter_config: IncludeExclude | None) -> dict[str, object]:
    """Filter detected attribute keys using include/exclude glob patterns.

    Mirrors other SDK IncludeExcludePredicate.createPatternMatching behavior:
    - No filter config (attributes absent) → include all detected attributes.
    - included patterns are checked first; excluded patterns are applied after.
    - An empty included list is treated as "include everything".

    The filter applies to detected attributes only. An attribute written in
    the configuration file reaches the resource whether or not it matches,
    because it is merged after this runs.

    Args:
        attrs: Every attribute the configured detectors reported, already
            merged across detectors.
        filter_config: The ``attributes`` field of the
            ``detection/development`` block, holding the ``included`` and
            ``excluded`` pattern lists. ``None`` means the field was absent.

    Returns:
        The attributes that survive the patterns. When no filtering applies
        the argument itself is returned rather than a copy, so a caller that
        mutated the result would also change ``attrs``.
    """
    if filter_config is None:
        return attrs

    included = filter_config.included
    excluded = filter_config.excluded

    if not included and not excluded:
        return attrs

    result: dict[str, object] = {}
    for key, value in attrs.items():
        if included and not any(_matches_glob(key, pat) for pat in included):
            continue
        if excluded and any(_matches_glob(key, pat) for pat in excluded):
            continue
        result[key] = value
    return result
