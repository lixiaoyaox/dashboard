"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  time: string;
  sources?: string[];
};

type ApiChatResponse = {
  data: {
    answer: string;
    sources: string[];
  };
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8080";

const quickPrompts = [
  "请总结本周业务风险点。",
  "结合知识库，给出亚太增长建议。",
  "上季度营收下滑原因有哪些？",
  "从知识库里找出客户流失的预警信号。",
];

const nowLabel = () =>
  new Date().toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });

export default function AIChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages, loading]);

  const handleSend = async (event?: FormEvent) => {
    event?.preventDefault();
    const content = input.trim();
    if (!content || loading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      time: nowLabel(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content }),
      });
      if (!response.ok) {
        throw new Error("api error");
      }
      const payload = (await response.json()) as ApiChatResponse;
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: payload.data.answer,
        time: nowLabel(),
        sources: payload.data.sources,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: "暂时无法获得回答，请稍后再试。",
          time: nowLabel(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen px-6 py-8 text-white">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <header className="surface glow-border rounded-[32px] p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-white/50">
                私有知识库 AI
              </p>
              <h1 className="font-display text-3xl md:text-4xl">
                智能问答中枢
              </h1>
              <p className="mt-2 max-w-xl text-sm text-white/70">
                提问前先检索飞书知识库，并结合实时指标给出建议。
              </p>
            </div>
            <Link
              href="/"
              className="rounded-2xl border border-amber-200/30 px-4 py-2 text-sm text-amber-100 transition hover:border-amber-200/60"
            >
              返回仪表盘
            </Link>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="surface rounded-[28px] p-6">
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-[0.3em] text-white/50">
                对话
              </p>
              <span className="text-xs text-amber-200/90">
                知识库优先
              </span>
            </div>
            <div
              ref={listRef}
              className="mt-4 h-[420px] space-y-3 overflow-y-auto rounded-2xl border border-white/10 bg-black/20 p-4 text-sm"
            >
              {messages.length === 0 ? (
                <div className="text-white/50">
                  输入问题或点选快速问题，AI 会结合飞书知识库回答。
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`rounded-2xl border border-white/10 px-4 py-3 ${
                      msg.role === "user"
                        ? "bg-white/10 text-white"
                        : "bg-white/5 text-white/80"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs text-white/40">
                      <span>{msg.role === "user" ? "你" : "AI"}</span>
                      <span>{msg.time}</span>
                    </div>
                    <p className="mt-2 leading-relaxed">{msg.content}</p>
                    {msg.sources && msg.sources.length > 0 ? (
                      <p className="mt-2 text-xs text-white/40">
                        数据来源：{msg.sources.join(" / ")}
                      </p>
                    ) : null}
                  </div>
                ))
              )}
              {loading ? (
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-xs text-white/50">
                  AI 正在分析知识库与实时指标…
                </div>
              ) : null}
            </div>
            <form onSubmit={handleSend} className="mt-4 flex flex-col gap-3">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="输入问题，例如：根据飞书知识库，本季度最紧急的动作是什么？"
                rows={3}
                className="w-full resize-none rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white placeholder:text-white/40"
              />
              <button
                type="submit"
                disabled={loading}
                className="inline-flex items-center justify-center rounded-2xl border border-amber-200/30 bg-amber-200/10 px-4 py-3 text-sm font-semibold text-amber-100 transition hover:-translate-y-0.5 hover:border-amber-200/60 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "生成中…" : "发送问题"}
              </button>
            </form>
          </div>

          <div className="surface rounded-[28px] p-6">
            <p className="text-xs uppercase tracking-[0.3em] text-white/50">
              快速问题
            </p>
            <h2 className="mt-2 font-display text-2xl">策略建议</h2>
            <p className="mt-2 text-sm text-white/70">
              点击即可填入问题，快速进入思考模式。
            </p>
            <div className="mt-6 space-y-3">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setInput(prompt)}
                  className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-left text-sm text-white/80 transition hover:border-amber-200/40 hover:text-white"
                >
                  {prompt}
                </button>
              ))}
            </div>
            <div className="mt-6 rounded-2xl border border-amber-200/20 bg-black/30 p-4 text-xs text-white/60">
              已接入飞书知识库与实时业务指标，回答将附带来源标签。
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
