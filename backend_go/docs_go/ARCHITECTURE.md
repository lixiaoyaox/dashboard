# MyDashboard 后端架构说明

## 📋 目录
- [整体架构](#整体架构)
- [目录结构](#目录结构)
- [数据流向](#数据流向)
- [核心模块详解](#核心模块详解)
- [API接口说明](#api接口说明)

---

## 整体架构

本项目采用经典的**分层架构**设计，从上到下分为：

```
┌─────────────────────────────────────┐
│   HTTP API Layer (api/)             │  ← 路由、请求处理、响应格式化
├─────────────────────────────────────┤
│   Service Layer (service/)          │  ← 业务逻辑、数据模拟、AI调用
├─────────────────────────────────────┤
│   Data Layer (store/)               │  ← 数据库操作、SQL查询
├─────────────────────────────────────┤
│   Model Layer (models/)             │  ← 数据结构定义
└─────────────────────────────────────┘
         ↓                    ↓
    MySQL 数据库          DeepSeek AI
```

---

## 目录结构

```
backend/
├── cmd/server/
│   └── main.go                    # 程序入口，初始化所有组件
├── internal/
│   ├── api/                       # HTTP API层
│   │   ├── server.go              # 服务器定义、路由配置
│   │   ├── metrics_handler.go     # 指标相关的HTTP处理器
│   │   ├── insights_handler.go    # 洞察相关的HTTP处理器
│   │   └── utils.go               # 工具函数（CORS、JSON、错误处理）
│   ├── service/                   # 业务逻辑层
│   │   ├── metrics.go             # 指标服务
│   │   ├── insights.go            # 洞察服务
│   │   └── simulation.go          # 数据模拟器
│   ├── store/                     # 数据访问层
│   │   └── store.go               # 数据库操作
│   ├── models/                    # 数据模型
│   │   ├── metrics.go             # 指标数据结构
│   │   └── insight.go             # 洞察数据结构
│   └── ai/                        # AI集成层
│       └── deepseek.go            # DeepSeek API客户端
└── docs/
    └── ARCHITECTURE.md            # 本文档
```

---

## 数据流向

### 1. 启动流程 (main.go)

```
main()
  ├─ loadEnv()                     # 加载 .env 环境变量
  ├─ loadConfig()                  # 读取配置
  ├─ sql.Open()                    # 连接 MySQL 数据库
  ├─ ai.NewDeepSeekClient()        # 创建 AI 客户端
  ├─ store.New(db)                 # 创建数据访问层
  ├─ service.NewMetricsService()   # 创建指标服务
  ├─ service.NewInsightsService()  # 创建洞察服务
  ├─ api.NewServer()               # 创建 API 服务器
  ├─ httpServer.ListenAndServe()   # 启动 HTTP 服务器
  └─ StartSimulation()             # (可选) 启动数据模拟
```

### 2. HTTP 请求处理流程

以 `GET /api/metrics/latest` 为例：

```
HTTP Request
  ↓
[api/server.go] Routes() → 路由匹配
  ↓
[api/metrics_handler.go] handleLatestMetrics()
  ↓
[service/metrics.go] Latest()
  ↓
[store/store.go] LatestMetrics()
  ↓
MySQL 数据库查询
  ↓
返回 models.Metrics
  ↓
[api/utils.go] writeJSON() → 格式化为 JSON
  ↓
HTTP Response
```

### 3. AI 洞察生成流程

以 `POST /api/insights` 为例：

```
HTTP Request (metricKey: "revenue")
  ↓
[api/insights_handler.go] handleCreateInsight()
  ↓
[service/insights.go] Create()
  ├─ store.LatestMetrics()        # 获取最新指标
  ├─ store.Trend()                # 获取趋势数据
  ├─ buildDeepSeekPrompt()        # 构建 AI 提示词
  ├─ ai.Chat()                    # 调用 DeepSeek API
  ├─ normalizeInsight()           # 格式化 AI 响应
  └─ store.InsertInsight()        # 保存到数据库
  ↓
HTTP Response (新生成的洞察)
```

---

## 核心模块详解

### 1. 入口模块 (cmd/server/main.go)

**职责**：
- 加载环境变量和配置
- 初始化数据库连接
- 创建所有服务实例
- 启动 HTTP 服务器
- 处理优雅关闭

**关键配置**：
```go
type config struct {
    addr             string        // 服务器地址 (默认 :8080)
    dsn              string        // MySQL 连接字符串
    allowedOrigins   string        // CORS 允许的源
    enableSimulation bool          // 是否启用数据模拟
    metricsEvery     time.Duration // 指标生成间隔
    insightsEvery    time.Duration // 洞察生成间隔
    deepseekAPIKey   string        // DeepSeek API 密钥
    deepseekBaseURL  string        // DeepSeek API 地址
    deepseekModel    string        // 使用的模型名称
}
```

---

### 2. API 层 (internal/api/)

#### server.go
**职责**：定义服务器结构、配置路由

**核心结构**：
```go
type Server struct {
    metrics  *service.MetricsService   // 指标服务
    insights *service.InsightsService  // 洞察服务
}
```

**路由配置**：
```go
GET  /healthz                    # 健康检查
GET  /api/metrics/latest         # 获取最新指标
GET  /api/metrics/trend          # 获取趋势数据
GET  /api/insights/latest        # 获取最新洞察
POST /api/insights               # 生成新洞察
POST /api/metrics/simulate       # 模拟生成新指标
```

#### metrics_handler.go
**职责**：处理指标相关的 HTTP 请求

**处理器**：
- `handleLatestMetrics()`: 返回最新的指标快照
- `handleTrend()`: 返回指定窗口的趋势数据
- `handleSimulateMetrics()`: 手动触发指标模拟

#### insights_handler.go
**职责**：处理洞察相关的 HTTP 请求

**处理器**：
- `handleLatestInsights()`: 返回最新的洞察列表
- `handleCreateInsight()`: 根据指定指标生成新洞察

#### utils.go
**职责**：提供通用工具函数

**函数**：
- `corsMiddleware()`: CORS 中间件
- `parseQueryInt()`: 解析查询参数
- `writeJSON()`: 写入 JSON 响应
- `writeError()`: 写入错误响应

---

### 3. 服务层 (internal/service/)

#### metrics.go - 指标服务
**职责**：管理业务指标的获取、模拟和存储

**核心方法**：
```go
Latest(ctx)              # 获取最新指标（如果没有则初始化默认值）
Trend(ctx, window)       # 获取趋势数据（如果没有则生成种子数据）
Simulate(ctx)            # 模拟生成下一个指标
StartSimulation(ctx)     # 启动后台模拟循环
```

**依赖**：
- `store.Store`: 数据持久化
- `Simulation`: 数据模拟器

#### insights.go - 洞察服务
**职责**：使用 AI 生成业务洞察

**核心方法**：
```go
Latest(ctx, limit)           # 获取最新洞察列表
Create(ctx, metricKey)       # 根据指定指标生成洞察
GenerateAuto(ctx, metrics)   # 自动生成洞察
generateInsight()            # 内部方法：调用 AI 并保存
```

**AI 提示词构建**：
- 系统提示：定义 AI 角色为"企业战略分析师"
- 用户提示：包含当前指标、趋势数据、关注点
- 输出格式：严格 JSON（analysis + suggestions）

**依赖**：
- `store.Store`: 数据持久化
- `ai.AIChatBot`: AI 客户端接口

#### simulation.go - 数据模拟器
**职责**：生成模拟的指标数据

**算法**：
```go
NextMetrics(previous) {
    revenue   = clamp(previous.revenue + random(-0.35, 0.65) * 0.12, 3.9, 6.2)
    growth    = clamp(previous.growth + random(-0.45, 0.55) * 1.6, 10, 28)
    sentiment = clamp(previous.sentiment + random(-0.5, 0.5) * 2.4, 58, 90)
    backlog   = clamp(previous.backlog + random(-0.4, 0.6) * 6, 95, 180)
}
```

---

### 4. 数据层 (internal/store/)

#### store.go
**职责**：封装所有数据库操作

**核心方法**：
```go
LatestMetrics(ctx)              # 查询最新指标
InsertMetrics(ctx, metrics)     # 插入新指标
Trend(ctx, limit)               # 查询趋势数据（倒序后反转）
LatestInsights(ctx, limit)      # 查询最新洞察
InsertInsight(ctx, insight)     # 插入新洞察
```

**数据库表**：
- `metrics_snapshot`: 存储指标快照
- `insights`: 存储 AI 生成的洞察

---

### 5. 模型层 (internal/models/)

#### metrics.go
```go
type Metrics struct {
    Revenue   float64   // 营收 (单位: B)
    Growth    float64   // 增长率 (%)
    Sentiment float64   // 情绪指数 (%)
    Backlog   int       // 积压任务 (K)
    CreatedAt time.Time // 创建时间
}
```

#### insight.go
```go
type Insight struct {
    ID        int64     // 主键
    Title     string    // 标题
    Message   string    // 洞察内容
    Source    string    // 来源 (auto/metric)
    CreatedAt time.Time // 创建时间
}
```

---

### 6. AI 层 (internal/ai/)

#### deepseek.go
**职责**：封装 DeepSeek API 调用

**核心方法**：
```go
Chat(ctx, systemPrompt, userPrompt) string
```

**特性**：
- 自动重试（最多 3 次）
- 超时控制（20 秒）
- 日志记录
- 错误处理

**API 配置**：
```go
MaxTokens:   500      # 最大生成 token 数
Temperature: 0.4      # 温度参数（较低 = 更确定性）
Stream:      false    # 不使用流式响应
```

---

## API 接口说明

### 1. 获取最新指标
```http
GET /api/metrics/latest
```

**响应**：
```json
{
  "data": {
    "revenue": 4.82,
    "growth": 18.6,
    "sentiment": 72,
    "backlog": 128,
    "created_at": "2026-01-23T10:30:00Z"
  },
  "timestamp": "2026-01-23T10:30:05Z"
}
```

---

### 2. 获取趋势数据
```http
GET /api/metrics/trend?window=12
```

**参数**：
- `window`: 数据点数量（默认 12，最小 3）

**响应**：
```json
{
  "data": [
    {
      "timestamp": "2026-01-23T10:20:00Z",
      "revenue": 4.65
    },
    {
      "timestamp": "2026-01-23T10:25:00Z",
      "revenue": 4.73
    }
  ]
}
```

---

### 3. 获取最新洞察
```http
GET /api/insights/latest?limit=6
```

**参数**：
- `limit`: 返回数量（默认 6）

**响应**：
```json
{
  "data": [
    {
      "id": 1,
      "title": "AI 战略顾问",
      "message": "营收稳步增长，情绪指数保持高位...",
      "source": "auto",
      "created_at": "2026-01-23T10:30:00Z"
    }
  ]
}
```

---

### 4. 生成新洞察
```http
POST /api/insights
Content-Type: application/json

{
  "metricKey": "revenue"
}
```

**响应**：
```json
{
  "data": {
    "id": 2,
    "title": "AI 战略顾问",
    "message": "针对营收指标的分析...",
    "source": "metric",
    "created_at": "2026-01-23T10:35:00Z"
  }
}
```

---

### 5. 模拟生成指标
```http
POST /api/metrics/simulate
```

**响应**：
```json
{
  "data": {
    "revenue": 4.89,
    "growth": 19.2,
    "sentiment": 73,
    "backlog": 125,
    "created_at": "2026-01-23T10:40:00Z"
  }
}
```

---

## 关键设计模式

### 1. 依赖注入
所有服务通过构造函数注入依赖，便于测试和解耦：
```go
// main.go
store := store.New(db)
metricsService := service.NewMetricsService(store, simulator)
insightsService := service.NewInsightsService(store, aiClient)
apiServer := api.NewServer(metricsService, insightsService)
```

### 2. 接口抽象
AI 客户端使用接口定义，便于替换实现：
```go
type AIChatBot interface {
    Chat(ctx context.Context, systemPrompt, userPrompt string) (string, error)
}
```

### 3. 上下文传递
所有数据库和网络操作都接受 `context.Context`，支持超时和取消：
```go
func (s *Store) LatestMetrics(ctx context.Context) (models.Metrics, error)
```

### 4. 优雅关闭
使用信号监听和超时控制实现优雅关闭：
```go
ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
defer stop()
// ...
shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()
httpServer.Shutdown(shutdownCtx)
```

---

## 环境变量配置

创建 `.env` 文件：

```env
# 服务器配置
APP_PORT=8080
ALLOWED_ORIGINS=*

# 数据库配置
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASS=123456
DB_NAME=dashboard

# 模拟配置
ENABLE_SIMULATION=true
SIM_METRICS_EVERY=1s
SIM_INSIGHTS_EVERY=5s

# AI 配置
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

---

## 总结

本项目采用清晰的分层架构，各层职责明确：

- **API 层**：处理 HTTP 请求和响应
- **服务层**：实现业务逻辑和编排
- **数据层**：封装数据库操作
- **模型层**：定义数据结构
- **AI 层**：集成外部 AI 服务

这种设计使得代码易于理解、测试和维护。
