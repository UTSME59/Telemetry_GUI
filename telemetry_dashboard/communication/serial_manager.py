from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import serial
from serial import SerialException
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from telemetry_dashboard.communication.frame_parser import (
    CrcPolicy,
    ParserStatistics,
    UsartFrameParser,
)
from telemetry_dashboard.config_manager import ConfigManager


LOGGER = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass(frozen=True)
class SerialDeviceInfo:
    device: str
    name: str
    description: str
    hardware_id: str
    vid: int | None
    pid: int | None
    serial_number: str
    manufacturer: str
    product: str
    interface: str
    location: str

    @classmethod
    def from_port_info(
        cls,
        port: ListPortInfo,
    ) -> "SerialDeviceInfo":
        return cls(
            device=port.device or "",
            name=port.name or "",
            description=port.description or "",
            hardware_id=port.hwid or "",
            vid=port.vid,
            pid=port.pid,
            serial_number=port.serial_number or "",
            manufacturer=port.manufacturer or "",
            product=port.product or "",
            interface=port.interface or "",
            location=port.location or "",
        )

    @property
    def vid_hex(self) -> str:
        if self.vid is None:
            return ""

        return f"{self.vid:04X}"

    @property
    def pid_hex(self) -> str:
        if self.pid is None:
            return ""

        return f"{self.pid:04X}"

    @property
    def display_name(self) -> str:
        description = (
            self.description
            or self.product
            or self.manufacturer
            or "Serial Device"
        )

        return f"{self.device} - {description}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "device": self.device,
            "name": self.name,
            "description": self.description,
            "hardware_id": self.hardware_id,
            "vid": self.vid_hex,
            "pid": self.pid_hex,
            "serial_number": self.serial_number,
            "manufacturer": self.manufacturer,
            "product": self.product,
            "interface": self.interface,
            "location": self.location,
        }


class SerialManager(QObject):
    connection_state_changed = Signal(str, str)
    ports_changed = Signal(object)
    connected = Signal(object)
    disconnected = Signal(str)
    error_occurred = Signal(str)

    frame_received = Signal(object)
    statistics_changed = Signal(object)
    raw_bytes_received = Signal(bytes)

    def __init__(
        self,
        config_manager: ConfigManager,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self.config_manager = config_manager
        self.serial_config = config_manager.serial

        protocol_config = getattr(
            config_manager,
            "protocol",
            {},
        )

        self._serial: serial.Serial | None = None
        self._connected_device: SerialDeviceInfo | None = None
        self._available_ports: list[SerialDeviceInfo] = []

        self._selected_port = ""
        self._manual_disconnect = False
        self._is_shutting_down = False

        self._last_port_signature: tuple[
            tuple[Any, ...],
            ...
        ] = ()

        self._state = ConnectionState.DISCONNECTED

        self._frame_parser = UsartFrameParser(
            maximum_dlc=int(
                protocol_config.get(
                    "maximum_dlc",
                    8,
                )
            ),
            can_id_byte_order=str(
                protocol_config.get(
                    "can_id_byte_order",
                    "little",
                )
            ),
            crc_byte_order=str(
                protocol_config.get(
                    "crc_byte_order",
                    "little",
                )
            ),
            crc_policy=CrcPolicy(
                protocol_config.get(
                    "crc_policy",
                    "disabled",
                )
            ),
            crc_algorithm=str(
                protocol_config.get(
                    "crc_algorithm",
                    "none",
                )
            ),
        )

        self._last_parser_statistics = (
            self._frame_parser.statistics
        )

        self._scan_timer = QTimer(self)
        self._scan_timer.setInterval(
            int(
                self.serial_config[
                    "scan_interval_ms"
                ]
            )
        )
        self._scan_timer.timeout.connect(
            self.scan_ports
        )

        self._connection_check_timer = QTimer(self)
        self._connection_check_timer.setInterval(
            int(
                self.serial_config[
                    "connection_check_interval_ms"
                ]
            )
        )
        self._connection_check_timer.timeout.connect(
            self._check_connection
        )

        self._read_timer = QTimer(self)
        self._read_timer.setInterval(
            int(
                self.serial_config.get(
                    "read_interval_ms",
                    10,
                )
            )
        )
        self._read_timer.timeout.connect(
            self._read_serial_data
        )

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.setInterval(
            int(
                self.serial_config[
                    "reconnect_interval_ms"
                ]
            )
        )
        self._reconnect_timer.timeout.connect(
            self._attempt_reconnect
        )

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return (
            self._serial is not None
            and self._serial.is_open
            and self._connected_device is not None
        )

    @property
    def available_ports(
        self,
    ) -> list[SerialDeviceInfo]:
        return list(self._available_ports)

    @property
    def connected_device(
        self,
    ) -> SerialDeviceInfo | None:
        return self._connected_device

    @property
    def selected_port(self) -> str:
        return self._selected_port

    @property
    def statistics(self) -> ParserStatistics:
        return self._frame_parser.statistics

    @Slot()
    def start(self) -> None:
        if self._is_shutting_down:
            return

        LOGGER.info(
            "Starting serial-device monitoring."
        )

        self._set_state(
            ConnectionState.SCANNING,
            "Scanning for serial devices",
        )

        self.scan_ports()

        if not self._scan_timer.isActive():
            self._scan_timer.start()

        if not self._connection_check_timer.isActive():
            self._connection_check_timer.start()

        if not self._read_timer.isActive():
            self._read_timer.start()

    @Slot()
    def stop(self) -> None:
        self._is_shutting_down = True

        self._scan_timer.stop()
        self._connection_check_timer.stop()
        self._read_timer.stop()
        self._reconnect_timer.stop()

        self._close_connection(
            count_pending_as_incomplete=True
        )

        LOGGER.info(
            "Serial-device monitoring stopped."
        )

    @Slot()
    def scan_ports(self) -> None:
        if self._is_shutting_down:
            return

        try:
            raw_ports = sorted(
                list_ports.comports(),
                key=lambda port: port.device,
            )

            devices = [
                SerialDeviceInfo.from_port_info(port)
                for port in raw_ports
            ]

        except Exception as error:
            message = (
                f"Serial-port scan failed: {error}"
            )

            LOGGER.exception(message)
            self.error_occurred.emit(message)

            self._set_state(
                ConnectionState.ERROR,
                message,
            )
            return

        signature = tuple(
            (
                device.device,
                device.vid,
                device.pid,
                device.serial_number,
                device.description,
                device.manufacturer,
            )
            for device in devices
        )

        self._available_ports = devices

        if signature != self._last_port_signature:
            self._last_port_signature = signature

            self.ports_changed.emit(
                self.available_ports
            )

            LOGGER.info(
                "Available serial ports changed: %s",
                [
                    device.display_name
                    for device in devices
                ],
            )

        if self.is_connected:
            if not self._connected_port_exists():
                self._handle_connection_loss(
                    "Selected serial device was disconnected"
                )

            return

        if (
            self._selected_port
            and not self._manual_disconnect
            and not self._reconnect_timer.isActive()
        ):
            selected_device = self._find_device(
                self._selected_port
            )

            if selected_device is not None:
                self.connect_to_device(
                    selected_device
                )

        elif not self._selected_port:
            self._set_state(
                ConnectionState.SCANNING,
                "Select a serial device",
            )

    @Slot(str)
    def select_port(
        self,
        port_name: str,
    ) -> None:
        port_name = port_name.strip()

        if not port_name:
            return

        LOGGER.info(
            "Serial device selected: %s",
            port_name,
        )

        self._selected_port = port_name
        self._manual_disconnect = False
        self._reconnect_timer.stop()

        selected_device = self._find_device(
            port_name
        )

        if selected_device is None:
            message = (
                f"{port_name} is no longer available"
            )

            self.error_occurred.emit(message)

            self._set_state(
                ConnectionState.ERROR,
                message,
            )
            return

        self.connect_to_device(
            selected_device
        )

    def connect_to_device(
        self,
        device: SerialDeviceInfo,
    ) -> None:
        if self._is_shutting_down:
            return

        if (
            self.is_connected
            and self._connected_device is not None
            and self._connected_device.device
            == device.device
        ):
            return

        if self.is_connected:
            self._close_connection(
                count_pending_as_incomplete=True
            )

        self._set_state(
            ConnectionState.CONNECTING,
            f"Connecting to {device.device}",
        )

        LOGGER.info(
            "Opening serial device: %s",
            device.as_dict(),
        )

        serial_port: serial.Serial | None = None

        try:
            serial_port = serial.Serial(
                port=device.device,
                baudrate=int(
                    self.serial_config[
                        "baud_rate"
                    ]
                ),
                bytesize=int(
                    self.serial_config[
                        "data_bits"
                    ]
                ),
                parity=str(
                    self.serial_config[
                        "parity"
                    ]
                ),
                stopbits=float(
                    self.serial_config[
                        "stop_bits"
                    ]
                ),
                timeout=0,
                write_timeout=float(
                    self.serial_config[
                        "write_timeout_seconds"
                    ]
                ),
            )

            if not serial_port.is_open:
                serial_port.open()

            serial_port.reset_input_buffer()

        except (
            SerialException,
            OSError,
            ValueError,
        ) as error:
            if serial_port is not None:
                self._close_serial_safely(
                    serial_port
                )

            message = (
                f"Could not open "
                f"{device.device}: {error}"
            )

            LOGGER.warning(message)
            self.error_occurred.emit(message)

            self._set_state(
                ConnectionState.ERROR,
                message,
            )

            self._schedule_reconnect()
            return

        self._serial = serial_port
        self._connected_device = device
        self._selected_port = device.device
        self._manual_disconnect = False

        self._frame_parser.reset(
            clear_statistics=False,
            count_pending_as_incomplete=False,
        )

        self._emit_statistics_if_changed()

        LOGGER.info(
            "Connected to serial device on %s.",
            device.device,
        )

        self._set_state(
            ConnectionState.CONNECTED,
            f"Connected to {device.display_name}",
        )

        self.connected.emit(device)

    @Slot()
    def disconnect_manual(self) -> None:
        self._manual_disconnect = True
        self._reconnect_timer.stop()

        previous_device = self._connected_device

        self._close_connection(
            count_pending_as_incomplete=True
        )

        if previous_device is not None:
            LOGGER.info(
                "Disconnected manually from %s.",
                previous_device.device,
            )

        self._set_state(
            ConnectionState.DISCONNECTED,
            "Disconnected by user",
        )

        self.disconnected.emit(
            "Disconnected by user"
        )

    @Slot()
    def refresh_ports(self) -> None:
        self.scan_ports()

    @Slot()
    def reconnect_selected(self) -> None:
        if not self._selected_port:
            self._set_state(
                ConnectionState.SCANNING,
                "Select a serial device",
            )
            return

        self._manual_disconnect = False

        selected_device = self._find_device(
            self._selected_port
        )

        if selected_device is None:
            self._set_state(
                ConnectionState.SCANNING,
                (
                    f"Waiting for "
                    f"{self._selected_port}"
                ),
            )
            return

        self.connect_to_device(
            selected_device
        )

    @Slot()
    def reset_statistics(self) -> None:
        self._frame_parser.reset(
            clear_statistics=True,
            count_pending_as_incomplete=False,
        )

        self._last_parser_statistics = (
            self._frame_parser.statistics
        )

        self.statistics_changed.emit(
            self._last_parser_statistics
        )

        LOGGER.info(
            "USART frame statistics reset."
        )

    @Slot()
    def _read_serial_data(self) -> None:
        if (
            self._is_shutting_down
            or not self.is_connected
        ):
            return

        try:
            assert self._serial is not None

            waiting_bytes = self._serial.in_waiting

            if waiting_bytes <= 0:
                return

            incoming = self._serial.read(
                waiting_bytes
            )

        except (
            SerialException,
            OSError,
        ) as error:
            self._handle_connection_loss(
                f"Serial read failed: {error}"
            )
            return

        if not incoming:
            return

        self.raw_bytes_received.emit(
            bytes(incoming)
        )

        parsed_frames = self._frame_parser.feed(
            incoming
        )

        for frame in parsed_frames:
            self.frame_received.emit(
                frame
            )

            LOGGER.debug(
                (
                    "USART frame received: "
                    "CAN ID=%s, DLC=%s, "
                    "DATA=%s, CRC=%s"
                ),
                frame.can_id_hex,
                frame.dlc,
                frame.data_hex,
                frame.received_crc_hex,
            )

        self._emit_statistics_if_changed()

    @Slot()
    def _check_connection(self) -> None:
        if (
            self._is_shutting_down
            or not self.is_connected
        ):
            return

        if not self._connected_port_exists():
            self._handle_connection_loss(
                "Selected serial device was disconnected"
            )
            return

        try:
            assert self._serial is not None

            if not self._serial.is_open:
                raise SerialException(
                    "Serial port is closed"
                )

            _ = self._serial.in_waiting

        except (
            SerialException,
            OSError,
        ) as error:
            self._handle_connection_loss(
                f"Serial connection lost: {error}"
            )

    def _emit_statistics_if_changed(self) -> None:
        statistics = self._frame_parser.statistics

        if statistics == self._last_parser_statistics:
            return

        self._last_parser_statistics = statistics

        self.statistics_changed.emit(
            statistics
        )

    def _handle_connection_loss(
        self,
        reason: str,
    ) -> None:
        LOGGER.warning(reason)

        self._close_connection(
            count_pending_as_incomplete=True
        )

        self._set_state(
            ConnectionState.RECONNECTING,
            reason,
        )

        self.disconnected.emit(reason)
        self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        if (
            self._is_shutting_down
            or self._manual_disconnect
            or not self._selected_port
        ):
            return

        delay_ms = int(
            self.serial_config[
                "reconnect_interval_ms"
            ]
        )

        self._set_state(
            ConnectionState.RECONNECTING,
            (
                f"Waiting for "
                f"{self._selected_port}"
            ),
        )

        if not self._reconnect_timer.isActive():
            self._reconnect_timer.start(
                delay_ms
            )

    @Slot()
    def _attempt_reconnect(self) -> None:
        if (
            self._is_shutting_down
            or self._manual_disconnect
            or self.is_connected
            or not self._selected_port
        ):
            return

        self.scan_ports()

        selected_device = self._find_device(
            self._selected_port
        )

        if selected_device is None:
            self._schedule_reconnect()
            return

        self.connect_to_device(
            selected_device
        )

    def _find_device(
        self,
        port_name: str,
    ) -> SerialDeviceInfo | None:
        target = port_name.casefold()

        for device in self._available_ports:
            if device.device.casefold() == target:
                return device

        return None

    def _connected_port_exists(self) -> bool:
        if self._connected_device is None:
            return False

        return (
            self._find_device(
                self._connected_device.device
            )
            is not None
        )

    def _close_connection(
        self,
        *,
        count_pending_as_incomplete: bool,
    ) -> None:
        self._frame_parser.reset(
            clear_statistics=False,
            count_pending_as_incomplete=(
                count_pending_as_incomplete
            ),
        )

        self._emit_statistics_if_changed()

        self._close_serial_safely(
            self._serial
        )

        self._serial = None
        self._connected_device = None

    @staticmethod
    def _close_serial_safely(
        serial_port: serial.Serial | None,
    ) -> None:
        if serial_port is None:
            return

        try:
            if serial_port.is_open:
                serial_port.close()

        except (
            SerialException,
            OSError,
        ):
            LOGGER.exception(
                "Error while closing serial port."
            )

    def _set_state(
        self,
        state: ConnectionState,
        message: str,
    ) -> None:
        state_changed = state != self._state
        self._state = state

        self.connection_state_changed.emit(
            state.value,
            message,
        )

        if state_changed:
            LOGGER.info(
                "Serial state changed to %s: %s",
                state.value,
                message,
            )