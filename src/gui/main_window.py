import queue
import threading
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from src.gui.log_panel import LogPanel
from src.gui.measurement_control import MeasurementControl
from src.gui.sensor_panel import SensorPanel
from src.gui.plot_widget import PlotWidget, SENSOR_LABELS
from src.gui.training_tab import TrainingTab
from src.gui.visualization_tab import VisualizationTab
from src.hardware.multi_device import MultiDeviceController
from src.hardware.pixet_manager import PixetManager
from src.acquisition.measurement_thread import MeasurementThread
from src.analysis.classifier import Classifier
from src.config import Config
from src.logger import setup_logger


SENSOR_IDS = ["E02", "I03", "J03"]
SENSOR_ID_MAP: dict[str, str] = dict(zip(SENSOR_IDS, SENSOR_LABELS))


class AnalysisWorker(QThread):
    analysis_result = Signal(str, int, int, int, int, object, object, object)

    def __init__(
        self,
        classifier: Classifier,
        maxsize: int = 30,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._classifier = classifier
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self._running = True

    def enqueue(self, sensor_id: str, frame_num: int, data: np.ndarray) -> bool:
        try:
            self._queue.put_nowait((sensor_id, frame_num, data))
            return True
        except queue.Full:
            return False

    def stop(self) -> None:
        self._running = False
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        self.wait(5000)

    def run(self) -> None:
        import logging
        logger = logging.getLogger("usplit")
        while self._running:
            try:
                item = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if item is None:
                break
            sensor_id, frame_num, data = item
            if not isinstance(data, np.ndarray):
                continue
            from src.analysis.feature_extractor import extract_features
            try:
                features, labelled, props = extract_features(data)
                results = self._classifier.predict(features)
                alpha = sum(1 for r in results if r.get("class") == 0)
                beta  = sum(1 for r in results if r.get("class") == 1)
                gamma = sum(1 for r in results if r.get("class") == 2)
                logger.info(f"  analysis [{sensor_id} f{frame_num}]: {alpha}a {beta}b {gamma}g / {len(results)} clusters")
                self.analysis_result.emit(sensor_id, frame_num, alpha, beta, gamma, results, labelled, props)
            except Exception as e:
                logger.error(f"  analysis failed [{sensor_id} f{frame_num}]: {e}")
                self.analysis_result.emit(sensor_id, frame_num, 0, 0, 0, [], None, None)


class HitmapWorker:
    """背景スレッドでヒットマップPNGを生成するワーカー"""

    def __init__(self, maxsize: int = 30):
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def enqueue(
        self,
        labelled: np.ndarray,
        props: list,
        classification: list[dict],
        frame_num: int,
        sensor_name: str,
        save_subdir: Path,
    ) -> bool:
        if not self._running:
            return False
        try:
            self._queue.put_nowait((labelled, props, classification, frame_num, sensor_name, save_subdir))
            return True
        except queue.Full:
            return False

    def stop(self) -> None:
        self._running = False
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        self._thread.join(timeout=5)

    def _run(self) -> None:
        plt.ioff()

        class_colors = {
            -1: (0.02, 0.03, 0.10),
            0:  (1.00, 0.27, 0.27),
            1:  (1.00, 0.84, 0.00),
            2:  (0.60, 0.50, 0.80),
        }

        while self._running:
            try:
                item = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if item is None:
                break

            labelled, props, classification, frame_num, sensor_name, save_subdir = item

            max_label = int(labelled.max())
            label_to_class = np.full(max_label + 1, 2, dtype=int)
            label_to_class[0] = -1
            for i, rp in enumerate(props):
                if i < len(classification):
                    label_to_class[rp.label] = classification[i].get("class", 2)
                else:
                    label_to_class[rp.label] = 2

            class_map = label_to_class[labelled]
            rgb = np.zeros((*labelled.shape, 3), dtype=np.float64)
            for cls, color in class_colors.items():
                rgb[class_map == cls] = color

            counts = {0: 0, 1: 0, 2: 0}
            for r in classification:
                counts[r.get("class", 2)] = counts.get(r.get("class", 2), 0) + 1
            total = sum(counts.values())

            fig, ax = plt.subplots(figsize=(8, 8))
            ax.imshow(rgb, extent=[0, labelled.shape[1], labelled.shape[0], 0], interpolation="nearest")
            ax.set_title(f"Classification: frame_{frame_num:06d}.out",
                         fontsize=14, fontweight="bold", pad=10)
            ax.set_xlabel("X (pixels)", fontsize=12)
            ax.set_ylabel("Y (pixels)", fontsize=12)
            ax.set_xlim(0, labelled.shape[1])

            if total > 0:
                stats_text = (
                    f"Total Clusters: {total}\n"
                    f"Alpha: {counts[0]}/{total} ({counts[0] / total * 100:.1f}%)\n"
                    f"Beta: {counts[1]}/{total} ({counts[1] / total * 100:.1f}%)\n"
                    f"Gamma: {counts[2]}/{total} ({counts[2] / total * 100:.1f}%)"
                )
            else:
                stats_text = "Total Clusters: 0\nAlpha: 0\nBeta: 0\nGamma: 0"
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                    ha="left", va="top",
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                              alpha=0.85, edgecolor="gray"))

            legend_elements = [
                Patch(facecolor=class_colors[0], edgecolor="white", label="Alpha"),
                Patch(facecolor=class_colors[1], edgecolor="white", label="Beta"),
                Patch(facecolor=class_colors[2], edgecolor="white", label="Gamma"),
                Patch(facecolor=class_colors[-1], edgecolor="white", label="Background"),
            ]
            ax.legend(handles=legend_elements, loc="upper right", fontsize=10,
                      framealpha=0.85)

            plt.tight_layout()
            save_subdir.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_subdir / f"frame_{frame_num:06d}.png", dpi=200,
                        bbox_inches="tight", facecolor="#0a0e27")
            plt.close(fig)
            plt.close("all")

        plt.close("all")


class TrainingWorker(QThread):
    progress = Signal(str, int)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, alpha: str, beta: str, gamma: str, name: str, threshold: float, n_trials: int = 0, parent: Any = None) -> None:
        super().__init__(parent)
        self._alpha = alpha
        self._beta = beta
        self._gamma = gamma
        self._name = name
        self._threshold = threshold
        self._n_trials = n_trials

    def run(self) -> None:
        from src.training.training_manager import TrainingManager
        def cb(stage: str, pct: int) -> None:
            self.progress.emit(stage, pct)
        mgr = TrainingManager(progress_callback=cb)
        try:
            result = mgr.run_pipeline(self._alpha, self._beta, self._gamma, self._name, self._threshold, self._n_trials)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("microSPLIT-R")
        self.resize(1280, 800)
        self._logger = setup_logger()
        self._config = Config()
        self._pixet_mgr: PixetManager | None = None
        self._multi_ctrl: MultiDeviceController | None = None
        self._meas_thread: MeasurementThread | None = None
        self._classifier = Classifier(rule_thresholds=self._config.get("rule_based"))
        self._ts_frames: dict[str, list[int]] = {}
        self._ts_alpha: dict[str, list[int]] = {}
        self._ts_beta: dict[str, list[int]] = {}
        self._ts_gamma: dict[str, list[int]] = {}
        self._plot_timer = QTimer(self)
        self._plot_timer.timeout.connect(self._redraw_plot)
        self._plot_timer.setInterval(2000)

        self._hitmap_worker = HitmapWorker(maxsize=30)
        self._analysis_worker = AnalysisWorker(self._classifier, maxsize=30)
        self._train_worker: TrainingWorker | None = None
        self._analysis_worker.analysis_result.connect(self._on_analysis_result)
        self._analysis_worker.start()
        self._viz_initialized = False

        self._build_ui()
        self._init_hardware()
        self._load_saved_model()

        self._info_timer = QTimer(self)
        self._info_timer.timeout.connect(self._update_sensor_info)
        self._info_timer.setInterval(5000)
        if self._multi_ctrl is not None:
            self._info_timer.start()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self._build_measurement_tab()
        self._build_visualization_tab()
        self._build_training_tab()
        layout.addWidget(self.tabs, stretch=1)

        self.log_panel = LogPanel()
        self.log_panel.setMaximumHeight(150)
        layout.addWidget(self.log_panel)

    def _build_measurement_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.meas_ctrl = MeasurementControl(self._config)
        layout.addWidget(self.meas_ctrl)

        sensors = QHBoxLayout()
        self.sensor_panels: dict[str, SensorPanel] = {}
        for sid in SENSOR_ID_MAP.values():
            panel = SensorPanel(sid)
            self.sensor_panels[sid] = panel
            sensors.addWidget(panel)
        layout.addLayout(sensors)

        self.plot = PlotWidget()
        layout.addWidget(self.plot, stretch=1)

        self.tabs.addTab(tab, "Measurement")

        self.meas_ctrl.start_requested.connect(self._start_measurement)
        self.meas_ctrl.stop_requested.connect(self._stop_measurement)
        self.meas_ctrl.clear_requested.connect(self._clear_plot)
        self.meas_ctrl.model_changed.connect(self._on_model_changed)

    def _build_visualization_tab(self) -> None:
        self.viz_tab = VisualizationTab()
        self.tabs.addTab(self.viz_tab, "Visualization")

    def _build_training_tab(self) -> None:
        self.training_tab = TrainingTab()
        self.tabs.addTab(self.training_tab, "Training")
        self.training_tab.training_started.connect(self._start_training)

    def _init_hardware(self) -> None:
        try:
            self._pixet_mgr = PixetManager.initialize()
            self._multi_ctrl = MultiDeviceController(self._pixet_mgr)
            self._multi_ctrl.connect_all()
            self._logger.info(f"Hardware initialized. Sensors: {self._multi_ctrl.sensor_order}")
            for sid in self._multi_ctrl.sensor_order:
                disp = SENSOR_ID_MAP.get(sid)
                if disp and disp in self.sensor_panels:
                    self.sensor_panels[disp].update_status(True)
            self.meas_ctrl.set_hardware_available(True)
        except Exception as e:
            self._logger.warning(f"Hardware init failed: {e}")
            # SDK 無しでも学習・可視化は使える。測定だけ明示的に閉じる
            self.meas_ctrl.set_hardware_available(False, str(e))
            self.tabs.setTabText(0, "Measurement (no hardware)")

    def _start_measurement(self, interval: float, save_dir: str, comment: str = "") -> None:
        self._logger.info("Start requested")
        if self._multi_ctrl is None:
            self._logger.error("No hardware connected")
            self.meas_ctrl.restore_start_button()
            return
        self._ts_frames.clear()
        self._ts_alpha.clear()
        self._ts_beta.clear()
        self._ts_gamma.clear()
        try:
            self._meas_thread = MeasurementThread(self._multi_ctrl, interval, save_dir, comment)
            self._meas_thread.frame_acquired.connect(self._on_frame)
            self._meas_thread.measurement_error.connect(lambda s, e: self._logger.error(f"[{s}] {e}"))
            self._meas_thread.finished.connect(lambda: self._logger.info("Measurement thread finished"))
            self._meas_thread.start()
            self._plot_timer.start()
            self._logger.info(f"Measurement started: interval={interval}s")
        except Exception as e:
            self._logger.error(f"Failed to start measurement: {e}")

    def _stop_measurement(self) -> None:
        self._plot_timer.stop()
        self.viz_tab.stop()
        self._viz_initialized = False
        if self._meas_thread is not None:
            self._meas_thread.stop()
            self._meas_thread.wait(3000)
            self._save_analysis_csv()
            self._meas_thread = None
            self._logger.info("Measurement stopped")
        self._analysis_worker.stop()
        self._analysis_worker = AnalysisWorker(self._classifier, maxsize=30)
        self._analysis_worker.analysis_result.connect(self._on_analysis_result)
        self._analysis_worker.start()
        self._hitmap_worker.stop()
        self._hitmap_worker = HitmapWorker(maxsize=30)

    def _save_analysis_csv(self) -> None:
        meas_dir = getattr(self._meas_thread, "_measurement_dir", None)
        if not meas_dir:
            return
        base = meas_dir / "analysis_results"
        base.mkdir(parents=True, exist_ok=True)
        import pandas as pd
        rows: list[dict] = []
        for sid in SENSOR_IDS:
            frames = self._ts_frames.get(sid, [])
            alpha = self._ts_alpha.get(sid, [])
            beta = self._ts_beta.get(sid, [])
            gamma = self._ts_gamma.get(sid, [])
            for f, a, b, g in zip(frames, alpha, beta, gamma):
                rows.append({"sensor": sid, "frame": f, "alpha": a, "beta": b, "gamma": g})
        if rows:
            pd.DataFrame(rows).to_csv(base / "time_series.csv", index=False)
        self._logger.info(f"Analysis results saved to {base}")

    def _on_frame(self, sensor_id: str, frame_num: int, data: Any) -> None:
        self._logger.info(f"_on_frame called: {sensor_id} frame={frame_num}")
        if not self._viz_initialized:
            self._init_viz_watch()
        disp = SENSOR_ID_MAP.get(sensor_id, sensor_id)
        panel = self.sensor_panels.get(disp)
        if panel is None or not isinstance(data, np.ndarray):
            self._logger.warning(f"_on_frame skipped: panel={panel is not None}, is_ndarray={isinstance(data, np.ndarray)}")
            return
        if not self._analysis_worker.enqueue(sensor_id, frame_num, data):
            self._logger.warning(f"  analysis queue full, dropping frame {frame_num} [{sensor_id}]")

    def _on_analysis_result(
        self,
        sensor_id: str,
        frame_num: int,
        alpha: int,
        beta: int,
        gamma: int,
        results: list[dict],
        labelled: np.ndarray | None,
        props: list | None,
    ) -> None:
        disp = SENSOR_ID_MAP.get(sensor_id, sensor_id)
        panel = self.sensor_panels.get(disp)
        if panel is not None:
            panel.update_counts(alpha, beta, gamma, len(results))
        self._ts_frames.setdefault(sensor_id, []).append(frame_num)
        self._ts_alpha.setdefault(sensor_id, []).append(alpha)
        self._ts_beta.setdefault(sensor_id, []).append(beta)
        self._ts_gamma.setdefault(sensor_id, []).append(gamma)
        if labelled is not None:
            self._on_hitmap(sensor_id, labelled, props, frame_num, results)

    def _on_hitmap(self, sensor_id: str, labelled: np.ndarray, props: list, frame_num: int, classification: list[dict]) -> None:
        meas_dir = getattr(self._meas_thread, "_measurement_dir", None)
        if meas_dir is None:
            return
        sub = meas_dir / "analysis_results" / SENSOR_ID_MAP.get(sensor_id, sensor_id)
        queued = self._hitmap_worker.enqueue(labelled, props, classification, frame_num,
                                             SENSOR_ID_MAP.get(sensor_id, sensor_id), sub)
        if not queued:
            self._logger.warning(f"  hitmap queue full, skipping frame {frame_num} [{sensor_id}]")

    def _redraw_plot(self) -> None:
        def get(k: str) -> tuple:
            return (
                self._ts_frames.get(k, []),
                self._ts_alpha.get(k, []),
                self._ts_beta.get(k, []),
                self._ts_gamma.get(k, []),
            )
        self.plot.update_counts(
            *get("E02"), *get("I03"), *get("J03"),
        )

    def _load_saved_model(self) -> None:
        saved = self._config.get("model_path", "")
        if saved and Path(saved).exists():
            try:
                self._classifier.load_model(saved)
                self.meas_ctrl.select_model_by_path(saved)
                self.meas_ctrl.set_classifier_label(saved)
                self._logger.info(f"Auto-loaded model: {saved}")
            except Exception as e:
                self._logger.warning(f"Failed to auto-load model: {e}")
                self.meas_ctrl.set_classifier_label(None)

    def _clear_plot(self) -> None:
        self._ts_frames.clear()
        self._ts_alpha.clear()
        self._ts_beta.clear()
        self._ts_gamma.clear()
        self.plot.switch_mode("counts")
        self._logger.info("Plot cleared")

    def _init_viz_watch(self) -> None:
        if self._viz_initialized:
            return
        meas_dir = getattr(self._meas_thread, "_measurement_dir", None)
        if meas_dir is None:
            self._logger.debug("Viz watch deferred (no measurement dir yet)")
            return
        base = meas_dir / "analysis_results"
        for sid, disp in SENSOR_ID_MAP.items():
            png_dir = base / disp
            self.viz_tab.set_watch_dir(disp, png_dir)
        self.viz_tab.start()
        self._viz_initialized = True
        self._logger.info("Visualization watching started")

    def _on_model_changed(self, model_path: str) -> None:
        try:
            self._classifier.load_model(model_path)
            self._analysis_worker._classifier = self._classifier
            self.meas_ctrl.set_classifier_label(model_path)
            self._config.set("model_path", model_path)
            self._config.save()
            self._logger.info(f"Model loaded: {model_path}")
        except Exception as e:
            self._logger.warning(f"Failed to load model: {e}")
            self.meas_ctrl.set_classifier_label(None)

    def _start_training(self, alpha: str, beta: str, gamma: str, name: str, threshold: float, n_trials: int = 0) -> None:
        self.training_tab.train_btn.setEnabled(False)
        opt = f" (Optuna x{n_trials})" if n_trials > 0 else ""
        self._logger.info(f"Training started: α={alpha} β={beta} γ={gamma}{opt}")
        self._train_worker = TrainingWorker(alpha, beta, gamma, name, threshold, n_trials)
        self._train_worker.progress.connect(self.training_tab.update_progress)
        self._train_worker.finished.connect(self._on_training_done)
        self._train_worker.error.connect(self._on_training_error)
        self._train_worker.start()

    def _on_training_done(self, result: object) -> None:
        self.training_tab.train_btn.setEnabled(True)
        d = dict(result) if hasattr(result, "__getitem__") else {}
        model_path = d.get("model_path", "")
        acc = d.get("accuracy", 0)
        report = d.get("report", {})
        self._logger.info(f"Training complete: accuracy={acc:.3f}, model={model_path}")
        lines = [f"Model: {model_path}", f"Accuracy: {acc:.3f}"]
        for cls_name, metrics in report.items():
            if isinstance(metrics, dict):
                lines.append(f"  {cls_name}: P={metrics.get('precision', 0):.3f} "
                             f"R={metrics.get('recall', 0):.3f} F1={metrics.get('f1-score', 0):.3f}")
        self.training_tab.result_label.setText("\n".join(lines))

    def _on_training_error(self, err: str) -> None:
        self.training_tab.train_btn.setEnabled(True)
        self._logger.error(f"Training failed: {err}")
        self.training_tab.result_label.setText(f"Error: {err}")

    def closeEvent(self, event: Any) -> None:
        self._logger.info("Shutting down...")
        self._info_timer.stop()
        self._plot_timer.stop()
        self.viz_tab.stop()
        if self._meas_thread is not None:
            self._meas_thread.stop()
            self._meas_thread.wait(3000)
        self._analysis_worker.stop()
        self._hitmap_worker.stop()
        if self._train_worker is not None and self._train_worker.isRunning():
            self._train_worker.quit()
            self._train_worker.wait(3000)
        event.accept()

    def _update_sensor_info(self) -> None:
        if self._multi_ctrl is None:
            return
        try:
            infos = self._multi_ctrl.get_all_device_info()
            for sid, info in infos.items():
                disp = SENSOR_ID_MAP.get(sid, sid)
                panel = self.sensor_panels.get(disp)
                if panel:
                    panel.update_info(info)
        except Exception as e:
            self._logger.debug(f"Sensor info update failed: {e}")

    def update_sensor_temp(self, sensor_id: str, temp: float) -> None:
        disp = SENSOR_ID_MAP.get(sensor_id, sensor_id)
        panel = self.sensor_panels.get(disp)
        if panel:
            panel.update_temperature(temp)
