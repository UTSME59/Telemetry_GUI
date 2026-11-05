from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from telemetry_dashboard.communication.serial_manager import SerialManager
from telemetry_dashboard.config_manager import ConfigManager
from telemetry_dashboard.main_window import MainWindow
from telemetry_dashboard.styles.theme import LIGHT_THEME

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "app_config.json"


def configure_logging(config_manager: ConfigManager) -> None:
    logging_config = config_manager.logging
    level_name = str(logging_config.get("level", "INFO")).upper()
    logging_level = getattr(logging, level_name, logging.INFO)

    configured_directory = Path(
        str(logging_config.get("directory", "logs"))
    )
    log_directory = (
        configured_directory
        if configured_directory.is_absolute()
        else PROJECT_ROOT / configured_directory
    )
    log_directory.mkdir(parents=True, exist_ok=True)

    log_file = log_directory / str(
        logging_config.get("filename", "telemetry_dashboard.log")
    )

    handlers: list[logging.Handler] = [
        logging.FileHandler(log_file, encoding="utf-8")
    ]
    if bool(logging_config.get("console_output", True)):
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )
    logging.getLogger(__name__).info("Logging initialised: %s", log_file)


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("UTS Motorsports Telemetry Dashboard")
    application.setOrganizationName("UTS Motorsports")
    application.setStyleSheet(LIGHT_THEME)

    serial_manager: SerialManager | None = None
    try:
        config_manager = ConfigManager(CONFIG_PATH)
        configure_logging(config_manager)

        serial_manager = SerialManager(config_manager)
        main_window = MainWindow(serial_manager)
        serial_manager.error_occurred.connect(
            lambda message: main_window.statusBar().showMessage(message, 8000)
        )

        main_window.show()
        serial_manager.start()
        return application.exec()

    except Exception as error:
        logging.exception("Telemetry Dashboard failed to start.")
        QMessageBox.critical(
            None,
            "Telemetry Dashboard Startup Error",
            str(error),
        )
        return 1
    finally:
        if serial_manager is not None:
            serial_manager.stop()


if __name__ == "__main__":
    raise SystemExit(main())