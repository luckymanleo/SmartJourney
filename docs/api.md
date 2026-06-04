# SmartJourney（智旅）API 接口文档

> 版本：v1.0 | 日期：2026-06-05

---

## 1. 概述

- **Base URL**: `/api/v1`
- **认证方式**: Bearer Token (JWT)
- **Content-Type**: `application/json`
- **SSE Content-Type**: `text/event-stream`
- **字符编码**: UTF-8

### 1.1 通用响应格式

**成功响应：**
```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

**错误响应：**
```json
{
  "code": 40001,
  "message": "参数错误",
  "error": {
    "code": "INVALID_PARAM",
    "message": "出发城市不能为空",
    "details": {}
  }
}
```

### 1.2 错误码

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

---

## 2. 认证接口

### 2.1 发送验证码

```
POST /api/v1/auth/send-code
```

**Request:**
```json
{
  "phone": "13800138000"
}
```

**Response:**
```json
{
  "code": 0,
  "message": "验证码已发送",
  "data": {
    "expire_seconds": 300
  }
}
```

**限制：** 同一手机号 60 秒内只能发送一次。

### 2.2 登录

```
POST /api/v1/auth/login
```

**Request:**
```json
{
  "phone": "13800138000",
  "code": "123456"
}
```

**Response:**
```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 604800,
    "user": {
      "id": "uuid",
      "phone": "138****8000",
      "nickname": "旅行者",
      "avatar_url": null,
      "is_new": true
    }
  }
}
```

### 2.3 获取当前用户

```
GET /api/v1/auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "id": "uuid",
    "phone": "138****8000",
    "nickname": "旅行者",
    "avatar_url": "https://...",
    "created_at": "2026-05-31T10:00:00Z"
  }
}
```

### 2.4 更新个人信息

```
PUT /api/v1/auth/profile
Authorization: Bearer <token>
```

**Request:**
```json
{
  "nickname": "新昵称",
  "avatar_url": "https://..."
}
```

---

## 3. 搜索接口

所有搜索接口都需要认证。

### 3.1 机票查询

```
GET /api/v1/search/flights
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| from | string | 是 | 出发城市（中文） |
| to | string | 是 | 到达城市（中文） |
| date | string | 是 | 出发日期 YYYY-MM-DD |
| source | string | 否 | 数据源 fliggy/meituan，默认 fliggy |
| cabin | string | 否 | 舱位 economy/business/first |
| sort_by | string | 否 | price/time，默认 price |
| direct_only | boolean | 否 | 仅直飞 |

**Response:**
```json
{
  "code": 0,
  "data": {
    "source": "fliggy",
    "total": 12,
    "items": [
      {
        "id": "flight_001",
        "flight_no": "MU5678",
        "airline": "东方航空",
        "airline_logo": "https://...",
        "departure": {
          "city": "上海",
          "airport": "浦东国际机场",
          "code": "PVG",
          "terminal": "T1",
          "time": "2026-06-01T08:30:00"
        },
        "arrival": {
          "city": "三亚",
          "airport": "凤凰国际机场",
          "code": "SYX",
          "terminal": "T1",
          "time": "2026-06-01T11:45:00"
        },
        "duration_minutes": 195,
        "stops": 0,
        "cabin": "经济舱",
        "price": 890.00,
        "currency": "CNY",
        "booking_url": "https://fliggy.com/...",
        "refund_policy": "起飞前24小时免费退票"
      }
    ]
  }
}
```

### 3.2 火车票查询

```
GET /api/v1/search/trains
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| from | string | 是 | 出发城市 |
| to | string | 是 | 到达城市 |
| date | string | 是 | 出发日期 |
| source | string | 否 | fliggy/meituan |
| train_type | string | 否 | G/D/Z/T/K，逗号分隔 |
| seat_type | string | 否 | 二等座/一等座/商务座/软卧/硬卧/硬座 |

**Response:**
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "train_001",
        "train_no": "G1234",
        "train_type": "高速动车",
        "departure": {
          "city": "上海",
          "station": "上海虹桥站",
          "time": "2026-06-01T08:00:00"
        },
        "arrival": {
          "city": "北京",
          "station": "北京南站",
          "time": "2026-06-01T12:30:00"
        },
        "duration_minutes": 270,
        "seats": [
          {"type": "二等座", "price": 553.00, "available": true},
          {"type": "一等座", "price": 933.00, "available": true},
          {"type": "商务座", "price": 1748.00, "available": false}
        ],
        "booking_url": "https://fliggy.com/..."
      }
    ]
  }
}
```

### 3.3 酒店搜索

```
GET /api/v1/search/hotels
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| city | string | 是 | 目标城市 |
| keyword | string | 否 | 关键词（区域/品牌/特色） |
| source | string | 否 | fliggy/meituan/hotel_smart |
| check_in | string | 否 | 入住日期 |
| check_out | string | 否 | 离店日期 |
| star_min | integer | 否 | 最低星级 |
| price_min | number | 否 | 最低价格 |
| price_max | number | 否 | 最高价格 |
| brand | string | 否 | 品牌筛选（万豪/希尔顿/...） |
| sort_by | string | 否 | price/rating/distance |

**Response:**
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "hotel_001",
        "name": "三亚亚龙湾万豪度假酒店",
        "brand": "万豪",
        "stars": 5,
        "rating": 4.7,
        "review_count": 3280,
        "price_per_night": 850.00,
        "address": "亚龙湾国家旅游度假区",
        "lat": 18.2205,
        "lng": 109.6345,
        "distance_to_center": "25km",
        "amenities": ["游泳池", "免费WiFi", "儿童乐园"],
        "image_url": "https://...",
        "booking_url": "https://fliggy.com/..."
      }
    ]
  }
}
```

### 3.4 景点查询

```
GET /api/v1/search/pois
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| city | string | 是 | 目标城市 |
| keyword | string | 否 | 关键词 |
| source | string | 否 | fliggy/meituan |

**Response:**
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "poi_001",
        "name": "天涯海角",
        "level": "4A",
        "category": "自然风光",
        "rating": 4.3,
        "ticket_price": 81.00,
        "open_time": "07:30-18:00",
        "recommended_duration": 180,
        "address": "三亚市天涯区",
        "lat": 18.2965,
        "lng": 109.3488,
        "description": "三亚标志性景点...",
        "image_url": "https://...",
        "booking_url": "https://fliggy.com/..."
      }
    ]
  }
}
```

### 3.5 美食查询

```
GET /api/v1/search/foods
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| city | string | 是 | 目标城市 |
| keyword | string | 否 | 关键词（菜系/区域） |
| source | string | 否 | fliggy/meituan |
| price_min | number | 否 | |
| price_max | number | 否 | |

**Response:**
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "food_001",
        "name": "海底捞火锅（南京东路店）",
        "cuisine": "火锅",
        "avg_price": 120,
        "rating": 4.5,
        "address": "上海市黄浦区南京东路...",
        "lat": 31.2378,
        "lng": 121.4820,
        "booking_url": "https://..."
      }
    ]
  }
}
```

### 3.6 市内交通查询

```
GET /api/v1/search/transport
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| from | string | 是 | 出发地点 |
| to | string | 是 | 到达地点 |
| city | string | 否 | 所在城市 |
| source | string | 否 | fliggy |

**Response:**
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "type": "metro",
        "description": "地铁2号线 → 地铁10号线",
        "duration_minutes": 55,
        "price": 5.00,
        "steps": ["浦东国际机场站上车（2号线）", "南京东路站换乘10号线", "..."]
      },
      {
        "type": "taxi",
        "description": "出租车/网约车",
        "duration_minutes": 45,
        "price_estimate": 150.00,
        "distance_km": 45.0
      }
    ]
  }
}
```

---

## 4. 行程管理接口

### 4.1 创建行程

```
POST /api/v1/trips
Authorization: Bearer <token>
```

**Request:**
```json
{
  "title": "三亚亲子游",
  "origin": "上海",
  "destination": "三亚",
  "start_date": "2026-06-01",
  "end_date": "2026-06-05",
  "traveler_count": 3,
  "budget_total": 10000.00
}
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "id": "trip_uuid",
    "title": "三亚亲子游",
    "status": "planning",
    "days": []
  }
}
```

### 4.2 获取行程列表

```
GET /api/v1/trips?status=planning&page=1&page_size=10
Authorization: Bearer <token>
```

### 4.3 获取行程详情

```
GET /api/v1/trips/{trip_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "id": "trip_uuid",
    "title": "三亚亲子游",
    "status": "planning",
    "origin": "上海",
    "destination": "三亚",
    "start_date": "2026-06-01",
    "end_date": "2026-06-05",
    "traveler_count": 3,
    "budget_total": 10000.00,
    "budget_spent": 3200.00,
    "days": [
      {
        "id": "day_uuid",
        "day_number": 1,
        "date": "2026-06-01",
        "items": [
          {
            "id": "item_uuid",
            "type": "flight",
            "title": "MU5678 上海 → 三亚",
            "start_time": "08:30",
            "end_time": "11:45",
            "price": 890.00,
            "booking_url": "https://...",
            "status": "planned",
            "extra_data": {
              "flight_no": "MU5678",
              "airline": "东方航空",
              "departure_airport": "浦东国际机场",
              "arrival_airport": "凤凰国际机场"
            }
          },
          {
            "id": "item_uuid_2",
            "type": "hotel",
            "title": "三亚亚龙湾万豪度假酒店",
            "start_time": "14:00",
            "end_time": null,
            "price": 850.00,
            "booking_url": "https://...",
            "status": "planned"
          }
        ]
      }
    ]
  }
}
```

### 4.4 更新行程

```
PUT /api/v1/trips/{trip_id}
Authorization: Bearer <token>
```

### 4.5 删除行程

```
DELETE /api/v1/trips/{trip_id}
Authorization: Bearer <token>
```

### 4.6 添加行程项

```
POST /api/v1/trips/{trip_id}/items
Authorization: Bearer <token>
```

**Request:**
```json
{
  "day_id": "day_uuid",
  "type": "flight",
  "title": "MU5678 上海 → 三亚",
  "start_time": "08:30",
  "end_time": "11:45",
  "price": 890.00,
  "booking_url": "https://...",
  "extra_data": {
    "flight_no": "MU5678",
    "airline": "东方航空"
  }
}
```

### 4.7 删除行程项

```
DELETE /api/v1/trips/{trip_id}/items/{item_id}
Authorization: Bearer <token>
```

### 4.8 获取预算

```
GET /api/v1/trips/{trip_id}/budget
Authorization: Bearer <token>
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "total_estimated": 10000.00,
    "total_actual": 3200.00,
    "categories": [
      {"category": "transport", "estimated": 2000.00, "actual": 1780.00},
      {"category": "lodging", "estimated": 4000.00, "actual": 850.00},
      {"category": "food", "estimated": 2000.00, "actual": 0},
      {"category": "tickets", "estimated": 1500.00, "actual": 0},
      {"category": "other", "estimated": 500.00, "actual": 0}
    ]
  }
}
```

---

## 5. AI 智能规划接口

### 5.1 生成行程规划（SSE 流式）

```
POST /api/v1/plan/generate
Authorization: Bearer <token>
Content-Type: application/json
Accept: text/event-stream
```

**Request:**
```json
{
  "query": "带家人三亚5天亲子游，预算1万，想去海边和热带雨林",
  "origin": "上海",
  "destination": "三亚",
  "start_date": "2026-06-01",
  "end_date": "2026-06-05",
  "traveler_count": 3,
  "budget_total": 10000.00,
  "use_weather": true,
  "route_count": 1,
  "route_strategy": -1,
  "preferences": {
    "flight_cabin": "economy",
    "hotel_stars": 4,
    "pace": "relaxed",
    "interests": ["beach", "nature", "family"]
  },
  "save_as_trip": true
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 自然语言出行需求 |
| origin | string | 是 | 出发地城市 |
| destination | string | 否 | 目的地（可从query解析） |
| start_date | string | 否 | 出发日期 YYYY-MM-DD |
| end_date | string | 否 | 返回日期 YYYY-MM-DD |
| traveler_count | int | 否 | 出行人数，默认1 |
| budget_total | number | 否 | 总预算（元） |
| use_weather | boolean | 否 | 是否参考天气，默认true |
| route_count | int | 否 | 生成路线数量（1-3），默认1 |
| route_strategy | int | 否 | 路线策略：-1=全部，0=经济，1=舒适，2=最快 |
| preferences | object | 否 | 出行偏好 |
| save_as_trip | boolean | 否 | 是否保存为行程，默认true |

**SSE 事件流：**

```
event: step
data: {"step": "analyzing", "text": "正在分析出行需求..."}

event: step
data: {"step": "searching", "text": "正在搜索上海到三亚的航班..."}

event: tool_call
data: {"name": "search_flight", "args": {"from": "上海", "to": "三亚", "date": "2026-06-01"}}

event: tool_result
data: {"name": "search_flight", "summary": "找到 12 个航班，最低 ¥580"}

event: step
data: {"step": "searching", "text": "正在搜索三亚亲子酒店..."}

event: tool_call
data: {"name": "search_hotel", "args": {"city": "三亚", "keyword": "亲子 4星"}}

event: tool_result
data: {"name": "search_hotel", "summary": "找到 8 家酒店"}

event: step
data: {"step": "generating", "text": "正在生成行程方案..."}

event: chunk
data: {"text": "为您规划的三亚5天亲子游方案如下：\n\n**Day 1 - 抵达三亚**\n..."}

event: trip_data
data: {"trip": {...}}

event: done
data: {"trip_id": "uuid", "elapsed_seconds": 12.5}
```

### 5.2 优化已有行程

```
POST /api/v1/plan/optimize
Authorization: Bearer <token>
```

**Request:**
```json
{
  "trip_id": "trip_uuid",
  "instruction": "把第三天的行程调整得更轻松一些，减少一个景点"
}
```

**Response:** SSE 流式（同 generate）

---

## 6. 辅助接口

### 6.1 天气查询

```
GET /api/v1/info/weather?city=三亚&days=7
Authorization: Bearer <token>
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "city": "三亚",
    "current": {
      "temp": 32,
      "weather": "晴",
      "humidity": 75,
      "wind": "东南风 3级"
    },
    "forecast": [
      {"date": "2026-06-01", "weather": "晴", "temp_high": 33, "temp_low": 26},
      {"date": "2026-06-02", "weather": "多云", "temp_high": 32, "temp_low": 25}
    ]
  }
}
```

### 6.2 目的地信息

```
GET /api/v1/info/destination/三亚
Authorization: Bearer <token>
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "name": "三亚",
    "province": "海南",
    "description": "三亚位于海南岛最南端...",
    "best_season": "11月-次年3月",
    "crowd_level": "medium",
    "tips": ["注意防晒", "海鲜市场可砍价"],
    "activities": ["三亚国际音乐节 (3月)", "海天盛筵 (12月)"],
    "visa_info": null,
    "currency": "CNY",
    "language": "中文"
  }
}
```

### 6.3 热门目的地

```
GET /api/v1/info/popular?limit=6
```
无需认证，公开接口。

**Response:**
```json
{
  "code": 0,
  "data": {
    "destinations": [
      {
        "name": "三亚",
        "image": "🏖️",
        "description": "热带海滨度假天堂，拥有中国最美的海滩",
        "best_season": "11月-次年3月",
        "tags": ["海滩", "亲子", "度假", "热带雨林"],
        "lat": 18.2528,
        "lng": 109.5120
      },
      {
        "name": "成都",
        "image": "🐼",
        "description": "天府之国，美食与文化的交汇之地",
        "best_season": "3月-6月、9月-11月",
        "tags": ["美食", "熊猫", "文化", "休闲"],
        "lat": 30.5728,
        "lng": 104.0668
      }
    ],
    "total": 12
  }
}
```

### 6.4 行政区划查询

```
GET /api/v1/info/locations?pid=0
```
无需认证，公开接口。省市区三级联动查询。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pid | int | 否 | 父级ID，0=省/直辖市，默认0 |

**Response (pid=0):**
```json
{
  "code": 0,
  "data": [
    {"id": 110000, "name": "北京", "pid": 0, "level": "province"},
    {"id": 310000, "name": "上海", "pid": 0, "level": "province"},
    {"id": 440000, "name": "广东", "pid": 0, "level": "province"}
  ]
}
```

**Response (pid=440000 广东省):**
```json
{
  "code": 0,
  "data": [
    {"id": 440100, "name": "广州", "pid": 440000, "level": "city"},
    {"id": 440300, "name": "深圳", "pid": 440000, "level": "city"},
    {"id": 440400, "name": "珠海", "pid": 440000, "level": "city"}
  ]
}
```

### 6.5 位置搜索

```
GET /api/v1/info/locations/search?keyword=三亚&limit=20
```
无需认证。支持拼音、首字母、汉字搜索。

### 6.6 用户偏好

```
GET /api/v1/user/preferences
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "data": {
    "flight": {
      "cabin": "economy",
      "seat": "window",
      "max_transfers": 1
    },
    "train": {
      "type_preference": ["G", "D"],
      "seat": "二等座",
      "quiet_cabin": false
    },
    "hotel": {
      "min_stars": 4,
      "max_price_per_night": 800,
      "brands": []
    },
    "food": {
      "cuisines": ["川菜", "火锅", "海鲜"],
      "max_price_per_person": 150
    },
    "travel_pace": "relaxed",
    "interests": ["beach", "nature", "history"]
  }
}
```

```
PUT /api/v1/user/preferences
Authorization: Bearer <token>
```

---

## 7. 接口汇总

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/auth/send-code` | 否 | 发送验证码 |
| POST | `/auth/login` | 否 | 登录 |
| GET | `/auth/me` | 是 | 当前用户 |
| PUT | `/auth/profile` | 是 | 更新个人信息 |
| GET | `/search/flights` | 是 | 机票查询 |
| GET | `/search/trains` | 是 | 火车票查询 |
| GET | `/search/hotels` | 是 | 酒店搜索 |
| GET | `/search/pois` | 是 | 景点查询 |
| GET | `/search/foods` | 是 | 美食查询 |
| GET | `/search/transport` | 是 | 市内交通 |
| POST | `/trips` | 是 | 创建行程 |
| GET | `/trips` | 是 | 行程列表 |
| GET | `/trips/{id}` | 是 | 行程详情 |
| PUT | `/trips/{id}` | 是 | 更新行程 |
| DELETE | `/trips/{id}` | 是 | 删除行程 |
| POST | `/trips/{id}/items` | 是 | 添加行程项 |
| DELETE | `/trips/{id}/items/{iid}` | 是 | 删除行程项 |
| GET | `/trips/{id}/budget` | 是 | 预算查询 |
| POST | `/plan/generate` | 是 | AI 生成行程（SSE） |
| POST | `/plan/optimize` | 是 | AI 优化行程（SSE） |
| GET | `/info/weather` | 是 | 天气查询 |
| GET | `/info/popular` | 否 | 热门目的地 |
| GET | `/info/destination/{city}` | 是 | 目的地信息 |
| GET | `/info/locations` | 否 | 行政区划查询 |
| GET | `/info/locations/search` | 否 | 位置搜索 |
| GET | `/user/preferences` | 是 | 获取偏好 |
| PUT | `/user/preferences` | 是 | 更新偏好 |
| | | | |
| **Phase 2 — 混合交通 / 预警 / 票夹** | | | |
| GET | `/multimodal/compare` | 是 | 飞机vs高铁vs联程智能比价 |
| GET | `/alerts/{trip_id}` | 是 | 行程预警（天气/延误） |
| GET | `/tickets/{trip_id}` | 是 | 统一票夹 |
| GET | `/itinerary/{trip_id}` | 是 | 行程单摘要 |
| GET | `/search/bus` | 是 | 长途大巴查询 |
| GET | `/search/car-rental` | 是 | 租车查询 |
| GET | `/search/taxi` | 是 | 打车预估 |
| | | | |
| **Phase 3 — 多人协同 / 分账 / 分享** | | | |
| POST | `/trips/{id}/collaboration` | 是 | 创建协作组 |
| POST | `/collaboration/join` | 是 | 邀请码加入行程 |
| GET | `/trips/{id}/members` | 是 | 成员列表 |
| PUT | `/trips/{id}/members/{uid}/role` | 是 | 修改成员角色 |
| POST | `/trips/{id}/leave` | 是 | 退出行程 |
| DELETE | `/trips/{id}/members/{uid}` | 是 | 移除成员 |
| GET | `/trips/{id}/invite-code` | 是 | 获取邀请码 |
| POST | `/trips/{id}/invite-code/refresh` | 是 | 刷新邀请码 |
| PUT | `/trips/{id}/location` | 是 | 更新位置 |
| GET | `/trips/{id}/locations` | 是 | 成员位置 |
| PUT | `/trips/{id}/location-sharing` | 是 | 开关位置共享 |
| POST | `/trips/{id}/expenses` | 是 | 添加消费记录 |
| GET | `/trips/{id}/expenses` | 是 | 消费记录列表 |
| DELETE | `/trips/{id}/expenses/{eid}` | 是 | 删除消费记录 |
| GET | `/trips/{id}/settlement` | 是 | 账单结算汇总 |
| POST | `/trips/{id}/share` | 是 | 生成分享链接 |
| GET | `/trips/{id}/poster` | 是 | 行程海报数据 |
| GET | `/trips/{id}/travelogue` | 是 | 生成游记 |
| GET | `/services/luggage` | 是 | 行李寄存查询 |
| GET | `/services/insurance` | 是 | 旅行保险推荐 |
| GET | `/services/airport-transfer` | 是 | 接送机服务 |
| | | | |
| **Phase 4 — 偏好学习 / 异常改签 / 无障碍 / 多语言** | | | |
| GET | `/preferences/learn` | 是 | 偏好学习 |
| GET | `/preferences/feed` | 是 | 个性化推荐流 |
| GET | `/disruption/alternatives` | 是 | 异常改签替代方案 |
| GET | `/accessibility/info` | 是 | 无障碍出行信息 |
| GET | `/border/info` | 是 | 出入境信息 |
| GET | `/translate/phrases` | 是 | 常用语翻译卡片 |
| GET | `/transit/metro` | 是 | 地铁线路查询 |
| GET | `/transit/bus` | 是 | 公交线路查询 |
| GET | `/transit/bike` | 是 | 共享单车信息 |
| GET | `/transit/walking` | 是 | 步行导航 |
| GET | `/ferry/search` | 是 | 渡轮/游船查询 |
| | | | |
| **Phase 5 — 管理后台 / 钱包** | | | |
| GET | `/admin/stats` | 是 | 平台概览统计 |
| GET | `/admin/trips` | 是 | 全部行程管理 |
| GET | `/admin/users` | 是 | 全部用户管理 |
| GET | `/wallet/balance` | 是 | 钱包余额 |
| POST | `/wallet/charge` | 是 | 钱包充值 |
| POST | `/wallet/pay` | 是 | 钱包支付 |
| GET | `/wallet/transactions` | 是 | 交易记录 |
