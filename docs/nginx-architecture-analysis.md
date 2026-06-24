# SmartJourney Nginx 架构分析

> 日期: 2026-06-08 | 版本: 1.0 | 状态: 分析完成

---

## 目录

1. [概述与结论](#1-概述与结论)
2. [部署架构全景](#2-部署架构全景)
3. [nginx 承担的三项职责](#3-nginx-承担的三项职责)
4. [配置逐段解析](#4-配置逐段解析)
5. [两种运行模式对比](#5-两种运行模式对比)
6. [数据流全景](#6-数据流全景)
7. [与后端 CORS 的配合关系](#7-与后端-cors-的配合关系)
8. [已解决的场景与配置要点](#8-已解决的场景与配置要点)
9. [潜在问题与改进方向](#9-潜在问题与改进方向)
10. [附录：验证命令](#10-附录验证命令)

---

## 1. 概述与结论

### 结论

**SmartJourney 架构中确实使用了 nginx，担任反向代理 + 静态文件服务双重角色。** 配置规范且针对场景做了针对性优化（SSE 长连接、gzip 分层缓存）。当前配置整体合理，唯一较大的缺口是 HTTPS 尚未配置。

### nginx 角色

```
所有外部流量 → nginx :80 → ├─ 静态文件（Vite dist 产物）
                           └─ 反向代理 /api/ → backend:8000
```

### 配置位置

| 文件 | 内容 |
|------|------|
| `nginx.conf` | 完整 nginx 配置（gzip + 缓存 + 代理 + SSE） |
| `docker-compose.yml` | nginx 容器定义（镜像、端口、挂载、依赖） |
| `frontend/vite.config.ts` | 开发模式 Vite proxy（仅 npm run dev 生效） |

---

## 2. 部署架构全景

```
                      Internet
                         │
                ┌────────┴────────┐
                │  Nginx :80/443  │   ← 唯一入口，反向代理 + 静态
                │  nginx:alpine   │
                └────────┬────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
  ┌────────────┐  ┌────────────┐  ┌───────────────┐
  │ Frontend   │  │  Backend   │  │  PostgreSQL   │
  │ (静态文件)  │  │  :8000     │  │  :5432        │
  │ nginx 内置  │  │  FastAPI   │  │  pgvector 16  │
  └────────────┘  └─────┬──────┘  └───────────────┘
                        │
                 ┌──────┴──────┐
                 │Redis :6379  │
                 │7-alpine     │
                 └─────────────┘
```

### Docker Compose 容器拓扑（4 容器）

| 容器 | 镜像 | 端口 | 对外暴露 |
|------|------|------|---------|
| nginx | nginx:alpine | 80 | ✅ 宿主机:80 |
| backend | 自建 Dockerfile | 8000 | ❌ 仅 internal（`expose`） |
| postgres | pgvector/pgvector:pg16 | 5432 | ✅ 宿主机:5432（开发便利） |
| redis | redis:7-alpine | 6379 | ✅ 宿主机:6379（开发便利） |

> **注意**：生产部署建议将 postgres 和 redis 也改为 `expose` 而非 `ports`，仅通过 Docker 内网访问。

---

## 3. nginx 承担的三项职责

| 职责 | 配置段 | 关键指令 |
|------|--------|---------|
| **① 静态文件服务** | `location /` + `location ~* ^/assets/` | `root /usr/share/nginx/html; try_files` |
| **② API 反向代理** | `location /api/` | `proxy_pass http://backend:8000/api/` |
| **③ SSE 长连接代理** | `location /api/` 子配置 | `proxy_buffering off; proxy_read_timeout 3600s` |

---

## 4. 配置逐段解析

### 4.1 全局 HTTP 设置

```nginx
events { worker_connections 1024; }

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile      on;            # 零拷贝文件传输，静态文件性能关键
    tcp_nodelay   on;            # 禁用 Nagle 算法，小包不聚合
    keepalive_timeout 65;        # 复用连接 65s
```

`sendfile on` 利用 Linux kernel 零拷贝机制，减少静态文件服务的 CPU 开销和内存拷贝。

### 4.2 Gzip 压缩

```nginx
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 256;
    gzip_types
        text/plain text/css text/javascript
        application/javascript application/json application/xml
        text/xml image/svg+xml application/wasm;
```

| 指令 | 值 | 说明 |
|------|-----|------|
| `gzip on` | — | 启用压缩 |
| `gzip_vary on` | — | 响应头加 `Vary: Accept-Encoding`，CDN/代理可按此分缓存 |
| `gzip_comp_level` | 6 | 压缩级别 1-9，6 是 CPU 与压缩率的甜点 |
| `gzip_min_length` | 256B | 小于 256 字节不压缩（压缩后可能更大） |
| `gzip_types` | 9 种 MIME | 仅压缩文本类，不压缩图片/字体（已压缩） |

### 4.3 缓存策略（分层）

```
层次 1 — HTML 入口（永不缓存）
   location = /index.html  →  no-cache, must-revalidate
   location = /pc.html     →  no-cache, must-revalidate

层次 2 — 带 hash 的静态资源（永久缓存）
   location ~* ^/assets/.*\.(js|css|png|...)
   →  expires 1y + Cache-Control: public, immutable

层次 3 — SPA fallback（短期缓存）
   location /  →  try_files $uri $uri/ /index.html
   →  Cache-Control: no-cache
```

**设计原理**：

- `index.html` / `pc.html` 是入口，必须实时生效 → 不缓存
- Vite 构建的 JS/CSS 文件名含 content hash（如 `main-a3f2.js`），内容变则文件名变 → 可永久缓存（`immutable`）
- 其他未知路径回退到 index.html（React Router SPA 路由）

### 4.4 API 反向代理

```nginx
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
```

| 指令 | 说明 |
|------|------|
| `proxy_pass` | 转发给 Docker 内部 DNS 名 `backend:8000`（Docker Compose 服务名即主机名） |
| `X-Real-IP` | 传递真实客户端 IP 给后端（日志/安全用） |
| `X-Forwarded-For` | 完整代理链 IP（$proxy_add_x_forwarded_for 追加本节点） |
| `X-Forwarded-Proto` | HTTP/HTTPS 协议标识 |
| `proxy_buffering off` | **SSE 必须** — 关闭响应缓冲，数据即时推送给客户端 |
| `proxy_cache off` | 禁用代理缓存（API 响应不应缓存） |
| `proxy_read_timeout 3600s` | AI 规划流最长 1 小时（实际 2-3 分钟，但留足余量） |
| `chunked_transfer_encoding on` | 分块传输编码，SSE 流式依赖 |

---

## 5. 两种运行模式对比

| | 开发模式 (`npm run dev`) | Docker 生产模式 |
|---|---|---|
| **入口端口** | Vite dev server :5173 | nginx :80 |
| **API 代理** | Vite 内置 `server.proxy` → `:8000` | nginx `proxy_pass` → `backend:8000` |
| **静态文件** | Vite HMR 内存热更新 | nginx 托管 `frontend/dist` |
| **nginx 是否参与** | ❌ 不使用 | ✅ 使用 |
| **变化生效** | 保存即刷新（200ms） | 需 `npm run build` 后重启 |
| **适用场景** | 本地开发调试 | 生产/预发布/演示 |

### 开发模式 Vite proxy 配置

```typescript
// frontend/vite.config.ts
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```

Vite proxy 处理 `/api/*` 请求转发，无需 nginx。这是开发时的轻量替代。

---

## 6. 数据流全景

### 6.1 首次页面加载

```
浏览器 GET /
  → nginx location = /index.html
    → 返回 index.html（无缓存）
      → 浏览器解析 <script src="/assets/main-a3f2.js">
        → nginx location ~* ^/assets/
          → 返回 main-a3f2.js（gzip 压缩，1y immutable 缓存）
```

### 6.2 AI 规划 SSE 流

```
浏览器 POST /api/v1/plan/generate  (SSE)
  → nginx location /api/
    → proxy_pass http://backend:8000/api/v1/plan/generate
      → FastAPI agent_service.generate_plan()
        → SSE: data: {"type":"step","status":"searching"}
        → SSE: data: {"type":"tool_call","tool":"search_flights"}
        → SSE: data: {"type":"tool_result","data":{...}}
        → SSE: data: {"type":"trip_data","data":{...}}   ← 关键帧
        → SSE: data: {"type":"done"}
      ← 所有 SSE 帧即时通过 nginx 推送
        （proxy_buffering off 确保不积攒）
  → 浏览器 EventSource / fetch reader 逐帧处理
```

### 6.3 取消规划

```
用户点击取消按钮
  → 浏览器 AbortController.abort()
    → fetch 断开 → TCP 连接关闭
      → nginx 感知上游（客户端）断开
        → 转发 connection close 信号给 backend
          → asyncio Task.cancel()
            → MCP 请求自然终止
            → LLM 上下文释放
```

---

## 7. 与后端 CORS 的配合关系

### 后端 CORS 配置

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_debug_origins() if debug else settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### nginx 代理下的 CORS 行为

| 场景 | 走 nginx | 请求域 | CORS 生效？ |
|------|---------|--------|------------|
| Docker 生产 | ✅ | 同域（都是 :80） | ❌ 不触发 |
| Vite 开发 | ❌ | 跨域 :5173 ↔ :8000 | ✅ 生效 |
| 直接访问 API | ❌ | 取决于调用方 | ✅ 生效 |

> **关键认知**：nginx 反向代理后，前端和 API 同域（`http://localhost`），浏览器不再发送跨域请求，CORS 中间件实际不触发。当前 CORS 配置对生产环境来说是无害的冗余。

---

## 8. 已解决的场景与配置要点

### 8.1 SSE（Server-Sent Events）支持

**问题**：nginx 默认开启 `proxy_buffering`，会积攒后端响应直到缓冲区满才发送。SSE 流式推送会被"卡住"。

**解决**：`proxy_buffering off` + `proxy_cache off` + `chunked_transfer_encoding on`

### 8.2 前端代码分割后的缓存

**问题**：Vite 构建产物中 `vendor-*.js` 体积大，但含 content hash。不缓存导致重复传输。

**解决**：`Cache-Control: public, immutable` + `expires 1y`，二次访问命中浏览器缓存，零网络请求。

### 8.3 部署更新即时生效

**问题**：如果 `index.html` 也被缓存，用户可能看到旧版本。

**解决**：`index.html` / `pc.html` 设 `no-cache, must-revalidate`，每次访问都向服务器确认。

### 8.4 超长连接不中断

**问题**：nginx 默认 `proxy_read_timeout=60s`，AI 规划可能超 60s 导致连接断开。

**解决**：`proxy_read_timeout 3600s`（1 小时），留足余量。

---

## 9. 潜在问题与改进方向

### 9.1 ⚠️ HTTPS 缺失（高优先级）

**现状**：`docker-compose.yml` 只暴露 80 端口，无 443。

**影响**：生产环境缺少 TLS 加密，浏览器可能标记为不安全，第三方登录（如有）不可用。

**建议**：
```yaml
# docker-compose.yml 增加
services:
  nginx:
    ports:
      - "80:80"
      - "443:443"         # 新增
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro   # 新增：证书目录
      - ./frontend/dist:/usr/share/nginx/html:ro
```

nginx.conf 增加：
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    # ... 其余配置同上
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;   # HTTP → HTTPS 重定向
}
```

> 证书可通过 Let's Encrypt certbot 或阿里云免费 SSL 获取。

---

### 9.2 ⚠️ API 限流未配置（中优先级）

**现状**：`/api/` 路径无限流，恶意请求可打满 LLM/外部 API 配额。

**建议**：在 `location /api/` 中增加：
```nginx
# 每秒 10 请求 / 突发 20
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    # ... 原有配置
}
```

---

### 9.3 ⚠️ 后端健康检查缺失（低优先级）

**现状**：nginx 不主动检查 backend 是否存活。backend 宕机时 nginx 仍尝试转发直到超时。

**单实例场景影响小**（只有一个 backend，故障转移无意义）。但可加 active health check：
```nginx
location /api/ {
    # 60s 内 3 次失败则标记为 down，30s 后重试
    proxy_next_upstream error timeout http_502 http_503;
    # ... 原有配置
}
```

---

### 9.4 ✅ 已正确处理的要点

| 要点 | 状态 | 说明 |
|------|------|------|
| 后端端口不对外暴露 | ✅ | 使用 `expose` 而非 `ports` |
| SSE 缓冲关闭 | ✅ | `proxy_buffering off` |
| 代理头完整传递 | ✅ | Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto |
| 静态资源缓存分层 | ✅ | HTML 不缓存 / 资源 permanent |
| gzip 文本压缩 | ✅ | level 6，全覆盖 js/css/json/svg/xml/wasm |
| Docker 内网通信 | ✅ | `http://backend:8000` 使用 Compose DNS |
| 静态文件只读挂载 | ✅ | `:ro` 防止容器内篡改 |
| 路由 fallback | ✅ | `try_files` 支持 SPA 路由 |

---

### 9.5 改进优先级总结

```
P0 (生产必须)
  ☐ HTTPS 证书配置 (TLS 1.2+)

P1 (生产推荐)
  ☐ /api/ 限流 (limit_req)
  ☐ 日志格式中增加 $request_time（性能分析用）
  ☐ postgres/redis 端口改为 expose 而非 ports

P2 (优化项)
  ☐ 后端 active health check
  ☐ gzip_static（预压缩 .gz 文件，省 CPU）
  ☐ HTTP/2 push 或 103 Early Hints

P3 (暂不需要)
  ☐ 多 upstream 负载均衡（当前单实例）
  ☐ CDN 回源（本地项目不需要）
```

---

## 10. 附录：验证命令

### 验证 nginx 配置语法

```bash
docker compose exec nginx nginx -t
# 期望: nginx: configuration file ... test is successful
```

### 验证 gzip 压缩

```bash
# 首次请求
curl -H "Accept-Encoding: gzip" -sI http://localhost/ | grep -i content-encoding
# 期望: Content-Encoding: gzip

# 静态资源
curl -H "Accept-Encoding: gzip" -sI http://localhost/assets/main-xxx.js | grep -i content-encoding
# 期望: Content-Encoding: gzip
```

### 验证缓存头

```bash
# HTML — 不应缓存
curl -sI http://localhost/index.html | grep -i cache-control
# 期望: Cache-Control: no-cache, must-revalidate

# 静态资源 — 应永久缓存
curl -sI http://localhost/assets/main-xxx.js | grep -i cache-control
# 期望: Cache-Control: public, immutable

# 对比响应大小
curl -s http://localhost/assets/main-xxx.js | wc -c     # 原始大小
curl -H "Accept-Encoding: gzip" -s http://localhost/assets/main-xxx.js | wc -c  # gzip 大小
# 后者应为前者的 20-40%
```

### 验证 SSE 代理

```bash
# 连接 SSE 端点，观察是否即时返回数据而非等待缓冲满
curl -N http://localhost/api/v1/health
# -N 禁用 curl 自身的缓冲，配合 proxy_buffering off 验证即时性
```

### 验证代理头

```bash
# 在后端服务中添加一个 echo endpoint，或检查日志
docker compose logs backend | grep X-Forwarded-For
```

### 查看 nginx 访问日志

```bash
docker compose exec nginx cat /var/log/nginx/access.log
```

### 重载 nginx（不中断服务）

```bash
docker compose exec nginx nginx -s reload
```

---

> 相关文档：[架构文档](architecture.md) · [部署文档](deployment.md) · [性能优化方案](performance-optimization.md)
