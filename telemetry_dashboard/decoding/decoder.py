from __future__ import annotations

import struct

from .lookup_table import LookupTable
from .models import (
    ByteOrder,
    DecodedSignal,
    SignalDataType,
    SignalDefinition,
    SignalStatus,
)


class DecodeError(Exception):
    """Raised when a telemetry signal cannot be decoded safely."""


class TelemetryDecoder:
    def __init__(
        self,
        lookup_table: LookupTable,
    ) -> None:
        self.lookup_table = lookup_table

    def reload_lookup_table(
        self,
        path: str,
        *,
        strict: bool = False,
    ) -> list[str]:
        new_table = LookupTable.load_csv(
            path,
            strict=strict,
        )

        self.lookup_table = new_table

        return [
            str(issue)
            for issue in new_table.issues
        ]

    def decode_message(
        self,
        can_id: int,
        payload: bytes,
    ) -> list[DecodedSignal]:
        decoded_signals: list[DecodedSignal] = []

        for definition in self.lookup_table.for_can_id(
            can_id
        ):
            decoded_signals.append(
                self.decode_signal(
                    definition,
                    payload,
                )
            )

        return decoded_signals

    def decode_signal(
        self,
        definition: SignalDefinition,
        payload: bytes,
    ) -> DecodedSignal:
        self._validate_payload_length(
            definition,
            payload,
        )

        if (
            definition.data_type
            == SignalDataType.FLOAT
        ):
            raw_value: int | float = (
                self._decode_float(
                    definition,
                    payload,
                )
            )
        else:
            raw_value = self._decode_integer(
                definition,
                payload,
            )

        scaled_value = (
            raw_value * definition.scale
            + definition.offset
        )

        value: int | float | bool | str
        numeric_value: float | None

        if (
            definition.data_type
            == SignalDataType.BOOLEAN
        ):
            value = bool(raw_value)
            numeric_value = float(raw_value)

        elif (
            definition.data_type
            == SignalDataType.ENUMERATION
        ):
            integer_value = int(raw_value)

            value = definition.enum_map.get(
                integer_value,
                f"Unknown ({integer_value})",
            )

            numeric_value = float(scaled_value)

        elif (
            definition.data_type
            == SignalDataType.INTEGER
        ):
            value = _normalise_number(
                float(scaled_value)
            )

            numeric_value = float(scaled_value)

        else:
            value = float(scaled_value)
            numeric_value = float(scaled_value)

        status = _classify_status(
            definition,
            numeric_value,
        )

        return DecodedSignal(
            definition=definition,
            raw_value=raw_value,
            value=value,
            numeric_value=numeric_value,
            status=status,
        )

    @staticmethod
    def _validate_payload_length(
        definition: SignalDefinition,
        payload: bytes,
    ) -> None:
        required_bits = (
            definition.start_byte * 8
            + definition.start_bit
            + definition.bit_length
        )

        available_bits = len(payload) * 8

        if required_bits > available_bits:
            raise DecodeError(
                f"{definition.signal_name!r} requires "
                f"{required_bits} payload bits, but only "
                f"{available_bits} are available."
            )

    @staticmethod
    def _decode_integer(
        definition: SignalDefinition,
        payload: bytes,
    ) -> int:
        if (
            definition.byte_order
            == ByteOrder.LITTLE
        ):
            return _decode_little_endian_integer(
                definition,
                payload,
            )

        return _decode_big_endian_integer(
            definition,
            payload,
        )

    @staticmethod
    def _decode_float(
        definition: SignalDefinition,
        payload: bytes,
    ) -> float:
        if definition.start_bit != 0:
            raise DecodeError(
                f"Float signal "
                f"{definition.signal_name!r} "
                "must start on a byte boundary."
            )

        if definition.bit_length not in {
            32,
            64,
        }:
            raise DecodeError(
                f"Float signal "
                f"{definition.signal_name!r} "
                "must be 32 or 64 bits."
            )

        byte_length = (
            definition.bit_length // 8
        )

        start_index = definition.start_byte
        end_index = start_index + byte_length

        signal_bytes = payload[
            start_index:end_index
        ]

        if len(signal_bytes) != byte_length:
            raise DecodeError(
                f"Float signal "
                f"{definition.signal_name!r} "
                f"requires {byte_length} bytes, but "
                f"only {len(signal_bytes)} were available."
            )

        byte_order_prefix = (
            "<"
            if (
                definition.byte_order
                == ByteOrder.LITTLE
            )
            else ">"
        )

        format_code = (
            "f"
            if definition.bit_length == 32
            else "d"
        )

        try:
            unpacked_value = struct.unpack(
                byte_order_prefix + format_code,
                signal_bytes,
            )[0]

        except struct.error as error:
            raise DecodeError(
                f"Could not decode float signal "
                f"{definition.signal_name!r}: "
                f"{error}"
            ) from error

        return float(unpacked_value)


def _decode_little_endian_integer(
    definition: SignalDefinition,
    payload: bytes,
) -> int:
    payload_integer = int.from_bytes(
        payload,
        byteorder="little",
        signed=False,
    )

    shift = (
        definition.start_byte * 8
        + definition.start_bit
    )

    mask = (
        1 << definition.bit_length
    ) - 1

    raw_value = (
        payload_integer >> shift
    ) & mask

    return _apply_signed_conversion(
        raw_value,
        definition.bit_length,
        definition.signed,
    )


def _decode_big_endian_integer(
    definition: SignalDefinition,
    payload: bytes,
) -> int:
    payload_integer = int.from_bytes(
        payload,
        byteorder="big",
        signed=False,
    )

    total_payload_bits = len(payload) * 8

    shift = (
        total_payload_bits
        - definition.start_byte * 8
        - definition.start_bit
        - definition.bit_length
    )

    if shift < 0:
        raise DecodeError(
            f"Big-endian signal "
            f"{definition.signal_name!r} extends "
            "past the end of the payload."
        )

    mask = (
        1 << definition.bit_length
    ) - 1

    raw_value = (
        payload_integer >> shift
    ) & mask

    return _apply_signed_conversion(
        raw_value,
        definition.bit_length,
        definition.signed,
    )


def _apply_signed_conversion(
    raw_value: int,
    bit_length: int,
    signed: bool,
) -> int:
    if not signed:
        return raw_value

    sign_bit = 1 << (bit_length - 1)

    if raw_value & sign_bit:
        raw_value -= 1 << bit_length

    return raw_value


def _normalise_number(
    value: float,
) -> int | float:
    if value.is_integer():
        return int(value)

    return value


def _classify_status(
    definition: SignalDefinition,
    value: float | None,
) -> SignalStatus:
    if value is None:
        return SignalStatus.NORMAL

    below_minimum = (
        definition.minimum is not None
        and value < definition.minimum
    )

    above_maximum = (
        definition.maximum is not None
        and value > definition.maximum
    )

    if below_minimum or above_maximum:
        return SignalStatus.OUT_OF_RANGE

    below_fault = (
        definition.fault_low is not None
        and value <= definition.fault_low
    )

    above_fault = (
        definition.fault_high is not None
        and value >= definition.fault_high
    )

    if below_fault or above_fault:
        return SignalStatus.FAULT

    below_warning = (
        definition.warning_low is not None
        and value <= definition.warning_low
    )

    above_warning = (
        definition.warning_high is not None
        and value >= definition.warning_high
    )

    if below_warning or above_warning:
        return SignalStatus.WARNING

    return SignalStatus.NORMAL