def encode_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varint values must be non-negative")
    output = bytearray()
    while value > 0x7F:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value)
    return bytes(output)
