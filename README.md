# SmartJourney（智旅）

全栈旅行规划平台 — AI 驱动的智能行程生成，支持移动端与 PC Web 双版本。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 18 + TypeScript + Vite + TailwindCSS + Zustand + React Router |
| 后端 | FastAPI (Python 3.11) + SQLAlchemy 2.0 async + PostgreSQL + Redis |
| AI | DeepSeek / OpenAI-compatible LLM + MCP 网关 |
| 数据 | FliggyTravel MCP（飞猪）、Meituan MCP（美团）、高德天气、eduosi/district |

## 核心功能

- **多类型搜索**：机票、火车票、酒店、景点、美食、市内交通
- **AI 智能规划**：LLM + MCP 自动搜索→生成完整 JSON 行程方案，SSE 流式返回
- **双端支持**：移动端（Phone/App）+ PC Web（侧边栏布局），Vite 多页面构建
- **行程管理**：CRUD + 时间线视图 + 预算追踪 + 天气集成
- **城市选择器**：3434 行民政部省市区数据，拼音搜索，三级联动
- **路线策略**：经济 / 舒适 / 快速三选一
- **扩展功能**：钱包积分、多人协作、行程分享、偏好学习、价格预警

## 项目结构

```
SmartJourney/
├── frontend/          # React 前端（mobile + PC）
│   ├── src/pages/     # 移动端页面
│   ├── src/pc/        # PC Web 页面
│   ├── src/stores/    # Zustand 状态管理（共享）
│   └── src/components/# 共享 UI 组件
├── backend/           # FastAPI 后端
│   └── app/
│       ├── api/       # 10 个路由模块
│       ├── services/  # 21 个服务模块
│       └── models/    # 11 张数据库表
├── docs/              # 技术文档
└── docker-compose.yml # PostgreSQL + Redis + Nginx
```

## 快速启动

```bash
# 数据库
docker compose up -d postgres redis

# 后端
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000

# 前端
cd frontend && npm install && npm run dev
# 移动端: http://localhost:5173/
# PC 端:  http://localhost:5173/pc.html
```

## 文档

- [架构文档](docs/architecture.md)
- [API 接口文档](docs/api.md)
- [需求文档](docs/requirements.md)
- [路线图](docs/roadmap.md)
- [部署指南](docs/deployment.md)
