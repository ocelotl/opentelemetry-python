# tests/test__varint.py

from pytest import raises

from opentelemetry.pyproto._pyprotobuf import encode_varint


def test_zero() -> None:
    assert encode_varint(0) == b"\x00"


def test_single_byte_max() -> None:
    assert encode_varint(127) == b"\x7f"


def test_first_two_byte_value() -> None:
    assert encode_varint(128) == b"\x80\x01"


def test_150() -> None:
    assert encode_varint(150) == b"\x96\x01"


def test_300() -> None:
    assert encode_varint(300) == b"\xac\x02"


def test_uint32_max() -> None:
    assert encode_varint(2**32 - 1) == b"\xff\xff\xff\xff\x0f"


def test_uint64_max() -> None:
    assert encode_varint(2**64 - 1) == b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01"


def test_rejects_negative_values() -> None:
    with raises(ValueError, match="varint values must be non-negative"):
        encode_varint(-1)


def test_two_byte_boundary_low() -> None:
    # 16383 = 0x3FFF — the largest value that fits in two varint bytes.
    # 7-bit groups: 0x7F (lower), 0x7F (upper, no continuation bit).
    assert encode_varint(16_383) == b"\xff\x7f"


def test_three_byte_boundary_low() -> None:
    # 16384 = 0x4000 — the first value that requires three varint bytes.
    assert encode_varint(16_384) == b"\x80\x80\x01"


def test_one() -> None:
    # 1 fits in a single byte; no continuation bit needed.
    assert encode_varint(1) == b"\x01"
