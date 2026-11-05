from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from telemetry_dashboard.cache.models import SignalSnapshot
from telemetry_dashboard.communication.serial_manager import SerialManager
from telemetry_dashboard.pages import (
    FaultsPage,
    HighVoltagePage,
    LowVoltagePage,
    MainOverviewPage,
)
from telemetry_dashboard.pages.usart_frames import UsartFramesPage
from telemetry_dashboard.services.telemetry_service import TelemetryService


class MainWindow(QMainWindow):
    """Top-level Telemetry Dashboard window."""

    PAGE_NAMES = (
        "Main Overview",
        "High Voltage",
        "Low Voltage",
        "Faults",
        "USART Frames",
    )

    IMD_SIGNAL_NAMES = {
        "IMD Fault",
        "Insulation Monitoring Device Fault",
        "Insulation Monitoring Device",
    }

    def __init__(self, serial_manager: SerialManager) -> None:
        super().__init__()
        self.serial_manager = serial_manager
        self.telemetry_service = TelemetryService(
            self,
            serial_manager=self.serial_manager,
        )
        self._imd_fault_active = False
        self._imd_fault_dialog: QMessageBox | None = None

        self.setWindowTitle("UTS Motorsports Telemetry Dashboard")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        self._build_ui()
        self.telemetry_service.signal_snapshot_updated.connect(
            self._handle_critical_signal
        )

    def _build_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_navigation())

        self.page_stack = QStackedWidget()
        root_layout.addWidget(self.page_stack, 1)

        pages = (
            MainOverviewPage(
                self.serial_manager,
                self.telemetry_service,
            ),
            HighVoltagePage(self.telemetry_service),
            LowVoltagePage(self.telemetry_service),
            FaultsPage(self.telemetry_service),
            UsartFramesPage(self.serial_manager),
        )

        for page in pages:
            self.page_stack.addWidget(page)

        self.navigation_buttons[0].setChecked(True)
        self.page_stack.setCurrentIndex(0)

    def _build_navigation(self) -> QWidget:
        navigation = QFrame()
        navigation.setObjectName("navigationPanel")
        navigation.setFixedWidth(235)

        layout = QVBoxLayout(navigation)
        layout.setContentsMargins(16, 24, 16, 20)
        layout.setSpacing(8)

        app_title = QLabel("UTS MOTORSPORTS")
        app_title.setObjectName("navigationTitle")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        app_subtitle = QLabel("Telemetry Dashboard")
        app_subtitle.setObjectName("navigationSubtitle")
        app_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(app_title)
        layout.addWidget(app_subtitle)
        layout.addSpacing(22)

        self.navigation_buttons: list[QPushButton] = []
        button_group = QButtonGroup(self)
        button_group.setExclusive(True)

        for page_index, page_name in enumerate(self.PAGE_NAMES):
            button = QPushButton(page_name)
            button.setObjectName("navigationButton")
            button.setCheckable(True)
            button.setMinimumHeight(42)
            button.clicked.connect(self._page_switch_handler(page_index))
            button_group.addButton(button)
            self.navigation_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()

        version_label = QLabel("UTS Motorsports 2026")
        version_label.setObjectName("navigationFooter")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        return navigation

    def _page_switch_handler(self, index: int) -> Callable[[bool], None]:
        return lambda _checked=False: self.page_stack.setCurrentIndex(index)

    def _handle_critical_signal(self, snapshot: SignalSnapshot) -> None:
        if snapshot.name not in self.IMD_SIGNAL_NAMES:
            return

        active = self._value_is_fault(snapshot.value)
        if active and not self._imd_fault_active:
            self._show_imd_fault_popup(snapshot)
        elif not active and self._imd_fault_active:
            self._imd_fault_active = False
            if self._imd_fault_dialog is not None:
                self._imd_fault_dialog.close()
                self._imd_fault_dialog = None

    def _show_imd_fault_popup(self, snapshot: SignalSnapshot) -> None:
        self._imd_fault_active = True

        dialog = QMessageBox(self)
        dialog.setWindowTitle("CRITICAL FAULT - IMD")
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setText("IMD FAULT ACTIVE")
        dialog.setInformativeText(
            "The Insulation Monitoring Device has reported a fault. "
            "Treat the tractive system as unsafe until the fault has been investigated and cleared."
        )
        dialog.setDetailedText(
            f"Signal: {snapshot.name}\n"
            f"Value: {snapshot.value}\n"
            f"CAN ID: {self._format_can_id(snapshot.can_id)}"
        )
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        dialog.finished.connect(self._clear_imd_dialog_reference)
        self._imd_fault_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _clear_imd_dialog_reference(self, _result: int) -> None:
        self._imd_fault_dialog = None

    @staticmethod
    def _value_is_fault(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if value is None:
            return False
        text = str(value).strip().casefold()
        return text not in {
            "",
            "0",
            "false",
            "clear",
            "ok",
            "normal",
            "inactive",
            "no fault",
        }

    @staticmethod
    def _format_can_id(can_id: int | None) -> str:
        return "--" if can_id is None else f"0x{can_id:X}"

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._imd_fault_dialog is not None:
            self._imd_fault_dialog.close()
        self.serial_manager.stop()
        self.telemetry_service.shutdown()
        event.accept()
