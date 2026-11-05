from __future__ import annotations

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from telemetry_dashboard.communication.frame_parser import (
    ParserStatistics,
    UsartFrame,
)
from telemetry_dashboard.communication.serial_manager import (
    ConnectionState,
    SerialManager,
)


class FrameReceptionStatus(QFrame):
    def __init__(
        self,
        serial_manager: SerialManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.serial_manager = serial_manager

        self.setObjectName("dashboardCard")

        self.connection_value = QLabel("Disconnected")
        self.port_value = QLabel("—")

        self.valid_value = QLabel("0")
        self.incomplete_value = QLabel("0")
        self.rejected_value = QLabel("0")
        self.discarded_value = QLabel("0")
        self.buffered_value = QLabel("0")

        self.last_can_id_value = QLabel("—")
        self.last_dlc_value = QLabel("—")
        self.last_data_value = QLabel("—")
        self.last_crc_value = QLabel("—")
        self.last_frame_time_value = QLabel("—")

        self._build_ui()
        self._connect_signals()
        self._apply_initial_state()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 9, 11, 10)
        layout.setSpacing(8)

        title = QLabel("USART Frame Reception")
        title.setObjectName("cardTitle")

        layout.addWidget(title)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(6)

        rows = [
            ("Connection", self.connection_value),
            ("Serial port", self.port_value),
            ("Valid frames", self.valid_value),
            ("Incomplete frames", self.incomplete_value),
            ("Rejected frames", self.rejected_value),
            ("Discarded bytes", self.discarded_value),
            ("Buffered bytes", self.buffered_value),
            ("Last CAN ID", self.last_can_id_value),
            ("Last DLC", self.last_dlc_value),
            ("Last data bytes", self.last_data_value),
            ("Last received CRC", self.last_crc_value),
            ("Last frame received", self.last_frame_time_value),
        ]

        for row_index, (label_text, value_label) in enumerate(rows):
            label = QLabel(label_text)
            label.setObjectName("cardTitle")

            value_label.setObjectName("statusText")
            value_label.setWordWrap(True)

            grid.addWidget(label, row_index, 0)
            grid.addWidget(value_label, row_index, 1)

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)

        layout.addLayout(grid)

        reset_button = QPushButton("Reset frame counters")
        reset_button.clicked.connect(
            self.serial_manager.reset_statistics
        )

        layout.addWidget(reset_button)

    def _connect_signals(self) -> None:
        self.serial_manager.connection_state_changed.connect(
            self._update_connection_state
        )

        self.serial_manager.connected.connect(
            self._update_connected_device
        )

        self.serial_manager.disconnected.connect(
            self._update_disconnected
        )

        self.serial_manager.statistics_changed.connect(
            self._update_statistics
        )

        self.serial_manager.frame_received.connect(
            self._update_last_frame
        )

    def _apply_initial_state(self) -> None:
        state = self.serial_manager.state

        self._update_connection_state(
            state.value,
            self._state_message(state),
        )

        connected_device = self.serial_manager.connected_device

        if connected_device is not None:
            self._update_connected_device(connected_device)

        self._update_statistics(
            self.serial_manager.statistics
        )

    def _update_connection_state(
        self,
        state_value: str,
        message: str,
    ) -> None:
        try:
            state = ConnectionState(state_value)

        except ValueError:
            state = ConnectionState.ERROR

        state_text = {
            ConnectionState.DISCONNECTED: "Disconnected",
            ConnectionState.SCANNING: "Scanning",
            ConnectionState.CONNECTING: "Connecting",
            ConnectionState.CONNECTED: "Connected",
            ConnectionState.RECONNECTING: "Reconnecting",
            ConnectionState.ERROR: "Error",
        }.get(
            state,
            "Unknown",
        )

        self.connection_value.setText(state_text)

        if state != ConnectionState.CONNECTED:
            self.port_value.setText("—")

    def _update_connected_device(
        self,
        device: object,
    ) -> None:
        device_name = getattr(
            device,
            "device",
            "",
        )

        display_name = getattr(
            device,
            "display_name",
            "",
        )

        self.connection_value.setText("Connected")

        self.port_value.setText(
            device_name
            or display_name
            or "Unknown port"
        )

    def _update_disconnected(
        self,
        reason: str,
    ) -> None:
        self.connection_value.setText("Disconnected")
        self.port_value.setText("—")

    def _update_statistics(
        self,
        statistics: ParserStatistics,
    ) -> None:
        self.valid_value.setText(
            str(statistics.valid_frames)
        )

        self.incomplete_value.setText(
            str(statistics.incomplete_frames)
        )

        self.rejected_value.setText(
            str(statistics.rejected_frames)
        )

        self.discarded_value.setText(
            str(statistics.discarded_bytes)
        )

        self.buffered_value.setText(
            str(statistics.buffered_bytes)
        )

    def _update_last_frame(
        self,
        frame: UsartFrame,
    ) -> None:
        self.last_can_id_value.setText(
            frame.can_id_hex
        )

        self.last_dlc_value.setText(
            str(frame.dlc)
        )

        self.last_data_value.setText(
            frame.data_hex or "No data"
        )

        self.last_crc_value.setText(
            frame.received_crc_hex
        )

        current_time = QDateTime.currentDateTime()

        self.last_frame_time_value.setText(
            current_time.toString("hh:mm:ss.zzz")
        )

    @staticmethod
    def _state_message(
        state: ConnectionState,
    ) -> str:
        return {
            ConnectionState.DISCONNECTED:
                "No serial device connected",
            ConnectionState.SCANNING:
                "Scanning for serial devices",
            ConnectionState.CONNECTING:
                "Connecting to serial device",
            ConnectionState.CONNECTED:
                "Serial device connected",
            ConnectionState.RECONNECTING:
                "Reconnecting to serial device",
            ConnectionState.ERROR:
                "Serial connection error",
        }.get(
            state,
            "Serial connection status unavailable",
        )