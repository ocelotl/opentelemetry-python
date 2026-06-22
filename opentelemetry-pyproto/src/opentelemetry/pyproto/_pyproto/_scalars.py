import struct

from opentelemetry.pyproto._pyproto._varint import encode_varint


def encode_uint32(value: int) -> bytes:
    return encode_varint(value & 0xFFFFFFFF)


def encode_uint64(value: int) -> bytes:
    return encode_varint(value & 0xFFFFFFFFFFFFFFFF)


def encode_bool(value: bool) -> bytes:
    return encode_varint(1 if value else 0)


def encode_int(value: int) -> bytes:
    if value < 0:
        value += 1 << 64
    return encode_varint(value)


def encode_sint32(value: int) -> bytes:
    return encode_varint((value << 1) ^ (value >> 31))


def encode_sint64(value: int) -> bytes:
    return encode_varint((value << 1) ^ (value >> 63))


def encode_float(value: float) -> bytes:
    return struct.pack("<f", value)


def encode_fixed32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def encode_sfixed32(value: int) -> bytes:
    return struct.pack("<i", value)


def encode_double(value: float) -> bytes:
    return struct.pack("<d", value)


def encode_fixed64(value: int) -> bytes:
    return struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)


def encode_sfixed64(value: int) -> bytes:
    return struct.pack("<q", value)


def encode_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return encode_varint(len(encoded)) + encoded


def encode_bytes(value: bytes) -> bytes:
    return encode_varint(len(value)) + value
