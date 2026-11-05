from __future__ import annotations

from telemetry_dashboard.cache.models import SignalSnapshot
from telemetry_dashboard.pages.base_page import DashboardPage
from telemetry_dashboard.services.telemetry_service import TelemetryService
from telemetry_dashboard.widgets import FaultIndicatorWidget


class FaultsPage(DashboardPage):
    """Central fault view backed by decoded fault signals."""

    SIGNAL_TO_LABEL = {
        "AMS Fault": "Accumulator Management System",
        "IMD Fault": "Insulation Monitoring Device",
        "Insulation Monitoring Device Fault": "Insulation Monitoring Device",
        "Precharge Fault": "Precharge / AIR Control",
        "VCU Fault": "VCU Plausibility",
        "PDM Fault": "PDM Output Fault",
        "Inverter Fault": "Inverter / Motor Controller",
    }

    def __init__(self, telemetry_service: TelemetryService) -> None:
        self._fault_widgets: dict[str, FaultIndicatorWidget] = {}
        super().__init__(
            telemetry_service,
            "Faults",
            "Central decoded fault view. The IMD also generates a separate critical popup from any page.",
        )

        for label in (
            "Accumulator Management System",
            "Insulation Monitoring Device",
            "Precharge / AIR Control",
            "VCU Plausibility",
            "PDM Output Fault",
            "Inverter / Motor Controller",
            "Telemetry Communication",
        ):
            widget = FaultIndicatorWidget(label)
            self._fault_widgets[label] = widget
            self.layout.addWidget(widget)

        self.finish_layout()

    def _handle_snapshot(self, snapshot: SignalSnapshot) -> None:
        super()._handle_snapshot(snapshot)
        label = self.SIGNAL_TO_LABEL.get(snapshot.name)
        if label is None:
            return
        widget = self._fault_widgets.get(label)
        if widget is None:
            return
        active = self._value_is_fault(snapshot.value)
        detail = f"{snapshot.name}: {snapshot.value}"
        widget.set_fault(active, detail if active else "No active fault")

    @staticmethod
    def _value_is_fault(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if value is None:
            return False
        return str(value).strip().casefold() not in {
            "",
            "0",
            "false",
            "clear",
            "ok",
            "normal",
            "inactive",
            "no fault",
        }
