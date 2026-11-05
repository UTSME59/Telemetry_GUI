from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SignalState(str, Enum):
    """Health state of a telemetry signal."""

    VALID = "valid"
    STALE = "stale"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class SignalDefinition:
    """Static metadata describing a telemetry signal."""

    name: str
    unit: str = ""
    can_id: int | None = None
    expected_rate_hz: float | None = None

    @property
    def expected_period_s(self) -> float | None:
        """Return the expected time between updates in seconds."""

        if self.expected_rate_hz is None:
            return None

        if self.expected_rate_hz <= 0:
            return None

        return 1.0 / self.expected_rate_hz


@dataclass(frozen=True, slots=True)
class HistoryPoint:
    """One historical telemetry sample."""

    timestamp: datetime
    monotonic_timestamp: float
    value: Any
    raw_value: Any


@dataclass(frozen=True, slots=True)
class SignalSnapshot:
    """Immutable view of the current state of one signal."""

    name: str
    value: Any = None
    raw_value: Any = None
    unit: str = ""
    timestamp: datetime | None = None
    can_id: int | None = None
    update_count: int = 0
    expected_rate_hz: float | None = None
    data_age_s: float | None = None
    state: SignalState = SignalState.MISSING


@dataclass(slots=True)
class MutableSignalRecord:
    """Internal mutable storage used by SignalCache."""

    definition: SignalDefinition
    value: Any = None
    raw_value: Any = None
    timestamp: datetime | None = None
    monotonic_timestamp: float | None = None
    update_count: int = 0
    history: Any = field(default=None)

    def snapshot(
        self,
        now_monotonic: float,
        stale_after_periods: float,
    ) -> SignalSnapshot:
        """Create an immutable snapshot of this signal."""

        if self.monotonic_timestamp is None:
            age = None
            state = SignalState.MISSING
        else:
            age = max(
                0.0,
                now_monotonic - self.monotonic_timestamp,
            )

            expected_period = self.definition.expected_period_s

            if expected_period is None:
                state = SignalState.VALID
            else:
                stale_threshold = (
                    expected_period * stale_after_periods
                )

                if age > stale_threshold:
                    state = SignalState.STALE
                else:
                    state = SignalState.VALID

        return SignalSnapshot(
            name=self.definition.name,
            value=self.value,
            raw_value=self.raw_value,
            unit=self.definition.unit,
            timestamp=self.timestamp,
            can_id=self.definition.can_id,
            update_count=self.update_count,
            expected_rate_hz=self.definition.expected_rate_hz,
            data_age_s=age,
            state=state,
        )


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)