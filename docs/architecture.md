# SmartJourney（智旅）架构文档

> 2026-06-05 | 全栈旅行规划平台 | 移动端 + PC Web 双版本 | 327 节点知识图谱

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS + Zustand + React Router |
| 后端 | FastAPI (Python 3.11) + SQLAlchemy 2.0 async + PostgreSQL |
| 数据库 | PostgreSQL 16 + asyncpg |
| 缓存 | Redis 7 |
| AI | DeepSeek v4 (via OpenAI-compatible API) |
| 外部数据 | ModelScope MCP (FliggyTravel 飞猪旅行, Meituan 美团) |
| 天气 | 高德 AMAP API |
| 城市数据 | eduosi/district (3434行民政部数据，含拼音) |
| LLM | DeepSeek (via OpenAI-compatible API) |

## 项目结构

```
SmartJourney/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口，CORS，lifespan
│   │   ├── config_loader.py         # config.json 加载器
│   │   ├── database.py              # SQLAlchemy async engine + session
│   │   ├── redis_client.py          # Redis 缓存
│   │   ├── api/
│   │   │   ├── auth.py              # 登录/注册/Token (手机验证码)
│   │   │   ├── search.py            # 6 类搜索端点 (flights/trains/hotels/pois/foods/transport)
│   │   │   ├── plan.py              # AI 行程规划 (SSE 流式) + 优化
│   │   │   ├── trips.py             # 行程 CRUD
│   │   │   ├── info.py              # 天气/城市/热门目的地/省市区联动
│   │   │   ├── user.py              # 用户偏好设置
│   │   │   ├── phase2.py            # Phase 2 分布式搜索
│   │   │   ├── phase3.py            # Phase 3 搜索结果解析
│   │   │   ├── phase4.py            # Phase 4 钱包/积分
│   │   │   └── phase5.py            # Phase 5 社交/协作
│   │   ├── services/
│   │   │   ├── agent_service.py     # AI Agent 核心 (LLM + MCP + SSE)
│   │   │   ├── markdown_parser.py   # MCP Markdown → 结构化 (6工具12变体)
│   │   │   ├── mcp_gateway.py       # MCP 多服务器网关 + 路由
│   │   │   ├── mcp_manager.py       # MCP 会话管理 + 连接池
│   │   │   ├── remote_mcp.py        # ModelScope HTTP MCP 客户端
│   │   │   ├── trip_service.py      # 行程 CRUD + 天数管理
│   │   │   ├── auth_service.py      # 验证码发送/验证
│   │   │   ├── location_service.py  # 省市区三级联动 (3434行)
│   │   │   ├── weather_service.py   # 高德天气 API
│   │   │   ├── route_strategies.py  # 路线策略 (经济/舒适/快速)
│   │   │   ├── trip_expiry.py       # 行程过期自动清理
│   │   │   ├── accessibility_service.py  # 无障碍/辅助功能
│   │   │   ├── alert_service.py     # 价格/库存预警
│   │   │   ├── collaboration_service.py  # 多人协作编辑
│   │   │   ├── disruption_service.py     # 行程中断处理
│   │   │   ├── expense_service.py   # 费用分摊/结算
│   │   │   ├── multimodal_service.py     # 多模态 (图片/语音)
│   │   │   ├── preference_learning.py    # 用户偏好学习
│   │   │   ├── sharing_service.py   # 行程分享
│   │   │   ├── ticket_service.py    # 票务验证
│   │   │   ├── wallet_service.py    # 钱包/积分管理
│   │   │   └── __init__.py
│   │   ├── models/                  # SQLAlchemy 模型 (11张表)
│   │   │   └── __init__.py          # User, UserPreference, Trip, TripDay, TripItem,
│   │   │                            # Budget, SystemConfig, TripMember, TripExpense,
│   │   │                            # Wallet, Transaction
│   ├── config.json                  # 外部化配置
│   └── tests/                       # Pytest (25+ 用例)
│
├── frontend/
│   ├── index.html                   # 移动端入口
│   ├── pc.html                      # PC Web 入口 (2026-06-05 新增)
│   ├── vite.config.ts               # Vite 多页面配置 (main + pc)
│   ├── src/
│   │   ├── main.tsx                 # 移动端 React 挂载
│   │   ├── main-pc.tsx              # PC 端 React 挂载 (HashRouter)
│   │   ├── App.tsx                  # 移动端路由 + Auth 恢复
│   │   ├── AppPC.tsx                # PC 端路由
│   │   ├── index.css                # Tailwind + 全局样式
│   │   ├── api/
│   │   │   ├── client.ts            # axios 实例 (90s 超时)
│   │   │   └── index.ts             # API 函数封装
│   │   ├── pages/                   # 移动端页面（未改动）
│   │   │   ├── HomePage.tsx         # 首页 (热门目的地)
│   │   │   ├── SearchPage.tsx       # 搜索页 (6类搜索 + CityCascader)
│   │   │   ├── PlanPage.tsx         # AI 规划页 (SSE 进度条 + 多路线)
│   │   │   ├── MyTripsPage.tsx      # 我的行程
│   │   │   ├── TripDetailPage.tsx   # 行程详情
│   │   │   └── SettingsPage.tsx     # 设置 (偏好)
│   │   ├── pc/                      # PC 版页面（共享 stores/api/components）
│   │   │   ├── LayoutPC.tsx         # 侧边栏布局 (clamp 自适应宽度)
│   │   │   ├── HomePagePC.tsx       # 首页 Dashboard
│   │   │   ├── SearchPagePC.tsx     # 搜索页 (水平栏 + 网格)
│   │   │   ├── PlanPagePC.tsx       # AI 规划 (左中右三栏)
│   │   │   ├── MyTripsPagePC.tsx    # 行程卡片网格
│   │   │   ├── TripDetailPagePC.tsx # 行程详情 (双栏)
│   │   │   ├── SettingsPagePC.tsx   # 设置 (宽表单)
│   │   │   └── CityCascaderPC.tsx   # 城市选择器 (下拉面板)
│   │   ├── components/              # 移动端 + PC 共享组件
│   │   │   ├── Layout.tsx           # 底部导航 + max-w-md 容器
│   │   │   ├── SearchCards.tsx      # 6 类搜索结果卡片 (共享)
│   │   │   ├── CityCascader.tsx     # 省市区三级联动 (移动端)
│   │   │   ├── TripCard.tsx         # 行程卡片 (移动端)
│   │   │   ├── TripTimeline.tsx     # 行程时间线 (共享)
│   │   │   ├── BudgetPanel.tsx      # 预算面板 (共享)
│   │   │   └── SearchBar.tsx        # 搜索栏
│   │   ├── stores/                  # Zustand 状态管理 (移动端+PC共享)
│   │   │   ├── authStore.ts         # 认证状态
│   │   │   ├── searchStore.ts       # 搜索状态 + 历史 (localStorage)
│   │   │   ├── planStore.ts         # 规划进度 (SSE 事件, 含分析完成提示)
│   │   │   └── tripStore.ts         # 行程列表 (含 origin 字段)
│   │   └── utils/
│   │       └── parseQuery.ts        # 自然语言查询解析 (共享)
│   └── dist/                        # 构建输出 (index.html + pc.html)
│
├── docs/
│   ├── architecture.md              # 本文档
│   ├── plans/pc-web-design.md       # PC Web 版设计方案
│   ├── deployment.md                # 部署文档
│   ├── api.md                       # API 接口文档
│   ├── requirements.md              # 需求文档
│   ├── roadmap.md                   # 路线图
│   ├── tool-integration.md          # 工具集成文档
│   ├── search-result-redesign.md    # 搜索结果解析器设计
│   └── city-cascader-design.md      # 城市选择器设计
│
├── docker-compose.yml               # Docker 编排（PG + Redis + Nginx）
├── nginx.conf                       # Nginx 反向代理配置
└── config.json                      # 外部化配置
```

## PC Web 版架构

### 构建方式
- Vite 多页面：`index.html`(移动端) + `pc.html`(PC 端)
- PC 端使用 `HashRouter`，URL 格式 `/pc.html#/plan`
- 共享所有 Store、API、子组件（SearchCards、TripTimeline、BudgetPanel）
- 现有移动端代码零改动

### PC 版布局
```
┌──────────┬──────────────────────────────────────────┐
│ 侧边栏    │  内容区                                    │
│ (自适应)   │                                          │
│          │                                          │
│ 🌍 智旅  │                                          │
│ 🏠 首页  │                                          │
│ 🗺️ 行程▾ │  各页面内容                                │
│ 🔍 搜索▾ │                                          │
│ ⚙️ 设置  │                                          │
│ 👤 用户  │                                          │
└──────────┴──────────────────────────────────────────┘
```

- 侧边栏：`w-64` (256px) 固定宽度
- 导航：4 个一级节点（首页、行程▾、搜索▾、设置）
- 行程组：AI智能规划 + 我的行程
- 搜索组：机票/火车票/酒店/景点/美食/同城交通
- 用户信息底部固定（`margin-bottom: 5vh`），含登出按钮

### AI 规划页三栏布局
```
┌──────────┬─────────────────────┬──────────────┐
│ 出行信息  │  进度 / 时间线        │  天气/提示/预算│
│ (35%)    │  (flex-1)            │  (25%)       │
└──────────┴─────────────────────┴──────────────┘
```

## 核心数据流

### 搜索流程
```
SearchPage → searchStore.search()
  → GET /api/v1/search/{type} → search.py
    → mcp_manager.call_tool() → FliggyTravel MCP
    → markdown_parser._parse_xxx() → 结构化 items
    → SearchCards.tsx 渲染卡片
```

### AI 规划流程
```
PlanPage → SSE /api/v1/plan/generate
  → agent_service.generate_plan()
    → LLM 决策 → MCP 工具调用 (asyncio.gather 并行)
    → LLM 生成 JSON → _save_trip() 持久化 (含 origin)
    → SSE: step → tool_call → tool_result → trip_data → done
```

规划进度阶段（PC + 移动端统一）：
1. 正在分析出行需求...
2. ✅ 出行需求分析完成
3. 并行搜索 N 个数据源 (done/total)
4. 🔍 / ✅ 搜索步骤详情（黄色=进行中，绿色=完成）
5. 正在生成行程方案...
6. ✅ 行程方案已生成

### 城市选择流程
```
CityCascader → GET /api/v1/info/locations?pid=0 → 省份 (拼音排序)
  → 点击省份 → GET /api/v1/info/locations?pid={id} → 城市列表
    → 点击城市 → SearchPage 填入值
  或 搜索框 → GET /api/v1/info/locations/search?keyword= → 拼音匹配
```

PC 版 CityCascaderPC：下拉面板替代底部弹窗，跟随输入框定位。

## 关键设计决策

1. **MCP 仅走 HTTP**：不使用 stdio 子进程（破坏 asyncio event loop），统一用 `remote_mcp.py`
2. **asyncio.gather 并行**：LLM 多工具调用并行执行，6×15s → 1×15s
3. **SSE done 优先于 DB 写入**：用户先看到结果，持久化在后
4. **markdown_parser 工具专属分派**：6 种工具各走各的解析函数，bag-of-fields 多正则提取
5. **城市数据内存加载**：3433 行 CSV 启动时加载到内存，拼音排序 + 搜索
6. **前端卡片结构化渲染**：后端解析出结构化字段，前端零正则直接渲染
7. **max-w-md 容器**：移动端优先，全应用统一 448px 最大宽度
8. **PostgreSQL + Redis (Docker)**：生产级数据库，开发/测试环境通过 Docker Compose 一键启动
9. **PC 版零侵入**：Vite 多页面构建，共享 Store/API/组件，移动端代码无改动
10. **侧边栏级联导航**：搜索和行程各为一个可折叠组，展开状态持久化 localStorage
11. **origin 字段**：Trip 模型新增 origin 列，AI 规划完成后持久化出发地，行程详情展示出发地/目的地天气
12. **行程标题规范**：LLM 系统提示约束 title 为 `出发地→目的地 M人N日游`，禁止添加任何修饰性主题词
13. **删除确认弹窗**：PC 版行程删除使用自定义 Modal 替代浏览器 confirm()
14. **myTrip store**: 支持 `deleteTrip` 操作，删除后自动刷新列表
15. **11 张数据库表**: User, UserPreference, Trip, TripDay, TripItem, Budget, SystemConfig, TripMember, TripExpense, Wallet, Transaction
16. **21 个后端服务模块**: 覆盖 AI 规划、搜索、认证、协作、钱包、分享、偏好学习等完整功能矩阵
17. **10 个 API 路由模块**: auth, search, plan, trips, info, user, phase2-5

## 数据库变更记录

| 日期 | 表 | 变更 |
|------|------|------|
| 2026-06-05 | trips | 新增 `origin VARCHAR(100)` 列 |

## 外部依赖

| 服务 | 用途 | 端点 |
|------|------|------|
| PostgreSQL 16 | 主数据库 | Docker / 宿主机 :5432 |
| Redis 7 | 缓存（验证码、MCP 结果） | Docker / 宿主机 :6379 |
| FliggyTravel MCP | 机票/火车/酒店/景点/美食/交通搜索 | `mcp.api-inference.modelscope.net/...` |
| DeepSeek API | LLM 行程规划 | 用户配置 |
| 高德 API | 天气查询 | `restapi.amap.com` |
| eduosi/district | 省市区数据 | 本地 CSV (GitHub) |

## 启动方式

```bash
# 数据库
docker compose up -d postgres redis

# 后端
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# 前端 (dev)
cd frontend && npm run dev
# 移动端: http://localhost:5173/
# PC 端:  http://localhost:5173/pc.html

# 前端 (build)
cd frontend && npm run build
# 输出: dist/index.html (移动端) + dist/pc.html (PC 端)
```
