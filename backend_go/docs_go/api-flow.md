API 调用链路说明（基于代码）
===========================

目的
----
面向非代码读者解释一次请求从 API Server 进入，到 Handler 处理，再到 Store 访问 DB 的全过程。

1) API Server：路由与中间件
---------------------------
代码位置：internal/api/server.go

- 入口方法：func (s *Server) Routes(allowedOrigins string) http.Handler
  - 创建路由器：chi.NewRouter()
  - 注册中间件：
    - middleware.RequestID：给每个请求分配 ID
    - middleware.RealIP：解析真实客户端 IP
    - middleware.Recoverer：拦截 panic，避免服务崩溃
    - middleware.Logger：输出访问日志
    - corsMiddleware(allowedOrigins)：跨域处理（Access-Control-Allow-*）
  - 注册路由：
    - router.Get("/healthz", s.handleHealth)
    - router.Route("/api", func(r chi.Router) { ... })
    - 在 /api 路由组内绑定具体接口：
      - GET  /metrics/latest  -> handleLatestMetrics
      - GET  /metrics/trend   -> handleTrend
      - GET  /insights/latest -> handleLatestInsights
      - POST /insights        -> handleCreateInsight
      - POST /metrics/simulate-> handleSimulateMetrics

承上启下：Routes 返回的 Handler 会被 main.go 传入 http.Server，成为真正的 HTTP 入口。

.

2) Handler：请求解析与业务组织
-----------------------------
代码位置：internal/api/server.go

Handler 的共性模式：
1) 解析参数或请求体
2) 调用 Store 获取/写入数据
3) 组装 JSON 响应

示例 A：handleLatestMetrics（读取最新指标）
- 获取数据：s.store.LatestMetrics(r.Context())
- 若无数据：使用 defaultMetrics() 生成默认值，并写入 s.store.InsertMetricsAt(...)
- 输出响应：writeJSON(w, http.StatusOK, MetricsResponse{...})

示例 B：handleTrend（读取趋势）
- 解析参数：parseQueryInt(r, "window", 12)
- 拉取数据：s.store.Trend(r.Context(), window)
- 若无数据：seedTrendMetrics() 生成 12 条并逐条 InsertMetricsAt
- 只返回时间与收入：TrendPoint{Timestamp, Revenue}

示例 C：handleLatestInsights（读取洞察）
- 解析参数：parseQueryInt(r, "limit", 6)
- 拉取数据：s.store.LatestInsights(...)
- 若无数据：插入一条默认洞察（InsertInsight）

示例 D：handleCreateInsight（创建洞察）
- 解析请求体：json.NewDecoder(r.Body).Decode(&payload)
- 拉取最新指标：s.store.LatestMetrics(...)
- 根据 metricKey 生成标题/内容：buildMetricInsight(...)
- 写入数据库：s.store.InsertInsight(...)
- 返回写入结果

承上启下：Handler 不直接写 SQL，只调用 Store，保持职责分离。

3) Store：数据库访问层
----------------------
代码位置：internal/store/store.go

Store 的职责是封装 SQL，只做查询与写入：
- LatestMetrics：查询 metrics_snapshot 最新一条记录
- InsertMetricsAt：插入一条指标快照
- Trend：按 created_at 倒序取 N 条，然后反转为时间升序
- LatestInsights：查询 insights 最新 N 条
- InsertInsight：插入洞察并返回自增 ID

承上启下：Store 的输入是业务层传来的参数，输出是业务层需要的数据结构。

4) DB：表结构与索引
-------------------
代码位置：db/migrations/0001_init.up.sql

表一：metrics_snapshot
- 字段：revenue, growth, sentiment, backlog, created_at
- 索引：created_at（用于最新/趋势查询）

表二：insights
- 字段：title, message, source, created_at
- 索引：created_at（用于最新列表）

承上启下：Store 的 SQL 查询与插入，直接对应这两张表。

5) 端到端请求示意
------------------
用户请求
  |
  v
API Server (Routes + Middleware)
  |
  v
Handler (参数解析 + 业务组织)
  |
  v
Store (SQL 读写封装)
  |
  v
DB (metrics_snapshot / insights)
