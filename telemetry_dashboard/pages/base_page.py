from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from telemetry_dashboard.cache.models import SignalSnapshot
from telemetry_dashboard.services.telemetry_service import TelemetryService
from telemetry_dashboard.widgets import MultiGraphWidget, NumericValueWidget


class DashboardPage(QScrollArea):
    """Base class for cache-backed dashboard pages."""

    def __init__(
        self,
        telemetry_service: TelemetryService,
        title: str,
        subtitle: str,
    ) -> None:
        super().__init__()
        self.telemetry_service = telemetry_service
        self._numeric_bindings: dict[str, list[NumericValueWidget]] = {}
        self._graph_bindings: dict[str, list[tuple[MultiGraphWidget, str]]] = {}

        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)

        self.body = QWidget()
        self.layout = QVBoxLayout(self.body)
        self.layout.setContentsMargins(18, 16, 18, 18)
        self.layout.setSpacing(14)

        heading = QLabel(title)
        heading.setObjectName("sectionHeading")
        description = QLabel(subtitle)
        description.setObjectName("sectionSubtitle")
        description.setWordWrap(True)

        self.layout.addWidget(heading)
        self.layout.addWidget(description)
        self.setWidget(self.body)

        self.telemetry_service.signal_snapshot_updated.connect(
            self._handle_snapshot
        )

    def bind_numeric(
        self,
        widget: NumericValueWidget,
        signal_names: str | Iterable[str],
    ) -> None:
        names = self._normalise_names(signal_names)
        for name in names:
            self._numeric_bindings.setdefault(name, []).append(widget)

        self._refresh_numeric_widget(widget, names)

    def bind_graph_series(
        self,
        graph: MultiGraphWidget,
        series_label: str,
        signal_names: str | Iterable[str],
    ) -> None:
        names = self._normalise_names(signal_names)
        for name in names:
            self._graph_bindings.setdefault(name, []).append((graph, series_label))

        self._refresh_graph_series(graph, series_label, names)

    def finish_layout(self) -> None:
        self.layout.addStretch(1)

    def _handle_snapshot(self, snapshot: SignalSnapshot) -> None:
        for widget in self._numeric_bindings.get(snapshot.name, []):
            self._set_numeric_from_snapshot(widget, snapshot)

        for graph, series_label in self._graph_bindings.get(snapshot.name, []):
            self._refresh_graph_series(graph, series_label, (snapshot.name,))

    def _refresh_numeric_widget(
        self,
        widget: NumericValueWidget,
        names: tuple[str, ...],
    ) -> None:
        for name in names:
            snapshot = self.telemetry_service.get_signal(name)
            if snapshot is not None and snapshot.value is not None:
                self._set_numeric_from_snapshot(widget, snapshot)
                return

    def _refresh_graph_series(
        self,
        graph: MultiGraphWidget,
        series_label: str,
        names: tuple[str, ...],
    ) -> None:
        for name in names:
            history = self.telemetry_service.get_history(name)
            values = [point.value for point in history]
            if values:
                graph.set_series_values(series_label, values)
                return

    @staticmethod
    def _set_numeric_from_snapshot(
        widget: NumericValueWidget,
        snapshot: SignalSnapshot,
    ) -> None:
        value = snapshot.value
        if isinstance(value, float):
            value = f"{value:.2f}".rstrip("0").rstrip(".")
        widget.set_value(value, snapshot.unit or None)

    @staticmethod
    def _normalise_names(signal_names: str | Iterable[str]) -> tuple[str, ...]:
        if isinstance(signal_names, str):
            return (signal_names,)
        return tuple(signal_names)
