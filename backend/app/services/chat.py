from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..ai.deepseek import DeepSeekClient
from ..models import ChatAnswer, Insight, Metrics
from ..store import Store
from .metrics import _default_metrics
from .vector_store import FeishuVectorStore, VectorResult


@dataclass
class ChatContext:
    metrics: Metrics
    trend: List[Metrics]
    insights: List[Insight]


class ChatService:
    def __init__(
        self,
        store: Store,
        ai_client: DeepSeekClient,
        kb: FeishuVectorStore | None = None,
    ) -> None:
        self._store = store
        self._ai = ai_client
        self._kb = kb

    def ask(self, message: str) -> ChatAnswer:
        context = self._build_context()
        kb_results = self._kb.search(message) if self._kb and self._kb.enabled else []
        system_prompt = (
            "你是公司经营分析助理。只能基于提供的数据回答，不编造外部事实。"
            "优先使用知识库检索结果，其次参考实时指标。"
            "如果问题超出数据范围，请说明无法确定并给出建议如何补充数据。"
            "回答使用中文，控制在 220 字以内。"
        )
        user_prompt = build_chat_prompt(message, context, kb_results)
        answer = self._ai.chat(system_prompt, user_prompt)
        answer = " ".join(answer.strip().split())
        sources = _build_sources(context, kb_results)
        return ChatAnswer(answer=answer, sources=sources)

    def _build_context(self) -> ChatContext:
        metrics = self._store.latest_metrics() or _default_metrics()
        trend = self._store.trend(12)
        insights = self._store.latest_insights(6)
        return ChatContext(metrics=metrics, trend=trend, insights=insights)


def _build_sources(context: ChatContext, kb_results: List[VectorResult]) -> List[str]:
    sources = [
        f"metrics@{context.metrics.created_at.strftime('%H:%M')}",
        f"trend@{len(context.trend)}",
        f"insights@{len(context.insights)}",
    ]
    seen = set()
    for result in kb_results:
        label = result.label
        if label in seen:
            continue
        seen.add(label)
        sources.append(f"kb:{label}")
    return sources


def build_chat_prompt(
    message: str,
    context: ChatContext,
    kb_results: List[VectorResult],
) -> str:
    metrics = context.metrics
    trend_summary = "暂无趋势数据"
    if len(context.trend) >= 2:
        first = context.trend[0]
        last = context.trend[-1]
        trend_summary = (
            f"趋势({first.created_at.strftime('%H:%M')}->{last.created_at.strftime('%H:%M')}): "
            f"营收{last.revenue:.2f}B, 增长{last.growth:.1f}%, 情绪{last.sentiment:.0f}%, 积压{last.backlog}K"
        )

    insights_summary = " / ".join([ins.message for ins in context.insights][:3])
    if insights_summary:
        insights_summary = f"最新洞察: {insights_summary}"

    kb_summary = _format_kb_results(kb_results)

    return (
        "公司实时指标："
        f"营收{metrics.revenue:.2f}B，增长{metrics.growth:.1f}%，"
        f"情绪{metrics.sentiment:.0f}%，积压{metrics.backlog}K。"
        f"更新时间：{metrics.created_at.strftime('%H:%M')}。"
        f"{trend_summary}。"
        f"{insights_summary}\n"
        f"{kb_summary}\n"
        f"用户问题：{message}"
    )


def _format_kb_results(results: List[VectorResult]) -> str:
    if not results:
        return "知识库检索结果：未找到相关内容。"
    lines = ["知识库检索结果："]
    for index, result in enumerate(results, start=1):
        lines.append(
            f"{index}. 来源[{result.label}] {result.content}"
        )
    return "\n".join(lines)

