# SmartJourney（智旅）API 接口文档

> 版本：v2.1 | 日期：2026-06-12 | 7 个路由模块，40+ 端点

---

## 1. 概述

- **Base URL**: `/api/v1`
- **认证方式**: Bearer Token (JWT)，Header: `Authorization: Bearer <token>`
- **Content-Type**: `application/json`
- **SSE Content-Type**: `text/event-stream`（仅规划接口）
- **字符编码**: UTF-8

### 1.1 通用响应格式

**成功：**
```json
{ "code": 0, "message": "success", "data": {} }
```

**错误：**
```json
{
  "code": 40001,
  "message": "参数错误",
  "error": { "code": "INVALID_PARAM", "message": "出发城市不能为空" }
}
```

### 1.2 路由模块

| 前缀 | 模块 | 用途 |
|------|------|------|
| `/api/v1/auth` | auth.py | 短信登录认证 |
| `/api/v1/user` | user.py | 用户偏好 |
| `/api/v1/search` | search.py | 6 类搜索（机票/火车/酒店/景点/美食/交通） |
| `/api/v1/trips` | trips.py | 行程 CRUD + 行程项管理 |
| `/api/v1/plan` | plan.py | AI 智能规划 SSE |
| `/api/v1/info` | info.py | 天气/城市/热门目的地 |
| `/api/v1/map` | map_routes.py | 地图（地理编码/POI/路径/行程聚合） |

---

## 2. 认证接口 — `/api/v1/auth`

### 2.1 发送验证码

```
POST /api/v1/auth/send-code
```

**Request:** `{ "phone": "13800138000" }`

**Response:** `{ "code": 0, "message": "验证码已发送", "data": { "expire_seconds": 300 } }`

> 同一手机号 60 秒内只能发送一次。Mock 模式下任意 6 位验证码均可通过。

### 2.2 登录

```
POST /api/v1/auth/login
```

**Request:** `{ "phone": "13800138000", "code": "123456" }`

**Response:**
```json
{
  "code": 0,
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 604800,
    "user": { "id": "uuid", "phone": "138****8000", "nickname": "旅行者", "is_new": true }
  }
}
```

### 2.3 获取当前用户

```
GET /api/v1/auth/me
Authorization: Bearer <token>
```

### 2.4 更新个人信息

```
PUT /api/v1/auth/profile
Authorization: Bearer <token>
```

**Request:** `{ "nickname": "新昵称", "avatar_url": "https://..." }`

---

## 3. 用户偏好 — `/api/v1/user`

### 3.1 获取偏好

```
GET /api/v1/user/preferences
Authorization: Bearer <token>
```

**Response:** `{ "code": 0, "data": { "use_weather": true, "route_strategy": -1, "special_notes": "" } }`

### 3.2 保存偏好

```
PUT /api/v1/user/preferences
Authorization: Bearer <token>
```

**Request:** `{ "use_weather": true, "route_strategy": 0, "special_notes": "素食" }`

| 字段 | 类型 | 说明 |
|------|------|------|
| use_weather | boolean | 是否参考天气因素 |
| route_strategy | integer | -1=智能平衡, 0=经济实惠, 1=舒适优先, 2=最快到达 |
| special_notes | string | 特殊说明（过敏、素食等） |

---

## 4. 搜索接口 — `/api/v1/search`

所有搜索接口需认证。

### 4.1 机票 — `GET /search/flights`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| from | string | 是 | 出发城市 |
| to | string | 是 | 到达城市 |
| date | string | 是 | 出发日期 YYYY-MM-DD |
| source | string | 否 | fliggy/meituan，默认 fliggy |
| cabin | string | 否 | economy/business/first |
| sort_by | string | 否 | price/time |

### 4.2 火车票 — `GET /search/trains`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| from | string | 是 | 出发城市 |
| to | string | 是 | 到达城市 |
| date | string | 是 | 出发日期 |
| source | string | 否 | fliggy/meituan |
| train_type | string | 否 | G/D/Z/T/K |
| seat_type | string | 否 | 二等座/一等座/商务座/软卧/硬卧/硬座 |

### 4.3 酒店 — `GET /search/hotels`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| city | string | 是 | 目标城市 |
| keyword | string | 否 | 区域/品牌关键词 |
| source | string | 否 | fliggy/meituan/hotel_smart |
| check_in | string | 否 | 入住日期 |
| check_out | string | 否 | 离店日期 |
| star_min | integer | 否 | 最低星级 |
| price_min | number | 否 | 最低价格 |
| price_max | number | 否 | 最高价格 |
| sort_by | string | 否 | price/rating/distance |

### 4.4 景点 — `GET /search/pois`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| city | string | 是 | 目标城市 |
| keyword | string | 否 | 关键词 |
| source | string | 否 | fliggy/meituan |

### 4.5 美食 — `GET /search/foods`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| city | string | 是 | 目标城市 |
| keyword | string | 否 | 菜系/区域关键词 |
| source | string | 否 | fliggy/meituan |

### 4.6 市内交通 — `GET /search/transport`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| from | string | 是 | 出发地点 |
| to | string | 是 | 到达地点 |
| city | string | 否 | 所在城市 |
| source | string | 否 | fliggy |

---

## 5. 行程管理 — `/api/v1/trips`

全部需认证。

### 5.1 创建行程

```
POST /api/v1/trips
Authorization: Bearer <token>
```

**Request:** `{ "title": "...", "origin": "深圳", "destination": "杭州", "start_date": "2026-06-13", "end_date": "2026-06-15", "traveler_count": 2, "budget_total": 3000 }`

### 5.2 行程列表

```
GET /api/v1/trips?status=planning&page=1&page_size=10
```

### 5.3 行程详情

```
GET /api/v1/trips/{trip_id}
```

返回含 `days[].items[]` 的完整行程结构，以及 `summary`、`tips`、`weather_info`、`special_notes` 等 AI 生成字段。

### 5.4 更新行程

```
PUT /api/v1/trips/{trip_id}
```

### 5.5 删除行程

```
DELETE /api/v1/trips/{trip_id}
```

### 5.6 添加行程项

```
POST /api/v1/trips/{trip_id}/items
```

**Request:** `{ "day_id": "...", "type": "train", "title": "D2325 杭州北→深圳北", "start_time": "08:24", "end_time": "15:38", "price": 320, "booking_url": "https://..." }`

### 5.7 删除行程项

```
DELETE /api/v1/trips/{trip_id}/items/{item_id}
```

### 5.8 预算概览

```
GET /api/v1/trips/{trip_id}/budget
```

**Response:** `{ "total_estimated": 8500, "total_actual": 0, "categories": [{ "category": "transport", "estimated": 3200, ... }, ...] }`

---

## 6. AI 智能规划 — `/api/v1/plan`

全部需认证。

### 6.1 生成行程（SSE 流式）

```
POST /api/v1/plan/generate
Authorization: Bearer <token>
Accept: text/event-stream
```

**Request:**
```json
{
  "query": "深圳出发杭州3天2人，预算3000",
  "origin": "深圳",
  "destination": "杭州",
  "start_date": "2026-06-13",
  "end_date": "2026-06-15",
  "traveler_count": 2,
  "budget_total": 3000,
  "save_as_trip": true,
  "use_weather": true,
  "route_strategy": -1,
  "special_notes": "素食"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 自然语言需求描述 |
| origin | string | 是 | 出发城市 |
| destination | string | 是 | 目的城市 |
| start_date | string | 是 | 出发日期 |
| end_date | string | 是 | 返程日期 |
| traveler_count | integer | 是 | 出行人数 |
| budget_total | number | 是 | 总预算 |
| save_as_trip | boolean | 否 | 规划完成后保存为行程（默认 true） |
| use_weather | boolean | 否 | 参考天气（默认 true） |
| route_strategy | integer | 否 | 路线策略（-1=智能, 0=经济, 1=舒适, 2=快速） |
| route_count | integer | 否 | 生成路线数（默认 1） |
| special_notes | string | 否 | 特殊说明 |

**SSE 事件流：**

| 事件 | 说明 |
|------|------|
| `step` | 进度步骤 |
| `tool_call` | MCP 工具调用中 |
| `tool_result` | MCP 工具返回 |
| `trip_data` | 行程 JSON 生成完成 |
| `error` | 异常信息 |
| `done` | 流结束 |

**取消：** 客户端断开 SSE 连接时后端自动终止 MCP/LLM 任务。

### 6.2 优化已有行程

```
POST /api/v1/plan/optimize
Authorization: Bearer <token>
```

基于已有行程重新生成优化版本。参数同 generate，额外需传 `trip_id`。

---

## 7. 辅助信息 — `/api/v1/info`

### 7.1 天气

```
GET /api/v1/info/weather?city=杭州&days=7
Authorization: Bearer <token>
```

### 7.2 热门目的地

```
GET /api/v1/info/popular?limit=6
```
公开接口，无需认证。

### 7.3 目的地综合信息

```
GET /api/v1/info/destination/{city}
Authorization: Bearer <token>
```

返回天气 + 描述 + 最佳季节 + 标签等综合信息。

### 7.4 城市列表/搜索

```
GET /api/v1/info/cities?keyword=深圳
```

支持拼音、首字母、汉字搜索。无 keyword 时返回省份列表。

### 7.5 省市区级联

```
GET /api/v1/info/locations?pid=0
```
pid=0 返回省/直辖市列表，传入上级 ID 返回下级区划。

### 7.6 位置搜索

```
GET /api/v1/info/locations/search?keyword=南山&limit=20
```

拼音/汉字搜索城市和区县。

---

## 8. 地图接口 — `/api/v1/map`

全部需认证。

### 8.1 地图配置

```
GET /api/v1/map/config
```
返回高德 JS API Key。

### 8.2 行程地图聚合

```
GET /api/v1/map/trip/{trip_id}
```
返回所有天的 POI 列表（含坐标、day_number、item_index），用于地图渲染。

### 8.3 单天地图数据

```
GET /api/v1/map/trip/{trip_id}/day/{day_number}
```
返回单天 POI + 坐标。

### 8.4 地理编码（单个）

```
GET /api/v1/map/geocode?address=深圳北站
```
返回 `{ lng, lat, formatted_address }`。

### 8.5 批量地理编码

```
POST /api/v1/map/geocode/batch
```
**Request:** `{ "addresses": ["深圳北站", "杭州北站"] }`

### 8.6 逆地理编码

```
GET /api/v1/map/regeocode?lng=114.0&lat=22.5
```

### 8.7 POI 文本搜索

```
GET /api/v1/map/poi/text?keywords=酒店&city=深圳&offset=10
```

### 8.8 POI 周边搜索

```
GET /api/v1/map/poi/around?lng=114.0&lat=22.5&keywords=美食&radius=3000
```

### 8.9 POI 详情

```
GET /api/v1/map/poi/{poi_id}
```
返回含 `photos` 照片列表的 POI 详情。

### 8.10 路径规划

```
GET /api/v1/map/direction?from_lng=114.0&from_lat=22.5&to_lng=114.1&to_lat=22.6&mode=walking
```
mode: walking/driving/transit。

### 8.11 距离测量

```
GET /api/v1/map/distance?from_lng=114.0&from_lat=22.5&to_lng=114.1&to_lat=22.6
```
返回直线距离（米）。

---

## 9. 健康检查

```
GET /api/v1/health
```
公开接口，返回 `{ "status": "ok", "version": "..." }`。

---

## 10. 错误码

| HTTP | code | 说明 |
|------|------|------|
| 400 | 40001 | 参数错误 |
| 401 | 40101 | 未登录 |
| 401 | 40102 | Token 过期 |
| 403 | 40301 | 无权限 |
| 404 | 40401 | 资源不存在 |
| 429 | 42901 | 请求频率限制 |
| 500 | 50001 | 服务器内部错误 |
| 502 | 50201 | MCP 数据源不可用 |
| 503 | 50301 | 服务维护中 |
