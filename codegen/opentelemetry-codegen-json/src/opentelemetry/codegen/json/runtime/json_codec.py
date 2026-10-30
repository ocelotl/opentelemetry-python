# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Encoding and decoding helpers that every generated message module calls.

This module is hand-written, and it is also the one module of
``opentelemetry-codegen-json`` that ends up inside the generated package.
``opentelemetry.codegen.json.generator`` reads its text off disk and writes it out as
``_json_codec.py`` at the root of the generated tree, so the generated code calls these functions
without ``opentelemetry-codegen-json`` being installed. Nothing here is itself generated.

Two consequences follow from being copied rather than imported. A change here reaches a generated
package only at its next regeneration, so the copy committed under ``opentelemetry-proto-json``
can be older than this file. And every import written here becomes a runtime requirement of the
generated distribution, since it is the generated distribution that will run this code.

The functions implement the Proto3 JSON mapping described at
https://protobuf.dev/programming-guides/json/, with one OTLP deviation: ``encode_hex`` and
``decode_hex`` carry ``trace_id``, ``span_id`` and ``parent_span_id`` as hex strings where Proto3
JSON would use base64.

Every ``decode_`` function takes the protobuf field name as its last argument and uses it only to
build the message of the exception it raises, so a failure names the field that caused it rather
than only the position in the payload. A ``decode_`` function raises ``TypeError`` when the JSON
value is of the wrong Python type and ``ValueError`` when the type is right but the content is
not, and it chains neither, so the traceback stops at the field rather than exposing the internals
of ``base64`` or ``int``.
"""

from __future__ import annotations

import abc
import base64
import collections.abc
import enum
import json
import math
import typing

from typing_extensions import Self

T = typing.TypeVar("T")
M = typing.TypeVar("M", bound="JsonMessage")
EnumT = typing.TypeVar("EnumT", bound=enum.IntEnum)


class JsonMessage(abc.ABC):
    """
    Abstract base class for protobuf messages with JSON serialization.

    Every generated message class is a dataclass that inherits from this one. The two abstract
    methods are what the generator writes out, field by field, for each message; the two concrete
    methods are the same thing with ``json.dumps`` and ``json.loads`` wrapped around them, and are
    inherited unchanged.

    Instances are not validated on construction. A generated class accepts whatever the caller
    assigns to its fields, and the type checking happens on the way in from JSON, inside
    ``from_dict``.
    """

    @abc.abstractmethod
    def to_dict(self) -> dict[str, typing.Any]:
        """
        Convert this message to a dictionary.

        Returns:
            A dictionary keyed by the lowerCamelCase JSON names of the fields, holding only the
            fields that are set. A field left at its proto3 default is omitted, as is every
            member of a oneof group other than the one that is set.
        """

    @classmethod
    @abc.abstractmethod
    def from_dict(cls: type[M], data: dict[str, typing.Any]) -> M:
        """
        Create an instance from a dictionary.

        Args:
            data: A dictionary keyed by the lowerCamelCase JSON names of the fields. A key that
                no field of this message claims is ignored rather than rejected, and a field
                whose key is absent or ``None`` keeps its default.

        Returns:
            An instance of the message class this was called on.

        Raises:
            TypeError: If ``data`` is not a dictionary, or if a value in it is of a Python type
                that its field cannot accept.
            ValueError: If a value is of an acceptable type but cannot be decoded, such as a
                malformed hex string or an integer that no member of the field's enum carries.
        """

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.

        Returns:
            The output of ``to_dict`` run through ``json.dumps`` with its default settings, so
            the keys appear in insertion order and the result carries no indentation.
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, data: str | bytes) -> Self:
        """
        Deserialize from a JSON string or bytes.

        Args:
            data: A JSON document holding an object. Bytes are decoded by ``json.loads``, which
                accepts UTF-8, UTF-16 and UTF-32.

        Returns:
            An instance of the message class this was called on.

        Raises:
            json.JSONDecodeError: If ``data`` is not well-formed JSON.
            TypeError: If the document is well-formed but is not an object, or if a value in it
                is of a Python type that its field cannot accept.
            ValueError: If a value is of an acceptable type but cannot be decoded.
        """
        return cls.from_dict(json.loads(data))


def encode_hex(value: bytes | None) -> str:
    """
    Encode bytes as hex string.

    This is the OTLP form for ``trace_id``, ``span_id`` and ``parent_span_id``, where Proto3 JSON
    would use base64. The digits are lowercase, which is what ``bytes.hex`` produces.

    Args:
        value: The bytes to encode.
    Returns:
        Hex string representation of the input bytes. ``None`` and empty bytes both give the
        empty string, and a generated ``to_dict`` drops the field rather than writing that.
    """
    return value.hex() if value else ""


def encode_base64(value: bytes | None) -> str:
    """
    Encode bytes as base64 string.
    Standard Proto3 JSON mapping for bytes.

    Args:
        value: The bytes to encode.
    Returns:
        Base64 string representation of the input bytes, with the standard alphabet and padding.
        ``None`` and empty bytes both give the empty string.
    """
    return base64.b64encode(value).decode("utf-8") if value else ""


def encode_int64(value: int) -> str:
    """
    Encode 64 bit integers as strings.
    Required for int64, uint64, fixed64, sfixed64 and sint64 per Proto3 JSON spec.

    A JSON number is a double in many parsers, which cannot hold every 64-bit integer exactly, so
    the string form is what keeps the value intact across a round trip.

    Args:
        value: The integer to encode.
    Returns:
        String representation of the input integer, in base ten, with a leading minus sign when
        negative.
    """
    return str(value)


def encode_float(value: float) -> float | str:
    """
    Encode float/double values.

    JSON has no literal for a non-finite number, so Proto3 JSON spells the three of them as
    strings. ``decode_float`` reads those same three spellings back.

    Args:
        value: The float to encode.
    Returns:
        The input value, or one of the strings ``"NaN"``, ``"Infinity"`` and ``"-Infinity"`` when
        it is not finite. A NaN carries no sign here, so a negative NaN comes out as ``"NaN"``.
    """
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    return value


def encode_repeated(
    values: list[T] | None,
    map_fn: collections.abc.Callable[[T], typing.Any],
) -> list[typing.Any]:
    """
    Helper to serialize repeated fields with a mapping function.

    The generated code calls this only when the element type needs conversion. A repeated field
    of a type that is already valid JSON, such as ``string``, is assigned straight across with no
    call here.

    Args:
        values: The list of values to encode.
        map_fn: A function that takes a single value and returns its encoded form. It is applied
            to every element, including ``None``, so it has to tolerate whatever the field holds.
    Returns:
        A list of encoded values, or an empty list if input is None or empty.
    """
    return [map_fn(v) for v in values] if values else []


def decode_hex(value: str | None, field_name: str) -> bytes:
    """
    Decode hex string to bytes.

    This is the OTLP form for ``trace_id``, ``span_id`` and ``parent_span_id``. Every other bytes
    field goes through ``decode_base64`` instead.

    The length is not checked against what the field means, so a trace id of the wrong number of
    bytes decodes without complaint and is caught, if at all, further along.

    Args:
        value: The hex string to decode.
        field_name: The name of the field being decoded (for error messages).
    Returns:
        The decoded bytes, or empty bytes if input is None or empty.

    Raises:
        TypeError: If ``value`` is neither ``None`` nor a ``str``.
        ValueError: If ``value`` is a string of odd length or holds a character that is not a hex
            digit.
    """
    if not value:
        return b""
    validate_type(value, str, field_name)
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise ValueError(f"Invalid hex string for field '{field_name}': {error}") from None


def decode_base64(value: str | None, field_name: str) -> bytes:
    """
    Decode base64 string to bytes.

    ``base64.b64decode`` is called without ``validate=True``, so a character outside the base64
    alphabet is discarded rather than rejected, and only a length or padding problem that survives
    that produces an error.

    Args:
        value: The base64 string to decode.
        field_name: The name of the field being decoded (for error messages).
    Returns:
        The decoded bytes, or empty bytes if input is None or empty.

    Raises:
        TypeError: If ``value`` is neither ``None`` nor a ``str``.
        ValueError: If ``base64.b64decode`` rejects the string. Any exception it raises is
            reported as a ``ValueError`` naming the field.
    """
    if not value:
        return b""
    validate_type(value, str, field_name)
    try:
        return base64.b64decode(value)
    except Exception as error:
        raise ValueError(f"Invalid base64 string for field '{field_name}': {error}") from None


def decode_int64(value: int | str | None, field_name: str) -> int:
    """
    Parse int64 from number or string.

    Both spellings are accepted because Proto3 JSON writes a 64-bit integer as a string but
    requires parsers to take a number as well.

    No range check is applied, so a value outside the range of the protobuf type is kept as the
    arbitrary precision Python integer it parsed to.

    Args:
        value: The value to decode, which can be an int, a string, or None
        field_name: The name of the field being decoded (for error messages).
    Returns:
        The decoded integer, or 0 if input is None.

    Raises:
        TypeError: If ``value`` is neither an ``int`` nor a ``str``. A ``bool`` passes this check,
            for the reason given on ``validate_type``.
        ValueError: If ``value`` is a string that does not spell an integer.
    """
    if value is None:
        return 0
    validate_type(value, (int, str), field_name)
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid int64 value for field '{field_name}': {value}") from None


def decode_float(value: float | str | None, field_name: str) -> float:
    """
    Parse float/double from number or string, handling special values.

    Proto3 JSON has no literals for the three non-finite values, so it spells them as the strings
    ``"NaN"``, ``"Infinity"`` and ``"-Infinity"``, which are matched here before any numeric
    conversion is attempted. Those three spellings are exact and case sensitive; ``"nan"`` and
    ``"inf"`` are left to ``float``, which happens to accept them too.

    Args:
        value: The value to decode, which can be a float, int, string, or None
        field_name: The name of the field being decoded (for error messages).
    Returns:
        The decoded float, or 0.0 if input is None.

    Raises:
        TypeError: If ``value`` is none of ``None``, ``float``, ``int`` or ``str``.
        ValueError: If ``value`` is a string that ``float`` cannot parse.
    """
    if value is None:
        return 0.0
    validate_type(value, (float, int, str), field_name)
    if value == "NaN":
        return math.nan
    if value == "Infinity":
        return math.inf
    if value == "-Infinity":
        return -math.inf
    try:
        return float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid float value for field '{field_name}': {value}") from None


def decode_repeated(
    values: list[typing.Any] | None,
    item_parser: collections.abc.Callable[[typing.Any], T],
    field_name: str,
) -> list[T]:
    """
    Parse a list of values using the provided item parser function.

    The list itself is type checked here; each element is checked by ``item_parser``, which the
    generated code supplies as a lambda closing over nothing. An element that fails stops the
    whole call, so a partially decoded list is never returned.

    Args:
        values: The list of values to decode, or None.
        item_parser: A function that takes a single value and returns the parsed form.
        field_name: The name of the field being decoded (for error messages). The index of the
            offending element is not included, so an error names the field only.
    Returns:
        A list of parsed values, or an empty list if input is None.

    Raises:
        TypeError: If ``values`` is neither ``None`` nor a ``list``, or if ``item_parser`` rejects
            the type of an element.
        ValueError: If ``item_parser`` rejects the content of an element.
    """
    if values is None:
        return []
    validate_type(values, list, field_name)
    return [item_parser(v) for v in values]


def validate_type(
    value: typing.Any,
    expected_types: type | tuple[type, ...],
    field_name: str,
) -> None:
    """
    Validate that a value is of the expected type(s).
    Raises TypeError if validation fails.

    The check is ``isinstance``, so a subclass passes as its base. That matters for one case in
    practice: ``bool`` is a subclass of ``int`` in Python, so a JSON ``true`` passes a check
    against ``int`` and is then decoded as the integer 1. ``decode_enum`` rejects ``bool``
    explicitly before calling this; the other integer paths do not.

    Args:
        value: The value to validate.
        expected_types: A type or tuple of types that the value is expected to be.
        field_name: The name of the field being validated (for error messages).

    Raises:
        TypeError: If ``value`` is an instance of none of ``expected_types``. The message names
            the field, the expected types and the actual type.
    """
    if not isinstance(value, expected_types):
        raise TypeError(f"Field '{field_name}' expected {expected_types}, got {type(value).__name__}")


def decode_enum(value: int | str, enum_type: type[EnumT], field_name: str) -> EnumT:
    """
    Decode a JSON enum value into an enum member.

    Per the ProtoJSON spec, parsers must accept both enum names (str)
    and integer values (int).

    A name is matched exactly and case sensitively against the members of ``enum_type``, which are
    generated with the names the ``.proto`` file gives them. An integer has to equal the value of
    a member: an unknown number is rejected rather than kept, which is stricter than protobuf's
    own rule that an unrecognised enum value in proto3 is preserved.

    Args:
        value: The enum name or integer value to decode.
        enum_type: The enum class to decode into.
        field_name: The name of the field being decoded (for error messages).
    Returns:
        The corresponding enum member.

    Raises:
        TypeError: If ``value`` is a ``bool``, which is rejected before the type check so that a
            JSON ``true`` cannot silently become the member whose value is 1, or if it is neither
            an ``int`` nor a ``str``.
        ValueError: If ``value`` names no member of ``enum_type``, or is a number that no member
            carries.
    """
    if isinstance(value, bool):
        raise TypeError(f"Field '{field_name}' expected int or str, got bool")
    validate_type(value, (int, str), field_name)
    if isinstance(value, str):
        try:
            return enum_type[value]
        except KeyError:
            raise ValueError(f"Invalid enum name '{value}' for field '{field_name}'") from None
    try:
        return enum_type(value)
    except ValueError:
        raise ValueError(f"Invalid enum value {value} for field '{field_name}'") from None
