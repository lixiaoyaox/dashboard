# Go + MySQL Backend

## Local dev
1. 启动 MySQL（或使用 docker-compose）并创建数据库 `dashboard`。
2. 运行迁移：
   - 推荐使用 golang-migrate 或手动执行 `db/migrations/0001_init.up.sql`。
3. 设置环境变量（参考 `.env.example`）。
4. 启动：
   - `go run ./cmd/server`

## API
- GET /api/metrics/latest
- GET /api/metrics/trend?window=12
- GET /api/insights/latest?limit=6
- POST /api/insights
- POST /api/metrics/simulate
