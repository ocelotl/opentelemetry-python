# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pyright: reportCallIssue=false

"""Encoding helpers shared by the trace, metrics and log encoders.

What the three signals have in common is what this module covers: the resource
and the instrumentation scope that every exported batch is grouped by, the
attribute lists that hang off nearly every OTLP message, and the fixed-width
byte form of trace and span identifiers that ``to_dict`` on the enclosing
message renders as hexadecimal.

Nothing here is public, and nothing outside this distribution imports these
names. The trace, metrics and log encoder packages under
``opentelemetry.exporter.otlp.json.common._internal`` each import the ones they
need, which is not the same set for all three. ``_encode_key_value`` is
imported by none of them: it is reached only from ``_encode_value`` and
``_encode_attributes`` in this module.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from opentelemetry.proto_json.common.v1.common import AnyValue as JSONAnyValue
from opentelemetry.proto_json.common.v1.common import (
    ArrayValue as JSONArrayValue,
)
from opentelemetry.proto_json.common.v1.common import (
    InstrumentationScope as JSONInstrumentationScope,
)
from opentelemetry.proto_json.common.v1.common import KeyValue as JSONKeyValue
from opentelemetry.proto_json.common.v1.common import (
    KeyValueList as JSONKeyValueList,
)
from opentelemetry.proto_json.resource.v1.resource import (
    Resource as JSONResource,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util.types import Attributes

_logger = logging.getLogger(__name__)


def _encode_instrumentation_scope(
    instrumentation_scope: InstrumentationScope | None,
) -> JSONInstrumentationScope:
    """Encode an SDK instrumentation scope as its OTLP JSON message.

    Args:
        instrumentation_scope: the scope recorded on the telemetry being
            exported, or ``None`` when the telemetry carries no scope.

    Returns:
        A ``JSONInstrumentationScope`` carrying the name, the version and the
        attributes of the scope. The schema URL of the scope is not encoded
        here: it belongs to the enclosing ``ScopeSpans``, ``ScopeMetrics`` or
        ``ScopeLogs`` message, and each signal encoder sets it there. When
        ``instrumentation_scope`` is ``None`` the result is a message left at
        its field defaults, which serialises to an empty JSON object.
    """
    return (
        JSONInstrumentationScope(
            name=instrumentation_scope.name,
            version=instrumentation_scope.version,
            attributes=_encode_attributes(instrumentation_scope.attributes),
        )
        if instrumentation_scope is not None
        else JSONInstrumentationScope()
    )


def _encode_resource(resource: Resource) -> JSONResource:
    """Encode an SDK resource as its OTLP JSON message.

    Args:
        resource: the resource the telemetry being exported was produced
            under.

    Returns:
        A ``JSONResource`` carrying the attributes of the resource. The schema
        URL of the resource is not encoded here: it belongs to the enclosing
        ``ResourceSpans``, ``ResourceMetrics`` or ``ResourceLogs`` message, and
        each signal encoder sets it there.
    """
    return JSONResource(attributes=_encode_attributes(resource.attributes))


# pylint: disable-next=too-many-return-statements
def _encode_value(value: Any) -> JSONAnyValue:
    """Encode one attribute value or log body as an OTLP JSON ``AnyValue``.

    A mapping or a sequence is encoded recursively, so a nested value becomes a
    tree of ``AnyValue`` messages. Mapping keys are passed through ``str``,
    because OTLP has no representation for a non-string key. The order in which
    the types are tested is load bearing: ``bool`` is tested before ``int``
    because ``bool`` is a subclass of ``int``, and ``str`` and ``bytes`` are
    tested before ``Sequence`` because both register as sequences.

    Args:
        value: the value to encode.

    Returns:
        The encoded ``JSONAnyValue``. For a ``value`` of ``None`` that is a
        message with no field set, which serialises to an empty JSON object
        rather than to a JSON ``null``.

    Raises:
        TypeError: if ``value`` is of a type OTLP has no representation for.
            ``_encode_attributes`` catches this for an attribute, but a log
            body of such a type reaches the caller.
    """
    if value is None:
        return JSONAnyValue()
    if isinstance(value, bool):
        return JSONAnyValue(bool_value=value)
    if isinstance(value, str):
        return JSONAnyValue(string_value=value)
    if isinstance(value, int):
        return JSONAnyValue(int_value=value)
    if isinstance(value, float):
        return JSONAnyValue(double_value=value)
    if isinstance(value, bytes):
        return JSONAnyValue(bytes_value=value)
    if isinstance(value, Sequence):
        return JSONAnyValue(array_value=JSONArrayValue(values=[_encode_value(v) for v in value]))
    if isinstance(value, Mapping):
        return JSONAnyValue(
            kvlist_value=JSONKeyValueList(values=[_encode_key_value(str(k), v) for k, v in value.items()])
        )
    raise TypeError(f"Invalid type {type(value)} of value {value}")


def _encode_key_value(key: str, value: Any) -> JSONKeyValue:
    """Encode one named value as an OTLP JSON ``KeyValue``.

    Args:
        key: the name, used unchanged.
        value: the value, encoded by ``_encode_value``.

    Returns:
        The encoded ``JSONKeyValue``.

    Raises:
        TypeError: if ``_encode_value`` has no representation for ``value``.
    """
    return JSONKeyValue(key=key, value=_encode_value(value))


def _encode_span_id(span_id: int) -> bytes:
    """Encode a span identifier as the eight bytes OTLP gives it.

    Args:
        span_id: the identifier as the SDK holds it, an unsigned integer of at
            most 64 bits.

    Returns:
        The identifier as eight big-endian bytes, which ``to_dict`` on the
        enclosing message then renders as a sixteen-character lowercase
        hexadecimal string.

    Raises:
        OverflowError: if ``span_id`` is negative or needs more than eight
            bytes.
    """
    return span_id.to_bytes(length=8, byteorder="big", signed=False)


def _encode_trace_id(trace_id: int) -> bytes:
    """Encode a trace identifier as the sixteen bytes OTLP gives it.

    Args:
        trace_id: the identifier as the SDK holds it, an unsigned integer of at
            most 128 bits.

    Returns:
        The identifier as sixteen big-endian bytes, which ``to_dict`` on the
        enclosing message then renders as a thirty-two-character lowercase
        hexadecimal string.

    Raises:
        OverflowError: if ``trace_id`` is negative or needs more than sixteen
            bytes.
    """
    return trace_id.to_bytes(length=16, byteorder="big", signed=False)


def _encode_attributes(
    attributes: Attributes,
) -> list[JSONKeyValue]:
    """Encode an attribute mapping as a list of OTLP JSON ``KeyValue`` messages.

    An attribute whose value ``_encode_value`` has no representation for does
    not fail the export. The exception is logged together with the key, that
    one attribute is left out, and the remaining attributes are still encoded,
    so one bad value does not cost the caller the whole batch.

    Args:
        attributes: the attributes to encode, or ``None`` when the telemetry
            carries none.

    Returns:
        One ``JSONKeyValue`` per attribute that encoded, in the iteration order
        of ``attributes``. ``None`` and an empty mapping both give an empty
        list.
    """
    if not attributes:
        return []
    json_attributes = []
    for key, value in attributes.items():
        # pylint: disable=broad-exception-caught
        try:
            json_attributes.append(_encode_key_value(key, value))
        except Exception as error:
            _logger.exception("Failed to encode key %s: %s", key, error)
    return json_attributes
