# Go + MySQL 后端方案（初稿）

## 目标
为仪表盘提供可扩展的后端能力：模拟/真实数据接口、AI洞察接口、用户与权限、审计与监控；与现有 Next.js 前端对接。

## 技术栈建议
- 语言与框架：Go 1.22 + Gin 或 Chi（轻量、成熟）
- 数据库：MySQL 8.x
- ORM/SQL：sqlc（强类型 SQL）或 GORM（快速开发）
- 配置：Viper（或 envconfig）
- 迁移：golang-migrate
- 日志：zap 或 slog
- 监控：Prometheus + Grafana（可选）

## 架构概览
- 前端：Next.js 客户端仅通过 HTTP/JSON 调用后端 API
- 后端：RESTful API（可替换为 GraphQL）
- 数据：MySQL 为主，未来可加 Redis 缓存

## 目录结构建议
```
backend/
  cmd/server/main.go
  internal/
    api/        # HTTP handlers
    service/    # 业务逻辑
    repo/       # 数据访问
    model/      # 结构体/DTO
    config/
    middleware/
  db/migrations/
  sql/          # sqlc 查询文件
```

## 核心数据模型（草案）
- metrics_snapshot
  - id, created_at
  - revenue, growth, sentiment, backlog
- insights
  - id, created_at
  - title, message, source (auto|metric)
- events (可选)
  - id, created_at, type, payload

## API 设计（草案）
- GET /api/metrics/latest
  - 返回最新指标 + 时间戳
- GET /api/metrics/trend?window=12
  - 返回折线趋势数据
- GET /api/insights/latest?limit=6
  - 返回最新洞察
- POST /api/insights
  - 前端点击 KPI 生成洞察（后端生成/模拟）
- POST /api/metrics/simulate
  - 触发模拟数据更新（可定时任务替代）

## 数据生成策略（模拟）
- 后端定时任务（每秒）写 metrics_snapshot
- 每 5 秒生成一条 insight（或根据 KPI 点击生成）
- 前端只拉取最新数据，不做随机数，避免 hydration mismatch

## 权限与安全（可选）
- JWT + RBAC（admin/viewer）
- 限流：基于 IP 或 Token
- CORS：仅允许前端域名

## 部署建议
- Docker Compose：
  - app (Go API)
  - mysql
- 环境变量：
  - DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
  - APP_PORT

## 下一步建议
1. 先做 API + mock 数据（1-2 天）
2. 接入 MySQL + migrations（1 天）
3. 把前端改为请求 API（半天）
4. 加权限/监控（可选）
