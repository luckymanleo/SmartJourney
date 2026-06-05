# SmartJourney（智旅）部署文档

> 版本：v1.0 | 日期：2026-05-31

---

## 1. 概述

SmartJourney 采用前后端分离 + Docker Compose 容器化部署方案。支持单机部署和云服务器部署。

### 1.1 部署架构

```
                    Internet
                       │
              ┌────────┴────────┐
              │   Nginx :80/443 │
              │  (反向代理+静态) │
              └────────┬────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
  ┌─────┴─────┐ ┌──────┴──────┐ ┌────┴─────┐
  │ Frontend  │ │  Backend    │ │ PostgreSQL│
  │ (静态文件) │ │  :8000      │ │ :5432     │
  └───────────┘ └──────┬──────┘ └──────────┘
                       │
              ┌────────┴────────┐
              │  Redis :6379    │
              └─────────────────┘
```

---

## 2. 环境要求

### 2.1 硬件

| 环境 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| 开发 | 2核 | 4GB | 20GB |
| 生产（最低） | 2核 | 4GB | 40GB SSD |
| 生产（推荐） | 4核 | 8GB | 80GB SSD |

### 2.2 软件

| 软件 | 版本 | 用途 |
|------|------|------|
| Docker | 24+ | 容器运行时 |
| Docker Compose | 2.20+ | 容器编排 |
| Python | 3.11+ | 后端运行时（非 Docker 部署时） |
| Node.js | 20+ | 前端构建（非 Docker 部署时） |
| PostgreSQL | 15+ | 数据库 |
| Redis | 7+ | 缓存 |

### 2.3 第三方服务

| 服务 | 用途 | 获取地址 |
|------|------|----------|
| 飞猪 FlyAI API | MCP 旅行数据 | https://flyai.open.fliggy.com/ |
| 高德地图 API | 天气/地理编码 | https://lbs.amap.com/ |
| LLM API | AI 规划推理 | 按需选择（DeepSeek/OpenAI 兼容接口） |
| 短信服务 | 验证码发送 | 阿里云短信/腾讯云短信 |

---

## 3. 快速部署（Docker Compose）

### 3.1 获取代码

```bash
cd /home/administrator/software/SmartJourney
```

### 3.2 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
# ==================== 数据库 ====================
DATABASE_URL=postgresql+asyncpg://smartjourney:smartjourney@localhost:5432/smartjourney
REDIS_URL=redis://localhost:6379/0

# ==================== 安全 ====================
SECRET_KEY=<random_secret_key_32_chars_min>
JWT_ALGORITHM=HS256
JWT_EXPIRE_SECONDS=604800

# ==================== 飞猪 MCP ====================
FLYAI_API_KEY=<your_flyai_api_key>
FLYAI_SIGN_SECRET=<your_flyai_sign_secret>

# ==================== 高德地图 ====================
GAODE_API_KEY=<your_gaode_api_key>

# ==================== LLM API ====================
LLM_API_KEY=<your_llm_api_key>
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-v4-pro

# ==================== 短信服务 ====================
SMS_PROVIDER=mock

# ==================== 服务配置 ====================
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 3.3 启动服务

```bash
docker compose up -d
```

### 3.4 初始化数据库

开发环境下表结构在应用启动时自动创建（`main.py` lifespan 中 `Base.metadata.create_all`）。
生产环境建议使用 Alembic 迁移管理。

### 3.5 创建测试数据库（可选，仅运行测试时需要）

```bash
docker compose exec postgres createdb -U smartjourney smartjourney_test
```

### 3.6 验证

```bash
# 后端健康检查
curl http://localhost:8000/api/v1/health

# 前端
curl http://localhost/
```

---

## 4. docker-compose.yml

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    expose:
      - "8000"
    env_file:
      - ./backend/.env
    environment:
      - DATABASE_URL=postgresql+asyncpg://smartjourney:smartjourney@postgres:5432/smartjourney
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U smartjourney -d smartjourney"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  pgdata:
  redisdata:
```

---

## 5. Nginx 配置

```nginx
events { worker_connections 1024; }

http {
    include       mime.types;
    default_type  application/octet-stream;

    server {
        listen 80;
        server_name localhost;

        # 前端静态文件
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }

        # 后端 API 代理
        location /api/ {
            proxy_pass http://backend:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # SSE 支持
            proxy_buffering off;
            proxy_cache off;
            proxy_read_timeout 3600s;
            chunked_transfer_encoding on;
        }
    }
}
```

---

## 6. 后端 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uvx (用于运行 MCP 工具)
RUN pip install --no-cache-dir uv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 7. 前端构建与部署

### 7.1 本地构建

```bash
cd frontend
npm install
npm run build        # 输出到 dist/
```

### 7.2 前端 Dockerfile

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf
```

### 7.3 环境变量

前端构建时注入 API 地址：

```bash
# .env.production
VITE_API_BASE_URL=https://your-domain.com/api/v1
VITE_AMAP_KEY=<your_gaode_js_api_key>
```

---

## 8. 开发环境

### 8.1 启动基础设施（Docker）

```bash
cd /home/administrator/software/SmartJourney
docker compose up -d postgres redis

# 创建测试数据库（首次）
docker compose exec postgres createdb -U smartjourney smartjourney_test
```

> **WSL2 用户注意**：若未启用 Docker Desktop WSL2 集成，需使用 Windows 宿主机 IP 连接容器。
> 宿主 IP 可通过 `grep nameserver /etc/resolv.conf | head -1 | awk '{print $2}'` 获取。

### 8.2 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 启动开发服务器（表结构自动创建）
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio
```

### 8.3 前端

```bash
cd frontend
npm install
npm run dev          # Vite 开发服务器 :5173
```

### 8.4 环境变量（开发 .env）

```bash
# backend/.env
DATABASE_URL=postgresql+asyncpg://smartjourney:smartjourney@localhost:5432/smartjourney
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-change-in-production-min-32-chars!!
JWT_ALGORITHM=HS256
JWT_EXPIRE_SECONDS=604800
FLYAI_API_KEY=<your_key>
FLYAI_SIGN_SECRET=<your_secret>
GAODE_API_KEY=<your_key>
LLM_API_KEY=<your_key>
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-v4-pro
SMS_PROVIDER=mock
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost
```

---

## 9. 生产部署检查清单

- [ ] 修改所有默认密码（PostgreSQL、Secret Key）
- [ ] 配置 HTTPS 证书（Let's Encrypt / 阿里云 SSL）
- [ ] 配置防火墙（仅开放 80/443）
- [ ] 设置数据库定期备份
- [ ] 配置日志轮转（logrotate）
- [ ] 设置监控告警（磁盘、内存、API 响应时间）
- [ ] 配置 LLM API 调用额度告警
- [ ] 配置飞猪/高德 API 配额监控
- [ ] 验证码切换到真实短信服务（非 Mock）
- [ ] 开启 PostgreSQL SSL 连接

---

## 10. 常见问题

**Q: MCP 工具连接失败？**
A: 检查 `FLYAI_API_KEY` 和 `FLYAI_SIGN_SECRET` 是否正确。确认服务器能访问外网。

**Q: 前端 API 请求 404？**
A: 检查 Nginx 配置中 `proxy_pass` 地址是否正确指向 `backend:8000`。

**Q: SSE 流式规划中断？**
A: 确保 Nginx 配置了 `proxy_buffering off` 和 `proxy_read_timeout` 足够大。

**Q: 数据库迁移报错？**
A: 确保 PostgreSQL 已启动并可以连接，检查 `DATABASE_URL` 格式是否正确。
