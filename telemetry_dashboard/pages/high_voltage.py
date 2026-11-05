from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout

from telemetry_dashboard.pages.base_page import DashboardPage
from telemetry_dashboard.services.telemetry_service import TelemetryService
from telemetry_dashboard.widgets import GraphWidget, MultiGraphWidget, NumericValueWidget


class HighVoltagePage(DashboardPage):
    """High-voltage accumulator and thermal overview."""

    def __init__(self, telemetry_service: TelemetryService) -> None:
        super().__init__(
            telemetry_service,
            "High Voltage",
            "Accumulator limits, auxiliary rails, temperatures, cell voltage spread, pack voltage, and cooling fan speed.",
        )

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(10)
        metrics.setVerticalSpacing(10)

        self.s_aux_positive = NumericValueWidget("S_AUX +", "--", "V")
        self.s_aux_negative = NumericValueWidget("S_AUX -", "--", "V")
        self.pack_soc = NumericValueWidget("Pack SOC", "--", "%")
        self.dcl = NumericValueWidget("DCL", "--", "A")
        self.ccl = NumericValueWidget("CCL", "--", "A")
        self.accy_temp = NumericValueWidget("Accy High Temp", "--", "°C")
        self.motor_temp = NumericValueWidget("Motor Temp", "--", "°C")
        self.motor_controller_temp = NumericValueWidget(
            "Motor Controller Temp", "--", "°C"
        )
        self.fan_speed = NumericValueWidget("Fan Speed", "--", "rpm")

        widgets = (
            self.s_aux_positive,
            self.s_aux_negative,
            self.pack_soc,
            self.dcl,
            self.ccl,
            self.fan_speed,
            self.accy_temp,
            self.motor_temp,
            self.motor_controller_temp,
        )
        for index, widget in enumerate(widgets):
            metrics.addWidget(widget, index // 3, index % 3)
        for column in range(3):
            metrics.setColumnStretch(column, 1)
        self.layout.addLayout(metrics)

        self.cell_voltage_graph = MultiGraphWidget(
            "Cell Voltage History",
            (
                ("Cell High", "#03BFD8"),
                ("Cell Low", "#F92785"),
            ),
            "V",
        )
        self.pack_voltage_graph = GraphWidget("Pack Voltage History", unit="V")

        graph_row = QHBoxLayout()
        graph_row.setSpacing(10)
        graph_row.addWidget(self.cell_voltage_graph, 1)
        graph_row.addWidget(self.pack_voltage_graph, 1)
        self.layout.addLayout(graph_row)

        self.bind_numeric(self.s_aux_positive, ("S_AUX +", "S AUX Positive"))
        self.bind_numeric(self.s_aux_negative, ("S_AUX -", "S AUX Negative"))
        self.bind_numeric(
            self.pack_soc,
            ("Pack SOC", "Accumulator State of Charge"),
        )
        self.bind_numeric(self.dcl, ("DCL", "Discharge Current Limit"))
        self.bind_numeric(self.ccl, ("CCL", "Charge Current Limit"))
        self.bind_numeric(
            self.accy_temp,
            ("Accumulator High Temperature", "Maximum Cell Temperature"),
        )
        self.bind_numeric(self.motor_temp, ("Motor Temperature", "Motor Temp"))
        self.bind_numeric(
            self.motor_controller_temp,
            ("Motor Controller Temperature", "Inverter Temperature"),
        )
        self.bind_numeric(self.fan_speed, ("Fan Speed", "Radiator Fan Speed"))

        self.bind_graph_series(
            self.cell_voltage_graph,
            "Cell High",
            "Maximum Cell Voltage",
        )
        self.bind_graph_series(
            self.cell_voltage_graph,
            "Cell Low",
            "Minimum Cell Voltage",
        )
        self.bind_graph_series(
            self.pack_voltage_graph,
            "Pack Voltage History",
            "Accumulator Voltage",
        )

        self.finish_layout()
