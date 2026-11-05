from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from telemetry_dashboard.communication.serial_manager import (
    SerialManager,
)
from telemetry_dashboard.widgets.frame_reception_status import (
    FrameReceptionStatus,
)


class UsartFramesPage(QWidget):
    def __init__(
        self,
        serial_manager: SerialManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.serial_manager = serial_manager

        self._build_ui()

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(18, 16, 18, 18)
        page_layout.setSpacing(10)

        section_heading = QLabel("USART Frames")
        section_heading.setObjectName("sectionHeading")

        section_subtitle = QLabel(
            "Low-level USART reception and frame parser status. "
            "This page displays raw frame information only; individual "
            "telemetry signals are not decoded."
        )
        section_subtitle.setObjectName("sectionSubtitle")
        section_subtitle.setWordWrap(True)

        self.frame_reception_status = FrameReceptionStatus(
            self.serial_manager
        )

        page_layout.addWidget(section_heading)
        page_layout.addWidget(section_subtitle)
        page_layout.addWidget(
            self.frame_reception_status
        )
        page_layout.addStretch()