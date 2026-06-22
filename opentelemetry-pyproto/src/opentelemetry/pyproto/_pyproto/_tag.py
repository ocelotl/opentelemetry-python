from opentelemetry.pyproto._pyproto._varint import encode_varint


def encode_tag(field_number: int, wire_type: int) -> bytes:
    return encode_varint((field_number << 3) | wire_type)
