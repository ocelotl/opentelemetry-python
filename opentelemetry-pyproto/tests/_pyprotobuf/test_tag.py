# tests/test__tag.py
#
# encode_tag(field_number, wire_type) encodes (field_number << 3) | wire_type
# as a varint. These tests verify the formula and the varint encoding of the
# resulting tag integer, using hand-computed expected bytes.
#
# Wire type constants:
#   0  VARINT    — int32, int64, uint32, uint64, bool, enum
#   1  64BIT     — fixed64, sfixed64, double
#   2  LEN       — string, bytes, embedded messages, packed repeated
#   5  32BIT     — fixed32, sfixed32, float

from pytest import mark

from opentelemetry.pyproto._pyprotobuf import encode_tag, encode_varint


@mark.parametrize(
    ("field_number", "wire_type"),
    [
        (1,  0),   # tag = 8    → 1-byte varint
        (1,  1),   # tag = 9    → 1-byte varint
        (1,  2),   # tag = 10   → 1-byte varint
        (1,  5),   # tag = 13   → 1-byte varint
        (15, 0),   # tag = 120  → last 1-byte tag for wire type 0
        (16, 0),   # tag = 128  → first 2-byte tag for wire type 0
        (150,       0),   # tag = 1200  → 2-byte varint
        (1024,      0),   # tag = 8192  → 2-byte varint
        (1048576,   2),   # tag = 8388610  → 4-byte varint
    ],
)
def test_encode_tag_matches_formula(field_number: int, wire_type: int) -> None:
    # encode_tag must produce the same bytes as encoding the tag integer directly.
    tag_int = (field_number << 3) | wire_type
    assert encode_tag(field_number, wire_type) == encode_varint(tag_int)


def test_field_1_wire_type_0() -> None:
    # (1 << 3) | 0 = 8 → single byte 0x08
    assert encode_tag(1, 0) == b"\x08"


def test_field_1_wire_type_2() -> None:
    # (1 << 3) | 2 = 10 → single byte 0x0A
    assert encode_tag(1, 2) == b"\x0a"


def test_field_15_wire_type_0() -> None:
    # (15 << 3) | 0 = 120 → single byte 0x78 (last 1-byte wt-0 tag)
    assert encode_tag(15, 0) == b"\x78"


def test_field_16_wire_type_0() -> None:
    # (16 << 3) | 0 = 128 → two bytes 0x80 0x01 (first 2-byte wt-0 tag)
    assert encode_tag(16, 0) == b"\x80\x01"


def test_field_2_wire_type_1() -> None:
    # (2 << 3) | 1 = 17 → single byte 0x11
    assert encode_tag(2, 1) == b"\x11"


def test_field_3_wire_type_5() -> None:
    # (3 << 3) | 5 = 29 → single byte 0x1D
    assert encode_tag(3, 5) == b"\x1d"
