from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout

from telemetry_dashboard.pages.base_page import DashboardPage
from telemetry_dashboard.services.telemetry_service import TelemetryService
from telemetry_dashboard.widgets import NumericValueWidget


class LowVoltagePage(DashboardPage):
    """Low-voltage supply and PDM overview."""

    def __init__(self, telemetry_service: TelemetryService) -> None:
        super().__init__(
            telemetry_service,
            "Low Voltage",
            "Vehicle state, GLV battery condition, and PDM current.",
        )

        metrics = QHBoxLayout()
        metrics.setSpacing(10)

        self.vehicle_state = NumericValueWidget("Vehicle State", "--", "state")
        self.glv_voltage = NumericValueWidget("GLV Battery Voltage", "--", "V")
        self.pdm_current = NumericValueWidget("PDM Current", "--", "A")

        metrics.addWidget(self.vehicle_state)
        metrics.addWidget(self.glv_voltage)
        metrics.addWidget(self.pdm_current)
        self.layout.addLayout(metrics)

        self.bind_numeric(self.vehicle_state, ("VCU State", "Vehicle State"))
        self.bind_numeric(
            self.glv_voltage,
            ("GLV Battery Voltage", "Low Voltage Battery Voltage"),
        )
        self.bind_numeric(self.pdm_current, "PDM Current")

        self.finish_layout()
