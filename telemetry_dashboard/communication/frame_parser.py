from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from telemetry_dashboard.communication.crc import (
    CrcAlgorithm,
    CrcFunction,
    get_crc_function,
)


SOF = b"\xAA\x55"

SOF_LENGTH = 2
CAN_ID_LENGTH = 2
DLC_LENGTH = 1
CRC_LENGTH = 2

FIXED_FRAME_LENGTH = (
    SOF_LENGTH
    + CAN_ID_LENGTH
    + DLC_LENGTH
    + CRC_LENGTH
)


class CrcPolicy(StrEnum):
    DISABLED = "disabled"
    VALIDATE_IF_CONFIGURED = "validate_if_configured"
    REQUIRED = "required"


@dataclass(frozen=True, slots=True)
class UsartFrame:
    can_id: int
    dlc: int
    data: bytes
    received_crc: int
    raw: bytes
    crc_checked: bool
    crc_valid: bool | None

    @property
    def can_id_hex(self) -> str:
        return f"0x{self.can_id:04X}"

    @property
    def data_hex(self) -> str:
        return self.data.hex(" ").upper()

    @property
    def received_crc_hex(self) -> str:
        return f"0x{self.received_crc:04X}"

    @property
    def raw_hex(self) -> str:
        return self.raw.hex(" ").upper()


@dataclass(frozen=True, slots=True)
class ParserStatistics:
    valid_frames: int
    incomplete_frames: int
    rejected_frames: int
    discarded_bytes: int
    buffered_bytes: int


class UsartFrameParser:
    """
    Incremental parser for frames with the format:

        AA 55 | CAN ID | DLC | DATA | CRC

    Assumed field sizes:

        SOF:    2 bytes
        CAN ID: 2 bytes
        DLC:    1 byte
        DATA:   DLC bytes
        CRC:    2 bytes

    The parser accepts serial data in arbitrary chunks. A frame can be split
    across multiple serial reads or several frames can arrive in one read.
    """

    def __init__(
        self,
        *,
        maximum_dlc: int = 8,
        can_id_byte_order: str = "little",
        crc_byte_order: str = "little",
        crc_policy: CrcPolicy | str = CrcPolicy.DISABLED,
        crc_algorithm: CrcAlgorithm | str = CrcAlgorithm.NONE,
        crc_function: CrcFunction | None = None,
    ) -> None:
        if maximum_dlc < 0 or maximum_dlc > 255:
            raise ValueError(
                "maximum_dlc must be between 0 and 255."
            )

        if can_id_byte_order not in {"little", "big"}:
            raise ValueError(
                "can_id_byte_order must be 'little' or 'big'."
            )

        if crc_byte_order not in {"little", "big"}:
            raise ValueError(
                "crc_byte_order must be 'little' or 'big'."
            )

        self.maximum_dlc = maximum_dlc
        self.can_id_byte_order = can_id_byte_order
        self.crc_byte_order = crc_byte_order

        self.crc_policy = CrcPolicy(crc_policy)
        self.crc_algorithm = CrcAlgorithm(crc_algorithm)

        if crc_function is not None:
            self.crc_function = crc_function
        else:
            self.crc_function = get_crc_function(
                self.crc_algorithm
            )

        self._buffer = bytearray()

        self._valid_frames = 0
        self._incomplete_frames = 0
        self._rejected_frames = 0
        self._discarded_bytes = 0

        self._partial_candidate_counted = False

    @property
    def statistics(self) -> ParserStatistics:
        return ParserStatistics(
            valid_frames=self._valid_frames,
            incomplete_frames=self._incomplete_frames,
            rejected_frames=self._rejected_frames,
            discarded_bytes=self._discarded_bytes,
            buffered_bytes=len(self._buffer),
        )

    def feed(
        self,
        incoming: bytes | bytearray | memoryview,
    ) -> list[UsartFrame]:
        """
        Add incoming serial bytes to the parser.

        Returns every complete and accepted frame found after the new data
        has been added.
        """

        if not incoming:
            return []

        self._buffer.extend(incoming)

        parsed_frames: list[UsartFrame] = []

        while True:
            start_index = self._buffer.find(SOF)

            if start_index < 0:
                self._discard_without_losing_partial_sof()
                break

            if start_index > 0:
                self._discarded_bytes += start_index

                del self._buffer[:start_index]

                self._partial_candidate_counted = False

            minimum_header_length = (
                SOF_LENGTH
                + CAN_ID_LENGTH
                + DLC_LENGTH
            )

            if len(self._buffer) < minimum_header_length:
                self._count_partial_candidate_once()
                break

            dlc_index = SOF_LENGTH + CAN_ID_LENGTH
            dlc = self._buffer[dlc_index]

            if dlc > self.maximum_dlc:
                self._reject_current_candidate()
                continue

            expected_frame_length = (
                FIXED_FRAME_LENGTH
                + dlc
            )

            if len(self._buffer) < expected_frame_length:
                self._count_partial_candidate_once()
                break

            raw_frame = bytes(
                self._buffer[:expected_frame_length]
            )

            frame = self._build_frame(
                raw_frame=raw_frame,
                dlc=dlc,
            )

            if frame.crc_valid is False:
                self._reject_current_candidate()
                continue

            parsed_frames.append(frame)

            self._valid_frames += 1

            del self._buffer[:expected_frame_length]

            self._partial_candidate_counted = False

        return parsed_frames

    def reset(
        self,
        *,
        clear_statistics: bool = False,
        count_pending_as_incomplete: bool = True,
    ) -> None:
        """
        Clear buffered serial bytes.

        clear_statistics:
            Also reset all counters.

        count_pending_as_incomplete:
            Count a pending partial frame before clearing the buffer.
        """

        if (
            count_pending_as_incomplete
            and self._buffer
            and not self._partial_candidate_counted
        ):
            self._incomplete_frames += 1

        self._buffer.clear()
        self._partial_candidate_counted = False

        if clear_statistics:
            self._valid_frames = 0
            self._incomplete_frames = 0
            self._rejected_frames = 0
            self._discarded_bytes = 0

    def _build_frame(
        self,
        *,
        raw_frame: bytes,
        dlc: int,
    ) -> UsartFrame:
        can_id_start = SOF_LENGTH
        can_id_end = (
            can_id_start
            + CAN_ID_LENGTH
        )

        dlc_index = can_id_end

        data_start = dlc_index + DLC_LENGTH
        data_end = data_start + dlc

        crc_start = data_end
        crc_end = crc_start + CRC_LENGTH

        can_id_bytes = raw_frame[
            can_id_start:can_id_end
        ]

        data = raw_frame[
            data_start:data_end
        ]

        received_crc_bytes = raw_frame[
            crc_start:crc_end
        ]

        can_id = int.from_bytes(
            can_id_bytes,
            byteorder=self.can_id_byte_order,
            signed=False,
        )

        received_crc = int.from_bytes(
            received_crc_bytes,
            byteorder=self.crc_byte_order,
            signed=False,
        )

        crc_checked, crc_valid = self._check_crc(
            raw_frame=raw_frame,
            received_crc=received_crc,
        )

        return UsartFrame(
            can_id=can_id,
            dlc=dlc,
            data=data,
            received_crc=received_crc,
            raw=raw_frame,
            crc_checked=crc_checked,
            crc_valid=crc_valid,
        )

    def _check_crc(
        self,
        *,
        raw_frame: bytes,
        received_crc: int,
    ) -> tuple[bool, bool | None]:
        if self.crc_policy is CrcPolicy.DISABLED:
            return False, None

        if self.crc_function is None:
            if self.crc_policy is CrcPolicy.REQUIRED:
                return False, False

            return False, None

        # Current assumed CRC coverage:
        #
        # CAN ID + DLC + DATA
        #
        # SOF and the received CRC bytes are excluded.
        crc_input = raw_frame[
            SOF_LENGTH:-CRC_LENGTH
        ]

        calculated_crc = self.crc_function(
            crc_input
        )

        return (
            True,
            calculated_crc == received_crc,
        )

    def _reject_current_candidate(self) -> None:
        """
        Reject the current SOF candidate, then discard only its first byte.

        Discarding one byte allows the parser to search again and recover
        from a false or malformed AA 55 sequence.
        """

        self._rejected_frames += 1
        self._discarded_bytes += 1

        del self._buffer[0]

        self._partial_candidate_counted = False

    def _count_partial_candidate_once(self) -> None:
        """
        Count a partial frame only once while waiting for more bytes.
        """

        if self._partial_candidate_counted:
            return

        self._incomplete_frames += 1
        self._partial_candidate_counted = True

    def _discard_without_losing_partial_sof(self) -> None:
        """
        Discard bytes that cannot form a valid SOF.

        A trailing AA is preserved because the next serial read may begin
        with 55.
        """

        if not self._buffer:
            return

        preserve_trailing_aa = (
            self._buffer[-1] == SOF[0]
        )

        keep_count = (
            1
            if preserve_trailing_aa
            else 0
        )

        discard_count = (
            len(self._buffer)
            - keep_count
        )

        if discard_count > 0:
            self._discarded_bytes += discard_count

            del self._buffer[:discard_count]

        if keep_count:
            self._count_partial_candidate_once()
        else:
            self._partial_candidate_counted = False