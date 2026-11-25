import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from src.config import Config
from src.gui.main_window import MainWindow
from src.hardware.pixet_manager import PixetManager
from src.logger import setup_logger, log_signal


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("microSPLIT-R")

    logger = setup_logger()
    config = Config()
    logger.info("microSPLIT-R starting...")

    pixet_mgr: PixetManager | None = None
    try:
        pixet_mgr = PixetManager.initialize()
        logger.info(f"Pixet SDK initialized. Devices: {len(pixet_mgr.list_devices())}")
    except Exception as e:
        logger.warning(f"Pixet SDK not available: {e}")

    window = MainWindow()
    window.show()

    exit_code = app.exec()

    if pixet_mgr is not None:
        PixetManager.shutdown()
    logger.info("microSPLIT-R shut down.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
