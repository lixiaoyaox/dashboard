# FastAPI 后端全流程说明

本文档说明 Python 后端从启动到关闭的完整协作流程，覆盖配置加载、数据库访问、服务层、API 路由、AI 调用与后台模拟任务。

## 1) 启动入口
入口文件：`backend/app/main.py`

启动命令示例：
- `uvicorn app.main:app --host 0.0.0.0 --port 8080`

执行流程：
1. 读取环境配置（`load_settings()`）。
2. 初始化数据库、Store、DeepSeek 客户端。
3. 组装服务层（Metrics/Insights/Chat）。
4. 构建 FastAPI 应用与路由。
5. 启动事件中启动后台模拟任务（可选）。

## 2) 配置加载
文件：`backend/app/config.py`

- `_load_env()`：从当前目录向上查找 `.env` 并加载。
- `load_settings()`：读取环境变量并解析为 `Settings`。
- 关键配置：
  - DB：`DB_HOST/DB_PORT/DB_USER/DB_PASS/DB_NAME`
  - API：`APP_PORT/ALLOWED_ORIGINS`
  - DeepSeek：`DEEPSEEK_API_KEY/DEEPSEEK_BASE_URL/DEEPSEEK_MODEL`
  - Simulation：`ENABLE_SIMULATION/SIM_METRICS_EVERY/SIM_INSIGHTS_EVERY`

如果 `DEEPSEEK_API_KEY` 为空，会抛异常阻止启动。

## 3) 数据库连接
文件：`backend/app/db.py`

- `Database.connect()`：返回 MySQL 连接上下文（PyMySQL）。
- 采用 `autocommit=True`，每次操作自动提交。

## 4) 数据模型
文件：`backend/app/models.py`

- `Metrics`：营收/增长/情绪/积压 + 时间戳。
- `Insight`：洞察记录（id/title/message/source/created_at）。
- `ChatAnswer`：聊天答案 + 来源标签。

## 5) 数据访问层 Store
文件：`backend/app/store.py`

职责：
- 读写 `metrics_snapshot` / `insights` 两张表。
- 提供以下方法：
  - `latest_metrics()` / `insert_metrics()` / `insert_metrics_at()`
  - `trend(limit)`
  - `latest_insights(limit)` / `insert_insight()`

## 6) 业务服务层

### 6.1 指标服务
文件：`backend/app/services/metrics.py`

- `latest()`：获取最新指标；无数据则写入默认值。
- `trend(window)`：获取趋势；无数据则写入默认趋势。
- `simulate()`：基于最新数据生成下一条并写入。

### 6.2 洞察服务
文件：`backend/app/services/insights.py`

- `latest(limit)`：读取最近洞察；为空时自动生成一条。
- `create(metric_key)`：按指定指标生成洞察。
- `generate_auto(metrics)`：用于后台自动生成。

洞察生成依赖 DeepSeek（见第 7 节），并会清洗输出确保可显示。

### 6.3 聊天服务
文件：`backend/app/services/chat.py`

- `ask(message)`：拼装上下文（最新指标 + 趋势 + 最新洞察）并调用 DeepSeek，
  输出问答结果和来源标签。

### 6.4 模拟器
文件：`backend/app/services/simulation.py`

- `Simulation.next_metrics(previous)`：根据随机扰动生成下一条指标。

## 7) AI 客户端（DeepSeek）
文件：`backend/app/ai/deepseek.py`

- `DeepSeekClient.chat(system_prompt, user_prompt)`：
  - POST 到 `{base_url}/chat/completions`
  - 最多 3 次重试
  - 解析 `choices[0].message.content`

## 8) API 路由
文件：`backend/app/api/routes.py`

路由列表：
- `GET /healthz`
- `GET /api/metrics/latest`
- `GET /api/metrics/trend?window=12`
- `POST /api/metrics/simulate`
- `GET /api/insights/latest?limit=6`
- `POST /api/insights`
- `POST /api/chat`

## 9) 背景模拟任务
文件：`backend/app/main.py`

- `SimulationRunner` 会在启动时（`@app.on_event("startup")`）根据配置开启后台线程：
  - `SIM_METRICS_EVERY`：周期写入新指标
  - `SIM_INSIGHTS_EVERY`：周期生成洞察

关闭时（`@app.on_event("shutdown")`）停止线程。

## 10) 运行期协作流程（简化时序）

1. 启动 uvicorn → import `app.main`。
2. 读取 `.env` → 生成 Settings。
3. 初始化 Database / Store / DeepSeek / Services。
4. 注册路由与中间件。
5. 启动事件触发 SimulationRunner（若启用）。
6. 前端请求 API → 路由 → 服务层 → Store → DB。
7. 若需 AI：服务层调用 DeepSeek 客户端 → 返回结果 → 写入 DB。
8. 关闭 uvicorn → 触发 shutdown → 停止 SimulationRunner。

## 11) 关键依赖文件清单
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/db.py`
- `backend/app/store.py`
- `backend/app/ai/deepseek.py`
- `backend/app/services/*.py`
- `backend/app/api/routes.py`
- `backend/app/api/schemas.py`

