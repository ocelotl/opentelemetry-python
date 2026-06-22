# tests/test__enum.py
#
# encode_enum encodes an integer enum value using the same wire format as
# int32: non-negative values as a plain varint, negative values as a 64-bit
# two's-complement varint. These tests verify that contract using hand-computed
# expected byte literals.

from opentelemetry.pyproto._pyproto import encode_enum, encode_int


def test_zero() -> None:
    # The proto3 default enum value is always 0.
    assert encode_enum(0) == b"\x00"


def test_one() -> None:
    # Typical enum constant fits in a single varint byte.
    assert encode_enum(1) == b"\x01"


def test_two() -> None:
    assert encode_enum(2) == b"\x02"


def test_two_byte_value() -> None:
    # A large enum constant that requires two varint bytes (same as encode_int(300)).
    assert encode_enum(300) == b"\xac\x02"


def test_negative_value() -> None:
    # Negative enum values use 64-bit two's-complement encoding.
    # -1 → 10-byte varint for 2^64-1.
    assert encode_enum(-1) == b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01"


def test_matches_encode_int_for_positive_values() -> None:
    # encode_enum and encode_int must produce identical bytes for non-negative inputs.
    for value in [0, 1, 2, 127, 128, 255, 300, 2**16]:
        assert encode_enum(value) == encode_int(value)


def test_matches_encode_int_for_negative_values() -> None:
    for value in [-1, -2, -(2**31)]:
        assert encode_enum(value) == encode_int(value)
