from __future__ import annotations

from PySide6.QtCore import QCoreApplication

from telemetry_dashboard.communication.frame_parser import UsartFrame
from telemetry_dashboard.services.telemetry_service import TelemetryService


def test_usart_frame_decodes_into_cache() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    service = TelemetryService(health_refresh_ms=60_000)

    frame = UsartFrame(
        can_id=0xC0,
        dlc=8,
        data=bytes.fromhex("E8 03 00 00 00 01 00 00"),
        received_crc=0,
        raw=b"",
        crc_checked=False,
        crc_valid=None,
    )

    service.handle_frame(frame)

    torque = service.get_signal("Torque Command")
    inverter = service.get_signal("Inverter Enable")

    assert torque is not None
    assert torque.raw_value == 1000
    assert torque.value == 100
    assert torque.unit == "Nm"
    assert torque.can_id == 0xC0
    assert torque.update_count == 1

    assert inverter is not None
    assert inverter.value is True

    service.shutdown()
    app.processEvents()
