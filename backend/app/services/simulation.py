from __future__ import annotations

import random
from datetime import datetime
from threading import Lock

from ..models import Metrics


class Simulation:
    def __init__(self) -> None:
        self._rng = random.Random()
        self._lock = Lock()

    def next_metrics(self, previous: Metrics) -> Metrics:
        with self._lock:
            return Metrics(
                revenue=_clamp(previous.revenue + (self._rng.random() - 0.35) * 0.12, 3.9, 6.2),
                growth=_clamp(previous.growth + (self._rng.random() - 0.45) * 1.6, 10.0, 28.0),
                sentiment=_clamp(previous.sentiment + (self._rng.random() - 0.5) * 2.4, 58.0, 90.0),
                backlog=int(
                    _clamp(float(previous.backlog) + (self._rng.random() - 0.4) * 6, 95.0, 180.0)
                ),
                created_at=datetime.now(),
            )


def _clamp(value: float, min_value: float, max_value: float) -> float:
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value

