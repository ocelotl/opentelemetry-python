"""Internal protobuf wire-format field builders.

Uses python-protobuf (python_protobuf) for the low-level primitives and
provides higher-level helpers for writing typed protobuf fields.
"""

from __future__ import annotations

import struct

from python_protobuf import (
    encode_fixed32,
    encode_fixed64,
    encode_sint32,
    encode_tag,
    encode_varint,
)

_WT_VARINT = 0  # int32, int64, uint32, uint64, bool, enum
_WT_64BIT = 1   # double, fixed64, sfixed64
_WT_LEN = 2     # string, bytes, embedded messages, packed arrays
_WT_32BIT = 5   # float, fixed32, sfixed32


def _msg(field: int, content: bytes) -> bytes:
    """Length-delimited field: tag + varint(len) + content."""
    return encode_tag(field, _WT_LEN) + encode_varint(len(content)) + content


def _str(field: int, value: str) -> bytes:
    """String field; omitted when empty (proto3 default)."""
    if not value:
        return b""
    utf8 = value.encode("utf-8")
    return encode_tag(field, _WT_LEN) + encode_varint(len(utf8)) + utf8


def _byt(field: int, value: bytes) -> bytes:
    """Bytes field; omitted when empty (proto3 default)."""
    if not value:
        return b""
    return encode_tag(field, _WT_LEN) + encode_varint(len(value)) + value


def _u64(field: int, value: int) -> bytes:
    """uint64/varint field; omitted when zero (proto3 default)."""
    if value == 0:
        return b""
    return encode_tag(field, _WT_VARINT) + encode_varint(value)


def _bool_field(field: int, value: bool) -> bytes:
    """bool field; omitted when False (proto3 default)."""
    if not value:
        return b""
    return encode_tag(field, _WT_VARINT) + encode_varint(1)


def _fix32(field: int, value: int) -> bytes:
    """fixed32 field (4 bytes, little-endian uint32); omitted when zero."""
    if value == 0:
        return b""
    return encode_tag(field, _WT_32BIT) + encode_fixed32(value)


def _fix64(field: int, value: int) -> bytes:
    """fixed64 field (8 bytes, little-endian uint64); omitted when zero."""
    if value == 0:
        return b""
    return encode_tag(field, _WT_64BIT) + encode_fixed64(value)


def _dbl(field: int, value: float) -> bytes:
    """double field (8 bytes, IEEE 754); omitted when zero."""
    if value == 0.0:
        return b""
    return encode_tag(field, _WT_64BIT) + struct.pack("<d", value)


def _opt_dbl(field: int, value: float | None) -> bytes:
    """Optional double field; omitted when None, written even if 0.0."""
    if value is None:
        return b""
    return encode_tag(field, _WT_64BIT) + struct.pack("<d", value)


def _sint32(field: int, value: int) -> bytes:
    """sint32 field (ZigZag varint); omitted when zero."""
    if value == 0:
        return b""
    return encode_tag(field, _WT_VARINT) + encode_sint32(value)


def _packed_uint64(field: int, values: list[int]) -> bytes:
    """Packed repeated uint64 (varint-encoded)."""
    if not values:
        return b""
    payload = b"".join(encode_varint(v) for v in values)
    return encode_tag(field, _WT_LEN) + encode_varint(len(payload)) + payload


def _packed_fix64(field: int, values: list[int]) -> bytes:
    """Packed repeated fixed64 (8-byte little-endian uint64 each)."""
    if not values:
        return b""
    payload = b"".join(encode_fixed64(v) for v in values)
    return encode_tag(field, _WT_LEN) + encode_varint(len(payload)) + payload


def _packed_double(field: int, values: list[float]) -> bytes:
    """Packed repeated double (8-byte IEEE 754 each)."""
    if not values:
        return b""
    payload = struct.pack(f"<{len(values)}d", *values)
    return encode_tag(field, _WT_LEN) + encode_varint(len(payload)) + payload
