"""Communication services for Telemetry Dashboard."""

from .serial_manager import (
    ConnectionState,
    SerialDeviceInfo,
    SerialManager,
)

__all__ = [
    "ConnectionState",
    "SerialDeviceInfo",
    "SerialManager",
]