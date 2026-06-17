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

## 架构关键设计

### 行程排序（sort_seq）

`trips` 表使用 `BIGSERIAL` 列 `sort_seq` 作为主排序键，替代 `updated_at`。原因：

- `updated_at` 会被过期定时任务、后台任务等系统操作污染，导致新行程被挤出首页
- `sort_seq` 由数据库序列自增，全局单调递增，不受任何 UPDATE 影响
- 过期任务（`trip_expiry.py`）不再修改 `updated_at`

### 坐标生成（唯一入口）

经纬度只在 **AI 规划 SSE 阶段**（`_emit_poi_coordinates`）生成，然后随 `_save_trip` 写入数据库。

```
SSE geocode（唯一入口）
  → 前端实时地图预览
  → 写入 DB（随 item INSERT）
  ↓
_enrich_items（仅照片富化，不再 geocode）
map_routes（纯 DB 读取，不再 geocode 补漏）
```

跨城行程使用 `seen_transit` 标记：首个 train/flight 后的所有 item 使用目的地城市 geocode（跨天不重置）。

火车/航班 item 始终取出发站（`→` 左侧）进行 geocode。

### 地图 marker 聚合

同坐标的多个 marker 自动聚合成一个圆角胶囊：
```
┌──────────────────┐
│ D3.1,D3.2   ❷   │  标签拼接 + 计数圈
└──────────────────┘
```

点击后弹出 InfoWindow 列表，可逐一查看详情卡片。

### 停运火车站过滤

两层防护：

| 层 | 位置 | 机制 |
|---|---|---|
| LLM 提示 | SYSTEM_PROMPT `{discontinued}` 占位符 | 运行时替换为 config 中的停运站列表 |
| 数据过滤 | `_compact_tool_result` | 搜索结果进入 LLM 前先关键词过滤 |

停运站列表配置在 `config.json` → `discontinued_stations`。

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
```

### config.json 关键配置

路径：`backend/config.json`

```json
{
  "discontinued_stations": ["深圳西站", "北京东站", ...],
  "city_search_aliases": {
    "武夷山": {"train": ["武夷山北", "南平市"], "flight": "武夷山"}
  },
  "route_strategies": [
    {"tag": "经济实惠", "emphasis": "..."},
    {"tag": "舒适优先", "emphasis": "..."},
    {"tag": "最快到达", "emphasis": "..."}
  ],
  "features": {
    "trip_expiry_interval_seconds": 1800,
    "mcp_tool_timeout_seconds": 180,
    "max_route_count": 3
  }
}
```

### 数据库迁移

手动 SQL 迁移文件在 `backend/migrations/` 目录：

| 文件 | 说明 |
|------|------|
| `add_comments.sql` | 表/列注释 |
| `add_sort_seq.sql` | trips 表加 BIGSERIAL 排序列 + 索引 |

### Docker Compose

`docker-compose.yml` 包含：PostgreSQL 16 + Redis 7 + 后端 + 前端 + Nginx

> 所有配置中的凭据均为占位符，不含真实密钥。
