"""MiniPIX TPX 全パラメータ列挙 (v6) - count() + params() 使用"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.hardware.pixet_manager import PixetManager


def main() -> None:
    pm = PixetManager.initialize()
    devices = pm.list_devices()
    print(f"Devices found: {len(devices)}")
    for idx, dev in enumerate(devices):
        print(f"\n=== Device {idx}: {dev.deviceID()} ===")
        try:
            params = dev.parameters()
            print(f"  type(params) = {type(params).__name__}")

            # 1. Try count()
            try:
                n = params.count()
                print(f"  count() = {n}")
            except Exception as e:
                print(f"  count() -> {type(e).__name__}: {e}")

            # 2. Try params() to get array
            try:
                all_p = params.params()
                print(f"  params() type = {type(all_p).__name__}")
                if hasattr(all_p, '__len__'):
                    print(f"  params() len = {len(all_p)}")
                print(f"  --- All parameters ({len(all_p) if hasattr(all_p, '__len__') else '?'}) ---")
                for i, p in enumerate(all_p):
                    name = ""
                    try:
                        name = p.name()
                    except Exception:
                        name = f"<index {i}>"
                    val_str = ""
                    for accessor in ["getDouble", "getInt", "getString", "getBOOL", "getByte", "getChar", "value"]:
                        if hasattr(p, accessor):
                            try:
                                raw = getattr(p, accessor)()
                                val_str = f"= {raw!r}"
                                break
                            except Exception:
                                continue
                    try:
                        desc = p.description()
                        if desc:
                            val_str += f"  [{desc}]"
                    except Exception:
                        pass
                    print(f"    [{i}] {name} {val_str}")
            except Exception as e:
                print(f"  params() -> {type(e).__name__}: {e}")

            # 3. Fallback: try known names we haven't tried yet
            try:
                extra = [
                    "BiasSenseVoltage", "BiasSenseCurrent",
                    "BiasInCpu", "BiasDischarge", "BiasVolt", "BiasCurr",
                    "TemperatureChipCpu",
                    "TemperatureReadBeforeAcqSerie",
                    "TemperatureReadBeforeEachAcq",
                    "CheckMaxTempInSW", "MaxAllowedChipTemp",
                    "DacBandGap", "DacTemp",
                    "HwLibVer",
                    "Motohours",
                    "SensorRefreshEnabled",
                    "PreShutterClockCount",
                    "TriggerStg",
                    "IsMaster",
                ]
                found_any = False
                for name in extra:
                    if params.hasParam(name):
                        p = params.get(name)
                        val = ""
                        for accessor in ["getDouble", "getInt", "getString", "value"]:
                            if hasattr(p, accessor):
                                try:
                                    raw = getattr(p, accessor)()
                                    val = f"= {raw!r}"
                                    break
                                except Exception:
                                    continue
                        print(f"  [extra] {name} {val}")
                        found_any = True
                if not found_any:
                    print("  (no extra params found)")
            except Exception as e:
                print(f"  extra scan: {e}")

        except Exception as e:
            print(f"  parameters() error: {type(e).__name__}: {e}")

    PixetManager.shutdown()


if __name__ == "__main__":
    main()
