from __future__ import annotations

import csv
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from telemetry_dashboard.cache.models import (
    HistoryPoint,
    MutableSignalRecord,
    SignalDefinition,
    SignalSnapshot,
    SignalState,
    utc_now,
)


LOGGER = logging.getLogger(__name__)

SignalCallback = Callable[[SignalSnapshot], None]


class SignalCache:
    """Thread-safe central cache for decoded telemetry signals.

    Data acquisition code writes decoded values into this class.

    Dashboard widgets should not directly process USART or CAN frames.
    Instead, widgets can:

    - Request immutable signal snapshots.
    - Request bounded historical data.
    - Subscribe to individual signals.
    - Subscribe to every signal update.

    Callback functions are called after releasing the cache lock. This
    prevents slow GUI code from blocking the data acquisition thread.
    """

    def __init__(
        self,
        *,
        history_seconds: float = 60.0,
        max_history_points_per_signal: int = 5000,
        stale_after_periods: float = 3.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialise the signal cache.

        Args:
            history_seconds:
                Maximum age of historical data retained for each signal.

            max_history_points_per_signal:
                Absolute maximum number of historical points stored for
                each signal.

            stale_after_periods:
                Number of missed expected update periods before a signal
                is considered stale.

            clock:
                Monotonic clock function. This can be replaced during
                unit testing.
        """

        if history_seconds < 0:
            raise ValueError(
                "history_seconds must be greater than or equal to 0"
            )

        if max_history_points_per_signal < 1:
            raise ValueError(
                "max_history_points_per_signal must be at least 1"
            )

        if stale_after_periods <= 0:
            raise ValueError(
                "stale_after_periods must be greater than 0"
            )

        self._history_seconds = float(history_seconds)

        self._max_history_points = int(
            max_history_points_per_signal
        )

        self._stale_after_periods = float(
            stale_after_periods
        )

        self._clock = clock

        self._lock = threading.RLock()

        self._records: dict[
            str,
            MutableSignalRecord,
        ] = {}

        self._subscriptions: dict[
            str,
            dict[int, SignalCallback],
        ] = defaultdict(dict)

        self._all_subscriptions: dict[
            int,
            SignalCallback,
        ] = {}

        self._next_subscription_id = 1

        self._started_monotonic = self._clock()

        self._total_updates = 0
        self._unknown_signal_updates = 0
        self._callback_errors = 0
        self._history_points_pruned = 0

    @property
    def history_seconds(self) -> float:
        """Maximum history age retained in seconds."""

        return self._history_seconds

    @property
    def max_history_points_per_signal(self) -> int:
        """Maximum history points retained per signal."""

        return self._max_history_points

    @property
    def stale_after_periods(self) -> float:
        """Number of expected periods before a signal becomes stale."""

        return self._stale_after_periods

    def register(
        self,
        definition: SignalDefinition,
        *,
        replace: bool = False,
    ) -> None:
        """Register metadata for one signal.

        Registering a signal before receiving it allows the cache to
        report the signal as missing.

        Args:
            definition:
                Signal metadata.

            replace:
                Replace metadata if the signal is already registered.
        """

        name = definition.name.strip()

        if not name:
            raise ValueError(
                "Signal name cannot be blank"
            )

        clean_definition = SignalDefinition(
            name=name,
            unit=definition.unit,
            can_id=definition.can_id,
            expected_rate_hz=definition.expected_rate_hz,
        )

        with self._lock:
            existing = self._records.get(name)

            if existing is not None and not replace:
                return

            if existing is None:
                history = deque(
                    maxlen=self._max_history_points
                )

                self._records[name] = MutableSignalRecord(
                    definition=clean_definition,
                    history=history,
                )
            else:
                existing.definition = clean_definition

    def register_many(
        self,
        definitions: Iterable[SignalDefinition],
        *,
        replace: bool = False,
    ) -> None:
        """Register several signal definitions."""

        for definition in definitions:
            self.register(
                definition,
                replace=replace,
            )

    def load_lookup_table(
        self,
        csv_path: str | Path,
    ) -> int:
        """Register cache metadata from the Stage 4 lookup table."""

        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Lookup table not found: {path}")

        count = 0
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required_columns = {
                "can_id",
                "signal_name",
                "unit",
                "suggested_send_rate_hz",
            }
            available_columns = set(reader.fieldnames or [])
            missing_columns = required_columns - available_columns
            if missing_columns:
                raise ValueError(
                    "Lookup table missing columns: "
                    f"{sorted(missing_columns)}"
                )

            for row in reader:
                enabled = (row.get("enabled") or "true").strip().casefold()
                if enabled in {"0", "false", "no", "disabled", "off"}:
                    continue

                name = (row.get("signal_name") or "").strip()
                if not name:
                    continue

                definition = SignalDefinition(
                    name=name,
                    unit=(row.get("unit") or "").strip(),
                    can_id=self._parse_can_id(row.get("can_id")),
                    expected_rate_hz=self._parse_float(
                        row.get("suggested_send_rate_hz")
                    ),
                )
                self.register(definition, replace=True)
                count += 1

        return count

    def update(
        self,
        name: str,
        value: Any,
        *,
        raw_value: Any = None,
        unit: str | None = None,
        can_id: int | None = None,
        expected_rate_hz: float | None = None,
        timestamp: datetime | None = None,
    ) -> SignalSnapshot:
        """Store one decoded signal update.

        Args:
            name:
                Decoded signal name.

            value:
                Scaled or engineering value.

            raw_value:
                Original unscaled signal value.

            unit:
                Optional updated unit metadata.

            can_id:
                Optional source CAN message identifier.

            expected_rate_hz:
                Optional expected update rate.

            timestamp:
                Optional timezone-aware wall-clock timestamp.

        Returns:
            Immutable snapshot containing the newly stored value.
        """

        clean_name = name.strip()

        if not clean_name:
            raise ValueError(
                "Signal name cannot be blank"
            )

        now_monotonic = self._clock()

        wall_timestamp = (
            timestamp
            if timestamp is not None
            else utc_now()
        )

        with self._lock:
            record = self._records.get(clean_name)

            if record is None:
                self._unknown_signal_updates += 1

                definition = SignalDefinition(
                    name=clean_name,
                    unit=unit or "",
                    can_id=can_id,
                    expected_rate_hz=expected_rate_hz,
                )

                record = MutableSignalRecord(
                    definition=definition,
                    history=deque(
                        maxlen=self._max_history_points
                    ),
                )

                self._records[clean_name] = record

            elif (
                unit is not None
                or can_id is not None
                or expected_rate_hz is not None
            ):
                old_definition = record.definition

                record.definition = SignalDefinition(
                    name=old_definition.name,
                    unit=(
                        old_definition.unit
                        if unit is None
                        else unit
                    ),
                    can_id=(
                        old_definition.can_id
                        if can_id is None
                        else can_id
                    ),
                    expected_rate_hz=(
                        old_definition.expected_rate_hz
                        if expected_rate_hz is None
                        else expected_rate_hz
                    ),
                )

            record.value = value

            if raw_value is None:
                record.raw_value = value
            else:
                record.raw_value = raw_value

            record.timestamp = wall_timestamp
            record.monotonic_timestamp = now_monotonic
            record.update_count += 1

            self._total_updates += 1

            if self._history_seconds > 0:
                history_was_full = (
                    len(record.history)
                    == self._max_history_points
                )

                record.history.append(
                    HistoryPoint(
                        timestamp=wall_timestamp,
                        monotonic_timestamp=now_monotonic,
                        value=value,
                        raw_value=record.raw_value,
                    )
                )

                if history_was_full:
                    self._history_points_pruned += 1

                self._prune_history_locked(
                    record,
                    now_monotonic,
                )

            snapshot = record.snapshot(
                now_monotonic,
                self._stale_after_periods,
            )

            callbacks = list(
                self._subscriptions.get(
                    clean_name,
                    {},
                ).values()
            )

            callbacks.extend(
                self._all_subscriptions.values()
            )

        self._invoke_callbacks(
            callbacks,
            snapshot,
        )

        return snapshot

    def get(
        self,
        name: str,
    ) -> SignalSnapshot | None:
        """Return the latest snapshot for one signal."""

        now = self._clock()

        with self._lock:
            record = self._records.get(name)

            if record is None:
                return None

            return record.snapshot(
                now,
                self._stale_after_periods,
            )

    def get_many(
        self,
        names: Iterable[str],
    ) -> dict[str, SignalSnapshot]:
        """Return snapshots for several signal names."""

        now = self._clock()

        with self._lock:
            return {
                name: self._records[name].snapshot(
                    now,
                    self._stale_after_periods,
                )
                for name in names
                if name in self._records
            }

    def snapshot(
        self,
    ) -> dict[str, SignalSnapshot]:
        """Return an immutable snapshot of every registered signal."""

        now = self._clock()

        with self._lock:
            return {
                name: record.snapshot(
                    now,
                    self._stale_after_periods,
                )
                for name, record
                in self._records.items()
            }

    def get_history(
        self,
        name: str,
        *,
        seconds: float | None = None,
    ) -> tuple[HistoryPoint, ...]:
        """Return bounded historical values for one signal.

        Args:
            name:
                Signal name.

            seconds:
                Optionally limit the returned values to the specified
                number of most recent seconds.

        Returns:
            Immutable tuple of history points.
        """

        now = self._clock()

        with self._lock:
            record = self._records.get(name)

            if record is None:
                return ()

            self._prune_history_locked(
                record,
                now,
            )

            points = tuple(record.history)

        if seconds is None:
            return points

        if seconds < 0:
            raise ValueError(
                "seconds must be greater than or equal to 0"
            )

        cutoff = now - seconds

        return tuple(
            point
            for point in points
            if point.monotonic_timestamp >= cutoff
        )

    def state_counts(
        self,
    ) -> dict[SignalState, int]:
        """Return the number of signals in each state."""

        counts = {
            state: 0
            for state in SignalState
        }

        for snapshot in self.snapshot().values():
            counts[snapshot.state] += 1

        return counts

    def statistics(
        self,
    ) -> dict[str, Any]:
        """Return cache-level statistics."""

        now = self._clock()

        with self._lock:
            snapshots = [
                record.snapshot(
                    now,
                    self._stale_after_periods,
                )
                for record
                in self._records.values()
            ]

            history_points = sum(
                len(record.history)
                for record
                in self._records.values()
            )

            subscriber_count = (
                len(self._all_subscriptions)
                + sum(
                    len(items)
                    for items
                    in self._subscriptions.values()
                )
            )

            valid_signals = sum(
                snapshot.state is SignalState.VALID
                for snapshot in snapshots
            )

            stale_signals = sum(
                snapshot.state is SignalState.STALE
                for snapshot in snapshots
            )

            missing_signals = sum(
                snapshot.state is SignalState.MISSING
                for snapshot in snapshots
            )

            return {
                "uptime_s": max(
                    0.0,
                    now - self._started_monotonic,
                ),
                "registered_signals": len(
                    self._records
                ),
                "valid_signals": valid_signals,
                "stale_signals": stale_signals,
                "missing_signals": missing_signals,
                "total_updates": self._total_updates,
                "unknown_signal_updates": (
                    self._unknown_signal_updates
                ),
                "history_points": history_points,
                "history_points_pruned": (
                    self._history_points_pruned
                ),
                "subscriber_count": subscriber_count,
                "callback_errors": (
                    self._callback_errors
                ),
                "history_seconds": (
                    self._history_seconds
                ),
                "max_history_points_per_signal": (
                    self._max_history_points
                ),
                "stale_after_periods": (
                    self._stale_after_periods
                ),
            }

    def diagnostics(
        self,
    ) -> dict[str, Any]:
        """Return detailed signal-health diagnostics."""

        signals = self.snapshot()

        stale_signals = sorted(
            name
            for name, item in signals.items()
            if item.state is SignalState.STALE
        )

        missing_signals = sorted(
            name
            for name, item in signals.items()
            if item.state is SignalState.MISSING
        )

        oldest_data_age = max(
            (
                item.data_age_s or 0.0
                for item in signals.values()
            ),
            default=0.0,
        )

        return {
            "statistics": self.statistics(),
            "stale": stale_signals,
            "missing": missing_signals,
            "oldest_data_age_s": oldest_data_age,
        }

    def subscribe(
        self,
        name: str,
        callback: SignalCallback,
    ) -> Callable[[], None]:
        """Subscribe to updates for one signal.

        Returns:
            Function that removes the subscription.
        """

        if not callable(callback):
            raise TypeError(
                "callback must be callable"
            )

        subscription_id = (
            self._allocate_subscription_id()
        )

        with self._lock:
            self._subscriptions[name][
                subscription_id
            ] = callback

        return lambda: self._unsubscribe(
            name,
            subscription_id,
        )

    def subscribe_all(
        self,
        callback: SignalCallback,
    ) -> Callable[[], None]:
        """Subscribe to every signal update.

        Returns:
            Function that removes the subscription.
        """

        if not callable(callback):
            raise TypeError(
                "callback must be callable"
            )

        subscription_id = (
            self._allocate_subscription_id()
        )

        with self._lock:
            self._all_subscriptions[
                subscription_id
            ] = callback

        return lambda: self._unsubscribe_all(
            subscription_id
        )

    def clear_history(
        self,
        name: str | None = None,
    ) -> None:
        """Clear history for one signal or every signal."""

        with self._lock:
            if name is None:
                for record in self._records.values():
                    record.history.clear()

                return

            record = self._records.get(name)

            if record is not None:
                record.history.clear()

    def _prune_history_locked(
        self,
        record: MutableSignalRecord,
        now: float,
    ) -> None:
        """Remove historical points older than the configured age.

        The caller must already hold the cache lock.
        """

        cutoff = now - self._history_seconds

        while (
            record.history
            and record.history[
                0
            ].monotonic_timestamp < cutoff
        ):
            record.history.popleft()

            self._history_points_pruned += 1

    def _allocate_subscription_id(
        self,
    ) -> int:
        """Create a unique callback subscription identifier."""

        with self._lock:
            value = self._next_subscription_id
            self._next_subscription_id += 1

            return value

    def _unsubscribe(
        self,
        name: str,
        subscription_id: int,
    ) -> None:
        """Remove a signal-specific subscription."""

        with self._lock:
            group = self._subscriptions.get(name)

            if group is None:
                return

            group.pop(
                subscription_id,
                None,
            )

            if not group:
                self._subscriptions.pop(
                    name,
                    None,
                )

    def _unsubscribe_all(
        self,
        subscription_id: int,
    ) -> None:
        """Remove a global subscription."""

        with self._lock:
            self._all_subscriptions.pop(
                subscription_id,
                None,
            )

    def _invoke_callbacks(
        self,
        callbacks: list[SignalCallback],
        snapshot: SignalSnapshot,
    ) -> None:
        """Invoke callbacks without allowing failures to stop acquisition."""

        for callback in callbacks:
            try:
                callback(snapshot)

            except Exception:
                with self._lock:
                    self._callback_errors += 1

                LOGGER.exception(
                    "Telemetry cache callback failed for %s",
                    snapshot.name,
                )

    @staticmethod
    def _parse_can_id(
        value: str | None,
    ) -> int | None:
        """Parse a decimal or hexadecimal CAN identifier."""

        text = (value or "").strip()

        if not text:
            return None

        return int(
            text,
            0,
        )

    @staticmethod
    def _parse_float(
        value: str | None,
    ) -> float | None:
        """Parse an optional floating-point lookup-table value."""

        text = (value or "").strip()

        if not text:
            return None

        return float(text)