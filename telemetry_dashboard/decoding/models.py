from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias


DecodedScalar: TypeAlias = int | float | bool | str


class SignalDataType(str, Enum):
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ENUMERATION = "enumeration"


class ByteOrder(str, Enum):
    LITTLE = "little"
    BIG = "big"


class SignalStatus(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    FAULT = "fault"
    OUT_OF_RANGE = "out_of_range"


@dataclass(frozen=True)
class LookupIssue:
    row_number: int
    field_name: str
    message: str
    severity: str = "error"

    def __str__(self) -> str:
        return (
            f"Row {self.row_number}, field '{self.field_name}': "
            f"{self.message}"
        )


@dataclass(frozen=True)
class SignalDefinition:
    can_id: int
    signal_name: str
    page: str

    start_byte: int
    start_bit: int
    bit_length: int

    signed: bool
    data_type: SignalDataType
    byte_order: ByteOrder

    scale: float = 1.0
    offset: float = 0.0
    unit: str = ""

    minimum: float | None = None
    maximum: float | None = None

    warning_low: float | None = None
    warning_high: float | None = None

    fault_low: float | None = None
    fault_high: float | None = None

    enum_map: dict[int, str] = field(default_factory=dict)

    suggested_send_rate_hz: float | None = None

    enabled: bool = True
    notes: str = ""
    source_row: int = 0


@dataclass(frozen=True)
class DecodedSignal:
    definition: SignalDefinition

    raw_value: int | float
    value: DecodedScalar
    numeric_value: float | None

    status: SignalStatus

    @property
    def name(self) -> str:
        return self.definition.signal_name

    @property
    def page(self) -> str:
        return self.definition.page

    @property
    def unit(self) -> str:
        return self.definition.unit

    @property
    def can_id(self) -> int:
        return self.definition.can_id