from __future__ import annotations

import json

from telemetry_dashboard.config_manager import ConfigManager


def test_protocol_and_telemetry_sections_are_exposed(tmp_path) -> None:
    config_path = tmp_path / "app_config.json"
    config_path.write_text(
        json.dumps(
            {
                "protocol": {"maximum_dlc": 16},
                "telemetry": {"enable_signal_decoding": True},
            }
        ),
        encoding="utf-8",
    )

    config = ConfigManager(config_path)

    assert config.protocol["maximum_dlc"] == 16
    assert config.telemetry["enable_signal_decoding"] is True
