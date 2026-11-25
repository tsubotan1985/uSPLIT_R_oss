from collections import defaultdict


class TimeSeriesAggregator:
    def __init__(self) -> None:
        self._data: dict[str, list[dict]] = defaultdict(list)

    def accumulate(self, frame_number: int, sensor_id: str, classification: list[dict]) -> None:
        alpha = sum(1 for c in classification if c.get("class") == 0)
        beta = sum(1 for c in classification if c.get("class") == 1)
        gamma = sum(1 for c in classification if c.get("class") == 2)
        self._data[sensor_id].append({
            "frame": frame_number,
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
            "total": len(classification),
        })

    def get_series(self, sensor_id: str) -> list[dict]:
        return list(self._data.get(sensor_id, []))

    def clear(self) -> None:
        self._data.clear()
