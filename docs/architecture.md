# SmartJourney（智旅）架构文档

> 2026-06-08 | 更新: 2026-06-12 | 全栈旅行规划平台 | 移动端 + PC Web 双版本

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
│   │   │   ├── auth.py              # 短信验证码登录/注册 + 用户信息
│   │   │   ├── search.py            # 6 类搜索(flights/trains/hotels/pois/foods/transport)
│   │   │   ├── plan.py              # AI 规划 SSE + 行程优化
│   │   │   ├── trips.py             # 行程 CRUD + 行程项 + 预算
│   │   │   ├── info.py              # 天气/城市/热门目的地/省市区联动
│   │   │   ├── user.py              # 用户偏好
│   │   │   └── map_routes.py        # 地图（地理编码/POI/路径/行程聚合）
│   │   ├── services/
│   │   │   ├── agent_service.py     # AI 核心 (跨城/同城自动识别 + MCP缓存 + LLM)
│   │   │   ├── mcp_manager.py       # MCP 会话 + Redis缓存 + Semaphore(6)
│   │   │   ├── mcp_gateway.py       # MCP 网关连接器
│   │   │   ├── remote_mcp.py        # ModelScope HTTP 客户端
│   │   │   ├── markdown_parser.py   # MCP Markdown → 结构化 (6工具)
│   │   │   ├── trip_service.py      # 行程 CRUD + 预算 + 偏好
│   │   │   ├── auth_service.py      # 短信验证码 + Token
│   │   │   ├── sms_service.py       # 阿里云/模拟短信发送
│   │   │   ├── weather_service.py   # 高德天气
│   │   │   ├── map_service.py       # 高德地图（地理编码/POI/路径/距离）
│   │   │   ├── location_service.py  # 省市区三级联动
│   │   │   ├── route_strategies.py  # 路线策略
│   │   │   └── trip_expiry.py       # 行程过期清理
│   │   ├── models/                  # 6 张表（全部在用）
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
│   │   ├── components/              # 共享: TripTimeline, TripMap, PoiDetailCard, BudgetPanel, LiveMapPreview, SearchCards, CityCascader, LlmStreamBox, TripCard
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
11. **预算对比显示**：BudgetPanel 支持原预算 vs 预计对比，自动计算节省/超支
12. **POI 照片预取**：行程生成时异步从高德获取照片存 DB，前端直读避免实时搜索错配
13. **地图行程聚合**：TripMap 统一加载全天 POI 数据，切换天时仅替换覆盖物不重建地图

## 数据库

### 表（6 张，全部在用）

| 表 | 说明 |
|------|------|
| users | 用户（手机号登录，昵称/头像） |
| user_preferences | 用户偏好（键值对，category+key 分组） |
| trips | 行程（出发地/目的地/日期/人数/预算/summary/tips） |
| trip_days | 每日行程（day_number, date, weather） |
| trip_items | 行程项（10 种类型：flight/train/hotel/poi/food/transport/bus/car_rental/ferry/other） |
| budgets | 分类预算（transport/lodging/food/tickets/other） |

## 外部依赖

| 服务 | 用途 | 备注 |
|------|------|------|
| PostgreSQL 16 | 主数据库 | Docker / 宿主机 :5432 |
| Redis 7 | 缓存 + 验证码 + MCP结果 | lazy proxy 模式，MemoryRedis 降级 |
| ModelScope MCP | 机票/火车/酒店/景点/美食/交通 | FliggyTravel（飞猪），免费端点 |
| DeepSeek API | LLM 行程规划 | OpenAI 兼容 |
| 高德 API | 天气 + 地图 + 地理编码 + POI | JS API 2.0 + Web 服务 API |
| 阿里云 Dypnsapi | 短信验证码 | 支持 mock 模式开发 |

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

## 部署架构（nginx）

```
Internet → Nginx :80 (反向代理+静态) → ├─ Frontend (静态文件)
                                        ├─ Backend :8000 (API)
                                        ├─ PostgreSQL :5432
                                        └─ Redis :6379
```

nginx 承担三项职责：静态文件服务（分层缓存）、API 反向代理、SSE 长连接代理。
配置规范，支持 gzip 压缩（前端体积减少 60-80%）和 SSE 流式推送（`proxy_buffering off`）。

详见 [Nginx 架构分析](nginx-architecture-analysis.md)。
