import numpy as np

from src.analysis.spectrum import compute_energy_spectrum
from src.analysis.time_series import TimeSeriesAggregator


class TestSpectrum:
    def test_compute_returns_dict_with_four_keys(self) -> None:
        matrix = np.random.rand(256, 256).astype(np.float64)
        labels = np.zeros((256, 256), dtype=int)
        labels[10:12, 10:12] = 1
        labels[20:25, 20:25] = 2
        classification = [{"class": 0}, {"class": 1}]
        result = compute_energy_spectrum(matrix, labels, classification)
        assert set(result.keys()) == {"alpha", "beta", "gamma", "total"}

    def test_empty_matrix_returns_zero_histograms(self) -> None:
        matrix = np.zeros((256, 256), dtype=np.float64)
        labels = np.zeros((256, 256), dtype=int)
        result = compute_energy_spectrum(matrix, labels, [])
        for arr in result.values():
            assert np.all(arr == 0)


class TestTimeSeries:
    def test_accumulate_and_get_series(self) -> None:
        agg = TimeSeriesAggregator()
        agg.accumulate(1, "E02", [{"class": 0}, {"class": 1}])
        agg.accumulate(2, "E02", [{"class": 2}])
        series = agg.get_series("E02")
        assert len(series) == 2
        assert series[0]["frame"] == 1
        assert series[0]["alpha"] == 1
        assert series[0]["beta"] == 1
        assert series[1]["gamma"] == 1

    def test_get_series_unknown_sensor(self) -> None:
        agg = TimeSeriesAggregator()
        assert agg.get_series("nonexistent") == []

    def test_clear(self) -> None:
        agg = TimeSeriesAggregator()
        agg.accumulate(1, "E02", [{"class": 0}])
        agg.clear()
        assert agg.get_series("E02") == []
