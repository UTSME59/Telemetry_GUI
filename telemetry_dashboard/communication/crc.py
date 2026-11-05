from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum


class CrcAlgorithm(StrEnum):
    NONE = "none"
    CRC16_CCITT_FALSE = "crc16_ccitt_false"


CrcFunction = Callable[[bytes], int]


def crc16_ccitt_false(data: bytes) -> int:
    """
    Calculate CRC-16/CCITT-FALSE.

    Polynomial: 0x1021
    Initial value: 0xFFFF
    Final XOR: 0x0000
    Reflected: No
    """

    crc = 0xFFFF

    for value in data:
        crc ^= value << 8

        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF

    return crc


CRC_FUNCTIONS: dict[CrcAlgorithm, CrcFunction | None] = {
    CrcAlgorithm.NONE: None,
    CrcAlgorithm.CRC16_CCITT_FALSE: crc16_ccitt_false,
}


def get_crc_function(
    algorithm: CrcAlgorithm | str,
) -> CrcFunction | None:
    selected_algorithm = CrcAlgorithm(algorithm)

    return CRC_FUNCTIONS[selected_algorithm]