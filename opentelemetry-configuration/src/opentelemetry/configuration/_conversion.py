# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Recursive dict-to-dataclass conversion for parsed config data.

The YAML/JSON loader produces nested dicts. Factory functions expect typed
dataclass instances (e.g. ``TracerProvider``, ``SpanProcessor``). This module
walks each field's type annotation and converts nested dicts into their
corresponding dataclass types.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING, fields, is_dataclass
from enum import Enum
from types import UnionType
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints

_T = TypeVar("_T")


def _unwrap_optional(type_hint: Any) -> Any:
    """Strip ``None`` from a ``X | None`` / ``Optional[X]`` annotation.

    Nearly every field of the generated models is optional, so this runs on
    almost every field before its type can be inspected.

    Args:
        type_hint: An evaluated annotation, as ``get_type_hints`` returns it.

    Returns:
        The single remaining member of the union when the annotation is a
        union of exactly one type with ``None``. ``type_hint`` unchanged in
        every other case, including a union of two or more types with
        ``None``, which stays a union.
    """
    origin = get_origin(type_hint)
    if origin is UnionType or origin is Union:
        non_none = [t for t in get_args(type_hint) if t is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return type_hint


def _is_empty_constructible_dataclass(unwrapped: Any) -> bool:
    """True if ``unwrapped`` is a dataclass type instantiable with no args.

    A dataclass with only optional fields (all have a default or
    default_factory) can be built as ``cls()``; one with a required field
    cannot, and coercing a present null into it would raise ``TypeError``.

    Args:
        unwrapped: A type hint with its ``| None`` already stripped by
            ``_unwrap_optional``. Any object is accepted, since a hint may be
            a generic alias or a string rather than a class.

    Returns:
        ``True`` only when ``unwrapped`` is a class, is a dataclass, and
        every one of its fields has a default or a default factory. A
        dataclass with no fields at all satisfies this.
    """
    return (
        isinstance(unwrapped, type)
        and is_dataclass(unwrapped)
        and all(field.default is not MISSING or field.default_factory is not MISSING for field in fields(unwrapped))
    )


def _convert_value(value: Any, type_hint: Any) -> Any:
    """Convert a value according to its type hint.

    Recursively converts dicts to dataclasses and lists of dicts to lists of
    dataclasses. Other values (primitives, enums, ``dict[str, Any]`` aliases)
    pass through unchanged.

    A ``None`` value is kept as ``None`` for a scalar field and for a
    dataclass that has a required field, and is replaced by an empty mapping
    for a ``dict`` field or an empty-constructible dataclass. That is what
    makes ``always_on:`` written with no value select the always-on sampler
    instead of leaving the field unset.

    Nothing is validated here. A value whose shape does not fit the
    annotation is passed through, and the error comes from a dataclass
    constructor instead. For a nested dataclass field that constructor runs
    inside this function, through ``_dict_to_dataclass``; for any other
    field it runs in the caller.

    Args:
        value: The parsed YAML or JSON value for one field.
        type_hint: The annotation of that field, evaluated. ``None`` is
            accepted, for a field name present in ``__init__`` but absent
            from ``get_type_hints``, and makes the value pass through.

    Returns:
        The converted value: a dataclass instance, a list of converted
        elements, an enum member, or ``value`` itself.

    Raises:
        ValueError: If ``value`` is not a member value of the enum the
            annotation names. The enum constructor raises it.
        TypeError: If ``value`` is a mapping for a nested dataclass field
            and carries a key that dataclass neither declares nor captures,
            or omits one of its fields that has no default.
            ``_dict_to_dataclass`` splats the mapping into the constructor,
            which rejects either one.
    """
    unwrapped = _unwrap_optional(type_hint)
    origin = get_origin(unwrapped)

    if value is None:
        # A mapping key present with an empty (null) YAML value parses to
        # ``None``, which is otherwise indistinguishable from an absent key.
        # For object-typed nodes the declarative-config spec treats a present
        # null as "select this with an empty config" — e.g. ``always_on:`` is
        # equivalent to ``always_on: {}`` and a metric ``console:`` exporter to
        # ``console: {}``. Substitute an empty mapping and let the dict/
        # dataclass handling below build it, so downstream ``is not None`` type
        # dispatch selects it. Scalar fields — and dataclasses with required
        # fields, which cannot be defaulted — keep ``None``, so an absent
        # optional section stays unset.
        if origin is dict or _is_empty_constructible_dataclass(unwrapped):
            value = {}
        else:
            return None

    # list[X] — recurse on each element
    if origin is list and isinstance(value, list):
        args = get_args(unwrapped)
        if args:
            item_type = args[0]
            return [_convert_value(item, item_type) for item in value]
        return value

    # Direct dataclass type — recurse
    if isinstance(unwrapped, type) and is_dataclass(unwrapped) and isinstance(value, dict):
        return _dict_to_dataclass(value, unwrapped)

    # Enum type — coerce string/value to the Enum member
    if isinstance(unwrapped, type) and issubclass(unwrapped, Enum) and not isinstance(value, unwrapped):
        return unwrapped(value)

    return value


def _dict_to_dataclass(data: Mapping[str, Any], cls: type[_T]) -> _T:
    """Recursively convert a mapping to a dataclass instance.

    For each key in ``data``:
    - If it matches a known dataclass field, the value is converted according
      to that field's type annotation (recursing for nested dataclasses).
    - Unknown keys are passed through as kwargs; classes decorated with
      ``@_additional_properties`` will capture them on the instance's
      ``additional_properties`` attribute.

    Non-init fields (e.g. the generated ``additional_properties`` field on
    decorated dataclasses) are ignored as expected.

    A key containing ``/``, which the configuration schema uses to mark a
    development feature (``otlp_file/development``), is matched against the
    field named with ``_`` in its place. Without that the key would fall
    through to ``additional_properties`` and the component lookup would find
    nothing.

    Args:
        data: One mapping from the parsed configuration file.
        cls: The dataclass type to build from it.

    Returns:
        An instance of ``cls`` with every recognised key converted to its
        annotated type and every unrecognised key passed through under its
        original name.

    Raises:
        TypeError: If ``cls`` is not a dataclass type, if ``cls`` is not
            decorated with ``@_additional_properties`` and ``data`` holds a
            key that is not one of its fields, or if ``data`` omits a field
            of ``cls`` that has neither a default nor a default factory.
            The dataclass constructor raises the last two.
    """
    if not is_dataclass(cls):
        raise TypeError(f"{cls.__name__} is not a dataclass")

    # Annotated as ``dict[str, Any]`` so astroid stops tracing into
    # ``get_type_hints`` — under pylint 3.x that path leads into
    # Python 3.14's ``annotationlib`` (which uses t-strings) and crashes.
    hints: dict[str, Any] = dict(get_type_hints(cls, include_extras=False))
    known_fields = {f.name for f in fields(cls) if f.init}
    kwargs: dict[str, Any] = {}

    for key, value in data.items():
        # The OTel configuration schema uses "/" as a namespace separator for
        # development/experimental features (e.g. "otlp_file/development",
        # "instrumentation/development").  Python identifiers cannot contain
        # "/", so the corresponding dataclass fields use "_" instead (e.g.
        # "otlp_file_development").  Without this normalisation the key would
        # not match any known field and would fall through to
        # additional_properties, causing the factory lookup to fail silently.
        field_key = key.replace("/", "_")
        if field_key in known_fields:
            type_hint = hints.get(field_key)
            kwargs[field_key] = _convert_value(value, type_hint)
        else:
            # Unknown key — @_additional_properties decorator will capture it.
            kwargs[key] = value

    return cls(**kwargs)
