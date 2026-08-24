from collections import defaultdict
from threading import Lock


class MetricsRegistry:
    """Small Prometheus text registry with bounded, low-cardinality labels."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: defaultdict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(
            float
        )
        self._histograms: defaultdict[
            tuple[str, tuple[tuple[str, str], ...]], tuple[int, float]
        ] = defaultdict(lambda: (0, 0.0))

    def increment(self, name: str, amount: float = 1, **labels: str) -> None:
        key = name, tuple(sorted(labels.items()))
        with self._lock:
            self._counters[key] += amount

    def observe(self, name: str, value: float, **labels: str) -> None:
        key = name, tuple(sorted(labels.items()))
        with self._lock:
            count, total = self._histograms[key]
            self._histograms[key] = count + 1, total + value

    def render(self) -> str:
        lines: list[str] = []
        with self._lock:
            for (name, labels), value in sorted(self._counters.items()):
                lines.append(f"{name}{self._format_labels(labels)} {value}")
            for (name, labels), (count, total) in sorted(self._histograms.items()):
                rendered = self._format_labels(labels)
                lines.append(f"{name}_count{rendered} {count}")
                lines.append(f"{name}_sum{rendered} {total}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _format_labels(labels: tuple[tuple[str, str], ...]) -> str:
        if not labels:
            return ""
        values = ",".join(f'{key}="{value}"' for key, value in labels)
        return "{" + values + "}"


metrics = MetricsRegistry()
