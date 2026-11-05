from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)


DEFAULT_CONFIG: dict[str, Any] = {
    "application": {
        "name": "UTS Motorsports Telemetry Dashboard",
        "version": "0.2.0",
    },
    "serial": {
        "auto_connect": True,
        "preferred_port": "",
        "baud_rate": 115200,
        "data_bits": 8,
        "parity": "N",
        "stop_bits": 1,
        "read_timeout_seconds": 0.1,
        "write_timeout_seconds": 0.5,
        "scan_interval_ms": 1000,
        "connection_check_interval_ms": 500,
        "reconnect_interval_ms": 2000,
        "receiver": {
            "vid": "",
            "pid": "",
            "serial_number": "",
            "manufacturer": "",
            "description": "",
        },
    },
    "logging": {
        "level": "INFO",
        "directory": "logs",
        "filename": "telemetry_dashboard.log",
        "console_output": True,
    },
}


class ConfigManager:
    """Loads, validates and saves the application configuration."""

    def __init__(self, config_path: str | Path = "app_config.json") -> None:
        self.config_path = Path(config_path)
        self._config: dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self.load()

    @property
    def data(self) -> dict[str, Any]:
        return self._config

    @property
    def serial(self) -> dict[str, Any]:
        return self._config["serial"]

    @property
    def logging(self) -> dict[str, Any]:
        return self._config["logging"]

    @property
    def protocol(self) -> dict[str, Any]:
        return self._config.get("protocol", {})

    @property
    def telemetry(self) -> dict[str, Any]:
        return self._config.get("telemetry", {})

    def load(self) -> None:
        """Load the JSON file and merge it with defaults."""

        if not self.config_path.exists():
            LOGGER.warning(
                "Configuration file %s was not found. Creating defaults.",
                self.config_path,
            )
            self._config = copy.deepcopy(DEFAULT_CONFIG)
            self.save()
            return

        try:
            with self.config_path.open("r", encoding="utf-8") as config_file:
                loaded_config = json.load(config_file)
        except json.JSONDecodeError as error:
            LOGGER.exception(
                "Invalid JSON in configuration file %s: %s",
                self.config_path,
                error,
            )
            raise RuntimeError(
                f"Invalid JSON in {self.config_path}: {error}"
            ) from error
        except OSError as error:
            LOGGER.exception(
                "Could not read configuration file %s.",
                self.config_path,
            )
            raise RuntimeError(
                f"Could not read {self.config_path}: {error}"
            ) from error

        if not isinstance(loaded_config, dict):
            raise RuntimeError(
                f"{self.config_path} must contain a JSON object."
            )

        self._config = self._deep_merge(
            copy.deepcopy(DEFAULT_CONFIG),
            loaded_config,
        )

        self._validate()
        self.save()

    def save(self) -> None:
        """Write the current configuration to disk."""

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with self.config_path.open("w", encoding="utf-8") as config_file:
                json.dump(
                    self._config,
                    config_file,
                    indent=2,
                    ensure_ascii=False,
                )
                config_file.write("\n")

        except OSError as error:
            LOGGER.exception(
                "Could not save configuration file %s.",
                self.config_path,
            )
            raise RuntimeError(
                f"Could not save {self.config_path}: {error}"
            ) from error

    def set_preferred_port(self, port_name: str) -> None:
        self._config["serial"]["preferred_port"] = port_name.strip()
        self.save()

    def get_receiver_filters(self) -> dict[str, str]:
        receiver = self._config["serial"]["receiver"]

        return {
            "vid": str(receiver.get("vid", "")).strip(),
            "pid": str(receiver.get("pid", "")).strip(),
            "serial_number": str(
                receiver.get("serial_number", "")
            ).strip(),
            "manufacturer": str(
                receiver.get("manufacturer", "")
            ).strip(),
            "description": str(
                receiver.get("description", "")
            ).strip(),
        }

    def _validate(self) -> None:
        serial_config = self._config["serial"]

        integer_fields = {
            "baud_rate": 115200,
            "data_bits": 8,
            "scan_interval_ms": 1000,
            "connection_check_interval_ms": 500,
            "reconnect_interval_ms": 2000,
        }

        for field_name, fallback in integer_fields.items():
            try:
                serial_config[field_name] = int(
                    serial_config.get(field_name, fallback)
                )
            except (TypeError, ValueError):
                LOGGER.warning(
                    "Invalid serial.%s. Using %s.",
                    field_name,
                    fallback,
                )
                serial_config[field_name] = fallback

        float_fields = {
            "stop_bits": 1,
            "read_timeout_seconds": 0.1,
            "write_timeout_seconds": 0.5,
        }

        for field_name, fallback in float_fields.items():
            try:
                serial_config[field_name] = float(
                    serial_config.get(field_name, fallback)
                )
            except (TypeError, ValueError):
                LOGGER.warning(
                    "Invalid serial.%s. Using %s.",
                    field_name,
                    fallback,
                )
                serial_config[field_name] = fallback

        serial_config["auto_connect"] = bool(
            serial_config.get("auto_connect", True)
        )

        parity = str(serial_config.get("parity", "N")).upper()
        if parity not in {"N", "E", "O", "M", "S"}:
            LOGGER.warning(
                "Invalid serial parity %r. Using N.",
                parity,
            )
            parity = "N"

        serial_config["parity"] = parity

        if serial_config["data_bits"] not in {5, 6, 7, 8}:
            LOGGER.warning(
                "Invalid data_bits %r. Using 8.",
                serial_config["data_bits"],
            )
            serial_config["data_bits"] = 8

        if serial_config["stop_bits"] not in {1.0, 1.5, 2.0}:
            LOGGER.warning(
                "Invalid stop_bits %r. Using 1.",
                serial_config["stop_bits"],
            )
            serial_config["stop_bits"] = 1.0

        for interval_name in (
            "scan_interval_ms",
            "connection_check_interval_ms",
            "reconnect_interval_ms",
        ):
            if serial_config[interval_name] < 100:
                LOGGER.warning(
                    "%s was below 100 ms. Using 100 ms.",
                    interval_name,
                )
                serial_config[interval_name] = 100

    @staticmethod
    def _deep_merge(
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        for key, value in override.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                base[key] = ConfigManager._deep_merge(
                    base[key],
                    value,
                )
            else:
                base[key] = value

        return base