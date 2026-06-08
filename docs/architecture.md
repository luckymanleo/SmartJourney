# SmartJourney（智旅）架构文档

> 2026-06-08 | 全栈旅行规划平台 | 移动端 + PC Web 双版本

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 18 + TypeScript + Vite 6 + Tailwind CSS + Zustand + React Router |
| 后端 | FastAPI (Python 3.11) + SQLAlchemy 2.0 async + PostgreSQL 16 |
| 缓存 | Redis 7（懒加载代理模式） |
| AI | DeepSeek v4 (via OpenAI-compatible API) |
| MCP | ModelScope HTTP MCP (FliggyTravel 飞猪) — 7 工具，结果 Redis 缓存 |
| 天气 | 高德 AMAP API（30min Redis 缓存） |
| 城市 | eduosi/district (3434 行民政部数据，内存加载) |

## 项目结构

```
SmartJourney/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口，CORS，lifespan
│   │   ├── config.py                # pydantic-settings (绝对路径 .env)
│   │   ├── config_loader.py         # config.json 加载器
│   │   ├── database.py              # SQLAlchemy async engine (pool_size/max_overflow)
│   │   ├── redis_client.py          # Redis 懒加载代理 + MemoryRedis 降级
│   │   ├── logging_config.py        # 日志配置（按日切分 + 10MB）
│   │   ├── api/
│   │   │   ├── auth.py              # 短信验证码登录/注册
│   │   │   ├── search.py            # 6 类搜索(flights/trains/hotels/pois/foods/transport)
│   │   │   ├── plan.py              # AI 规划 SSE + 取消支持
│   │   │   ├── trips.py             # 行程 CRUD
│   │   │   ├── info.py              # 天气/城市/热门目的地
│   │   │   ├── user.py              # 用户偏好
│   │   │   ├── phase4.py            # 辅助功能(stub)
│   │   │   └── phase5.py            # 管理统计(stub)
│   │   ├── services/
│   │   │   ├── agent_service.py     # AI 核心 (跨城/同城自动识别 + MCP缓存 + LLM)
│   │   │   ├── mcp_manager.py       # MCP 会话 + Redis缓存 + Semaphore(6)
│   │   │   ├── remote_mcp.py        # ModelScope HTTP 客户端
│   │   │   ├── markdown_parser.py   # MCP Markdown → 结构化 (6工具)
│   │   │   ├── trip_service.py      # 行程 CRUD
│   │   │   ├── auth_service.py      # 短信验证码
│   │   │   ├── weather_service.py   # 高德天气
│   │   │   ├── location_service.py  # 省市区三级联动
│   │   │   ├── route_strategies.py  # 路线策略
│   │   │   ├── trip_expiry.py       # 行程过期清理
│   │   │   └── [stubs]              # wallet/collaboration/sharing/alert 等骨架(未接前端)
│   │   ├── models/                  # 11 张表 (6 张在用, 5 张预留)
│   │   └── tests/                   # Pytest
│   ├── config.json                  # 外部化配置
│   ├── logs/                        # 按日切分日志
│   └── .env.example                 # 环境变量模板
│
├── frontend/
│   ├── index.html / pc.html         # 双入口
│   ├── vite.config.ts               # 多页面 + vendor 代码分割
│   ├── src/
│   │   ├── pages/                   # 移动端: Home, Search, Plan, MyTrips, TripDetail, Settings
│   │   ├── pc/                      # PC 端: 同上 + Layout + CityCascader
│   │   ├── components/              # 共享: SearchCards, TripTimeline, BudgetPanel, CityCascader
│   │   ├── stores/                  # auth, search, plan (AbortController), trip
│   │   ├── api/                     # axios 90s + SSE streamPlan (AbortController)
│   │   └── utils/parseQuery.ts      # NL 解析 (跨城/同城 + 人数推断)
│   └── dist/                        # 构建输出 (vendor chunk 分离)
│
├── docs/                            # 技术文档
├── docker-compose.yml               # PG + Redis + Nginx (性能参数)
├── nginx.conf                       # gzip + 缓存 + SSE
└── config.json                      # 外部化配置
```

## 核心数据流

### AI 规划 (v3 架构)

```
PlanPage → POST /api/v1/plan/generate (SSE)
  → agent_service.generate_plan()
    → _build_all_queries()  — 跨城: 8交通+3城市 | 同城: 1交通+3城市
    → asyncio.gather (11 queries, Semaphore 6)
      → mcp_manager.call_tool()
        → Redis GET (缓存命中 → 0s)
        → Redis MISS → RemoteMCPClient → FliggyTravel MCP
        → Redis SET (按类型 TTL: 5-60min)
    → _compact_tool_result()  — 保留 booking_url
    → LLM (DeepSeek v4, max_tokens=8192)
    → _save_trip() async fire-and-forget
  → SSE: step → tool_call → tool_result → trip_data → done
```

### 规划进度条（4 阶段）

```
分析(蓝脉冲) → 搜索(蓝脉冲) → 生成(蓝脉冲) → 完成(绿)

toolPhase: idle → calling → done → tripData
```

### 取消流程

```
用户点击取消 → AbortController.abort()
  → fetch 断开 → asyncio 取消生成器 task
  → MCP/LLM 自然终止
```

## 关键设计决策

1. **MCP HTTP only**：不使用 stdio（破坏 event loop）
2. **MCP 结果 Redis 缓存**：按类型 TTL 分档 (flight 5min / poi 60min)
3. **跨城/同城自动识别**：origin≠destination 时才搜机票/火车，同城搜市内交通
4. **Redis 懒加载代理**：首次使用时连接，失败降级 MemoryRedis
5. **frontend AbortController**：取消规划即断开连接，不依赖后端轮询
6. **Vite vendor 代码分割**：react/router/zustand/axios 独立 chunk
7. **PC 版零侵入**：Vite 多页面 + 共享 Store/API/组件
8. **booking_url 全链路保留**：compact → LLM → save 不丢失
9. **跨城交通规则**：SYSTEM_PROMPT 强制 Day1 首项为 flight/train
10. **日志按日切分**：smartjourney.log + error.log，单文件 10MB

## 数据库

### 在用表 (6)
User, UserPreference, Trip, TripDay, TripItem, Budget

### 预留表 (5，后端骨架未接前端)
SystemConfig, TripMember, TripExpense, Wallet, Transaction

## 外部依赖

| 服务 | 用途 | 备注 |
|------|------|------|
| PostgreSQL 16 | 主数据库 | Docker / 宿主机 :5432 |
| Redis 7 | 缓存 + 验证码 + MCP结果 | lazy proxy 模式 |
| ModelScope MCP | 机票/火车/酒店/景点/美食/交通 | 免费端点，周期性不稳定 |
| DeepSeek API | LLM 行程规划 | OpenAI 兼容 |
| 高德 API | 天气查询 | 30min 缓存 |

## 启动

```bash
docker compose up -d postgres redis
cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio
cd frontend && npm run dev
# 移动端: http://localhost:5173/   PC端: http://localhost:5173/pc.html
```

## 性能配置

| 优化项 | 说明 |
|--------|------|
| nginx gzip + 缓存 | 前端首屏快 60-80% |
| PG 连接池 | pool_size=10, max_overflow=20 |
| PG 服务端 | shared_buffers=256MB, work_mem=16MB |
| MCP Semaphore 6 | 11 查询分 2 批 |
| MCP Redis 缓存 | 按类型 TTL 5-60min |
| Vite vendor 分割 | react/router/zustand/axios 独立 chunk |
| 日志 | 按日切分 + error 单独文件 |

详见 [性能优化方案](performance-optimization.md)。
