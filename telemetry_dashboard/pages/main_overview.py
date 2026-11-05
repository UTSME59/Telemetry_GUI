from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from telemetry_dashboard.communication.serial_manager import SerialManager
from telemetry_dashboard.pages.base_page import DashboardPage
from telemetry_dashboard.services.telemetry_service import TelemetryService
from telemetry_dashboard.widgets import (
    MultiGraphWidget,
    NumericValueWidget,
)
from telemetry_dashboard.widgets.connection_panel import ConnectionPanel


class MainOverviewPage(DashboardPage):
    """Primary whole-vehicle telemetry overview page."""

    VEHICLE_STATE_SIGNALS = (
        "VCU State",
        "Vehicle State",
    )

    SOC_SIGNALS = (
        "Accumulator State of Charge",
        "Pack SOC",
    )

    ACCY_TEMP_SIGNALS = (
        "Maximum Cell Temperature",
        "Accumulator High Temperature",
    )

    MOTOR_TEMP_SIGNALS = (
        "Motor Temperature",
        "Motor Temp",
    )

    MOTOR_CONTROLLER_TEMP_SIGNALS = (
        "Motor Controller Temperature",
        "Inverter Temperature",
    )

    def __init__(
        self,
        serial_manager: SerialManager,
        telemetry_service: TelemetryService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            telemetry_service,
            "",
            "",
        )

        self.serial_manager = serial_manager

        # ==============================================================
        # HEADER
        # ==============================================================

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(20)

        # --------------------------------------------------------------
        # Left side: page title
        # --------------------------------------------------------------

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)

        page_title = QLabel("Main Overview")
        page_title.setObjectName("pageTitle")

        page_subtitle = QLabel(
            "Whole-vehicle health, accumulator condition, "
            "thermal state, and telemetry receiver status."
        )
        page_subtitle.setObjectName("pageSubtitle")
        page_subtitle.setWordWrap(True)

        title_layout.addWidget(page_title)
        title_layout.addWidget(page_subtitle)
        title_layout.addStretch()

        header_layout.addLayout(title_layout, 1)

        # --------------------------------------------------------------
        # Right side: telemetry receiver
        # --------------------------------------------------------------

        self.connection_panel = ConnectionPanel()

        header_layout.addWidget(
            self.connection_panel,
            0,
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignRight,
        )

        self.layout.addLayout(header_layout)

        # Connect receiver widget to SerialManager
        self._connect_receiver()

        # ==============================================================
        # NUMERIC TELEMETRY BLOCKS
        # ==============================================================

        metrics_layout = QGridLayout()
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setHorizontalSpacing(10)
        metrics_layout.setVerticalSpacing(10)

        self.pack_voltage = NumericValueWidget(
            "Pack Voltage",
            "--",
            "V",
        )

        self.soc = NumericValueWidget(
            "SOC",
            "--",
            "%",
        )

        self.vehicle_state = NumericValueWidget(
            "Vehicle State",
            "--",
            "state",
        )

        self.accy_temp = NumericValueWidget(
            "Accy High Temp",
            "--",
            "°C",
        )

        self.motor_temp = NumericValueWidget(
            "Motor Temp",
            "--",
            "°C",
        )

        self.motor_controller_temp = NumericValueWidget(
            "Motor Controller Temp",
            "--",
            "°C",
        )

        metric_widgets = (
            self.pack_voltage,
            self.soc,
            self.vehicle_state,
            self.accy_temp,
            self.motor_temp,
            self.motor_controller_temp,
        )

        for index, widget in enumerate(metric_widgets):
            row = index // 3
            column = index % 3

            metrics_layout.addWidget(
                widget,
                row,
                column,
            )

        for column in range(3):
            metrics_layout.setColumnStretch(
                column,
                1,
            )

        self.layout.addLayout(metrics_layout)

        # ==============================================================
        # HISTORY GRAPHS
        # ==============================================================

        graphs_layout = QHBoxLayout()
        graphs_layout.setContentsMargins(0, 0, 0, 0)
        graphs_layout.setSpacing(10)

        # --------------------------------------------------------------
        # Cell voltage graph
        # --------------------------------------------------------------

        self.cell_voltage_graph = MultiGraphWidget(
            "Cell Voltage History",
            (
                (
                    "Cell High",
                    "#03BFD8",
                ),
                (
                    "Cell Low",
                    "#F92785",
                ),
            ),
            "V",
        )

        # --------------------------------------------------------------
        # Temperature graph
        # --------------------------------------------------------------

        self.temperature_graph = MultiGraphWidget(
            "Temperature History",
            (
                (
                    "Accy High",
                    "#F92785",
                ),
                (
                    "Motor",
                    "#03BFD8",
                ),
                (
                    "Motor Controller",
                    "#012645",
                ),
            ),
            "°C",
        )

        graphs_layout.addWidget(
            self.cell_voltage_graph,
            1,
        )

        graphs_layout.addWidget(
            self.temperature_graph,
            1,
        )

        self.layout.addLayout(graphs_layout)

        # ==============================================================
        # STAGE 5 CACHE BINDINGS
        # ==============================================================

        # --------------------------------------------------------------
        # Pack voltage
        # --------------------------------------------------------------

        self.bind_numeric(
            self.pack_voltage,
            "Accumulator Voltage",
        )

        # --------------------------------------------------------------
        # SOC
        # --------------------------------------------------------------

        self.bind_numeric(
            self.soc,
            self.SOC_SIGNALS,
        )

        # --------------------------------------------------------------
        # Vehicle state
        #
        # Expected values:
        #
        # 0 = GLV On / Neutral
        # 1 = Precharge
        # 2 = Ready to Drive
        # 3 = Fault
        #
        # --------------------------------------------------------------

        self.bind_numeric(
            self.vehicle_state,
            self.VEHICLE_STATE_SIGNALS,
        )

        # --------------------------------------------------------------
        # Temperatures
        # --------------------------------------------------------------

        self.bind_numeric(
            self.accy_temp,
            self.ACCY_TEMP_SIGNALS,
        )

        self.bind_numeric(
            self.motor_temp,
            self.MOTOR_TEMP_SIGNALS,
        )

        self.bind_numeric(
            self.motor_controller_temp,
            self.MOTOR_CONTROLLER_TEMP_SIGNALS,
        )

        # ==============================================================
        # CELL VOLTAGE GRAPH BINDINGS
        # ==============================================================

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

        # ==============================================================
        # TEMPERATURE GRAPH BINDINGS
        # ==============================================================

        self.bind_graph_series(
            self.temperature_graph,
            "Accy High",
            self.ACCY_TEMP_SIGNALS,
        )

        self.bind_graph_series(
            self.temperature_graph,
            "Motor",
            self.MOTOR_TEMP_SIGNALS,
        )

        self.bind_graph_series(
            self.temperature_graph,
            "Motor Controller",
            self.MOTOR_CONTROLLER_TEMP_SIGNALS,
        )

        # Push page content upward
        self.finish_layout()

    def _connect_receiver(self) -> None:
        """
        Connect the Telemetry Receiver widget to SerialManager.
        """

        # ==============================================================
        # USER CONTROLS -> SERIAL MANAGER
        # ==============================================================

        self.connection_panel.device_selected.connect(
            self.serial_manager.select_port
        )

        self.connection_panel.refresh_requested.connect(
            self.serial_manager.refresh_ports
        )

        self.connection_panel.reconnect_requested.connect(
            self.serial_manager.reconnect_selected
        )

        self.connection_panel.disconnect_requested.connect(
            self.serial_manager.disconnect_manual
        )

        # ==============================================================
        # SERIAL MANAGER -> RECEIVER WIDGET
        # ==============================================================

        self.serial_manager.ports_changed.connect(
            self.connection_panel.set_available_devices
        )

        self.serial_manager.connection_state_changed.connect(
            self.connection_panel.set_connection_state
        )

        self.serial_manager.connected.connect(
            self.connection_panel.set_connected_device
        )

        self.serial_manager.disconnected.connect(
            self.connection_panel.clear_connected_device
        )

        # ==============================================================
        # INITIAL STATE
        # ==============================================================

        self.connection_panel.set_available_devices(
            self.serial_manager.available_ports
        )

        current_state = self.serial_manager.state.value

        self.connection_panel.set_connection_state(
            current_state,
            current_state.replace(
                "_",
                " ",
            ).title(),
        )

        if self.serial_manager.connected_device is not None:
            self.connection_panel.set_connected_device(
                self.serial_manager.connected_device
            )