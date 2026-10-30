# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Encoding helpers shared by the span, metric and log record encoders.

The functions here convert the pieces of SDK telemetry that all three signals
have in common: a resource, an instrumentation scope, an attribute mapping, an
arbitrary attribute or log body value, and the integer trace and span
identifiers. What each one hands back is whatever the protocol expects in that
position: a single message from ``opentelemetry-proto``, a list of such messages,
or raw bytes. None of them performs any input or output.

Everything in this subpackage is private to
``opentelemetry-exporter-otlp-proto-common`` and may change in any release.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from typing import (
    Any,
    TypeVar,
)

from opentelemetry.proto.common.v1.common_pb2 import AnyValue as PB2AnyValue
from opentelemetry.proto.common.v1.common_pb2 import (
    ArrayValue as PB2ArrayValue,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    InstrumentationScope as PB2InstrumentationScope,
)
from opentelemetry.proto.common.v1.common_pb2 import KeyValue as PB2KeyValue
from opentelemetry.proto.common.v1.common_pb2 import (
    KeyValueList as PB2KeyValueList,
)
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as PB2Resource,
)
from opentelemetry.sdk.trace import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util.types import Attributes

_logger = logging.getLogger(__name__)

_TypingResourceT = TypeVar("_TypingResourceT")
_ResourceDataT = TypeVar("_ResourceDataT")


def _encode_instrumentation_scope(
    instrumentation_scope: InstrumentationScope,
) -> PB2InstrumentationScope:
    """Encode an instrumentation scope as its protobuf equivalent.

    Args:
        instrumentation_scope: The scope recorded by the SDK on the telemetry
            being exported. ``None`` means the telemetry carries no scope, and
            produces an empty message whose name, version and attributes are all
            left at their protobuf defaults.

    Returns:
        The protobuf ``InstrumentationScope``, carrying the name, the version
        and the encoded attributes. Its ``dropped_attributes_count`` field is
        left at 0, whatever the SDK dropped from the scope attributes. It has no
        field for a schema URL, so the callers put the schema URL of the scope on
        the enclosing ``ScopeSpans``, ``ScopeMetrics`` or ``ScopeLogs`` message
        instead.
    """
    if instrumentation_scope is None:
        return PB2InstrumentationScope()
    return PB2InstrumentationScope(
        name=instrumentation_scope.name,
        version=instrumentation_scope.version,
        attributes=_encode_attributes(instrumentation_scope.attributes),
    )


def _encode_resource(resource: Resource) -> PB2Resource:
    """Encode a resource as its protobuf equivalent.

    Args:
        resource: The resource the SDK attached to the telemetry being exported.

    Returns:
        The protobuf ``Resource``, carrying the encoded attributes. Its
        ``dropped_attributes_count`` field is left at 0, as on the scope message
        above. It has no field for a schema URL, so the two callers, the span
        encoder and the log record encoder, put the schema URL of the resource on
        the enclosing ``ResourceSpans`` or ``ResourceLogs`` message instead. The
        metrics encoder does not use this function: it builds its ``Resource``
        inline and sets the schema URL on ``ResourceMetrics``. Attributes that
        cannot be encoded are dropped, as described on ``_encode_attributes``.
    """
    return PB2Resource(attributes=_encode_attributes(resource.attributes))


def _encode_value(value: Any) -> PB2AnyValue:
    """Encode an attribute value or a log record body as a protobuf ``AnyValue``.

    The type is matched at runtime, in an order the caller cannot change:
    ``bool`` before ``int`` because ``bool`` is a subclass of ``int``, and
    ``str`` and ``bytes`` before ``Sequence`` because both are sequences. A
    sequence or mapping is encoded recursively, so a nested structure deeper
    than the SDK allows in an attribute is still encoded here. The key of a
    mapping entry is passed through ``str``, since protobuf ``KeyValue`` keys
    are strings.

    Args:
        value: The value to encode. ``None`` produces an ``AnyValue`` with no
            field set, which is how the protocol spells an absent value.

    Returns:
        The protobuf ``AnyValue`` with the field matching the runtime type of
        ``value`` set.

    Raises:
        Exception: If ``value`` is of a type the protocol has no field for. The
            message names the type and the value. ``_encode_attributes`` catches
            this and drops the offending attribute.
    """
    if value is None:
        return PB2AnyValue()
    if isinstance(value, bool):
        return PB2AnyValue(bool_value=value)
    if isinstance(value, str):
        return PB2AnyValue(string_value=value)
    if isinstance(value, int):
        return PB2AnyValue(int_value=value)
    if isinstance(value, float):
        return PB2AnyValue(double_value=value)
    if isinstance(value, bytes):
        return PB2AnyValue(bytes_value=value)
    if isinstance(value, Sequence):
        return PB2AnyValue(array_value=PB2ArrayValue(values=[_encode_value(v) for v in value]))
    if isinstance(value, Mapping):
        return PB2AnyValue(
            kvlist_value=PB2KeyValueList(values=[_encode_key_value(str(k), v) for k, v in value.items()])
        )
    raise Exception(f"Invalid type {type(value)} of value {value}")


def _encode_key_value(key: str, value: Any) -> PB2KeyValue:
    """Encode one attribute as a protobuf ``KeyValue``.

    Args:
        key: The attribute name, used as the ``key`` field unchanged.
        value: The attribute value, encoded by ``_encode_value``.

    Returns:
        The protobuf ``KeyValue``.

    Raises:
        Exception: If ``_encode_value`` has no protobuf field for the type of
            ``value``.
        TypeError: If ``key`` is not a string. The protobuf ``key`` field accepts
            no other type, and this function does not convert the key, unlike the
            recursion inside ``_encode_value``.
    """
    return PB2KeyValue(key=key, value=_encode_value(value))


def _encode_span_id(span_id: int) -> bytes:
    """Encode a span identifier as the 8 bytes the protocol carries.

    Args:
        span_id: The span identifier as the SDK holds it, an unsigned integer.

    Returns:
        Exactly 8 bytes, most significant first.

    Raises:
        OverflowError: If ``span_id`` is negative or does not fit in 8 bytes.
    """
    return span_id.to_bytes(length=8, byteorder="big", signed=False)


def _encode_trace_id(trace_id: int) -> bytes:
    """Encode a trace identifier as the 16 bytes the protocol carries.

    Args:
        trace_id: The trace identifier as the SDK holds it, an unsigned integer.

    Returns:
        Exactly 16 bytes, most significant first.

    Raises:
        OverflowError: If ``trace_id`` is negative or does not fit in 16 bytes.
    """
    return trace_id.to_bytes(length=16, byteorder="big", signed=False)


def _encode_attributes(attributes: Attributes) -> list[PB2KeyValue]:
    """Encode an attribute mapping as a list of protobuf ``KeyValue`` messages.

    An attribute that ``_encode_key_value`` cannot encode is dropped rather than
    failing the export: the exception is logged at ``ERROR`` with its traceback
    and the key that caused it, and the remaining attributes are still encoded.
    That covers both causes, a value of a type the protocol has no field for and
    a key that is not a string. An attribute dropped here is counted nowhere. The count of
    attributes the SDK itself dropped is a separate number, which only the span,
    span event, span link and log record encoders copy into the
    ``dropped_attributes_count`` field of the message they build;
    ``_encode_instrumentation_scope`` and ``_encode_resource`` leave that field
    at 0, and no metric data point message defines it.

    Args:
        attributes: The attribute mapping from the SDK. ``None`` and an empty
            mapping both produce an empty list.

    Returns:
        One ``KeyValue`` per attribute that encoded successfully, in the
        iteration order of ``attributes``.
    """
    if not attributes:
        return []
    pb2_attributes = []
    for key, value in attributes.items():
        # pylint: disable=broad-exception-caught
        try:
            pb2_attributes.append(_encode_key_value(key, value))
        except Exception as error:
            _logger.exception("Failed to encode key %s: %s", key, error)
    return pb2_attributes


def _get_resource_data(
    sdk_resource_scope_data: dict[Resource, _ResourceDataT],
    resource_class: Callable[..., _TypingResourceT],
    name: str,
) -> list[_TypingResourceT]:
    """Build one protobuf resource message per resource in a grouped mapping.

    Args:
        sdk_resource_scope_data: The telemetry already grouped by resource. Each
            value is a mapping whose values are the per-scope protobuf messages
            belonging to that resource.
        resource_class: The protobuf message class to build, one of
            ``ResourceSpans``, ``ResourceMetrics`` or ``ResourceLogs``. It is
            called with the keyword arguments ``resource`` and ``scope_<name>``.
        name: The plural signal name that completes the ``scope_<name>`` keyword
            argument, so ``"spans"``, ``"metrics"`` or ``"logs"``. Passing a name
            the message class does not define raises ``ValueError`` from
            protobuf.

    Returns:
        One message of type ``resource_class`` per entry in
        ``sdk_resource_scope_data``, in its iteration order. The ``schema_url``
        of each resource is not copied, so a caller that needs it has to build
        the messages itself.
    """
    resource_data = []

    for (
        sdk_resource,
        scope_data,
    ) in sdk_resource_scope_data.items():
        collector_resource = PB2Resource(attributes=_encode_attributes(sdk_resource.attributes))
        resource_data.append(
            resource_class(
                **{
                    "resource": collector_resource,
                    f"scope_{name}": scope_data.values(),
                }
            )
        )
    return resource_data
