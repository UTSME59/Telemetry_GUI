from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from telemetry_dashboard.communication.serial_manager import (
    ConnectionState,
    SerialDeviceInfo,
)


class ConnectionPanel(QFrame):
    device_selected = Signal(str)
    refresh_requested = Signal()
    reconnect_requested = Signal()
    disconnect_requested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("receiverCard")
        self.setMinimumWidth(470)
        self.setMaximumWidth(620)

        self._state = ConnectionState.SCANNING
        self._connected_port = ""

        self._build_ui()

        self.set_connection_state(
            ConnectionState.SCANNING.value,
            "Select a serial device",
        )

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            14,
            11,
            14,
            11,
        )
        main_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(7)

        title_label = QLabel(
            "Telemetry Receiver"
        )
        title_label.setObjectName(
            "receiverCardTitle"
        )

        self.status_indicator = QLabel()
        self.status_indicator.setObjectName(
            "receiverStatusIndicator"
        )
        self.status_indicator.setFixedSize(
            10,
            10,
        )

        self.state_label = QLabel("Scanning")
        self.state_label.setObjectName(
            "receiverStateText"
        )

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        telemetry_link_layout = QHBoxLayout()
        telemetry_link_layout.setSpacing(7)

        telemetry_link_label = QLabel("Telemetry Link")
        telemetry_link_label.setObjectName("receiverDetailHeading")

        telemetry_link_layout.addWidget(telemetry_link_label)
        telemetry_link_layout.addStretch()
        telemetry_link_layout.addWidget(
            self.status_indicator,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        telemetry_link_layout.addWidget(self.state_label)

        main_layout.addLayout(telemetry_link_layout)

        selection_layout = QHBoxLayout()
        selection_layout.setSpacing(7)

        self.device_combo = QComboBox()
        self.device_combo.setObjectName(
            "receiverDeviceCombo"
        )
        self.device_combo.setMinimumWidth(300)

        self.device_combo.addItem(
            "No serial devices detected",
            "",
        )
        self.device_combo.setEnabled(False)

        # Selecting an item immediately requests connection.
        self.device_combo.activated.connect(
            self._handle_device_selection
        )

        self.refresh_button = QPushButton(
            "Refresh"
        )
        self.refresh_button.setObjectName(
            "receiverRefreshButton"
        )
        self.refresh_button.clicked.connect(
            self.refresh_requested.emit
        )

        selection_layout.addWidget(
            self.device_combo,
            1,
        )
        selection_layout.addWidget(
            self.refresh_button
        )

        main_layout.addLayout(selection_layout)

        details_layout = QGridLayout()
        details_layout.setHorizontalSpacing(14)
        details_layout.setVerticalSpacing(3)

        details_layout.addWidget(
            self._create_heading("Port"),
            0,
            0,
        )
        details_layout.addWidget(
            self._create_heading("Device"),
            0,
            1,
        )
        details_layout.addWidget(
            self._create_heading("VID:PID"),
            0,
            2,
        )

        self.port_value = self._create_value()
        self.device_value = self._create_value()
        self.usb_value = self._create_value()

        self.device_value.setWordWrap(True)

        details_layout.addWidget(
            self.port_value,
            1,
            0,
        )
        details_layout.addWidget(
            self.device_value,
            1,
            1,
        )
        details_layout.addWidget(
            self.usb_value,
            1,
            2,
        )

        details_layout.setColumnStretch(1, 1)

        main_layout.addLayout(details_layout)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        self.message_label = QLabel(
            "Select a serial device"
        )
        self.message_label.setObjectName(
            "receiverMessage"
        )
        self.message_label.setWordWrap(True)

        self.action_button = QPushButton(
            "Reconnect"
        )
        self.action_button.setObjectName(
            "receiverActionButton"
        )
        self.action_button.setFixedWidth(90)
        self.action_button.clicked.connect(
            self._handle_action_button
        )

        bottom_layout.addWidget(
            self.message_label,
            1,
        )
        bottom_layout.addWidget(
            self.action_button,
        )

        main_layout.addLayout(bottom_layout)

    @staticmethod
    def _create_heading(
        text: str,
    ) -> QLabel:
        label = QLabel(text)
        label.setObjectName(
            "receiverDetailHeading"
        )
        return label

    @staticmethod
    def _create_value() -> QLabel:
        label = QLabel("--")
        label.setObjectName(
            "receiverDetailValue"
        )
        return label

    @Slot(object)
    def set_available_devices(
        self,
        devices: list[SerialDeviceInfo],
    ) -> None:
        current_port = (
            self._connected_port
            or str(
                self.device_combo.currentData()
                or ""
            )
        )

        self.device_combo.blockSignals(True)
        self.device_combo.clear()

        if not devices:
            self.device_combo.addItem(
                "No serial devices detected",
                "",
            )
            self.device_combo.setEnabled(False)

        else:
            self.device_combo.addItem(
                "Select a serial device...",
                "",
            )

            for device in devices:
                self.device_combo.addItem(
                    device.display_name,
                    device.device,
                )

            self.device_combo.setEnabled(True)

            if current_port:
                matching_index = (
                    self.device_combo.findData(
                        current_port
                    )
                )

                if matching_index >= 0:
                    self.device_combo.setCurrentIndex(
                        matching_index
                    )

        self.device_combo.blockSignals(False)

    @Slot(str, str)
    def set_connection_state(
        self,
        state_value: str,
        message: str,
    ) -> None:
        try:
            self._state = ConnectionState(
                state_value
            )

        except ValueError:
            self._state = ConnectionState.ERROR

        state_names = {
            ConnectionState.DISCONNECTED:
                "Disconnected",
            ConnectionState.SCANNING:
                "Scanning",
            ConnectionState.CONNECTING:
                "Connecting",
            ConnectionState.CONNECTED:
                "Connected",
            ConnectionState.RECONNECTING:
                "Reconnecting",
            ConnectionState.ERROR:
                "Error",
        }

        self.state_label.setText(
            state_names[self._state]
        )

        self.message_label.setText(
            message or "--"
        )

        self.status_indicator.setProperty(
            "connectionState",
            self._state.value,
        )

        self.status_indicator.style().unpolish(
            self.status_indicator
        )
        self.status_indicator.style().polish(
            self.status_indicator
        )
        self.status_indicator.update()

        if self._state == ConnectionState.CONNECTED:
            self.action_button.setText(
                "Disconnect"
            )
            self.action_button.setEnabled(True)

        elif self._state in {
            ConnectionState.CONNECTING,
            ConnectionState.RECONNECTING,
        }:
            self.action_button.setText(
                "Reconnect"
            )
            self.action_button.setEnabled(False)

        else:
            self.action_button.setText(
                "Reconnect"
            )
            self.action_button.setEnabled(
                bool(
                    self.device_combo.currentData()
                )
            )

    @Slot(object)
    def set_connected_device(
        self,
        device: SerialDeviceInfo,
    ) -> None:
        self._connected_port = device.device

        self.port_value.setText(
            device.device
        )

        device_name = (
            device.description
            or device.product
            or device.manufacturer
            or "Serial Device"
        )

        self.device_value.setText(
            device_name
        )

        if (
            device.vid is not None
            and device.pid is not None
        ):
            usb_identifier = (
                f"{device.vid_hex}:"
                f"{device.pid_hex}"
            )
        else:
            usb_identifier = "Not reported"

        self.usb_value.setText(
            usb_identifier
        )

        selected_index = (
            self.device_combo.findData(
                device.device
            )
        )

        if selected_index >= 0:
            self.device_combo.blockSignals(True)
            self.device_combo.setCurrentIndex(
                selected_index
            )
            self.device_combo.blockSignals(False)

    @Slot(str)
    def clear_connected_device(
        self,
        reason: str = "",
    ) -> None:
        self.port_value.setText("--")
        self.device_value.setText("--")
        self.usb_value.setText("--")

        if reason:
            self.message_label.setText(reason)

    @Slot(int)
    def _handle_device_selection(
        self,
        index: int,
    ) -> None:
        port_name = str(
            self.device_combo.itemData(index)
            or ""
        ).strip()

        if not port_name:
            return

        self.action_button.setEnabled(False)

        self.device_selected.emit(
            port_name
        )

    def _handle_action_button(self) -> None:
        if self._state == ConnectionState.CONNECTED:
            self.disconnect_requested.emit()
        else:
            self.reconnect_requested.emit()