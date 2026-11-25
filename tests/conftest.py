import os

import pytest

# 画面のない環境（CI / WSL）でも Qt を起動できるようにする
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """テスト全体で1つだけ QApplication を作る。

    QCoreApplication を先に作るとウィジェットが使えなくなるため、
    各テストで個別に作らずこの fixture を共有する。
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]
