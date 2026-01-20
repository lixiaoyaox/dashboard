# CEO 远见仪表盘（MyDashboard）

## 项目简介
面向高层演示的实时业务仪表盘，主打黑金高端视觉与动态数据体验。前端以 Next.js + Tailwind 实现大屏布局与动效，后端以 Go + MySQL 提供模拟数据与洞察生成接口。

## 功能概览
- 全球业务概览与 KPI 实时指标卡
- 全球销售热力图 + 营收趋势曲线
- 社交情绪与运营就绪度面板
- AI 战略顾问洞察流（自动生成）
- KPI 点击即时生成洞察
- 后端模拟数据定时写入（可替换为真实数据源）

## 技术栈
**前端**
- Next.js (App Router)
- Tailwind CSS

**后端**
- Go 1.22
- MySQL 8.x
- Chi router

## 目录结构
```
MyDashboard/
  src/                  # 前端
  backend/              # Go API
    cmd/server
    internal/api
    internal/store
    db/migrations
  docker-compose.yml
```

## 运行方式

### 方案一：Docker（推荐）
1) 启动服务
```
docker compose up -d
```

2) 初始化数据库表（执行一次即可）
```
docker exec -i mydashboard-mysql mysql -uroot -p123456 dashboard < D:\Projects\MyDashboard\backend\db\migrations\0001_init.up.sql
```

3) 前端启动
- 复制 `D:\Projects\MyDashboard\.env.example` 为 `.env.local`
- 运行：
```
npm run dev
```

### 方案二：本地运行
1) 创建数据库并执行迁移：
- 执行 `D:\Projects\MyDashboard\backend\db\migrations\0001_init.up.sql`

2) 启动后端：
```
cd D:\Projects\MyDashboard\backend
go run ./cmd/server
```

3) 启动前端：
- 复制 `D:\Projects\MyDashboard\.env.example` 为 `.env.local`
- 运行：
```
cd D:\Projects\MyDashboard
npm run dev
```

## 环境变量
前端（`.env.local`）
```
NEXT_PUBLIC_API_BASE=http://localhost:8080
```

后端（参考 `backend/.env.example`）
```
APP_PORT=8080
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASS=123456
DB_NAME=dashboard
ENABLE_SIMULATION=true
SIM_METRICS_EVERY=1s
SIM_INSIGHTS_EVERY=5s
ALLOWED_ORIGINS=*
```

## API 列表
- GET `/api/metrics/latest`
- GET `/api/metrics/trend?window=12`
- GET `/api/insights/latest?limit=6`
- POST `/api/insights`
- POST `/api/metrics/simulate`

## 备注
- 当前为模拟数据，后续可接入真实业务数据源与权限控制。
- 如需添加自动迁移或更复杂的策略模型，可再扩展。
