# SmartJourney（智旅）

全栈旅行规划平台 — AI 驱动的智能行程生成，支持移动端与 PC Web 双版本。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 18 + TypeScript + Vite + TailwindCSS + Zustand + React Router |
| 后端 | FastAPI (Python 3.11) + SQLAlchemy 2.0 async + PostgreSQL + Redis |
| AI | DeepSeek / OpenAI-compatible LLM + MCP 网关 |
| 短信 | 阿里云 Dypnsapi（号码认证），支持 mock 模式开发 |
| 数据 | FliggyTravel MCP（飞猪）、高德天气 + 地图 + 地理编码、eduosi/district |

## 核心功能

- **手机号验证码登录/注册**：短信验证码 + mock 模式（开发用固定验证码），支持 PC/手机独立限流
- **多类型搜索**：机票、火车票、酒店、景点、美食、市内交通
- **AI 智能规划**：自然语言输入自动解析出发地/目的地/天数/人数/预算，LLM + MCP 生成完整行程，SSE 流式返回
  - Day 1 出发前自动搜索出发地景点/美食（若出发时间在下午/晚上）
  - 行程项自动按 `start_time` 排序保存
- **行程地图导航**：高德地图集成，行程 POI 可视化、按天过滤、点击联动定位、"开始导航"唤起高德 App
  - PC 版：左侧行程列表 + 右侧互动地图，点击联动
  - 移动版：天选择器 + 地图 + 行程列表，支持点击聚焦
  - 交通类站点/机场自动地理编码
- **双端支持**：移动端 + PC Web（侧边栏布局），Vite 多页面构建
- **行程管理**：CRUD + 时间线视图 + 预算概览 + 天气集成
- **偏好设置**：天气参考开关、路线策略（智能平衡/经济实惠/舒适优先/最快到达）

## 项目结构

```
SmartJourney/
├── frontend/              # React 前端（mobile + PC）
│   ├── src/pages/         # 移动端页面
│   ├── src/pc/            # PC Web 页面
│   ├── src/stores/        # Zustand 状态管理（共享）
│   └── src/components/    # 共享 UI 组件（TripTimeline, TripMap, PoiDetailCard 等）
├── backend/               # FastAPI 后端
│   ├── app/
│   │   ├── api/           # 路由模块（含 /map 地图路由）
│   │   ├── services/      # 服务模块（agent, map, mcp, weather 等）
│   │   └── models/        # 数据库表（11 张表）
│   ├── config.json        # 外部化配置（MCP URL、策略等）
│   └── .env.example       # 环境变量模板（不包含真实凭据）
├── docs/                  # 技术文档
├── docker-compose.yml     # PostgreSQL + Redis + Nginx
└── nginx.conf             # Nginx 反向代理 + 静态文件 + SSE
```

## 快速启动

```bash
# 数据库
docker compose up -d postgres redis

# 后端
cd backend
cp .env.example .env  # 编辑 .env 填入实际配置
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio

# 前端
cd frontend && npm install && npm run dev
# 移动端: http://localhost:5173/
# PC 端:  http://localhost:5173/pc.html
```

## 环境变量

参考 `backend/.env.example`，关键配置项：

| 变量 | 说明 |
|------|------|
| DATABASE_URL | PostgreSQL 连接串 |
| REDIS_URL | Redis 连接串 |
| SECRET_KEY | JWT 签名密钥（≥32 字符） |
| LLM_API_KEY | LLM API 密钥 |
| LLM_BASE_URL | LLM API 地址 |
| LLM_MODEL | LLM 模型名称 |
| GAODE_API_KEY | 高德地图 API Key（天气 + 地图 + 地理编码共用） |
| SMS_PROVIDER | 短信服务：`mock`（开发）/ `aliyun`（生产） |
| DB_POOL_SIZE | 连接池大小（默认 10） |
| DB_MAX_OVERFLOW | 最大溢出连接（默认 20） |

> `.env.example` 和所有文档中的凭据均为占位符，不含真实密钥。

## 性能优化（2026-06）

| 优化项 | 说明 | 效果 |
|--------|------|------|
| nginx gzip + 缓存 | JS/CSS 压缩 + 分层缓存策略 | 前端首屏快 60-80% |
| PostgreSQL 连接池 | pool_size=10, max_overflow=20 | 并发吞吐 2-3x |
| PostgreSQL 服务端 | shared_buffers=256MB, work_mem=16MB | 查询快 20-30% |
| MCP 并发优化 | Semaphore 3→6 | 搜索阶段快 ~50% |
| MCP Redis 缓存 | 按类型 TTL 分档 (5-60min) | 二次规划快 80% |
| Redis 持久化 | AOF + maxmemory 256MB | 重启不丢缓存 |
| Vite 代码分割 | vendor chunk 按框架/工具分离 | 首屏 JS 减 60%+ |
| 行程时间排序 | 保存前按 start_time 排序 | 时间线不乱序 |
| 出发地搜索 | 跨城时自动搜 origin 景点/美食 | Day 1 出发前有活动 |

详见 [性能优化方案](docs/performance-optimization.md)。

## 地图功能

- **数据源**：高德 Web 服务 API（地理编码、路径规划、POI 搜索、距离测量）
- **前端**：高德 JS API 2.0（动态 CDN 加载）
- **缓存**：Redis 分层缓存（坐标 24h / POI 30min / 路线 5min）
- **存储**：TripItem 自带 `lat`/`lng` 字段，缺失时自动 geocode 回写

详见 [地图功能规划](docs/plans/map-feature-plan.md) · [交互设计](docs/plans/trip-map-interactive.md)。

## 文档

- [架构文档](docs/architecture.md)
- [API 接口文档](docs/api.md)
- [需求文档](docs/requirements.md)
- [路线图](docs/roadmap.md)
- [部署指南](docs/deployment.md)
- [性能优化方案](docs/performance-optimization.md)
- [Nginx 架构分析](docs/nginx-architecture-analysis.md)
- [地图功能规划](docs/plans/map-feature-plan.md)
- [地图交互设计](docs/plans/trip-map-interactive.md)
- [行程详情页排版重构](docs/plans/pc-trip-detail-redesign.md)
