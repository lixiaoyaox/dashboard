from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import List

from ..ai.deepseek import DeepSeekClient
from ..models import Insight, Metrics
from ..store import Store


@dataclass
class InsightJSON:
    analysis: str
    suggestions: List[str]


class InsightsService:
    def __init__(self, store: Store, ai_client: DeepSeekClient) -> None:
        self._store = store
        self._ai = ai_client

    def latest(self, limit: int) -> List[Insight]:
        items = self._store.latest_insights(limit)
        if not items:
            metrics = self._store.latest_metrics() or _default_metrics()
            seed = self._generate_insight(metrics, "overview", "auto")
            items = [seed]
        return items

    def create(self, metric_key: str) -> Insight:
        metrics = self._store.latest_metrics() or _default_metrics()
        return self._generate_insight(metrics, metric_key, "metric")

    def generate_auto(self, metrics: Metrics) -> Insight:
        return self._generate_insight(metrics, "overview", "auto")

    def _generate_insight(self, metrics: Metrics, focus_key: str, source: str) -> Insight:
        trend = self._store.trend(12)
        system_prompt, user_prompt = build_deepseek_prompt(metrics, trend, focus_key)
        message = self._ai.chat(system_prompt, user_prompt)
        message = normalize_insight(message, 300)
        insight = Insight(id=0, title="AI 战略顾问", message=message, source=source, created_at=metrics.created_at)
        return self._store.insert_insight(insight)


def build_deepseek_prompt(metrics: Metrics, trend: List[Metrics], focus_key: str) -> tuple[str, str]:
    system_prompt = (
        "你是企业战略分析师。基于提供的数据做真实、克制的分析，不编造背景或外部事实。"
        "必须输出严格 JSON：{\"analysis\":\"...\",\"suggestions\":[\"...\",\"...\"]}。"
        "analysis 为连贯中文正文，不要标题、分段、列表、符号或 Markdown。"
        "analysis 必须覆盖营收、用户增长、情绪、未交付订单四项，并对每项给出一句简短判断。"
        "suggestions 为 2-4 条行动建议短句。总长度不超过 300 字。"
    )

    focus = focus_key or "overview"

    trend_summary = "趋势数据不足"
    if len(trend) >= 2:
        first = trend[0]
        last = trend[-1]
        trend_summary = (
            "趋势起止："
            f"{first.created_at.strftime('%H:%M')} -> {last.created_at.strftime('%H:%M')}，"
            f"营收{format_delta(first.revenue, last.revenue, 'B')}，"
            f"增长{format_delta(first.growth, last.growth, '%')}，"
            f"情绪{format_delta(first.sentiment, last.sentiment, '%')}，"
            f"积压{format_delta(float(first.backlog), float(last.backlog), 'K')}"
        )

    user_prompt = (
        "公司实时指标："
        f"营收{format_float(metrics.revenue, 2)}B，增长{format_float(metrics.growth, 1)}%，"
        f"情绪{format_float(metrics.sentiment, 0)}%，积压{metrics.backlog}K。"
        f"更新时间：{metrics.created_at.strftime('%H:%M')}。"
        f"关注点：{focus}。{trend_summary}。"
        "请给出真实分析与行动建议。"
    )

    return system_prompt, user_prompt


def normalize_insight(message: str, max_chars: int) -> str:
    trimmed = (message or "").strip()
    trimmed = _try_format_insight_json(trimmed)
    trimmed = _strip_markdown(trimmed)
    trimmed = " ".join(trimmed.replace("\n", " ").split())
    return trimmed[:max_chars]


def _strip_markdown(value: str) -> str:
    for token in ["#", "*", "`", "_", ">", "- ", "+ ", "|", "[", "]", "(", ")"]:
        value = value.replace(token, "")
    return value


def _try_format_insight_json(value: str) -> str:
    raw = value.strip()
    if not raw:
        return raw
    if raw.startswith("```"):
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return value
    raw = raw[start : end + 1]
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return value

    analysis = str(parsed.get("analysis", "")).strip()
    suggestions = [
        str(item).strip() for item in (parsed.get("suggestions") or []) if str(item).strip()
    ][:4]

    if not analysis and not suggestions:
        return value
    if not suggestions:
        return analysis
    return f"{analysis} 建议：{'；'.join(suggestions)}"


def format_delta(start: float, end: float, unit: str) -> str:
    delta = end - start
    prefix = "+" if delta >= 0 else ""
    return f"{prefix}{format_float(delta, 2)}{unit}"


def format_float(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}"


def _default_metrics() -> Metrics:
    return Metrics(
        revenue=4.82,
        growth=18.6,
        sentiment=72.0,
        backlog=128,
        created_at=datetime.now(),
    )
