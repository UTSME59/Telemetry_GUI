from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from .models import (
    ByteOrder,
    LookupIssue,
    SignalDataType,
    SignalDefinition,
)


CSV_COLUMNS = (
    "enabled",
    "can_id",
    "signal_name",
    "page",
    "start_byte",
    "start_bit",
    "bit_length",
    "byte_length",
    "signed",
    "data_type",
    "byte_order",
    "scale",
    "offset",
    "unit",
    "minimum",
    "maximum",
    "warning_low",
    "warning_high",
    "fault_low",
    "fault_high",
    "enum_map",
    "suggested_send_rate_hz",
    "notes",
)


class LookupTableError(Exception):
    def __init__(self, issues: list[LookupIssue]) -> None:
        self.issues = issues
        message = "\n".join(str(issue) for issue in issues)
        super().__init__(message)


class LookupTable:
    def __init__(
        self,
        definitions: list[SignalDefinition],
        issues: list[LookupIssue] | None = None,
        source_path: Path | None = None,
    ) -> None:
        self.definitions = definitions
        self.issues = issues or []
        self.source_path = source_path

        by_can_id: dict[int, list[SignalDefinition]] = defaultdict(list)

        for definition in definitions:
            by_can_id[definition.can_id].append(definition)

        self._by_can_id = dict(by_can_id)

    def for_can_id(
        self,
        can_id: int,
    ) -> tuple[SignalDefinition, ...]:
        return tuple(self._by_can_id.get(can_id, ()))

    @classmethod
    def load_csv(
        cls,
        path: str | Path,
        *,
        strict: bool = False,
    ) -> LookupTable:
        source_path = Path(path)

        if not source_path.exists():
            issue = LookupIssue(
                row_number=0,
                field_name="file",
                message=f"Lookup table not found: {source_path}",
            )
            raise LookupTableError([issue])

        definitions: list[SignalDefinition] = []
        issues: list[LookupIssue] = []

        with source_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            if reader.fieldnames is None:
                raise LookupTableError(
                    [
                        LookupIssue(
                            row_number=1,
                            field_name="header",
                            message="CSV has no header row.",
                        )
                    ]
                )

            missing_columns = [
                column
                for column in CSV_COLUMNS
                if column not in reader.fieldnames
            ]

            if missing_columns:
                raise LookupTableError(
                    [
                        LookupIssue(
                            row_number=1,
                            field_name="header",
                            message=(
                                "Missing required columns: "
                                + ", ".join(missing_columns)
                            ),
                        )
                    ]
                )

            for row_number, row in enumerate(
                reader,
                start=2,
            ):
                definition, row_issues = _parse_row(
                    row_number,
                    row,
                )

                issues.extend(row_issues)

                if definition is not None:
                    definitions.append(definition)

        if strict and any(
            issue.severity == "error"
            for issue in issues
        ):
            raise LookupTableError(issues)

        return cls(
            definitions=definitions,
            issues=issues,
            source_path=source_path,
        )


def _parse_row(
    row_number: int,
    row: dict[str, str | None],
) -> tuple[
    SignalDefinition | None,
    list[LookupIssue],
]:
    values = {
        key: (value or "").strip()
        for key, value in row.items()
        if key is not None and not isinstance(value, list)
    }

    if not any(values.values()):
        return None, []

    enabled_text = values["enabled"].casefold()

    if enabled_text in {
        "0",
        "false",
        "no",
        "disabled",
        "off",
    }:
        return None, []

    required_core = (
        "can_id",
        "signal_name",
        "start_byte",
        "data_type",
    )

    blank_core = [
        field_name
        for field_name in required_core
        if not values[field_name]
    ]

    if blank_core:
        return (
            None,
            [
                LookupIssue(
                    row_number=row_number,
                    field_name=field_name,
                    message=(
                        "Incomplete row ignored because "
                        "this field is blank."
                    ),
                    severity="warning",
                )
                for field_name in blank_core
            ],
        )

    issues: list[LookupIssue] = []

    can_id = _parse_int(
        values["can_id"],
        row_number,
        "can_id",
        issues,
    )

    start_byte = _parse_int(
        values["start_byte"],
        row_number,
        "start_byte",
        issues,
    )

    start_bit = _parse_int(
        values["start_bit"] or "0",
        row_number,
        "start_bit",
        issues,
    )

    bit_length = _parse_optional_int(
        values["bit_length"],
        row_number,
        "bit_length",
        issues,
    )

    byte_length = _parse_optional_int(
        values["byte_length"],
        row_number,
        "byte_length",
        issues,
    )

    if bit_length is None and byte_length is None:
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="bit_length",
                message=(
                    "Provide bit_length or byte_length."
                ),
            )
        )

    elif bit_length is None and byte_length is not None:
        bit_length = byte_length * 8

    elif (
        bit_length is not None
        and byte_length is not None
        and bit_length != byte_length * 8
    ):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="byte_length",
                message=(
                    "byte_length does not match "
                    "bit_length."
                ),
            )
        )

    signed = _parse_bool(
        values["signed"] or "false",
        row_number,
        "signed",
        issues,
    )

    try:
        data_type = SignalDataType(
            values["data_type"].casefold()
        )
    except ValueError:
        data_type = SignalDataType.INTEGER

        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="data_type",
                message=(
                    "Expected integer, float, boolean, "
                    "or enumeration."
                ),
            )
        )

    try:
        byte_order = ByteOrder(
            (
                values["byte_order"]
                or "little"
            ).casefold()
        )
    except ValueError:
        byte_order = ByteOrder.LITTLE

        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="byte_order",
                message="Expected little or big.",
            )
        )

    scale = _parse_float(
        values["scale"] or "1",
        row_number,
        "scale",
        issues,
    )

    offset = _parse_float(
        values["offset"] or "0",
        row_number,
        "offset",
        issues,
    )

    minimum = _parse_optional_float(
        values["minimum"],
        row_number,
        "minimum",
        issues,
    )

    maximum = _parse_optional_float(
        values["maximum"],
        row_number,
        "maximum",
        issues,
    )

    warning_low = _parse_optional_float(
        values["warning_low"],
        row_number,
        "warning_low",
        issues,
    )

    warning_high = _parse_optional_float(
        values["warning_high"],
        row_number,
        "warning_high",
        issues,
    )

    fault_low = _parse_optional_float(
        values["fault_low"],
        row_number,
        "fault_low",
        issues,
    )

    fault_high = _parse_optional_float(
        values["fault_high"],
        row_number,
        "fault_high",
        issues,
    )

    suggested_send_rate_hz = _parse_optional_float(
        values["suggested_send_rate_hz"],
        row_number,
        "suggested_send_rate_hz",
        issues,
    )

    enum_map = _parse_enum_map(
        values["enum_map"],
        row_number,
        issues,
    )

    if (
        can_id is not None
        and not 0 <= can_id <= 0x1FFFFFFF
    ):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="can_id",
                message=(
                    "CAN ID must be between 0 and "
                    "0x1FFFFFFF."
                ),
            )
        )

    if (
        start_byte is not None
        and start_byte < 0
    ):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="start_byte",
                message="Must be zero or greater.",
            )
        )

    if (
        start_bit is not None
        and not 0 <= start_bit <= 7
    ):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="start_bit",
                message="Must be between 0 and 7.",
            )
        )

    if (
        bit_length is not None
        and bit_length <= 0
    ):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="bit_length",
                message="Must be greater than zero.",
            )
        )

    if data_type == SignalDataType.FLOAT:
        if start_bit not in {0, None}:
            issues.append(
                LookupIssue(
                    row_number=row_number,
                    field_name="start_bit",
                    message=(
                        "Float signals must start on "
                        "a byte boundary."
                    ),
                )
            )

        if bit_length not in {32, 64, None}:
            issues.append(
                LookupIssue(
                    row_number=row_number,
                    field_name="bit_length",
                    message=(
                        "Float signals must be 32 or "
                        "64 bits."
                    ),
                )
            )

        if signed:
            issues.append(
                LookupIssue(
                    row_number=row_number,
                    field_name="signed",
                    message=(
                        "signed is not used for IEEE-754 "
                        "float signals."
                    ),
                    severity="warning",
                )
            )

    if (
        data_type == SignalDataType.BOOLEAN
        and bit_length != 1
    ):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="bit_length",
                message=(
                    "Boolean signals must be exactly "
                    "1 bit."
                ),
            )
        )

    if (
        data_type == SignalDataType.ENUMERATION
        and not enum_map
    ):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="enum_map",
                message=(
                    "Enumeration has no mappings; "
                    "raw numbers will be returned."
                ),
                severity="warning",
            )
        )

    if (
        minimum is not None
        and maximum is not None
        and minimum > maximum
    ):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="minimum",
                message=(
                    "minimum cannot exceed maximum."
                ),
            )
        )

    if (
        warning_low is not None
        and warning_high is not None
        and warning_low > warning_high
    ):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="warning_low",
                message=(
                    "warning_low cannot exceed "
                    "warning_high."
                ),
            )
        )

    if (
        fault_low is not None
        and fault_high is not None
        and fault_low > fault_high
    ):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="fault_low",
                message=(
                    "fault_low cannot exceed fault_high."
                ),
            )
        )

    if (
        suggested_send_rate_hz is not None
        and suggested_send_rate_hz <= 0
    ):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="suggested_send_rate_hz",
                message=(
                    "Suggested send rate must be "
                    "greater than zero."
                ),
            )
        )

    if any(
        issue.severity == "error"
        for issue in issues
    ):
        return None, issues

    assert can_id is not None
    assert start_byte is not None
    assert start_bit is not None
    assert bit_length is not None
    assert signed is not None
    assert scale is not None
    assert offset is not None

    definition = SignalDefinition(
        can_id=can_id,
        signal_name=values["signal_name"],
        page=values["page"],
        start_byte=start_byte,
        start_bit=start_bit,
        bit_length=bit_length,
        signed=signed,
        data_type=data_type,
        byte_order=byte_order,
        scale=scale,
        offset=offset,
        unit=values["unit"],
        minimum=minimum,
        maximum=maximum,
        warning_low=warning_low,
        warning_high=warning_high,
        fault_low=fault_low,
        fault_high=fault_high,
        enum_map=enum_map,
        suggested_send_rate_hz=(
            suggested_send_rate_hz
        ),
        enabled=True,
        notes=values["notes"],
        source_row=row_number,
    )

    return definition, issues


def _parse_int(
    text: str,
    row_number: int,
    field_name: str,
    issues: list[LookupIssue],
) -> int | None:
    try:
        return int(text, 0)

    except ValueError:
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name=field_name,
                message=(
                    f"Invalid integer value: {text!r}."
                ),
            )
        )
        return None


def _parse_optional_int(
    text: str,
    row_number: int,
    field_name: str,
    issues: list[LookupIssue],
) -> int | None:
    if not text:
        return None

    return _parse_int(
        text,
        row_number,
        field_name,
        issues,
    )


def _parse_float(
    text: str,
    row_number: int,
    field_name: str,
    issues: list[LookupIssue],
) -> float | None:
    try:
        return float(text)

    except ValueError:
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name=field_name,
                message=f"Invalid number: {text!r}.",
            )
        )
        return None


def _parse_optional_float(
    text: str,
    row_number: int,
    field_name: str,
    issues: list[LookupIssue],
) -> float | None:
    if not text:
        return None

    return _parse_float(
        text,
        row_number,
        field_name,
        issues,
    )


def _parse_bool(
    text: str,
    row_number: int,
    field_name: str,
    issues: list[LookupIssue],
) -> bool | None:
    normalised = text.casefold()

    if normalised in {
        "1",
        "true",
        "yes",
        "y",
        "signed",
    }:
        return True

    if normalised in {
        "0",
        "false",
        "no",
        "n",
        "unsigned",
    }:
        return False

    issues.append(
        LookupIssue(
            row_number=row_number,
            field_name=field_name,
            message=(
                "Expected true/false, yes/no, "
                "signed/unsigned, or 1/0."
            ),
        )
    )

    return None


def _parse_enum_map(
    text: str,
    row_number: int,
    issues: list[LookupIssue],
) -> dict[int, str]:
    if not text:
        return {}

    try:
        parsed = json.loads(text)

    except json.JSONDecodeError as error:
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="enum_map",
                message=(
                    "Invalid JSON object: "
                    f"{error.msg}."
                ),
            )
        )
        return {}

    if not isinstance(parsed, dict):
        issues.append(
            LookupIssue(
                row_number=row_number,
                field_name="enum_map",
                message=(
                    "Must be a JSON object such as "
                    '{"0":"Off","1":"On"}.'
                ),
            )
        )
        return {}

    result: dict[int, str] = {}

    for key, value in parsed.items():
        try:
            if isinstance(key, int):
                integer_key = key
            else:
                integer_key = int(str(key), 0)

        except (TypeError, ValueError):
            issues.append(
                LookupIssue(
                    row_number=row_number,
                    field_name="enum_map",
                    message=(
                        f"Enumeration key {key!r} "
                        "is not an integer."
                    ),
                )
            )
            continue

        result[integer_key] = str(value)

    return result