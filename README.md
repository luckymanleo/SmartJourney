# SmartJourney（智旅）

全栈旅行规划平台 — AI 驱动的智能行程生成，支持移动端与 PC Web 双版本。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 18 + TypeScript + Vite + TailwindCSS + Zustand + React Router |
| 后端 | FastAPI (Python 3.11) + SQLAlchemy 2.0 async + PostgreSQL + Redis |
| AI | DeepSeek / OpenAI-compatible LLM + MCP 网关 |
| 短信 | 阿里云 Dypnsapi（号码认证），支持 mock 模式开发 |
| 数据 | FliggyTravel MCP（飞猪）、Meituan MCP（美团）、高德天气、eduosi/district |

## 核心功能

- **手机号验证码登录/注册**：阿里云短信验证码 + mock 模式（开发用固定 9999），支持 PC/手机独立限流与独立登出
- **多类型搜索**：机票、火车票、酒店、景点、美食、市内交通
- **AI 智能规划**：自然语言输入（如"北京到三亚5天亲子游 预算6000"）自动解析出发地/目的地/天数/人数/预算，LLM + MCP 生成完整行程，SSE 流式返回
- **双端支持**：移动端 + PC Web（侧边栏布局），Vite 多页面构建（appType: mpa），平台隔离存储
- **用户系统**：昵称修改（2-20 字符限制 + 敏感词过滤，配置文件管理），默认昵称 `旅行者_6578`（手机后四位）
- **行程管理**：CRUD + 时间线视图 + 预算概览 + 天气集成
- **偏好设置**：天气参考开关、路线策略（智能平衡/经济实惠/舒适优先/最快到达）
- **热门目的地**：点击直达规划页，自动填充目的地
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
│   ├── app/
│   │   ├── api/       # 路由模块
│   │   ├── services/  # 服务模块（含 sms_service.py）
│   │   └── models/    # 数据库表
│   ├── sensitive_words.json  # 敏感词配置
│   └── .env           # 环境变量（含短信配置）
├── docs/              # 技术文档
└── docker-compose.yml # PostgreSQL + Redis + Nginx
```

## 快速启动

```bash
# 数据库
docker compose up -d postgres redis

# 后端
cd backend && source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend && npm install && npm run dev
# 移动端: http://localhost:5173/
# PC 端:  http://localhost:5173/pc.html
```

## 短信配置

```bash
# .env 中配置
SMS_PROVIDER=mock      # mock（开发）/ aliyun（生产）
SMS_ACCESS_KEY_ID=...  # 阿里云 AccessKey
SMS_ACCESS_KEY_SECRET=...
SMS_SIGN_NAME=速通互联验证码
SMS_TEMPLATE_CODE=100001
SMS_REGION=cn-shenzhen
```

- **mock 模式**：验证码固定 `9999`，不限频率，输出到日志
- **aliyun 模式**：Dypnsapi SendSmsVerifyCode（##code## 自动生成）+ CheckSmsVerifyCode 校验
- **限流**：PC/手机各自独立 60 秒限制，Redis key `sms_rate:{platform}:{phone}`

## 敏感词配置

编辑 `backend/sensitive_words.json`（JSON 数组），重启或下次请求自动生效：

```json
["习近平", "法轮功", "台独", "藏独", "港独", ...]
```

## 文档

- [架构文档](docs/architecture.md)
- [API 接口文档](docs/api.md)
- [需求文档](docs/requirements.md)
- [路线图](docs/roadmap.md)
- [部署指南](docs/deployment.md)
