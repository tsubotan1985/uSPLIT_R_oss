import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow
from src.hardware.pixet_manager import PixetManager
from src.logger import setup_logger


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("microSPLIT-R")

    logger = setup_logger()
    logger.info("microSPLIT-R starting...")

    # ハードウェア初期化は MainWindow 側で行い、失敗しても学習・可視化タブは使える
    window = MainWindow()
    window.show()

    exit_code = app.exec()

    PixetManager.shutdown()
    logger.info("microSPLIT-R shut down.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
