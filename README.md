# SmartJourney（智旅）

全栈旅行规划平台 — AI 驱动的智能行程生成，支持移动端与 PC Web 双版本。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 18 + TypeScript + Vite + TailwindCSS + Zustand + React Router |
| 后端 | FastAPI (Python 3.11) + SQLAlchemy 2.0 async + PostgreSQL + Redis |
| AI | DeepSeek / OpenAI-compatible LLM + MCP 网关 |
| 短信 | 阿里云 Dypnsapi（号码认证），支持 mock 模式开发 |
| 数据 | FliggyTravel MCP（飞猪）、高德天气、eduosi/district |

## 核心功能

- **手机号验证码登录/注册**：短信验证码 + mock 模式（开发用固定验证码），支持 PC/手机独立限流与独立登出
- **多类型搜索**：机票、火车票、酒店、景点、美食、市内交通
- **AI 智能规划**：自然语言输入自动解析出发地/目的地/天数/人数/预算，LLM + MCP 生成完整行程，SSE 流式返回
- **双端支持**：移动端 + PC Web（侧边栏布局），Vite 多页面构建，平台隔离存储
- **用户系统**：昵称修改（长度限制 + 敏感词过滤，配置文件管理），默认昵称格式
- **行程管理**：CRUD + 时间线视图 + 预算概览 + 天气集成
- **偏好设置**：天气参考开关、路线策略（智能平衡/经济实惠/舒适优先/最快到达）
- **热门目的地**：点击直达规划页，自动填充目的地

## 项目结构

```
SmartJourney/
├── frontend/          # React 前端（mobile + PC）
│   ├── src/pages/     # 移动端页面
│   ├── src/pc/        # PC Web 页面
│   ├── src/stores/    # Zustand 状态管理（共享）
│   └── src/components/# 共享 UI 组件
├── backend/           # FastAPI 后端
│   ├── app/
│   │   ├── api/       # 路由模块
│   │   ├── services/  # 服务模块
│   │   └── models/    # 数据库表
│   ├── .env.example   # 环境变量模板
│   └── config.json    # 外部化配置
├── docs/              # 技术文档
├── docker-compose.yml # PostgreSQL + Redis + Nginx
└── nginx.conf         # Nginx 配置
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
# 生产环境可增加 workers 提升并发: uvicorn ... --workers 4

# 前端
cd frontend && npm install && npm run dev
# 移动端: http://localhost:5173/
# PC 端:  http://localhost:5173/pc.html
```

## 环境变量

参考 `backend/.env.example`，关键配置项：

| 变量 | 说明 | 示例 |
|------|------|------|
| DATABASE_URL | PostgreSQL 连接串 | `postgresql+asyncpg://user:pass@host:5432/db` |
| REDIS_URL | Redis 连接串 | `redis://host:6379/0` |
| REDIS_USERNAME | Redis 用户名（可选） | 如 `default` |
| REDIS_PASSWORD | Redis 密码（可选） | 生产环境必填 |
| SECRET_KEY | JWT 签名密钥 | 随机字符串（≥32字符） |
| LLM_API_KEY | LLM API 密钥 | `sk-xxxx` |
| LLM_BASE_URL | LLM API 地址 | `https://api.deepseek.com/v1` |
| LLM_MODEL | LLM 模型名称 | `deepseek-v4-pro` |
| GAODE_API_KEY | 高德地图 API Key | 从高德开放平台获取 |
| SMS_PROVIDER | 短信服务 | `mock`（开发）/ `aliyun`（生产） |
| SMS_ACCESS_KEY_ID | 短信服务 AK | 从云厂商控制台获取 |
| SMS_ACCESS_KEY_SECRET | 短信服务 SK | 从云厂商控制台获取 |
| SMS_SIGN_NAME | 短信签名 | 运营商审核通过的签名 |
| SMS_TEMPLATE_CODE | 短信模板 | 运营商审核通过的模板码 |
| DB_POOL_SIZE | 连接池大小 | `10`（可选，有默认值） |
| DB_MAX_OVERFLOW | 最大溢出连接 | `20`（可选，有默认值） |
| DB_POOL_RECYCLE | 连接回收秒数 | `1800`（可选，有默认值） |

## 性能优化（2026-06）

已实施的优化项：

| 优化项 | 说明 | 效果 |
|--------|------|------|
| nginx gzip + 缓存 | JS/CSS 压缩 + 带 hash 文件永久缓存 | 前端首屏快 60-80%，二次访问零请求 |
| PostgreSQL 连接池 | pool_size / max_overflow / pool_pre_ping | 并发吞吐 2-3x |
| PostgreSQL 服务端 | shared_buffers / work_mem / random_page_cost | 查询快 20-30% |
| 数据库索引 | expiry 查询部分索引 | 定时任务零扫描 |
| MCP 并发优化 | Semaphore 3→6 + 超时 90→60s | 搜索阶段快 ~50% |
| Redis 持久化 | AOF + maxmemory | 重启不丢缓存 |
| Vite 代码分割 | vendor chunk 按框架/工具分离 | 首屏 JS 减 60%+ |

详见 [性能优化方案](docs/performance-optimization.md)。

## 短信配置

- **mock 模式**：开发环境使用，验证码固定，不限频率
- **aliyun 模式**：Dypnsapi SendSmsVerifyCode + CheckSmsVerifyCode 校验
- **限流**：PC/手机各自独立限制，Redis key 按平台隔离

## 敏感词配置

编辑 `backend/sensitive_words.json`（JSON 数组），重启或下次请求自动生效。

## 文档

- [架构文档](docs/architecture.md)
- [API 接口文档](docs/api.md)
- [需求文档](docs/requirements.md)
- [路线图](docs/roadmap.md)
- [部署指南](docs/deployment.md)
- [性能优化方案](docs/performance-optimization.md)
