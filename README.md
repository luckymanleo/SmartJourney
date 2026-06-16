# SmartJourney（智旅）

AI 驱动的智能旅行规划平台，支持移动端与 PC Web 双版本。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 18 + TypeScript + Vite + TailwindCSS + Zustand |
| 后端 | FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Redis |
| AI | DeepSeek / OpenAI-compatible LLM + MCP 网关 |
| 地图 | 高德 JS API 2.0 + Web 服务 API |

## 快速开始

```bash
# 1. 启动依赖服务
docker compose up -d postgres redis

# 2. 后端
cd backend
cp .env.example .env          # 编辑 .env 填入配置
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio

# 3. 前端
cd frontend
npm install
npm run dev                   # 移动端 :5173 / PC端 :5173/pc.html
```

## 部署

```bash
# 完整部署（PostgreSQL + Redis + Nginx + 前后端）
docker compose up -d

# 仅重建前后端
docker compose up -d --build backend frontend

# 查看日志
docker compose logs -f backend
```

Nginx 配置文件：`nginx.conf`（反向代理 + 静态文件 + SSE 长连接）

## 平台集成

### .env 配置模板

```bash
# ---- 数据库 ----
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/smartjourney
REDIS_URL=redis://host:6379/0

# ---- 安全 ----
SECRET_KEY=<random-32-chars>

# ---- LLM ----
LLM_API_KEY=sk-xxxx...
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# ---- 高德地图 ----
GAODE_API_KEY=<your-gaode-key>

# ---- 短信（开发用 mock，生产切换 aliyun）----
SMS_PROVIDER=mock
# SMS_ACCESS_KEY_ID=LTAIxxxx...
# SMS_ACCESS_KEY_SECRET=xxxx...
# SMS_SIGN_NAME=<your-sign-name>
# SMS_TEMPLATE_CODE=SMS_xxxxx
```

### config.json（MCP / 策略配置）

路径：`backend/config.json`

```json
{
  "mcp_url": "https://api.modelscope.cn/mcp/xxx",
  "mcp_headers": { "Authorization": "Bearer <token>" },
  "city_search_aliases": {},
  "route_strategies": {
    "smart_balance": "智能平衡",
    "budget_first": "经济实惠",
    "comfort_first": "舒适优先",
    "fastest": "最快到达"
  },
  "features": {
    "weather_reference": true,
    "mcp_tool_timeout_seconds": 15,
    "mcp_max_retries": 3
  }
}
```

### Docker Compose

`docker-compose.yml` 包含：PostgreSQL 16 + Redis 7 + 后端 + 前端 + Nginx

> 所有配置中的凭据均为占位符，不含真实密钥。
