def byte_offset_to_line(code: bytes, byte_offset: int) -> int:
    if byte_offset <= 0:
        return 1
    return code[:byte_offset].count(b"\n") + 1
