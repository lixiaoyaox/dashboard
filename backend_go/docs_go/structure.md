项目结构说明（后端）
====================

目的
----
这份说明用于清晰表达后端结构：
- 入口在哪里、如何启动
- 数据如何流动
- 核心模块是什么（根据目录判断）
- 一个简易的结构/流程示意图

入口与启动
----------
- 入口文件：cmd/server/main.go
- 启动流程（高层概览）：
  1) 从环境变量读取配置
  2) 建立 MySQL 连接
  3) 创建 Store（数据访问层）
  4) 创建 API Server 并注册路由
  5) 启动 HTTP 服务，并可选开启模拟数据的后台任务

数据流动（请求路径）
--------------------
典型读取请求（最新指标）：
用户请求 -> API Server -> Handler -> Store -> DB

典型写入请求（创建洞察）：
用户请求 -> API Server -> Handler -> Store -> DB

核心模块（按目录）
-----------------
- cmd/server：程序入口与启动组装
- internal/api：HTTP 路由与处理器
- internal/store：数据库访问层（SQL 读写）
- db/migrations：数据库结构与索引定义

简易流程图
----------
用户请求
  |
  v
API Server (internal/api)
  |
  v
Store (internal/store)
  |
  v
MySQL (db/migrations 中的表结构)

简易结构脑图
------------
backend/
|- cmd/
|  `- server/
|     `- main.go            （入口 + 配置 + HTTP 服务）
|- internal/
|  |- api/
|  |  `- server.go          （路由 + 处理器）
|  `- store/
|     `- store.go           （数据访问）
`- db/
   `- migrations/
      |- 0001_init.up.sql   （建表）
      `- 0001_init.down.sql （回滚）
