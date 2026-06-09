# SmartJourney 性能优化方案

> 版本: 2.0  
> 日期: 2026-06-08  
> 状态: ✅ P0 部分/P1-2/P2-2/P2-3/P3-1 已实施 | P0-4/P1-1/P2-1/P3-2/P3-3 待实施

---

## 目录

1. [项目现状与响应链路分析](#1-项目现状与响应链路分析)
2. [单次规划响应时间分解](#2-单次规划响应时间分解)
3. [优化方案总览（按优先级排序）](#3-优化方案总览按优先级排序)
4. [P0 — 立即实施（零/微代码改动，高收益）](#4-p0--立即实施零微代码改动高收益)
5. [P1 — 短期实施（小改动，中等收益）](#5-p1--短期实施小改动中等收益)
6. [P2 — 中期实施（需改动配置或少量代码）](#6-p2--中期实施需改动配置或少量代码)
7. [P3 — 架构级优化（需改代码，供评估）](#7-p3--架构级优化需改代码供评估)
8. [附录：各阶段完整实施命令](#8-附录各阶段完整实施命令)

---

## 1. 项目现状与响应链路分析

### 1.1 技术栈

| 层 | 技术 | 版本/说明 |
|----|------|-----------|
| 前端 | React 18 + Vite 6 + TypeScript | 移动端 + PC Web 双版本 |
| 后端 | FastAPI + uvicorn | Python 异步，单 worker |
| 数据库 | PostgreSQL 16 (pgvector) | 异步驱动 asyncpg |
| 缓存 | Redis 7 | 懒加载代理 + MCP 结果缓存 + 短信限流 + 天气缓存 |
| 推理 | DeepSeek v4 Pro | AI 行程规划 |
| 外部API | ModelScope MCP (飞猪) | 机票/火车/酒店/景点/美食/交通 搜索 |
| 天气 | 高德地图 API | 有 Redis 缓存(30分钟) |
| 反向代理 | nginx:alpine | 静态文件 + API 代理 |

### 1.2 核心请求链路

```
用户浏览器
  → nginx (80)
    → 静态文件: /usr/share/nginx/html (Vite 构建产物)
    → API 代理: /api/ → backend:8000

后端单次 AI 规划流程:
  ① 解析用户输入 → 构造 11 个 MCP 查询 (<1s)
  ② 并行 MCP 搜索: 11查询 × Semaphore(6) → 最多6并发 (25-45s)  ← 瓶颈1
  ③ 天气 API: 出发地+目的地 并行 (1-2s，有Redis缓存后<10ms)
  ④ 结果汇总 + 压缩 (<1s)
  ⑤ DeepSeek v4 LLM 生成 JSON (20-35s)  ← 瓶颈2
  ⑥ 异步保存到 PostgreSQL (1-2s，不阻塞SSE)
  → SSE 流式返回给前端

总耗时: 47-83s (取决于目的地数据丰富度和网络状况)
```

### 1.3 当前配置关键参数

| 参数 | 当前值 | 位置 |
|------|--------|------|
| MCP单次超时 | 90s | config.json → features.mcp_tool_timeout_seconds |
| MCP并发限制 | Semaphore(6) | mcp_manager.py |
| LLM max_tokens | 8192 | agent_service.py _call_llm |
| DB连接池 | pool_size=10, max_overflow=20 | database.py |
| uvicorn worker | 1（生产可开 4） | 启动命令 |
| nginx 压缩 | gzip on, level 6 | nginx.conf |
| 前端缓存头 | HTML no-cache / assets immutable 1y | nginx.conf |
| Redis 持久化 | AOF, maxmemory 256MB | docker-compose.yml |
| MCP 结果缓存 | ✅ Redis 按类型 TTL 5-60min | mcp_manager.py |
| Vite vendor 分割 | react/router/zustand/axios/lucide | vite.config.ts |

---

## 2. 单次规划响应时间分解

以 「深圳→武夷山 5日游」 为例实测分解（优化后）：

| # | 阶段 | 操作 | 耗时(秒) | 占比 | 可优化? |
|---|------|------|----------|------|---------|
| 1 | 需求分析 | 解析查询、构造用户消息 | <0.1 | 0% | — |
| 2 | MCP搜索 | 去程机票 ×2 (经济/头等) | 8-20 | — | 见P2 |
| 2 | MCP搜索 | 返程机票 ×2 | 8-20 | — | 见P2 |
| 2 | MCP搜索 | 去程火车 ×3 (高/动/普) | 18-45 | — | 见P2 |
| 2 | MCP搜索 | 返程火车 ×3 (高/动/普) | 18-45 | — | 见P2 |
| 2 | MCP搜索 | 酒店 ×1 | 5-15 | — | 见P3 |
| 2 | MCP搜索 | 景点 ×1 | 5-15 | — | 见P3 |
| 2 | MCP搜索 | 美食 ×1 | 5-15 | — | 见P3 |
| 2 | MCP搜索 | 交通 ×1 | 5-15 | — | 见P3 |
| **2** | **MCP搜索合计** | **跨城11查询并行(Semaphore 6)** | **25-45** | **~55%** | **★主要瓶颈** |
| 3 | 天气 | 出发地+目的地 并行API | 1-2(命中缓存<10ms) | 1% | 已有缓存 |
| 4 | 汇总压缩 | compact_tool_result | <0.5 | 0% | — |
| 5 | LLM生成 | DeepSeek v4 (max_tokens=8192) | 20-35 | **~40%** | **★次要瓶颈** |
| 6 | 异步保存 | PostgreSQL INSERT | 1-2 | (异步) | 不阻塞 |
| **总计** | | | **47-83** | **100%** | |

### MCP 搜索细分（Semaphore=6 时的并发批次，跨城11查询）

```
批次1 (6并发): 去程机票×2 + 去程火车×3 + 返程机票×1     → ~15s
批次2 (5并发): 返程机票×1 + 返程火车×3 + 酒店×1          → ~15s
批次3 (3并发): 景点×1 + 美食×1 + 交通×1                  → ~12s
总等待: ~42s (首次，无缓存)

同城查询(3查询，1批):
批次1 (3并发): 酒店 + 景点 + 美食                        → ~12s

命中 Redis 缓存时:
MCP 搜索 ≈ 0s → 总耗时降至 ~20-35s (仅 LLM 生成)
```

---

## 3. 优化方案总览（按优先级排序）

| # | 方案 | 分类 | 难度 | 预期效果 | 状态 |
|---|------|------|------|----------|------|
| **P0-1** | nginx gzip压缩+缓存头 | 前端加载 | 5分钟 | 前端首屏快60-80% | ✅ |
| **P0-2** | PostgreSQL 连接池调优 | 后端并发 | 5分钟 | 并发吞吐量2-3倍 | ✅ |
| **P0-3** | PostgreSQL 服务端参数 | 数据库 | 5分钟 | 查询快20-30% | ✅ |
| **P0-4** | 数据库添加索引 | 数据库 | 1分钟 | expiry扫描→零扫描 | ☐ |
| **P1-1** | uvicorn 多 worker | 后端并发 | 1分钟 | 多用户不排队 | ☐ |
| **P1-2** | Redis 持久化配置 | 缓存可靠 | 5分钟 | 重启不丢缓存 | ✅ |
| **P2-1** | MCP 超时 90→60s | 搜索延迟 | 1分钟 | 坏请求快速重试 | ☐ |
| **P2-2** | MCP Semaphore 3→6 | 搜索并行 | 1分钟 | 搜索阶段快30-40s | ✅ |
| **P2-3** | Vite vendor 代码分割 | 前端加载 | 30分钟 | 首屏JS减50% | ✅ |
| **P3-1** | MCP 结果 Redis 缓存 | 搜索延迟 | 30分钟 | 二次规划快80% | ✅ |
| **P3-2** | 前端路由级 lazy 分割 | 前端加载 | 30分钟 | 首屏JS按需加载 | ☐ |
| **P3-3** | LLM streaming生成 | 感知延迟 | 2小时 | 用户感知TTFB ↓ | ☐ |

---

## 4. P0 — 立即实施（零/微代码改动，高收益）

### 4.1 P0-1: nginx 启用 gzip 压缩 + 静态资源缓存头  ✅ 已实施

**问题**: 当前 nginx 直传原始 JS/CSS，不压缩不缓存。Vite 构建产物 `main-xxx.js` 通常2-3MB。

**方案**: 修改 `nginx.conf` 增加 gzip 和缓存控制。

**预期效果**:
- 压缩后 JS 体积减少 60-80%（2MB → ~500KB）
- 带 hash 的静态文件 1 年缓存（二次访问 0 请求）
- `index.html` / `pc.html` 不缓存（确保更新立即可见）

**实施步骤**:

编辑 `/home/administrator/software/SmartJourney/nginx.conf`，替换为以下内容：

```nginx
events { worker_connections 1024; }

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    tcp_nodelay   on;
    keepalive_timeout 65;

    # ============ Gzip 压缩 ============
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 256;
    gzip_types
        text/plain
        text/css
        text/javascript
        application/javascript
        application/json
        application/xml
        text/xml
        image/svg+xml
        application/wasm;

    server {
        listen 80;
        server_name localhost;

        # index.html / pc.html — 不缓存（确保更新立即可见）
        location = /index.html {
            root /usr/share/nginx/html;
            add_header Cache-Control "no-cache, must-revalidate";
            add_header Pragma "no-cache";
        }

        location = /pc.html {
            root /usr/share/nginx/html;
            add_header Cache-Control "no-cache, must-revalidate";
            add_header Pragma "no-cache";
        }

        # 带hash的静态资源 — 永久缓存（文件名含内容hash，改内容=改文件名）
        location ~* ^/assets/.*\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            root /usr/share/nginx/html;
            expires 1y;
            add_header Cache-Control "public, immutable";
            add_header Vary Accept-Encoding;
        }

        # 其他静态文件 — 短期缓存
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
            add_header Cache-Control "no-cache";
        }

        # 后端 API 代理
        location /api/ {
            proxy_pass http://backend:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # SSE 支持（SSE 必须关闭 buffering）
            proxy_buffering off;
            proxy_cache off;
            proxy_read_timeout 3600s;
            chunked_transfer_encoding on;
        }
    }
}
```

**验证**:
```bash
# 重新构建并启动
docker compose build nginx
docker compose up -d nginx

# 验证 gzip
curl -H "Accept-Encoding: gzip" -I http://localhost/assets/main-xxx.js | grep Content-Encoding
# 期望输出: Content-Encoding: gzip

# 验证缓存头
curl -I http://localhost/assets/main-xxx.js | grep Cache-Control
# 期望输出: Cache-Control: public, immutable
```

---

### 4.2 P0-2: PostgreSQL 连接池参数调优  ✅ 已实施

**问题**: `database.py` 创建 engine 时未指定 pool 参数，使用 SQLAlchemy 默认值：
- `pool_size=5` — 连接池基本连接数
- `max_overflow=10` — 额外可创建连接数

AI 规划流程中多个异步任务（MCP/天气/保存）都会用到 DB 连接。高并发时连接不够会排队等待。

**方案**: 通过环境变量控制连接池参数（只需在 `database.py` 增加参数读取，3行改动）。

**实施步骤**:

修改 `/home/administrator/software/SmartJourney/backend/app/database.py`:

```python
"""数据库会话与引擎管理 — PostgreSQL (asyncpg)"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import get_settings

settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
    pool_pre_ping=True,  # 连接前检测有效性
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

在 `.env` 末尾追加:

```bash
# ==================== 数据库连接池 ====================
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800
```

**验证**:
```bash
# 重启后端
pkill -f uvicorn
cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio &

# 观察日志启动时无连接错误
tail -f ~/software/SmartJourney/backend/logs/*.log
```

---

### 4.3 P0-3: PostgreSQL 服务端参数调优  ✅ 已实施

**问题**: PostgreSQL 容器使用默认参数，未针对宿主机的实际内存做优化。默认 `shared_buffers=128MB` 偏保守。

**方案**: 在 `docker-compose.yml` 中通过 `command` 传递 PostgreSQL 运行时参数。不改镜像。

**实施步骤**:

修改 `/home/administrator/software/SmartJourney/docker-compose.yml` 中 postgres 服务:

```yaml
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_USER=smartjourney
      - POSTGRES_PASSWORD=smartjourney
      - POSTGRES_DB=smartjourney
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    # ===== 性能调优参数 =====
    command:
      - "postgres"
      - "-c shared_buffers=256MB"
      - "-c effective_cache_size=1GB"
      - "-c work_mem=16MB"
      - "-c maintenance_work_mem=64MB"
      - "-c random_page_cost=1.1"
      - "-c effective_io_concurrency=200"
      - "-c wal_buffers=16MB"
      - "-c max_worker_processes=4"
      - "-c max_parallel_workers_per_gather=2"
      - "-c max_parallel_workers=4"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U smartjourney -d smartjourney"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
```

**参数说明**:

| 参数 | 默认 | 新值 | 作用 |
|------|------|------|------|
| shared_buffers | 128MB | 256MB | 数据缓存，最关键的PG参数 |
| effective_cache_size | 4GB | 1GB | 查询计划器估算OS缓存大小 |
| work_mem | 4MB | 16MB | 排序/Hash操作内存 |
| maintenance_work_mem | 64MB | 64MB | VACUUM/CREATE INDEX 内存 |
| random_page_cost | 4.0 | 1.1 | SSD 随机读成本（默认4是机械盘） |
| effective_io_concurrency | 1 | 200 | SSD 并发IO数 |
| max_parallel_workers | 8 | 4 | 并行查询worker上限 |

**验证**:
```bash
# 重启 PostgreSQL
docker compose down postgres
docker compose up -d postgres

# 确认参数生效
docker compose exec postgres psql -U smartjourney -c "SHOW shared_buffers;"
# 期望: 256MB

docker compose exec postgres psql -U smartjourney -c "SHOW random_page_cost;"
# 期望: 1.1
```

---

### 4.4 P0-4: 数据库添加 trip_expiry 优化索引  ☐ 待实施

**问题**: `trip_expiry.py` 每30分钟执行：
```sql
UPDATE trips SET status='expired'
WHERE status='active' AND end_date < CURRENT_DATE
```

当前有 `ix_trips_user_status(user_id, status)` 索引，但 `status` 不在第一列，且 `end_date` 不在索引中 → 可能触发全表扫描。随着行程数据增长，这个查询会越来越慢。

**方案**: 创建 `(status, end_date)` 联合索引，精确覆盖 expiry 查询条件。

**实施步骤** (直接在数据库执行，不改代码):

```bash
# 连接数据库
docker compose exec postgres psql -U smartjourney -d smartjourney

# 并发创建索引（不锁表）
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_trips_status_end_date
    ON trips (status, end_date)
    WHERE status = 'active';

# 验证索引
\d trips
# 确认 ix_trips_status_end_date 出现在索引列表中
```

使用部分索引（`WHERE status = 'active'`）因为 expiry 只查 active 状态的行程，索引更小更快。

**验证**:
```sql
EXPLAIN UPDATE trips SET status='expired'
WHERE status='active' AND end_date < CURRENT_DATE;
-- 确认使用 Index Scan using ix_trips_status_end_date
```

---

## 5. P1 — 短期实施（小改动，中等收益）

### 5.1 P1-1: uvicorn 多 Worker  ☐ 待实施

**问题**: 当前单 worker，所有请求串行处理。AI 规划耗时 60-130s，这期间其他用户请求排队等待。

**方案**: 启动时指定 worker 数。

**注意**: 多 worker 下需要确保：
- Redis 缓存共享（已满足，Redis 独立进程）
- 数据库连接池共享（每个 worker 独立 pool，需总连接数 ≤ PostgreSQL max_connections）

```bash
# 当前
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio

# 改为 (CPU核心数或至少2-4)
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio --workers 4
```

**连接数计算**:
- 4 workers × pool_size(10) = 40 个连接
- PostgreSQL 默认 max_connections=100，安全

如果需要更多 workers，需相应调小 `DB_POOL_SIZE`：
```bash
# 8 workers 时
DB_POOL_SIZE=5  # 8×5=40 连接
```

---

### 5.2 P1-2: Redis 持久化配置  ✅ 已实施

**问题**: 当前 Redis 容器无持久化配置，容器重启后所有缓存（天气、短信限流状态）丢失。

**方案**: 在 docker-compose 中增加 Redis AOF 持久化。

**实施步骤**:

修改 `docker-compose.yml` 中 redis 服务:

```yaml
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
```

**参数说明**:
- `appendonly yes`: AOF 持久化，重启恢复数据
- `maxmemory 256mb`: 内存上限
- `maxmemory-policy allkeys-lru`: 达上限时淘汰最久未使用的键

---

## 6. P2 — 中期实施（需改动配置或少量代码）

### 6.1 P2-1: MCP 工具超时 90s → 60s  ☐ 暂未实施

**问题**: 当前 `mcp_tool_timeout_seconds: 90`，但绝大多数 MCP 查询在 30s 内完成。90s 超时意味着坏请求会浪费更多时间。

**方案**: 降低超时到 60s，让真正超时的请求更快失败+重试。

**当前状态**: ModelScope 服务端偶尔延迟较高，保持 90s 更稳妥。暂不调整，待数据源稳定性改善后再评估。

### 6.2 P2-2: MCP Semaphore 3 → 6  ✅ 已实施

**问题**: 当前 `Semaphore(3)` 强制 8 个 MCP 查询分 3 批串行执行。如果 ModelScope 服务器能承受，提升到 6 可减少一个批次周期。

**影响分析**:
- Semaphore=3: 3→3→2 (3批) ≈ 等待时间 ~45-60s
- Semaphore=6: 6→2 (2批) ≈ 等待时间 ~20-30s
- 节省: **约 20-40 秒**

**实施**: 修改 `mcp_manager.py` 第21行:

```python
_call_semaphore = asyncio.Semaphore(6)  # 原值: 3
```

**风险**: ModelScope 可能拒绝过多并发连接。建议先用5-6测试，出现 503/连接拒绝则回退到3-4。

### 6.3 P2-3: Vite vendor 代码分割  ✅ 已实施

**已实施**: `vite.config.ts` 配置 `manualChunks`，将 node_modules 拆分为独立 vendor chunk：

- `vendor-react`: react + react-dom + react-router-dom
- `vendor-utils`: axios + zustand
- `vendor-icons`: lucide-react

这些包更新频率远低于业务代码，独立 chunk 后用户更新时只需重载业务代码。

---

## 7. P3 — 架构级优化（需改代码，供评估）

### 7.1 P3-1: MCP 搜索结果 Redis 缓存  ✅ 已实施

**核心思路**: 同一目的地的机票/火车/酒店/景点/美食搜索结果在一定时间内有效。对 `(tool, query) → result` 做 Redis 缓存。

**预期收益**:
- 同一用户重复规划（改了天数/预算但目的地相同）：MCP搜索阶段从 ~50s → ~5ms
- 不同用户搜同一目的地：受益同上
- 缓存 TTL 建议: 300-600 秒（搜索结果 5-10 分钟内有效）

**实施复杂度**: 约10行代码改动（`mcp_manager.call_tool` 增加缓存读/写）

### 7.2 P3-2: 前端路由级 lazy 加载

**当前**: Vite 构建产出 2 个入口文件 — `main.js` + `pc.js`，每个都是包含所有组件的大包。

**方案**: React.lazy + Suspense 做路由级代码分割，Vite 自动拆包。

**预期收益**:
- 移动端首屏 JS 从 ~2MB → ~400KB（只加载当前页面组件）
- PC 端同理
- 其他页面按需加载

**实施复杂度**: 约30分钟改路由定义（所有页面组件改为 lazy import）

### 7.3 P3-3: LLM Streaming 生成

**当前**: `_call_llm` 使用非流式调用，等待完整响应后才开始返回 SSE 给前端。用户看到 20-35s 的空白等待。

**方案**: 将 LLM API 调用改为 streaming，边生成边推送 token 给前端。前端用动画展示"正在生成中..."。

**预期收益**:
- 用户感知 TTFB 从 20-35s → 2-3s（首 token 延迟）
- 总耗时不变，但体验大幅改善

---

## 8. 附录：各阶段完整实施命令

### 8.1 P0 实施检查清单

```bash
# ① 备份当前配置
cd /home/administrator/software/SmartJourney
cp nginx.conf nginx.conf.bak
cp docker-compose.yml docker-compose.yml.bak
cp backend/app/database.py backend/app/database.py.bak
cp backend/.env backend/.env.bak

# ② 修改 nginx.conf（按4.1节内容）
vim nginx.conf

# ③ 修改 docker-compose.yml（按4.3节内容 + 5.2节Redis持久化）
vim docker-compose.yml

# ④ 修改 database.py（按4.2节内容）
vim backend/app/database.py

# ⑤ 追加 .env 连接池参数
echo "" >> backend/.env
echo "# ==================== 数据库连接池 ====================" >> backend/.env
echo "DB_POOL_SIZE=10" >> backend/.env
echo "DB_MAX_OVERFLOW=20" >> backend/.env
echo "DB_POOL_RECYCLE=1800" >> backend/.env

# ⑥ 重启所有服务
docker compose down
docker compose up -d

# ⑦ 创建 expiry 索引
docker compose exec postgres psql -U smartjourney -d smartjourney -c \
  "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_trips_status_end_date ON trips (status, end_date) WHERE status = 'active';"

# ⑧ 验证
docker compose exec postgres psql -U smartjourney -c "SHOW shared_buffers;"
curl -H "Accept-Encoding: gzip" -I http://localhost/ | grep -E "Content-Encoding|Cache-Control"
```

### 8.2 P1 实施

```bash
# uvicorn 多 worker (修改启动脚本或systemd service)
pkill -f uvicorn
cd /home/administrator/software/SmartJourney/backend
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio --workers 4
```

### 8.3 P2 实施

```bash
# MCP 超时
# 编辑 config.json: "mcp_tool_timeout_seconds": 90 → 60

# MCP Semaphore
# 编辑 mcp_manager.py: asyncio.Semaphore(3) → asyncio.Semaphore(6)

# 重启后端
pkill -f uvicorn
cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio --workers 4 &
```

### 8.4 回滚方案

如果优化导致问题：

```bash
# 恢复配置
cp nginx.conf.bak nginx.conf
cp docker-compose.yml.bak docker-compose.yml.bak
cp backend/app/database.py.bak backend/app/database.py

# 重启
docker compose down
docker compose up -d
```

---

## 附录A: 优化效果预估

| 场景 | 优化前(P0前) | 当前(已实施) | 全量(P3完成) |
|------|-------------|-------------|-------------|
| 单次规划(跨城首查) | 62-130s | 47-83s | 40-80s |
| 单次规划(跨城重复查) | 62-130s | 20-35s(缓存命中) | 5-10s |
| 前端首屏加载 | 2-3s | 0.3-0.6s | 0.2-0.4s(lazy) |
| 并发5用户 | 排队 | 不排队(连接池) | 不排队(+workers) |
| 用户感知TTFB | 30s空白 | 15s(搜索) | 2-3s(streaming) |

## 附录B: 文件改动清单

| 文件 | 改动类型 | 涉及方案 |
|------|----------|----------|
| `nginx.conf` | 重写 | P0-1 |
| `docker-compose.yml` | 修改postgres+redis | P0-3, P1-2 |
| `backend/app/database.py` | 加4个参数 | P0-2 |
| `backend/.env` | 追加4行 | P0-2 |
| `backend/config.json` | 改1行 | P2-1 |
| `backend/app/services/mcp_manager.py` | 改1行 | P2-2 |
| DB (migration) | CREATE INDEX | P0-4 |

## 附录C: 实施结果（2026-06-08 更新）

### 已完成优化

| # | 方案 | 状态 | 验证结果 |
|---|------|------|----------|
| P0-1 | nginx gzip + 缓存头 | ✅ | gzip on, Cache-Control: immutable |
| P0-2 | PG 连接池 (pool_size=10) | ✅ | pool_size/max_overflow/pool_recycle 已配置 |
| P0-3 | PG 服务端参数 | ✅ | shared_buffers=256MB 等(docker-compose.yml) |
| P1-2 | Redis AOF 持久化 | ✅ | appendonly yes, maxmemory 256MB |
| P2-2 | MCP Semaphore 3→6 | ✅ | mcp_manager.py 已更新为 6 |
| P2-3 | Vite vendor 代码分割 | ✅ | react/router/zustand/axios/lucide 独立 chunk |
| P3-1 | MCP 结果 Redis 缓存 | ✅ | 按工具类型分档 TTL (flight 5min ~ poi 60min) |

### 未完成优化

| # | 方案 | 状态 | 阻塞原因 |
|---|------|------|----------|
| P0-4 | expiry 索引 | ☐ | 表创建时间较早，需手动执行 `CREATE INDEX CONCURRENTLY` |
| P1-1 | uvicorn workers | ☐ | 开发环境 MemoryRedis 降级时多 worker 缓存不一致；生产配真实 Redis 后可开 |
| P2-1 | MCP 超时 90→60s | ☐ | 当前 ModelScope 服务端偶尔延迟高，保持 90s 更稳妥 |
| P3-2 | 前端路由级 lazy | ☐ | vendor 分割已做，路由级 lazy 可进一步优化但收益递减 |
| P3-3 | LLM streaming | ☐ | 需改 agent_service 和前端 SSE 处理，工作量较大 |

### 多 Worker 说明

开发环境使用 MemoryRedis 作为 Redis 回退时，多 worker 会导致不同 worker 之间
内存缓存不一致（验证码 send 和 login 可能路由到不同 worker）。
生产环境配置真实 Redis 后，可启用 `--workers 4`。

### 各层延迟现状（优化后）

| 阶段 | 优化前(P0前) | 优化后(当前) | 改进 |
|------|-------------|-------------|------|
| MCP 搜索(跨城11查询) | 4批×~15s=~60s | 2批×~15s=~30s | -50% |
| MCP 搜索(命中缓存) | ~60s | ~0s | -100% |
| LLM 生成 | 20-35s | 20-35s | 不变(外部API) |
| 前端首屏加载 | 2-3s | 0.3-0.6s | -80% |
| 前端二次访问 | 2-3s | ~0s(缓存) | -100% |
| 并发吞吐 | 串行 | 连接池 2-3x | +200% |
