from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from ..models import Metrics
from ..store import Store
from .simulation import Simulation


class MetricsService:
    def __init__(self, store: Store, simulator: Simulation) -> None:
        self._store = store
        self._simulator = simulator

    def latest(self) -> Metrics:
        metrics = self._store.latest_metrics()
        if metrics is None:
            metrics = _default_metrics()
            try:
                self._store.insert_metrics_at(metrics)
            except Exception:
                pass
        return metrics

    def trend(self, window: int) -> List[Metrics]:
        points = self._store.trend(window)
        if not points:
            points = _seed_trend_metrics()
            for point in points:
                try:
                    self._store.insert_metrics_at(point)
                except Exception:
                    break
        return points

    def simulate(self) -> Metrics:
        metrics = self._store.latest_metrics() or _default_metrics()
        next_metrics = self._simulator.next_metrics(metrics)
        self._store.insert_metrics(next_metrics)
        return next_metrics


def _default_metrics() -> Metrics:
    return Metrics(
        revenue=4.82,
        growth=18.6,
        sentiment=72.0,
        backlog=128,
        created_at=datetime.now(),
    )


def _seed_trend_metrics() -> List[Metrics]:
    base = _default_metrics()
    points: List[Metrics] = []
    for i in range(12):
        value = 55 + float(i) * 1.8 + (float(i) / 1.8) * 2.0
        points.append(
            Metrics(
                revenue=value / 10,
                growth=base.growth,
                sentiment=base.sentiment,
                backlog=base.backlog,
                created_at=datetime.now() + timedelta(minutes=i - 12),
            )
        )
    return points

