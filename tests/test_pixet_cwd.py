import os
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from src.hardware import pixet_manager
from src.hardware.pixet_manager import PixetManager


@pytest.fixture(autouse=True)
def _reset(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    PixetManager._instance = None
    PixetManager._initialized = False
    monkeypatch.setattr(pixet_manager, "_cwd_pinned", False)
    yield
    PixetManager._instance = None
    PixetManager._initialized = False


class TestCwdHandling:
    def test_initialize_does_not_change_cwd(self) -> None:
        """SDK 初期化でプロセス全体の cwd を動かさない（スレッド競合の防止）。"""
        mp = MagicMock()
        mp.pixet.devices.return_value = []
        before = os.getcwd()
        with patch.dict("sys.modules", {"pypixet": mp}):
            PixetManager.initialize()
        assert os.getcwd() == before
        assert pixet_manager.cwd_pinned() is False

    def test_pin_cwd_moves_to_sdk_dir(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        """フォールバックは明示的に呼ばれたときだけ cwd を固定する。"""
        monkeypatch.chdir(tmp_path)
        target = tmp_path / "sdk"
        target.mkdir()
        try:
            PixetManager._pin_cwd(str(target))
            assert os.getcwd() == str(target)
            assert pixet_manager.cwd_pinned() is True
        finally:
            os.chdir(tmp_path)

    def test_shutdown_resets_pinned_flag(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        mp = MagicMock()
        with patch.dict("sys.modules", {"pypixet": mp}):
            PixetManager.initialize()
            PixetManager.shutdown()
        assert pixet_manager.cwd_pinned() is False
