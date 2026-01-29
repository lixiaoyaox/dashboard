from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class Metrics:
    revenue: float
    growth: float
    sentiment: float
    backlog: int
    created_at: datetime


@dataclass
class Insight:
    id: int
    title: str
    message: str
    source: str
    created_at: datetime


@dataclass
class ChatAnswer:
    answer: str
    sources: List[str]

