import os
import sys
import threading
from pathlib import Path


SDK_DIR = Path(__file__).resolve().parent.parent.parent / "pixet_sdk"


class PixetManager:
    _instance: "PixetManager | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.pixet = None
        self._initialized = False

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
        orig = os.getcwd()
        try:
            os.chdir(sdk_str)
            import pypixet  # type: ignore
            pypixet.start()
            self.pixet = pypixet.pixet
            self._initialized = True
        finally:
            os.chdir(orig)

    @classmethod
    def shutdown(cls) -> None:
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
                cls._instance._initialized = False
                cls._instance = None

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
