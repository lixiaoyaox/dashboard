"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type Metrics = {
  revenue: number;
  growth: number;
  sentiment: number;
  backlog: number;
};

type Insight = {
  id: string;
  title: string;
  message: string;
  time: string;
};

type ApiMetricsResponse = {
  data: Metrics;
};

type ApiInsight = {
  id: number;
  title: string;
  message: string;
  created_at: string;
};

type ApiInsightsResponse = {
  data: ApiInsight[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8080";

const seedMetrics: Metrics = {
  revenue: 4.82,
  growth: 18.6,
  sentiment: 72,
  backlog: 128,
};

const metricLabels: Array<{
  key: keyof Metrics;
  label: string;
  unit: string;
  hint: string;
}> = [
  { key: "revenue", label: "全球营收", unit: "B", hint: "年度达成率 78%" },
  { key: "growth", label: "用户增长", unit: "%", hint: "本周新增 +6.4%" },
  { key: "sentiment", label: "市场情绪", unit: "%", hint: "媒体声量上涨" },
  { key: "backlog", label: "未交付订单", unit: "K", hint: "48 小时内可清理" },
];

const formatMetric = (key: keyof Metrics, value: number) => {
  if (key === "revenue") {
    return `$${value.toFixed(2)}B`;
  }
  if (key === "backlog") {
    return `${Math.round(value)}K`;
  }
  return `${value.toFixed(1)}%`;
};

const formatClock = () =>
  new Date().toLocaleString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

const formatTime = (value: string) =>
  new Date(value).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });

export default function Home() {
  const [metrics, setMetrics] = useState<Metrics>(seedMetrics);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [clock, setClock] = useState(formatClock());

  useEffect(() => {
    const timer = setInterval(() => setClock(formatClock()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let active = true;
    const fetchMetrics = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/metrics/latest`, {
          cache: "no-store",
        });
        if (!response.ok) return;
        const payload = (await response.json()) as ApiMetricsResponse;
        if (!active) return;
        setMetrics(payload.data);
      } catch {
        // Keep last known metrics on error.
      }
    };

    const fetchInsights = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/insights/latest?limit=4`,
          { cache: "no-store" }
        );
        if (!response.ok) return;
        const payload = (await response.json()) as ApiInsightsResponse;
        if (!active) return;
        setInsights(
          payload.data.map((item) => ({
            id: String(item.id),
            title: item.title,
            message: item.message,
            time: formatTime(item.created_at),
          }))
        );
      } catch {
        // Ignore transient API errors.
      }
    };

    fetchMetrics();
    fetchInsights();
    const metricsTimer = setInterval(fetchMetrics, 4000);
    const insightsTimer = setInterval(fetchInsights, 8000);

    return () => {
      active = false;
      clearInterval(metricsTimer);
      clearInterval(insightsTimer);
    };
  }, []);

  const pulseScore = useMemo(() => {
    return Math.round((metrics.growth + metrics.sentiment) / 2);
  }, [metrics.growth, metrics.sentiment]);

  return (
    <div className="min-h-screen px-6 py-8 text-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <header className="surface glow-border relative overflow-hidden rounded-[32px] p-8">
          <div className="absolute right-8 top-8 hidden h-36 w-36 rounded-full bg-amber-300/20 blur-3xl md:block" />
          <p className="text-xs uppercase tracking-[0.4em] text-amber-200/80">
            CEO 远见仪表盘
          </p>
          <div className="mt-4 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div className="space-y-3">
              <h1 className="font-display text-4xl md:text-5xl">
                经营要点 · 即时洞察
              </h1>
              <p className="max-w-xl text-sm text-white/70">
                汇总全球经营指标、战略线索与 AI 研判，支持高层快速决策。
              </p>
            </div>
            <div className="surface-strong rounded-2xl px-5 py-4 text-sm">
              <p className="text-xs text-white/50">实时刻度</p>
              <p className="mt-1 text-lg font-semibold">{clock}</p>
            </div>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {metricLabels.map((item, index) => (
            <div
              key={item.key}
              className="surface fade-up rounded-3xl p-5"
              style={{ animationDelay: `${index * 90}ms` }}
            >
              <p className="text-xs uppercase tracking-[0.3em] text-white/50">
                {item.label}
              </p>
              <p className="mt-4 text-3xl font-semibold">
                {formatMetric(item.key, metrics[item.key])}
              </p>
              <p className="mt-2 text-xs text-amber-100/80">{item.hint}</p>
            </div>
          ))}
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.4fr_0.6fr]">
          <div className="surface rounded-[32px] p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-white/50">
                  关键洞察
                </p>
                <h2 className="font-display text-2xl">战略信号流</h2>
              </div>
              <span className="rounded-full border border-amber-200/30 px-3 py-1 text-xs text-amber-200/90">
                持续更新
              </span>
            </div>
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {insights.length === 0 ? (
                <div className="surface-strong rounded-2xl p-4 text-sm text-white/60">
                  正在拉取最新洞察…
                </div>
              ) : (
                insights.map((insight) => (
                  <div
                    key={insight.id}
                    className="surface-strong rounded-2xl p-4"
                  >
                    <div className="flex items-center justify-between text-xs text-white/50">
                      <span>{insight.title}</span>
                      <span>{insight.time}</span>
                    </div>
                    <p className="mt-3 text-sm text-white/70">
                      {insight.message}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="surface rounded-[32px] p-6">
            <p className="text-xs uppercase tracking-[0.3em] text-white/50">
              AI 研判中心
            </p>
            <h3 className="mt-2 font-display text-2xl">AI 问答入口</h3>
            <p className="mt-3 text-sm text-white/70">
              点击进入新页面，与 AI 进行战略问答并引用飞书私有知识库。
            </p>
            <div className="mt-6 rounded-2xl border border-amber-200/20 bg-black/30 p-4">
              <div className="flex items-center justify-between text-xs text-white/60">
                <span>实时研判指数</span>
                <span className="text-amber-200">{pulseScore}%</span>
              </div>
              <div className="mt-3 h-2 rounded-full bg-white/10">
                <div
                  className="h-2 rounded-full bg-gradient-to-r from-amber-200 via-amber-400 to-amber-500"
                  style={{ width: `${pulseScore}%` }}
                />
              </div>
            </div>
            <Link
              href="/ai"
              className="mt-6 inline-flex w-full items-center justify-center rounded-2xl border border-amber-200/30 bg-amber-200/10 px-4 py-3 text-sm font-semibold text-amber-100 transition hover:-translate-y-0.5 hover:border-amber-200/60"
            >
              进入 AI 问答页面
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
