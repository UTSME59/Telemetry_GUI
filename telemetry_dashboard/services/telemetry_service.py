from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QObject,
    QTimer,
    Signal,
    Slot,
)

from telemetry_dashboard.cache import (
    HistoryPoint,
    SignalCache,
    SignalSnapshot,
)
from telemetry_dashboard.communication.frame_parser import UsartFrame
from telemetry_dashboard.communication.serial_manager import SerialManager
from telemetry_dashboard.decoding.decoder import DecodeError, TelemetryDecoder
from telemetry_dashboard.decoding.lookup_table import LookupTable, LookupTableError


LOGGER = logging.getLogger(__name__)


DEFAULT_CACHE_CONFIG = {
    "history_seconds": 60.0,
    "max_history_points_per_signal": 5000,
    "stale_after_periods": 3.0,
    "health_refresh_ms": 500,
    "lookup_table_path": (
        "data/telemetry_lookup_table.csv"
    ),
}


class TelemetryService(QObject):
    """Connect decoded telemetry acquisition to the central cache.

    This service keeps acquisition separate from dashboard rendering.

    Data flow:

        SerialManager
            -> frame parser
            -> decoder
            -> TelemetryService
            -> SignalCache
            -> GUI widgets

    GUI widgets should consume SignalSnapshot objects or retrieve values
    through get_signal() and get_history().
    """

    signal_updated = Signal(
        str,
        object,
    )

    signal_snapshot_updated = Signal(
        object
    )

    cache_health_updated = Signal(
        object
    )

    connection_changed = Signal(
        bool,
        str,
    )

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        serial_manager: SerialManager | None = None,
        config_path: str | Path = (
            "data/cache_config.json"
        ),
        lookup_table_path: str | Path | None = None,
        history_seconds: float | None = None,
        max_history_points_per_signal: int | None = None,
        stale_after_periods: float | None = None,
        health_refresh_ms: int | None = None,
    ) -> None:
        super().__init__(parent)

        package_root = Path(__file__).resolve().parents[1]
        config_path = self._resolve_path(config_path, package_root)
        config = self._load_config(config_path)

        resolved_lookup_path = (
            lookup_table_path
            if lookup_table_path is not None
            else config["lookup_table_path"]
        )

        resolved_history_seconds = (
            history_seconds
            if history_seconds is not None
            else config["history_seconds"]
        )

        resolved_max_history_points = (
            max_history_points_per_signal
            if max_history_points_per_signal
            is not None
            else config[
                "max_history_points_per_signal"
            ]
        )

        resolved_stale_after_periods = (
            stale_after_periods
            if stale_after_periods is not None
            else config["stale_after_periods"]
        )

        resolved_health_refresh_ms = (
            health_refresh_ms
            if health_refresh_ms is not None
            else config["health_refresh_ms"]
        )

        self.cache = SignalCache(
            history_seconds=float(
                resolved_history_seconds
            ),
            max_history_points_per_signal=int(
                resolved_max_history_points
            ),
            stale_after_periods=float(
                resolved_stale_after_periods
            ),
        )

        self._lookup_table_path = self._resolve_path(
            resolved_lookup_path,
            package_root,
        )
        self._registered_lookup_signals = 0
        self._decoder: TelemetryDecoder | None = None
        self._serial_manager = serial_manager

        if self._lookup_table_path.exists():
            try:
                lookup_table = LookupTable.load_csv(self._lookup_table_path)
                self._decoder = TelemetryDecoder(lookup_table)
                self._registered_lookup_signals = self.cache.load_lookup_table(
                    self._lookup_table_path
                )
                for issue in lookup_table.issues:
                    LOGGER.warning("Lookup table: %s", issue)
            except LookupTableError as error:
                LOGGER.error("Could not load telemetry lookup table: %s", error)
        else:
            LOGGER.warning(
                "Telemetry lookup table was not found: %s",
                self._lookup_table_path,
            )

        if self._serial_manager is not None:
            self._serial_manager.frame_received.connect(self.handle_frame)
            self._serial_manager.connection_state_changed.connect(
                self._forward_connection_state
            )

        self._unsubscribe_cache = (
            self.cache.subscribe_all(
                self._forward_snapshot
            )
        )

        self._health_timer = QTimer(self)

        self._health_timer.setInterval(
            int(resolved_health_refresh_ms)
        )

        self._health_timer.timeout.connect(
            self._emit_cache_health
        )

        self._health_timer.start()

    @Slot(object)
    def handle_frame(self, frame: UsartFrame) -> None:
        """Decode one validated USART frame and update the signal cache."""

        if self._decoder is None:
            return

        try:
            decoded_signals = self._decoder.decode_message(
                frame.can_id,
                frame.data,
            )
        except DecodeError as error:
            LOGGER.warning(
                "Could not decode CAN ID %s: %s",
                frame.can_id_hex,
                error,
            )
            return

        for decoded_signal in decoded_signals:
            self.handle_decoded_signal(decoded_signal.name, decoded_signal)

    @Slot(str, str)
    def _forward_connection_state(self, state: str, message: str) -> None:
        self.connection_changed.emit(state == "connected", message)

    @Slot(str, object)
    def handle_decoded_signal(
        self,
        name: str,
        decoded: object,
    ) -> None:
        """Store a Stage 4 decoded signal.

        A decoded object may provide these attributes:

        - value
        - raw_value
        - unit
        - can_id
        - expected_rate_hz
        - timestamp

        Plain values are also accepted.
        """

        if hasattr(decoded, "value"):
            self.cache.update(
                name=name,
                value=getattr(
                    decoded,
                    "value",
                ),
                raw_value=getattr(
                    decoded,
                    "raw_value",
                    None,
                ),
                unit=getattr(
                    decoded,
                    "unit",
                    None,
                ),
                can_id=getattr(
                    decoded,
                    "can_id",
                    None,
                ),
                expected_rate_hz=getattr(
                    decoded,
                    "expected_rate_hz",
                    None,
                ),
                timestamp=getattr(
                    decoded,
                    "timestamp",
                    None,
                ),
            )

            return

        self.cache.update(
            name=name,
            value=decoded,
        )

    def store_decoded_values(
        self,
        decoded_values: dict[str, Any],
    ) -> None:
        """Store a dictionary of decoded signal values.

        This is useful when one USART or CAN frame produces several
        decoded signals.
        """

        for name, decoded in decoded_values.items():
            self.handle_decoded_signal(
                name,
                decoded,
            )

    def get_signal(
        self,
        name: str,
    ) -> SignalSnapshot | None:
        """Return the current snapshot for one signal."""

        return self.cache.get(name)

    def get_signals(
        self,
        names: list[str],
    ) -> dict[str, SignalSnapshot]:
        """Return current snapshots for several signals."""

        return self.cache.get_many(names)

    def get_all_signals(
        self,
    ) -> dict[str, SignalSnapshot]:
        """Return a snapshot of the complete signal cache."""

        return self.cache.snapshot()

    def get_history(
        self,
        name: str,
        *,
        seconds: float | None = None,
    ) -> tuple[HistoryPoint, ...]:
        """Return bounded history for a signal."""

        return self.cache.get_history(
            name,
            seconds=seconds,
        )

    def statistics(
        self,
    ) -> dict[str, Any]:
        """Return cache statistics."""

        statistics = self.cache.statistics()

        statistics["lookup_table_path"] = str(
            self._lookup_table_path
        )

        statistics["lookup_signals_registered"] = (
            self._registered_lookup_signals
        )

        return statistics

    def diagnostics(
        self,
    ) -> dict[str, Any]:
        """Return cache health and signal diagnostics."""

        diagnostics = self.cache.diagnostics()

        diagnostics["statistics"].update(
            {
                "lookup_table_path": str(
                    self._lookup_table_path
                ),
                "lookup_signals_registered": (
                    self._registered_lookup_signals
                ),
            }
        )

        return diagnostics

    def subscribe(
        self,
        name: str,
        callback,
    ):
        """Subscribe a callback to one named signal."""

        return self.cache.subscribe(
            name,
            callback,
        )

    def subscribe_all(
        self,
        callback,
    ):
        """Subscribe a callback to all signal updates."""

        return self.cache.subscribe_all(
            callback
        )

    def clear_history(
        self,
        name: str | None = None,
    ) -> None:
        """Clear cached graph history."""

        self.cache.clear_history(name)

    def shutdown(
        self,
    ) -> None:
        """Stop timers and remove internal subscriptions."""

        self._health_timer.stop()
        self._unsubscribe_cache()
        if self._serial_manager is not None:
            try:
                self._serial_manager.frame_received.disconnect(self.handle_frame)
                self._serial_manager.connection_state_changed.disconnect(
                    self._forward_connection_state
                )
            except (RuntimeError, TypeError):
                pass

    def _forward_snapshot(
        self,
        snapshot: SignalSnapshot,
    ) -> None:
        """Forward cache updates through Qt signals."""

        self.signal_updated.emit(
            snapshot.name,
            snapshot.value,
        )

        self.signal_snapshot_updated.emit(
            snapshot
        )

    @Slot()
    def _emit_cache_health(
        self,
    ) -> None:
        """Emit current cache diagnostic information."""

        self.cache_health_updated.emit(
            self.diagnostics()
        )

    @staticmethod
    def _resolve_path(path: str | Path, base: Path) -> Path:
        candidate = Path(path)
        return candidate if candidate.is_absolute() else base / candidate

    @staticmethod
    def _load_config(
        config_path: str | Path,
    ) -> dict[str, Any]:
        """Load cache configuration with default fallback values."""

        config = DEFAULT_CACHE_CONFIG.copy()

        path = Path(config_path)

        if not path.exists():
            LOGGER.warning(
                "Cache configuration file was not found: %s. "
                "Using default cache settings.",
                path,
            )

            return config

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as handle:
                loaded_config = json.load(handle)

        except (
            OSError,
            json.JSONDecodeError,
        ) as error:
            LOGGER.warning(
                "Could not load cache configuration %s: %s. "
                "Using default cache settings.",
                path,
                error,
            )

            return config

        if not isinstance(
            loaded_config,
            dict,
        ):
            LOGGER.warning(
                "Cache configuration must contain a JSON object. "
                "Using default cache settings."
            )

            return config

        for key in config:
            if key in loaded_config:
                config[key] = loaded_config[key]

        return config