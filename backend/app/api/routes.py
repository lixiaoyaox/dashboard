from __future__ import annotations

from datetime import datetime

import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from ..models import Metrics
from ..services.chat import ChatService
from ..services.feishu_events import FeishuEventService
from ..services.insights import InsightsService
from ..services.metrics import MetricsService
from .schemas import (
    ChatEnvelope,
    ChatRequest,
    Insight,
    InsightRequest,
    InsightsResponse,
    Metrics as MetricsSchema,
    MetricsResponse,
    SimpleDataResponse,
    TrendPoint,
    TrendResponse,
)


class ServiceBundle:
    def __init__(
        self,
        metrics: MetricsService,
        insights: InsightsService,
        chat: ChatService,
        feishu: FeishuEventService,
    ) -> None:
        self.metrics = metrics
        self.insights = insights
        self.chat = chat
        self.feishu = feishu


def build_router(services: ServiceBundle) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @router.get("/api/metrics/latest", response_model=MetricsResponse)
    def latest_metrics() -> MetricsResponse:
        metrics = services.metrics.latest()
        return MetricsResponse(data=_metrics_to_schema(metrics), timestamp=datetime.now())

    @router.get("/api/metrics/trend", response_model=TrendResponse)
    def metrics_trend(window: int = 12) -> TrendResponse:
        if window < 3:
            window = 3
        points = services.metrics.trend(window)
        trend = [TrendPoint(timestamp=point.created_at, revenue=point.revenue) for point in points]
        return TrendResponse(data=trend)

    @router.post("/api/metrics/simulate", response_model=SimpleDataResponse)
    def metrics_simulate() -> SimpleDataResponse:
        next_metrics = services.metrics.simulate()
        return SimpleDataResponse(data=_metrics_to_schema(next_metrics).model_dump())

    @router.get("/api/insights/latest", response_model=InsightsResponse)
    def latest_insights(limit: int = 6) -> InsightsResponse:
        if limit < 1:
            limit = 6
        items = services.insights.latest(limit)
        return InsightsResponse(
            data=[
                Insight(
                    id=insight.id,
                    title=insight.title,
                    message=insight.message,
                    source=insight.source,
                    created_at=insight.created_at,
                )
                for insight in items
            ]
        )

    @router.post("/api/insights", response_model=SimpleDataResponse)
    def create_insight(payload: InsightRequest) -> SimpleDataResponse:
        try:
            insight = services.insights.create(payload.metricKey)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        return SimpleDataResponse(
            data={
                "id": insight.id,
                "title": insight.title,
                "message": insight.message,
                "source": insight.source,
                "created_at": insight.created_at,
            }
        )

    @router.post("/api/chat", response_model=ChatEnvelope)
    def chat(payload: ChatRequest) -> ChatEnvelope:
        if not payload.message.strip():
            raise HTTPException(status_code=400, detail="message is required")
        try:
            answer = services.chat.ask(payload.message)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        return ChatEnvelope(data={"answer": answer.answer, "sources": answer.sources})

    @router.post("/api/feishu/events")
    async def feishu_events(request: Request, background_tasks: BackgroundTasks) -> dict:
        raw_body = await request.body()
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid json") from exc
        return services.feishu.handle_event(payload, raw_body, request.headers, background_tasks)

    return router


def _metrics_to_schema(metrics: Metrics) -> MetricsSchema:
    return MetricsSchema(
        revenue=metrics.revenue,
        growth=metrics.growth,
        sentiment=metrics.sentiment,
        backlog=metrics.backlog,
        created_at=metrics.created_at,
    )
