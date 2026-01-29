from __future__ import annotations

from datetime import datetime
from typing import List

from .db import Database
from .models import Insight, Metrics


class Store:
    def __init__(self, db: Database) -> None:
        self._db = db

    def latest_metrics(self) -> Metrics | None:
        query = """
            SELECT revenue, growth, sentiment, backlog, created_at
            FROM metrics_snapshot
            ORDER BY created_at DESC
            LIMIT 1
        """
        with self._db.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                if not row:
                    return None
                return Metrics(
                    revenue=float(row["revenue"]),
                    growth=float(row["growth"]),
                    sentiment=float(row["sentiment"]),
                    backlog=int(row["backlog"]),
                    created_at=row["created_at"],
                )

    def insert_metrics(self, metrics: Metrics) -> None:
        self.insert_metrics_at(metrics)

    def insert_metrics_at(self, metrics: Metrics) -> None:
        query = """
            INSERT INTO metrics_snapshot (revenue, growth, sentiment, backlog, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        with self._db.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        metrics.revenue,
                        metrics.growth,
                        metrics.sentiment,
                        metrics.backlog,
                        metrics.created_at,
                    ),
                )

    def trend(self, limit: int) -> List[Metrics]:
        query = """
            SELECT revenue, growth, sentiment, backlog, created_at
            FROM metrics_snapshot
            ORDER BY created_at DESC
            LIMIT %s
        """
        with self._db.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit,))
                rows = cursor.fetchall() or []

        points = [
            Metrics(
                revenue=float(row["revenue"]),
                growth=float(row["growth"]),
                sentiment=float(row["sentiment"]),
                backlog=int(row["backlog"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
        points.reverse()
        return points

    def latest_insights(self, limit: int) -> List[Insight]:
        query = """
            SELECT id, title, message, source, created_at
            FROM insights
            ORDER BY created_at DESC
            LIMIT %s
        """
        with self._db.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit,))
                rows = cursor.fetchall() or []

        return [
            Insight(
                id=int(row["id"]),
                title=row["title"],
                message=row["message"],
                source=row["source"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def insert_insight(self, insight: Insight) -> Insight:
        query = """
            INSERT INTO insights (title, message, source)
            VALUES (%s, %s, %s)
        """
        with self._db.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (insight.title, insight.message, insight.source))
                insight_id = cursor.lastrowid
        return Insight(
            id=int(insight_id),
            title=insight.title,
            message=insight.message,
            source=insight.source,
            created_at=datetime.now(),
        )

