# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Mapping
from logging import getLogger
from re import compile
from types import MappingProxyType

from opentelemetry.context import create_key, get_value, set_value
from opentelemetry.context.context import Context
from opentelemetry.util.re import (
    _BAGGAGE_PROPERTY_FORMAT,
    _KEY_FORMAT,
    _VALUE_FORMAT,
)

_BAGGAGE_KEY = create_key("baggage")
_BAGGAGE_METADATA_KEY = create_key("baggage-metadata")
_logger = getLogger(__name__)

_KEY_PATTERN = compile(_KEY_FORMAT)
_VALUE_PATTERN = compile(_VALUE_FORMAT)
_PROPERT_PATTERN = compile(_BAGGAGE_PROPERTY_FORMAT)


def get_all(
    context: Context | None = None,
) -> Mapping[str, object]:
    """Returns the name/value pairs in the Baggage

    Args:
        context: The Context to use. If not set, uses current Context

    Returns:
        The name/value pairs in the Baggage
    """
    return MappingProxyType(_get_baggage_value(context=context))


def get_baggage(name: str, context: Context | None = None) -> object | None:
    """Provides access to the value for a name/value pair in the
    Baggage

    Args:
        name: The name of the value to retrieve
        context: The Context to use. If not set, uses current Context

    Returns:
        The value associated with the given name, or null if the given name is
        not present.
    """
    return _get_baggage_value(context=context).get(name)


def get_baggage_metadata(
    name: str, context: Context | None = None
) -> str | None:
    """Provides access to the metadata associated with a name/value pair in
    the Baggage.

    Metadata is the optional ``;``-delimited list of properties that a W3C
    Baggage entry may carry (see
    https://www.w3.org/TR/baggage/#definition). It is preserved verbatim so
    that it can be re-appended when the Baggage is injected downstream.

    Args:
        name: The name of the entry whose metadata to retrieve
        context: The Context to use. If not set, uses current Context

    Returns:
        The metadata string associated with the given name, or ``None`` if the
        given name has no metadata or is not present.
    """
    return _get_baggage_metadata_value(context=context).get(name)


def set_baggage(
    name: str,
    value: object,
    context: Context | None = None,
    metadata: str | None = None,
) -> Context:
    """Sets a value in the Baggage

    Args:
        name: The name of the value to set
        value: The value to set
        context: The Context to use. If not set, uses current Context
        metadata: Optional ``;``-delimited W3C Baggage metadata (properties)
            to associate with this entry. It is stored verbatim and
            re-appended when the Baggage is injected.

    Returns:
        A Context with the value updated
    """
    baggage = _get_baggage_value(context=context).copy()
    baggage[name] = value
    context = set_value(_BAGGAGE_KEY, baggage, context=context)

    existing_metadata = _get_baggage_metadata_value(context=context)
    # Only touch the metadata store when there is something to record or an
    # existing entry to clear, so entries set without metadata don't leave an
    # empty metadata mapping behind in the Context.
    if metadata is not None or name in existing_metadata:
        baggage_metadata = existing_metadata.copy()
        if metadata is None:
            baggage_metadata.pop(name, None)
        else:
            baggage_metadata[name] = metadata
        context = set_value(
            _BAGGAGE_METADATA_KEY, baggage_metadata, context=context
        )
    return context


def remove_baggage(name: str, context: Context | None = None) -> Context:
    """Removes a value from the Baggage

    Args:
        name: The name of the value to remove
        context: The Context to use. If not set, uses current Context

    Returns:
        A Context with the name/value removed
    """
    baggage = _get_baggage_value(context=context).copy()
    baggage.pop(name, None)
    context = set_value(_BAGGAGE_KEY, baggage, context=context)

    existing_metadata = _get_baggage_metadata_value(context=context)
    if name in existing_metadata:
        baggage_metadata = existing_metadata.copy()
        baggage_metadata.pop(name, None)
        context = set_value(
            _BAGGAGE_METADATA_KEY, baggage_metadata, context=context
        )
    return context


def clear(context: Context | None = None) -> Context:
    """Removes all values from the Baggage

    Args:
        context: The Context to use. If not set, uses current Context

    Returns:
        A Context with all baggage entries removed
    """
    context = set_value(_BAGGAGE_KEY, {}, context=context)
    if _get_baggage_metadata_value(context=context):
        context = set_value(_BAGGAGE_METADATA_KEY, {}, context=context)
    return context


def _get_baggage_value(context: Context | None = None) -> dict[str, object]:
    baggage = get_value(_BAGGAGE_KEY, context=context)
    if isinstance(baggage, dict):
        return baggage
    return {}


def _get_baggage_metadata_value(
    context: Context | None = None,
) -> dict[str, str]:
    baggage_metadata = get_value(_BAGGAGE_METADATA_KEY, context=context)
    if isinstance(baggage_metadata, dict):
        return baggage_metadata
    return {}


def _is_valid_key(name: str) -> bool:
    return _KEY_PATTERN.fullmatch(str(name)) is not None


def _is_valid_value(value: object) -> bool:
    parts = str(value).split(";")
    is_valid_value = _VALUE_PATTERN.fullmatch(parts[0]) is not None
    if len(parts) > 1:  # one or more properties metadata
        for property in parts[1:]:
            if _PROPERT_PATTERN.fullmatch(property) is None:
                is_valid_value = False
                break
    return is_valid_value


def _is_valid_pair(key: str, value: str) -> bool:
    return _is_valid_key(key) and _is_valid_value(value)
