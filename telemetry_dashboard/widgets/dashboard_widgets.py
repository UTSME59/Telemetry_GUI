from collections.abc import Iterable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class DashboardCard(QFrame):
    """Base container used by all Telemetry Dashboard dashboard widgets."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setObjectName("dashboardCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )


class NumericValueWidget(DashboardCard):
    """Displays a named numeric value with an optional engineering unit."""

    def __init__(
        self,
        title: str,
        value: object = "--",
        unit: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.title_label = QLabel(title)
        self.value_label = QLabel(str(value))
        self.unit_label = QLabel(unit)

        self.title_label.setObjectName("cardTitle")
        self.value_label.setObjectName("numericValue")
        self.unit_label.setObjectName("numericUnit")

        # The title has no separate background panel. It sits directly
        # inside the white dashboard card.
        self.title_label.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
        )
        self.value_label.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
        )
        self.unit_label.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
        )

        self.title_label.setWordWrap(True)

        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(8)

        value_row.addWidget(
            self.value_label,
            0,
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter,
        )

        value_row.addWidget(
            self.unit_label,
            0,
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignBottom,
        )

        value_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addLayout(value_row)

        self.setMinimumHeight(98)

    def set_value(
        self,
        value: object,
        unit: str | None = None,
    ) -> None:
        """Update the displayed value and optionally update its unit."""

        self.value_label.setText(str(value))

        if unit is not None:
            self.unit_label.setText(unit)

    def clear_value(self) -> None:
        """Reset the displayed value to the placeholder state."""

        self.value_label.setText("--")


class StatusLightWidget(DashboardCard):
    """Displays a named operating state using text and a status light."""

    COLORS = {
        "off": "#9E9E9E",
        "ok": "#03BFD8",
        "warning": "#F6B320",
        "fault": "#D32F2F",
        "info": "#012645",
    }

    def __init__(
        self,
        title: str,
        state_text: str = "Unknown",
        state: str = "off",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.title_label = QLabel(title)
        self.state_label = QLabel(state_text)
        self.light = QLabel()

        self.title_label.setObjectName("cardTitle")
        self.state_label.setObjectName("statusText")
        self.light.setObjectName("statusLight")

        self.title_label.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
        )
        self.state_label.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
        )

        self.title_label.setWordWrap(True)

        self.light.setFixedSize(16, 16)
        self.light.setToolTip(state_text)

        state_row = QHBoxLayout()
        state_row.setContentsMargins(0, 0, 0, 0)
        state_row.setSpacing(12)

        state_row.addWidget(
            self.light,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        state_row.addWidget(
            self.state_label,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        state_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        layout.addWidget(self.title_label)
        layout.addLayout(state_row)

        self.setMinimumHeight(82)

        self.set_state(state_text, state)

    def set_state(
        self,
        state_text: str,
        state: str,
    ) -> None:
        """Update the state label and status-light colour."""

        normalised_state = state.strip().lower()
        colour = self.COLORS.get(
            normalised_state,
            self.COLORS["off"],
        )

        self.state_label.setText(state_text)
        self.light.setToolTip(state_text)

        # The indicator remains circular because it represents a lamp,
        # while all containing dashboard cards remain square.
        self.light.setStyleSheet(
            f"""
            QLabel {{
                background-color: {colour};
                border: 1px solid #012645;
                border-radius: 8px;
            }}
            """
        )


class FaultIndicatorWidget(DashboardCard):
    """Displays the current state and detail text for one fault."""

    def __init__(
        self,
        fault_name: str,
        active: bool = False,
        detail: str = "No active fault",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.fault_name_label = QLabel(fault_name)
        self.detail_label = QLabel(detail)
        self.badge_label = QLabel()

        self.fault_name_label.setObjectName("faultName")
        self.detail_label.setObjectName("faultDetail")

        self.fault_name_label.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
        )
        self.detail_label.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
        )
        self.badge_label.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
        )

        self.fault_name_label.setWordWrap(True)
        self.detail_label.setWordWrap(True)

        self.badge_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter,
        )
        self.badge_label.setMinimumWidth(74)
        self.badge_label.setMaximumWidth(90)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)

        text_layout.addWidget(self.fault_name_label)
        text_layout.addWidget(self.detail_label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(14)

        layout.addLayout(text_layout, 1)

        layout.addWidget(
            self.badge_label,
            0,
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter,
        )

        self.setMinimumHeight(82)

        self.set_fault(active, detail)

    def set_fault(
        self,
        active: bool,
        detail: str | None = None,
    ) -> None:
        """Update the fault badge and optional detail text."""

        self.badge_label.setText(
            "ACTIVE" if active else "CLEAR"
        )

        self.badge_label.setProperty(
            "activeFault",
            active,
        )

        # Force Qt to re-evaluate the stylesheet after the dynamic
        # activeFault property changes.
        style = self.badge_label.style()

        if style is not None:
            style.unpolish(self.badge_label)
            style.polish(self.badge_label)

        self.badge_label.update()

        if detail is not None:
            self.detail_label.setText(detail)


class _MultiSeriesCanvas(QWidget):
    """Lightweight multi-series history graph canvas."""

    BACKGROUND_COLOUR = QColor("#FFFFFF")
    GRID_COLOUR = QColor("#D8D8D8")
    AXIS_COLOUR = QColor("#012645")
    EMPTY_TEXT_COLOUR = QColor("#6C7780")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._series: dict[str, tuple[list[float], QColor]] = {}
        self.setMinimumHeight(170)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    @staticmethod
    def _normalise_values(values: Iterable[float]) -> list[float]:
        result: list[float] = []
        for value in values:
            try:
                result.append(float(value))
            except (TypeError, ValueError):
                continue
        return result

    def set_series(self, label: str, values: Iterable[float], colour: str) -> None:
        self._series[label] = (self._normalise_values(values), QColor(colour))
        self.update()

    def append_series_value(
        self,
        label: str,
        value: float,
        colour: str,
        maximum_points: int = 100,
    ) -> None:
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return
        values, stored_colour = self._series.get(label, ([], QColor(colour)))
        values = list(values)
        values.append(numeric_value)
        if maximum_points > 0:
            values = values[-maximum_points:]
        self._series[label] = (values, stored_colour)
        self.update()

    def clear(self) -> None:
        self._series.clear()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.BACKGROUND_COLOUR)
        graph_rect = self.rect().adjusted(12, 12, -12, -12)
        self._draw_grid(painter, graph_rect)

        active = [(values, colour) for values, colour in self._series.values() if len(values) >= 2]
        if not active:
            painter.setPen(self.EMPTY_TEXT_COLOUR)
            painter.drawText(
                graph_rect,
                Qt.AlignmentFlag.AlignCenter,
                "Waiting for telemetry data",
            )
            return

        all_values = [value for values, _ in active for value in values]
        minimum_value = min(all_values)
        maximum_value = max(all_values)
        value_range = maximum_value - minimum_value or 1.0

        for values, colour in active:
            path = QPainterPath()
            for index, value in enumerate(values):
                x_position = graph_rect.left() + graph_rect.width() * index / (len(values) - 1)
                y_position = graph_rect.bottom() - graph_rect.height() * (value - minimum_value) / value_range
                point = QPointF(x_position, y_position)
                if index == 0:
                    path.moveTo(point)
                else:
                    path.lineTo(point)
            painter.setPen(
                QPen(
                    colour,
                    2.4,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.drawPath(path)

    def _draw_grid(self, painter: QPainter, graph_rect) -> None:
        painter.setPen(QPen(self.GRID_COLOUR, 1))
        for step in range(6):
            y_position = graph_rect.top() + graph_rect.height() * step / 5
            painter.drawLine(
                graph_rect.left(),
                int(y_position),
                graph_rect.right(),
                int(y_position),
            )
        painter.setPen(QPen(self.AXIS_COLOUR, 1))
        painter.drawLine(
            graph_rect.left(), graph_rect.bottom(), graph_rect.right(), graph_rect.bottom()
        )
        painter.drawLine(
            graph_rect.left(), graph_rect.top(), graph_rect.left(), graph_rect.bottom()
        )


class MultiGraphWidget(DashboardCard):
    """History graph supporting multiple labelled, differently coloured series."""

    DEFAULT_COLOURS = ("#03BFD8", "#F92785", "#012645", "#F6B320")

    def __init__(
        self,
        title: str,
        series: Iterable[tuple[str, str]],
        unit: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._series_colours = dict(series)
        self.title_label = QLabel(title)
        self.unit_label = QLabel(unit)
        self.canvas = _MultiSeriesCanvas()

        self.title_label.setObjectName("cardTitle")
        self.unit_label.setObjectName("graphUnit")
        self.title_label.setWordWrap(True)

        heading = QHBoxLayout()
        heading.setContentsMargins(0, 0, 0, 0)
        heading.addWidget(self.title_label)
        heading.addStretch(1)
        heading.addWidget(self.unit_label)

        legend = QHBoxLayout()
        legend.setContentsMargins(0, 0, 0, 0)
        legend.setSpacing(14)
        for label, colour in self._series_colours.items():
            marker = QLabel("■")
            marker.setStyleSheet(f"color: {colour}; background: transparent;")
            text = QLabel(label)
            text.setObjectName("graphLegendText")
            legend.addWidget(marker)
            legend.addWidget(text)
        legend.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        layout.addLayout(heading)
        layout.addLayout(legend)
        layout.addWidget(self.canvas, 1)
        self.setMinimumHeight(250)

    def set_series_values(self, label: str, values: Iterable[float]) -> None:
        colour = self._series_colours.get(label, self.DEFAULT_COLOURS[0])
        self.canvas.set_series(label, values, colour)

    def append_series_value(
        self,
        label: str,
        value: float,
        maximum_points: int = 100,
    ) -> None:
        colour = self._series_colours.get(label, self.DEFAULT_COLOURS[0])
        self.canvas.append_series_value(label, value, colour, maximum_points)

    def clear_values(self) -> None:
        self.canvas.clear()


class GraphWidget(MultiGraphWidget):
    """Backward-compatible single-series history graph."""

    def __init__(
        self,
        title: str,
        values: Iterable[float] | None = None,
        unit: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            title,
            ((title, "#03BFD8"),),
            unit,
            parent,
        )
        if values:
            self.set_values(values)

    def set_values(self, values: Iterable[float]) -> None:
        self.set_series_values(self.title_label.text(), values)

    def append_value(self, value: float, maximum_points: int = 100) -> None:
        self.append_series_value(self.title_label.text(), value, maximum_points)

    def set_unit(self, unit: str) -> None:
        self.unit_label.setText(unit)
