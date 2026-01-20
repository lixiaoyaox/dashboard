"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type MetricKey = "revenue" | "growth" | "sentiment" | "backlog";

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
  source: "auto" | "metric";
};

type ApiInsight = {
  id: number;
  title: string;
  message: string;
  source: "auto" | "metric";
  created_at: string;
};

type ApiMetricsResponse = {
  data: Metrics;
  timestamp: string;
};

type ApiTrendPoint = {
  timestamp: string;
  revenue: number;
};

type ApiTrendResponse = {
  data: ApiTrendPoint[];
};

type ApiInsightsResponse = {
  data: ApiInsight[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8080";

const baseMetrics: Metrics = {
  revenue: 4.82,
  growth: 18.6,
  sentiment: 72,
  backlog: 128,
};

const heatmapPoints = [
  { id: "NA", x: 70, y: 70, size: 14, intensity: 0.85 },
  { id: "LATAM", x: 96, y: 110, size: 10, intensity: 0.6 },
  { id: "EU", x: 155, y: 66, size: 12, intensity: 0.8 },
  { id: "MEA", x: 176, y: 102, size: 9, intensity: 0.55 },
  { id: "APAC", x: 238, y: 86, size: 16, intensity: 0.9 },
  { id: "ANZ", x: 256, y: 130, size: 8, intensity: 0.45 },
];

const metricConfig: Record<MetricKey, { label: string; unit: string; hint: string }> = {
  revenue: {
    label: "全球营收",
    unit: "B",
    hint: "滚动 24 小时",
  },
  growth: {
    label: "用户增长",
    unit: "%",
    hint: "月环比提升",
  },
  sentiment: {
    label: "情绪指数",
    unit: "%",
    hint: "社媒 + 媒体",
  },
  backlog: {
    label: "未交付订单",
    unit: "K",
    hint: "待交付",
  },
};

const nowLabel = () =>
  new Date().toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });

const formatTime = (value: string) =>
  new Date(value).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });

const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max);

const formatMetric = (key: MetricKey, value: number) => {
  if (key === "revenue") {
    return `$${value.toFixed(2)}${metricConfig[key].unit}`;
  }
  if (key === "backlog") {
    return `${Math.round(value)}${metricConfig[key].unit}`;
  }
  return `${value.toFixed(1)}${metricConfig[key].unit}`;
};

const buildMetricInsight = (key: MetricKey, metrics: Metrics) => {
  switch (key) {
    case "revenue":
      return `营收增速维持在 $${metrics.revenue.toFixed(2)}B。建议核心区域保持高端定价，同时在拉美通过组合包稳住份额。`;
    case "growth":
      return `用户增长保持在 ${metrics.growth.toFixed(1)}%。建议将获客预算倾向亚太，并在成熟市场加倍投入推荐裂变。`;
    case "sentiment":
      return `情绪指数为 ${metrics.sentiment.toFixed(0)}%。在 EMEA 提前布局公关，有望突破 75% 正面阈值。`;
    case "backlog":
      return `未交付订单约 ${Math.round(metrics.backlog)}K。建议优先提升物流吞吐，降低高端 SKU 流失风险。`;
    default:
      return "战略方向保持一致。";
  }
};

const seedTrend = () =>
  Array.from({ length: 12 }, (_, index) =>
    55 + index * 1.8 + Math.sin(index / 1.8) * 6
  );

export default function Home() {
  const [metrics, setMetrics] = useState<Metrics>(baseMetrics);
  const [trend, setTrend] = useState<number[]>(seedTrend);
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>("revenue");
  const [clock, setClock] = useState("—");
  const [insights, setInsights] = useState<Insight[]>([
    {
      id: "seed",
      title: "高管简报",
      message:
        "全球表现高于计划，继续将市场投入对齐高动能区域。",
      time: "—",
      source: "auto",
    },
  ]);

  const metricsRef = useRef(metrics);
  useEffect(() => {
    metricsRef.current = metrics;
  }, [metrics]);

  useEffect(() => {
    setClock(nowLabel());
    const clockInterval = setInterval(() => setClock(nowLabel()), 1000);
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
        // Ignore transient API errors.
      }
    };

    const fetchTrend = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/metrics/trend?window=12`,
          { cache: "no-store" }
        );
        if (!response.ok) return;
        const payload = (await response.json()) as ApiTrendResponse;
        if (!active) return;
        const mapped = payload.data.map((point) =>
          clamp(point.revenue * 10, 48, 96)
        );
        if (mapped.length) {
          setTrend(mapped);
        }
      } catch {
        // Ignore transient API errors.
      }
    };

    const fetchInsights = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/insights/latest?limit=6`,
          { cache: "no-store" }
        );
        if (!response.ok) return;
        const payload = (await response.json()) as ApiInsightsResponse;
        if (!active) return;
        const mapped = payload.data.map((insight) => ({
          id: String(insight.id),
          title: insight.title,
          message: insight.message,
          time: formatTime(insight.created_at),
          source: insight.source,
        }));
        if (mapped.length) {
          setInsights(mapped);
        }
      } catch {
        // Ignore transient API errors.
      }
    };

    fetchMetrics();
    fetchTrend();
    fetchInsights();

    const metricsInterval = setInterval(fetchMetrics, 1000);
    const trendInterval = setInterval(fetchTrend, 1000);
    const insightInterval = setInterval(fetchInsights, 5000);

    return () => {
      active = false;
      clearInterval(clockInterval);
      clearInterval(metricsInterval);
      clearInterval(trendInterval);
      clearInterval(insightInterval);
    };
  }, []);

  const linePoints = useMemo(() => {
    const width = 320;
    const height = 120;
    return trend
      .map((value, index) => {
        const x = (index / (trend.length - 1)) * width;
        const y = height - (value / 100) * 90 - 10;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [trend]);

  const handleMetricClick = async (key: MetricKey) => {
    setSelectedMetric(key);
    try {
      const response = await fetch(`${API_BASE}/api/insights`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ metricKey: key }),
      });
      if (!response.ok) {
        throw new Error("API error");
      }
      const payload = (await response.json()) as { data: ApiInsight };
      const mapped = {
        id: String(payload.data.id),
        title: payload.data.title,
        message: payload.data.message,
        time: formatTime(payload.data.created_at),
        source: payload.data.source,
      };
      setInsights((prev) => [mapped, ...prev].slice(0, 6));
      return;
    } catch {
      const message = buildMetricInsight(key, metricsRef.current);
      setInsights((prev) => [
        {
          id: `metric-${key}-${Date.now()}`,
          title: `${metricConfig[key].label}聚焦`,
          message,
          time: nowLabel(),
          source: "metric",
        },
        ...prev,
      ].slice(0, 6));
    }
  };

  return (
    <div className="min-h-screen text-white">
      <div className="grid grid-cols-1 gap-6 p-6 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
        <aside className="panel grid-fade flex flex-col justify-between rounded-3xl p-6">
          <div className="space-y-8">
            <div>
              <p className="text-xs uppercase tracking-[0.4em] text-gold">CEO 远见</p>
              <h2 className="font-display text-2xl">金辉中枢</h2>
              <p className="mt-2 text-sm text-white/60">
                面向实时决策的全球业务指挥台。
              </p>
            </div>
            <nav className="space-y-3 text-sm">
              {[
                "高管视图",
                "市场版图",
                "信号中心",
                "运营脉搏",
                "安全防线",
              ].map((item) => (
                <div
                  key={item}
                  className="flex items-center justify-between rounded-2xl border border-white/10 px-4 py-3 text-white/70"
                >
                  <span>{item}</span>
                  <span className="text-xs text-gold-soft">实时</span>
                </div>
              ))}
            </nav>
          </div>
          <div className="space-y-4">
            <div className="rounded-2xl border border-white/10 p-4">
              <p className="text-xs text-white/50">活跃区域</p>
              <p className="text-2xl font-semibold">18</p>
              <p className="text-xs text-white/50">实时信号流入</p>
            </div>
            <div className="rounded-2xl border border-white/10 p-4">
              <p className="text-xs text-white/50">AI 可信度</p>
              <p className="text-2xl font-semibold text-gold">94%</p>
              <p className="text-xs text-white/50">战略一致性</p>
            </div>
          </div>
        </aside>

        <main className="space-y-6">
          <header className="panel rounded-3xl p-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.35em] text-gold">全球总览</p>
                <h1 className="font-display text-4xl md:text-5xl">
                  CEO 远见仪表盘但是
                </h1>
                <p className="mt-2 text-sm text-white/60">
                  面向董事级决策场景的实时洞察。
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 px-4 py-3">
                <p className="text-xs text-white/50">实时同步</p>
                <p className="text-lg font-semibold">{clock}</p>
              </div>
            </div>
          </header>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {(Object.keys(metricConfig) as MetricKey[]).map((key) => {
              const metric = metricConfig[key];
              const isActive = selectedMetric === key;
              const delta = metrics[key] - baseMetrics[key];
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => handleMetricClick(key)}
                  className={`panel rounded-3xl p-5 text-left transition duration-300 hover:-translate-y-1 hover:border-white/30 ${
                    isActive ? "glow-ring border border-yellow-300/40" : ""
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.25em] text-white/50">
                        {metric.label}
                      </p>
                      <p className="mt-3 text-3xl font-semibold">
                        {formatMetric(key, metrics[key])}
                      </p>
                      <p className="mt-1 text-xs text-white/50">{metric.hint}</p>
                    </div>
                    <div className="rounded-full border border-white/15 p-3 text-gold">
                      <svg
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M4 12h6l2-4 4 8 2-4h2" />
                      </svg>
                    </div>
                  </div>
                  <div className="mt-5 flex items-center justify-between text-xs text-white/50">
                    <span>
                      变化 {delta >= 0 ? "+" : ""}
                      {delta.toFixed(2)}
                    </span>
                    <span>点击获取解读</span>
                  </div>
                </button>
              );
            })}
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <div className="panel rounded-3xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-white/50">
                    全球销售热力
                  </p>
                  <h3 className="font-display text-2xl">营收温度</h3>
                </div>
                <span className="text-xs text-gold">实时</span>
              </div>
              <div className="relative mt-6 h-[220px] rounded-2xl border border-white/10 bg-black/30">
                <svg viewBox="0 0 320 180" className="h-full w-full">
                  <defs>
                    <radialGradient id="heat" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stopColor="#f1d7a1" stopOpacity="0.9" />
                      <stop offset="100%" stopColor="#d6b36a" stopOpacity="0" />
                    </radialGradient>
                  </defs>
                  <rect width="320" height="180" fill="transparent" />
                  <path
                    d="M30 70l30-20 35 10 20 30-15 22-35 8-25-25z"
                    fill="#10151c"
                    stroke="#2f3a45"
                    strokeWidth="1"
                  />
                  <path
                    d="M130 55l35-18 30 10 16 28-12 30-34 10-25-18z"
                    fill="#10151c"
                    stroke="#2f3a45"
                    strokeWidth="1"
                  />
                  <path
                    d="M210 72l35-12 28 16 18 26-18 30-38 6-18-26z"
                    fill="#10151c"
                    stroke="#2f3a45"
                    strokeWidth="1"
                  />
                  {heatmapPoints.map((point) => (
                    <circle
                      key={point.id}
                      cx={point.x}
                      cy={point.y}
                      r={point.size}
                      fill="url(#heat)"
                      opacity={point.intensity}
                    />
                  ))}
                </svg>
                <div className="absolute inset-0 rounded-2xl border border-white/5" />
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3 text-xs text-white/60">
                <div className="rounded-xl border border-white/10 p-3">
                  <p className="text-gold">APAC</p>
                  <p className="text-lg font-semibold">+14.8%</p>
                </div>
                <div className="rounded-xl border border-white/10 p-3">
                  <p className="text-gold">EMEA</p>
                  <p className="text-lg font-semibold">+9.2%</p>
                </div>
                <div className="rounded-xl border border-white/10 p-3">
                  <p className="text-gold">AMER</p>
                  <p className="text-lg font-semibold">+11.6%</p>
                </div>
              </div>
            </div>

            <div className="panel rounded-3xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-white/50">
                    营收动能
                  </p>
                  <h3 className="font-display text-2xl">增长曲线</h3>
                </div>
                <span className="text-xs text-gold">自动更新</span>
              </div>
              <div className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4">
                <svg viewBox="0 0 320 120" className="h-40 w-full">
                  <defs>
                    <linearGradient id="line" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#d6b36a" stopOpacity="0.9" />
                      <stop offset="100%" stopColor="#d6b36a" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path
                    d={`M0 120 L${linePoints} L320 120 Z`}
                    fill="url(#line)"
                  />
                  <polyline
                    points={linePoints}
                    fill="none"
                    stroke="#f1d7a1"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <div className="mt-4 space-y-3 text-xs text-white/60">
                <div className="flex items-center justify-between">
                  <span>转化提升</span>
                  <span className="text-gold">+6.4%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>平均客单</span>
                  <span className="text-gold">$1.28M</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>管道加速</span>
                  <span className="text-gold">+12.2%</span>
                </div>
              </div>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="panel rounded-3xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-white/50">
                    社交情绪
                  </p>
                  <h3 className="font-display text-2xl">市场情绪指数</h3>
                </div>
                <span className="text-xs text-gold">流式更新</span>
              </div>
              <div className="mt-6 space-y-4">
                <div>
                  <div className="mb-2 flex items-center justify-between text-xs text-white/60">
                    <span>正面</span>
                    <span>{metrics.sentiment.toFixed(0)}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10">
                    <div
                      className="h-2 rounded-full bg-gradient-to-r from-amber-200 to-yellow-500"
                      style={{ width: `${metrics.sentiment}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="mb-2 flex items-center justify-between text-xs text-white/60">
                    <span>中性</span>
                    <span>{Math.max(0, 100 - metrics.sentiment - 12).toFixed(0)}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10">
                    <div
                      className="h-2 rounded-full bg-gradient-to-r from-slate-500 to-slate-300"
                      style={{ width: `${Math.max(0, 100 - metrics.sentiment - 12)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="mb-2 flex items-center justify-between text-xs text-white/60">
                    <span>负面</span>
                    <span>12%</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10">
                    <div className="h-2 w-[12%] rounded-full bg-gradient-to-r from-rose-500 to-red-400" />
                  </div>
                </div>
              </div>
              <div className="mt-6 grid grid-cols-3 gap-3 text-xs text-white/60">
                <div className="rounded-xl border border-white/10 p-3">
                  <p className="text-gold">提及量</p>
                  <p className="text-lg font-semibold">182K</p>
                </div>
                <div className="rounded-xl border border-white/10 p-3">
                  <p className="text-gold">影响力</p>
                  <p className="text-lg font-semibold">Top 4%</p>
                </div>
                <div className="rounded-xl border border-white/10 p-3">
                  <p className="text-gold">媒体声量</p>
                  <p className="text-lg font-semibold">+32%</p>
                </div>
              </div>
            </div>

            <div className="panel rounded-3xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-white/50">
                    运营脉搏
                  </p>
                  <h3 className="font-display text-2xl">履约就绪度</h3>
                </div>
                <span className="text-xs text-gold">实时</span>
              </div>
              <div className="mt-6 space-y-4 text-xs text-white/60">
                {[
                  { label: "物流", value: 86 },
                  { label: "供应", value: 72 },
                  { label: "客服", value: 91 },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="mb-2 flex items-center justify-between">
                      <span>{item.label}</span>
                      <span>{item.value}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-white/10">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-yellow-200 via-amber-400 to-yellow-500"
                        style={{ width: `${item.value}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-6 rounded-2xl border border-white/10 p-4 text-sm text-white/70">
                <p className="text-gold">优先告警</p>
                <p className="mt-2">
                  高端 SKU 积压需要在 48 小时内提升 6% 产能。
                </p>
              </div>
            </div>
          </section>
        </main>

        <aside className="panel-strong rounded-3xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-white/50">
                AI 战略顾问
              </p>
              <h3 className="font-display text-2xl">高管智囊</h3>
            </div>
            <span className="rounded-full border border-white/20 px-3 py-1 text-xs text-gold">
              已启用
            </span>
          </div>
          <div className="mt-6 space-y-4">
            {insights.map((insight) => (
              <div
                key={insight.id}
                className="rounded-2xl border border-white/10 bg-white/5 p-4"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-gold-soft">
                    {insight.title}
                  </p>
                  <span className="text-xs text-white/40">{insight.time}</span>
                </div>
                <p className="mt-2 text-sm text-white/70">{insight.message}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 rounded-2xl border border-white/10 bg-black/40 p-4 text-sm text-white/60">
            <p className="text-gold">提示</p>
            <p className="mt-2">点击任意 KPI 卡片即可获得即时解读。</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
