from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Metrics(BaseModel):
    revenue: float
    growth: float
    sentiment: float
    backlog: int
    created_at: datetime = Field(alias="created_at")


class Insight(BaseModel):
    id: int
    title: str
    message: str
    source: str
    created_at: datetime = Field(alias="created_at")


class MetricsResponse(BaseModel):
    data: Metrics
    timestamp: datetime


class TrendPoint(BaseModel):
    timestamp: datetime
    revenue: float


class TrendResponse(BaseModel):
    data: List[TrendPoint]


class InsightsResponse(BaseModel):
    data: List[Insight]


class InsightRequest(BaseModel):
    metricKey: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]


class ChatEnvelope(BaseModel):
    data: ChatResponse


class ErrorResponse(BaseModel):
    error: str


class SimpleDataResponse(BaseModel):
    data: dict

