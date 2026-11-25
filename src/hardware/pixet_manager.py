import logging
import os
import sys
import threading
from pathlib import Path


SDK_DIR = Path(__file__).resolve().parent.parent.parent / "pixet_sdk"

# pypixet が cwd 相対で DLL/INI を探す実装だった場合のフォールバックで、
# プロセス全体の cwd を SDK_DIR に固定したかどうか。
_cwd_pinned = False


def cwd_pinned() -> bool:
    return _cwd_pinned


class PixetManager:
    _instance: "PixetManager | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.pixet = None
        self._initialized = False
        self._dll_handle = None

    @classmethod
    def initialize(cls) -> "PixetManager":
        if cls._instance is not None and cls._instance._initialized:
            return cls._instance
        with cls._lock:
            if cls._instance is not None and cls._instance._initialized:
                return cls._instance
            inst = cls.__new__(cls)
            inst.__init__()
            inst._do_start()
            cls._instance = inst
            return inst

    def _do_start(self) -> None:
        sdk_str = str(SDK_DIR)
        if sdk_str not in sys.path:
            sys.path.insert(0, sdk_str)

        # Windows では os.chdir ではなく DLL 検索パスで解決する。
        # chdir はプロセス全体に効き、測定スレッドの保存処理と競合するため。
        self._dll_handle = self._add_dll_directory(sdk_str)
        try:
            import pypixet  # type: ignore
        except ImportError:
            # 古い SDK は cwd 相対で DLL/INI を探す。この場合だけ cwd を固定し、
            # 元に戻さない（起動直後の1回きり。保存系は絶対パスで動く）。
            if self._dll_handle is not None:
                self._dll_handle.close()
                self._dll_handle = None
            self._pin_cwd(sdk_str)
            import pypixet  # type: ignore

        pypixet.start()
        self.pixet = pypixet.pixet
        self._initialized = True

    @staticmethod
    def _add_dll_directory(sdk_str: str):
        if os.name != "nt" or not hasattr(os, "add_dll_directory"):
            return None
        try:
            return os.add_dll_directory(sdk_str)
        except OSError:
            return None

    @staticmethod
    def _pin_cwd(sdk_str: str) -> None:
        global _cwd_pinned
        _cwd_pinned = True
        if os.getcwd() == sdk_str:
            return
        logging.getLogger("usplit").warning(
            "Pixet SDK が cwd 基準で DLL/INI を探すため、カレントディレクトリを %s に固定します",
            sdk_str,
        )
        os.chdir(sdk_str)

    @classmethod
    def shutdown(cls) -> None:
        global _cwd_pinned
        with cls._lock:
            if cls._instance is not None and cls._instance._initialized:
                try:
                    cls._instance.pixet.exitPixet()
                except Exception:
                    pass
                try:
                    import pypixet
                    pypixet.exit()
                except Exception:
                    pass
                if cls._instance._dll_handle is not None:
                    try:
                        cls._instance._dll_handle.close()
                    except Exception:
                        pass
                    cls._instance._dll_handle = None
                cls._instance._initialized = False
                cls._instance = None
        _cwd_pinned = False

    @classmethod
    def instance(cls) -> "PixetManager":
        if cls._instance is None:
            raise RuntimeError("PixetManager not initialized. Call PixetManager.initialize() first.")
        return cls._instance

    def list_devices(self) -> list:
        if not self._initialized or self.pixet is None:
            raise RuntimeError("PixetManager not initialized.")
        devices = self.pixet.devices()
        return [d for d in devices if "FileDevice" not in d.fullName()]
