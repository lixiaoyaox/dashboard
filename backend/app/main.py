from __future__ import annotations

import threading
import time
from typing import Iterable

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .ai.deepseek import DeepSeekClient, DeepSeekConfig
from .api.routes import ServiceBundle, build_router
from .config import load_settings
from .db import Database
from .services.chat import ChatService
from .services.feishu_bot import FeishuBotService
from .services.feishu_doc_indexer import FeishuDocumentIndexer
from .services.feishu_events import FeishuEventService
from .services.insights import InsightsService
from .services.metrics import MetricsService
from .services.simulation import Simulation
from .services.vector_store import FeishuVectorStore
from .store import Store


def _parse_allowed_origins(value: str) -> Iterable[str]:
    if not value or value.strip() == "*":
        return ["*"]
    return [item.strip() for item in value.split(",") if item.strip()]


class SimulationRunner:
    def __init__(
        self,
        metrics_service: MetricsService,
        insights_service: InsightsService,
        metrics_every: float,
        insights_every: float,
    ) -> None:
        self._metrics_service = metrics_service
        self._insights_service = insights_service
        self._metrics_every = metrics_every
        self._insights_every = insights_every
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        next_metrics_at = time.time() + self._metrics_every
        next_insights_at = time.time() + self._insights_every
        while not self._stop_event.is_set():
            now = time.time()
            if now >= next_metrics_at:
                try:
                    self._metrics_service.simulate()
                except Exception:
                    pass
                next_metrics_at = now + self._metrics_every
            if now >= next_insights_at:
                try:
                    metrics = self._metrics_service.latest()
                    self._insights_service.generate_auto(metrics)
                except Exception:
                    pass
                next_insights_at = now + self._insights_every
            time.sleep(0.2)


settings = load_settings()

db = Database(settings)
store = Store(db)

deepseek = DeepSeekClient(
    DeepSeekConfig(
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key,
        model=settings.deepseek_model,
        embed_base_url=settings.deepseek_embed_base_url,
        embed_model=settings.deepseek_embed_model,
    )
)

metrics_service = MetricsService(store, Simulation())
insights_service = InsightsService(store, deepseek)
vector_store = FeishuVectorStore(settings)
doc_indexer = FeishuDocumentIndexer(settings, vector_store)
chat_service = ChatService(store, deepseek, vector_store)
feishu_bot_service = FeishuBotService(settings, doc_indexer)
feishu_event_service = FeishuEventService(settings, feishu_bot_service, doc_indexer)

services = ServiceBundle(
    metrics=metrics_service,
    insights=insights_service,
    chat=chat_service,
    feishu=feishu_event_service,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(build_router(services))


@app.on_event("startup")
def _startup() -> None:
    if settings.enable_simulation:
        app.state.simulation_runner = SimulationRunner(
            metrics_service,
            insights_service,
            settings.sim_metrics_every,
            settings.sim_insights_every,
        )
        app.state.simulation_runner.start()


@app.on_event("shutdown")
def _shutdown() -> None:
    runner = getattr(app.state, "simulation_runner", None)
    if runner is not None:
        runner.stop()


@app.exception_handler(HTTPException)
def _handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(ValueError)
def _handle_value_error(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(RuntimeError)
def _handle_runtime_error(_: Request, exc: RuntimeError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"error": str(exc)})


@app.exception_handler(Exception)
def _handle_exception(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": str(exc)})
