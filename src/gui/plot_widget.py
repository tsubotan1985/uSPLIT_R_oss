from typing import Any

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


SENSOR_LABELS = ["Sensor01 (E02)", "Sensor02 (I03)", "Sensor03 (J03)"]


class PlotWidget(FigureCanvasQTAgg):
    def __init__(self, parent: Any = None) -> None:
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.fig.set_tight_layout(True)
        super().__init__(self.fig)
        self.setParent(parent)
        self._axes: list[Any] = []
        self._setup_counts_plot()

    def _setup_counts_plot(self) -> None:
        self.fig.clear()
        self._axes = []
        for i, label in enumerate(SENSOR_LABELS):
            ax = self.fig.add_subplot(3, 1, i + 1)
            ax.set_title(label, fontsize=10)
            ax.set_ylabel("Count")
            ax.set_xlabel("Frame" if i == 2 else "")
            self._axes.append(ax)
        self.draw()

    def update_counts(
        self,
        frames_e02: list[int], alpha_e02: list[int], beta_e02: list[int], gamma_e02: list[int],
        frames_i03: list[int], alpha_i03: list[int], beta_i03: list[int], gamma_i03: list[int],
        frames_j03: list[int], alpha_j03: list[int], beta_j03: list[int], gamma_j03: list[int],
    ) -> None:
        all_data = [
            (frames_e02, alpha_e02, beta_e02, gamma_e02),
            (frames_i03, alpha_i03, beta_i03, gamma_i03),
            (frames_j03, alpha_j03, beta_j03, gamma_j03),
        ]
        for ax, (frames, alpha, beta, gamma) in zip(self._axes, all_data):
            ax.clear()
            if frames:
                ax.plot(frames, alpha, label="α", color="r", linewidth=1)
                ax.plot(frames, beta, label="β", color="g", linewidth=1)
                ax.plot(frames, gamma, label="γ", color="b", linewidth=1)
                ax.legend(fontsize=8)
                ax.set_ylabel("Count")
            ax.relim()
            ax.autoscale()
        self.draw()

    def switch_mode(self, mode: str) -> None:
        pass
