from opentelemetry.pyproto._pyproto._scalars import encode_int


def encode_enum(value: int) -> bytes:
    return encode_int(value)
