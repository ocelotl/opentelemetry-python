# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=no-member

"""Maps protobuf field types onto the Python the generator writes.

Every value this module returns is a fragment of Python source for
``opentelemetry.codegen.json.generator`` to splice into a generated file, not a Python object. The
string ``"builtins.int"`` is a type hint to be written out, and the string ``'""'`` is the source
text of an empty string literal.

Names are fully qualified against ``builtins`` throughout. Qualifying keeps a type hint from
resolving to a generated class that happens to carry a builtin's name, which a bare ``str`` or
``int`` in a generated module would.

The mappings follow the Proto3 JSON specification at
https://protobuf.dev/programming-guides/json/, with one OTLP deviation that
``is_hex_encoded_field`` carries: ``trace_id``, ``span_id`` and ``parent_span_id`` are hex strings
rather than the base64 strings Proto3 JSON gives bytes fields.

Three protobuf types are absent from every table here: ``TYPE_MESSAGE``, ``TYPE_ENUM`` and
``TYPE_GROUP``. The first two are resolved against the descriptor index rather than a fixed table,
which the generator does itself, and ``TYPE_GROUP`` is the proto2 construct that OTLP does not use.
"""

from typing import Final

from google.protobuf import descriptor_pb2 as descriptor

PROTO_TO_PYTHON: Final[dict[int, str]] = {
    descriptor.FieldDescriptorProto.TYPE_DOUBLE: "builtins.float",
    descriptor.FieldDescriptorProto.TYPE_FLOAT: "builtins.float",
    descriptor.FieldDescriptorProto.TYPE_INT64: "builtins.int",
    descriptor.FieldDescriptorProto.TYPE_UINT64: "builtins.int",
    descriptor.FieldDescriptorProto.TYPE_INT32: "builtins.int",
    descriptor.FieldDescriptorProto.TYPE_FIXED64: "builtins.int",
    descriptor.FieldDescriptorProto.TYPE_FIXED32: "builtins.int",
    descriptor.FieldDescriptorProto.TYPE_BOOL: "builtins.bool",
    descriptor.FieldDescriptorProto.TYPE_STRING: "builtins.str",
    descriptor.FieldDescriptorProto.TYPE_BYTES: "builtins.bytes",
    descriptor.FieldDescriptorProto.TYPE_UINT32: "builtins.int",
    descriptor.FieldDescriptorProto.TYPE_SFIXED32: "builtins.int",
    descriptor.FieldDescriptorProto.TYPE_SFIXED64: "builtins.int",
    descriptor.FieldDescriptorProto.TYPE_SINT32: "builtins.int",
    descriptor.FieldDescriptorProto.TYPE_SINT64: "builtins.int",
}

PROTO_DEFAULTS: Final[dict[int, str]] = {
    descriptor.FieldDescriptorProto.TYPE_DOUBLE: "0.0",
    descriptor.FieldDescriptorProto.TYPE_FLOAT: "0.0",
    descriptor.FieldDescriptorProto.TYPE_INT64: "0",
    descriptor.FieldDescriptorProto.TYPE_UINT64: "0",
    descriptor.FieldDescriptorProto.TYPE_INT32: "0",
    descriptor.FieldDescriptorProto.TYPE_FIXED64: "0",
    descriptor.FieldDescriptorProto.TYPE_FIXED32: "0",
    descriptor.FieldDescriptorProto.TYPE_BOOL: "False",
    descriptor.FieldDescriptorProto.TYPE_STRING: '""',
    descriptor.FieldDescriptorProto.TYPE_BYTES: 'b""',
    descriptor.FieldDescriptorProto.TYPE_UINT32: "0",
    descriptor.FieldDescriptorProto.TYPE_SFIXED32: "0",
    descriptor.FieldDescriptorProto.TYPE_SFIXED64: "0",
    descriptor.FieldDescriptorProto.TYPE_SINT32: "0",
    descriptor.FieldDescriptorProto.TYPE_SINT64: "0",
}

INT64_TYPES: Final[set[int]] = {
    descriptor.FieldDescriptorProto.TYPE_INT64,
    descriptor.FieldDescriptorProto.TYPE_UINT64,
    descriptor.FieldDescriptorProto.TYPE_FIXED64,
    descriptor.FieldDescriptorProto.TYPE_SFIXED64,
    descriptor.FieldDescriptorProto.TYPE_SINT64,
}

NUMERIC_TYPES: Final[set[int]] = {
    *INT64_TYPES,
    descriptor.FieldDescriptorProto.TYPE_DOUBLE,
    descriptor.FieldDescriptorProto.TYPE_FLOAT,
    descriptor.FieldDescriptorProto.TYPE_INT32,
    descriptor.FieldDescriptorProto.TYPE_FIXED32,
    descriptor.FieldDescriptorProto.TYPE_UINT32,
    descriptor.FieldDescriptorProto.TYPE_SFIXED32,
    descriptor.FieldDescriptorProto.TYPE_SINT32,
}

HEX_ENCODED_FIELDS: Final[set[str]] = {
    "trace_id",
    "span_id",
    "parent_span_id",
}


def get_python_type(proto_type: int) -> str:
    """
    Get the Python type corresponding to a protobuf field type.

    This covers the scalar types only. A message, an enum or a proto2 group has to be resolved
    against the descriptor index instead, which the generator does before it gets here.

    Args:
        proto_type: The protobuf field type as an integer (from FieldDescriptorProto).
    Returns:
        A string representing the Python type, qualified against ``builtins``.

    Raises:
        ValueError: If the type is not a scalar type. Failing here rather than guessing is
            deliberate: a wrong type hint would be written into a generated file and only
            surface later, far from its cause.
    """
    if proto_type not in PROTO_TO_PYTHON:
        raise ValueError(f"Unknown protobuf type: {proto_type}")
    return PROTO_TO_PYTHON[proto_type]


def get_default_value(proto_type: int) -> str:
    """
    Get the default value for a protobuf field type as a string.

    These are the proto3 zero values, written as Python source: ``0`` for every integer type,
    ``0.0`` for the floating point types, ``False``, ``""`` and ``b""``.

    Args:
        proto_type: The protobuf field type as an integer (from FieldDescriptorProto).
    Returns:
        A string representing the default value for that type. A type with no entry, which means
        a message, an enum or a proto2 group, gives the string ``"None"``. The generator does not
        rely on that fallback: it decides the default for those cases before calling this.
    """
    return PROTO_DEFAULTS.get(proto_type, "None")


def is_int64_type(proto_type: int) -> bool:
    """
    Check if type is a 64-bit integer type (int64, uint64, fixed64, sfixed64, sint64)

    These are the types Proto3 JSON encodes as strings, because a 64-bit integer does not survive
    a round trip through the IEEE 754 double that a JSON number becomes in many parsers.

    Args:
        proto_type: The protobuf field type as an integer (from FieldDescriptorProto).
    Returns:
        True if the type is a 64-bit integer type, False otherwise.
    """
    return proto_type in INT64_TYPES


def is_bytes_type(proto_type: int) -> bool:
    """
    Check if type is bytes.

    Args:
        proto_type: The protobuf field type as an integer (from FieldDescriptorProto).
    Returns:
        True if the type is bytes, False otherwise.
    """
    return proto_type == descriptor.FieldDescriptorProto.TYPE_BYTES


def is_hex_encoded_field(field_name: str) -> bool:
    """
    Check if field is a hex-encoded field (trace_id, span_id, parent_span_id).

    OTLP/JSON departs from Proto3 JSON for these three, carrying them as lowercase hex strings
    instead of base64. This function looks at the name alone and never at the type. The generator
    does check the type first, so a message-typed or enum-typed field never reaches this test,
    but among the remaining types the name is the whole decision.

    Args:
        field_name: The name of the protobuf field.
    Returns:
        True if the field is a hex-encoded field, False otherwise.
    """
    return field_name in HEX_ENCODED_FIELDS


def to_json_field_name(snake_name: str) -> str:
    """
    Convert snake_case field name to camelCase for JSON representation.

    This is the fallback for a descriptor that carries no ``json_name``. ``protoc`` normally fills
    that field in, and the generator prefers it when present.

    The conversion uses ``str.title`` on each component after the first, which lowercases the rest
    of a component as well as uppercasing its first character, so ``trace_ID`` gives ``traceId``.
    A leading underscore produces an empty first component, so the result begins with whatever
    ``str.title`` makes of the second one: ``_foo`` gives ``Foo``, and ``_1abc`` gives ``1Abc``.

    Args:
        snake_name: The field name in snake_case.
    Returns:
        The field name converted to camelCase.
    """
    components = snake_name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def is_numeric_type(proto_type: int) -> bool:
    """
    Check if the protobuf field type is a numeric type (int32, int64, uint32, uint64, float, double).

    Args:
        proto_type: The protobuf field type as an integer (from FieldDescriptorProto).
    Returns:
        True if the type is a numeric type, False otherwise.
    """
    return proto_type in NUMERIC_TYPES


def get_json_allowed_types(proto_type: int, field_name: str = "") -> str:
    """
    Get the Python type(s) allowed for the JSON representation of a field.

    The result is written into a generated ``from_dict`` as the second argument of a
    ``validate_type`` call, so it names what a decoder will accept off the wire rather than what
    the dataclass attribute ends up holding. Those differ wherever Proto3 JSON permits more than
    one spelling: a 64-bit integer arrives as either a number or a string, a float as a number or
    as one of the strings ``"NaN"``, ``"Infinity"`` and ``"-Infinity"``, and a bytes field as a
    base64 string.

    Args:
        proto_type: The protobuf field type as an integer (from FieldDescriptorProto).
        field_name: The name of the protobuf field (used to determine if it's hex-encoded)

    Returns:
        A string representing the allowed Python type(s) for the JSON representation of the
        field, either a single qualified name or a parenthesized tuple of them, ready to be
        written into generated source.

    Raises:
        ValueError: If the type is neither hex encoded by name nor one of the scalar types, since
            the remaining cases fall through to ``get_python_type``.
    """
    if is_hex_encoded_field(field_name):
        return "builtins.str"
    if is_int64_type(proto_type):
        return "(builtins.int, builtins.str)"
    if is_bytes_type(proto_type):
        return "builtins.str"
    if proto_type in (
        descriptor.FieldDescriptorProto.TYPE_FLOAT,
        descriptor.FieldDescriptorProto.TYPE_DOUBLE,
    ):
        return "(builtins.float, builtins.int, builtins.str)"
    return get_python_type(proto_type)
