# SmartJourney（智程）工具集成文档

> 版本：v1.0 | 日期：2026-05-31

---

## 1. 概述

SmartJourney 通过 Model Context Protocol (MCP) 集成第三方旅行数据源。主要使用 ModelScope 托管的 HTTP MCP Server，通过 `remote_mcp.py` 以 JSON-RPC over HTTP 方式通信。

---

## 2. MCP 工具总览

### 2.1 核心工具包（mako2026 系列）

| 工具包 | 版本 | 数据源 | 工具 |
|--------|------|--------|------|
| `mcp-fliggy-travel` | 0.1.1 | 飞猪旅行 | travel_plan, search_train, search_flight, search_hotel, search_poi, search_food, search_transport |
| `mcp-meituan-travel` | 1.0.1 | 美团旅行 | meituan_travel_query |
| `mcp-hotel-smart` | 2.0.3 | 飞猪旅行 | search_hotels, search_marriott_hotels |
| `mcp-domestic-flight` | 1.0.1 | 飞猪旅行 | search_flight |
| `mcp-travel-smart-plan` | 2.1.0 | 飞猪旅行 | (智能规划) |

### 2.2 工具间关系

```
mcp-fliggy-travel (一站式)
  ├── travel_plan     ← AI 行程规划入口
  ├── search_flight   ← 机票查询（与 mcp-domestic-flight 互补）
  ├── search_train    ← 火车票查询
  ├── search_hotel    ← 酒店搜索（与 mcp-hotel-smart 互补）
  ├── search_poi      ← 景点门票
  ├── search_food     ← 美食推荐
  └── search_transport ← 市内交通

mcp-hotel-smart (酒店专精)
  ├── search_hotels         ← 通用酒店搜索（品牌筛选更丰富）
  └── search_marriott_hotels ← 万豪品牌专区

mcp-domestic-flight (航班专精)
  └── search_flight  ← 航班查询（舱位/中转筛选更细）

mcp-meituan-travel (美团数据源)
  └── meituan_travel_query ← 综合查询（酒店+机票+火车票+景点）

mcp-travel-smart-plan (规划专精)
  └── (智能规划能力)
```

---

## 3. 工具详细说明

### 3.1 mcp-fliggy-travel（主要数据源）

**安装：** `pip install mcp-fliggy-travel`

**配置：**
```bash
export FLYAI_API_KEY="your_flyai_api_key"
export FLYAI_SIGN_SECRET="your_flyai_sign_secret"
export GAODE_API_KEY="your_gaode_api_key"  # 可选
```

**工具详情：**

#### travel_plan — 行程规划
```
输入：自然语言描述
示例："三亚5天亲子游预算1万"
返回：结构化行程方案（含交通/住宿/景点/美食推荐）
```

#### search_flight — 机票查询
```
输入：from, to, date（自然语言）
示例："上海飞三亚6月1日"
返回：航班号、起降时间、价格、舱位、预订链接
筛选：舱位、排序、价格、直飞/中转
```

#### search_train — 火车票查询
```
输入：from, to, date（自然语言）
示例："上海到北京明天的高铁"
返回：车次、时间、座型、价格、预订链接
```

#### search_hotel — 酒店搜索
```
输入：city, keyword（自然语言）
示例："三亚亚龙湾500元以内亲子酒店"
返回：酒店名称、星级、价格、评分、位置、预订链接
```

#### search_poi — 景点门票
```
输入：city, keyword
示例："杭州5A景区门票"
返回：景点名称、等级、门票价格、开放时间、预订链接
```

#### search_food — 美食推荐
```
输入：city, keyword
示例："上海南京路附近火锅"
返回：餐厅名称、菜系、人均、评分、地址、预订链接
```

#### search_transport — 市内交通
```
输入：from, to
示例："上海浦东机场到外滩"
返回：多种交通方案（地铁/公交/打车），价格和时长
```

### 3.2 mcp-meituan-travel（备用数据源）

**安装：** `pip install mcp-meituan-travel`

**配置：** 无需额外配置（使用内置代理 Key）

**工具：**

#### meituan_travel_query — 综合查询
```
输入：city（当前城市）, query（自然语言）
示例：city="上海", query="北京到上海的机票"
返回：对应类型的结果
```

### 3.3 mcp-hotel-smart（酒店专精）

**安装：** `pip install mcp-hotel-smart`

**配置：** 无需额外配置（使用内置公共 Key）

**工具：**

#### search_hotels — 酒店搜索
```
输入：query（自然语言）
支持：按城市、星级、价格、地标筛选
```

#### search_marriott_hotels — 万豪品牌专区
```
输入：query
示例："上海万豪酒店"、"北京JW万豪"
```

### 3.4 mcp-domestic-flight（航班专精，备用）

**安装：** `pip install mcp-domestic-flight`

**配置：** 无需额外配置（使用内置公共 Key）

**工具：**

#### search_flight
```
与 fliggy 的 search_flight 接口兼容
附加：更细粒度的舱位/中转筛选
```

### 3.5 mcp-travel-smart-plan（规划增强）

**安装：** `pip install mcp-travel-smart-plan`

**配置：** 需配置飞猪 API Key（同 fliggy）

**工具：** 智能规划能力（与 travel_plan 互补）

---

## 4. MCP Gateway 集成实现

### 4.1 架构

```
app/services/mcp_gateway.py
│
├── MCPServerConfig        # MCP Server 配置
├── MCPServerConnection    # 单个 Server 连接（子进程管理）
└── MCPGateway             # 网关（多 Server 管理）
    ├── initialize()       # 启动所有 Server
    ├── call_tool()        # 调用指定 Server 的工具
    ├── search()           # 多数据源聚合搜索
    ├── get_cache()        # 读取缓存
    └── set_cache()        # 写入缓存
```

### 4.2 MCP Server 配置

```python
# 配置文件定义
MCP_SERVERS = [
    {
        "name": "fliggy",
        "command": "uvx",
        "args": ["mcp-fliggy-travel"],
        "env": {
            "FLYAI_API_KEY": "${FLYAI_API_KEY}",
            "FLYAI_SIGN_SECRET": "${FLYAI_SIGN_SECRET}",
            "GAODE_API_KEY": "${GAODE_API_KEY}"
        },
        "enabled": True,
        "priority": 1,       # 主数据源
        "timeout": 15,       # 超时秒数
        "max_retries": 3     # 最大重试
    },
    {
        "name": "meituan",
        "command": "uvx",
        "args": ["mcp-meituan-travel"],
        "env": {},
        "enabled": True,
        "priority": 2,       # 备用数据源
        "timeout": 15,
        "max_retries": 3
    },
    {
        "name": "hotel_smart",
        "command": "uvx",
        "args": ["mcp-hotel-smart"],
        "env": {},
        "enabled": True,
        "priority": 1,
        "timeout": 15,
        "max_retries": 3
    },
    {
        "name": "domestic_flight",
        "command": "uvx",
        "args": ["mcp-domestic-flight"],
        "env": {},
        "enabled": True,
        "priority": 2,
        "timeout": 15,
        "max_retries": 3
    }
]
```

### 4.3 数据源路由策略

```python
# 搜索请求 → 选择数据源
ROUTE_MAP = {
    "flight":   ["fliggy", "domestic_flight", "meituan"],
    "train":    ["fliggy", "meituan"],
    "hotel":    ["fliggy", "hotel_smart", "meituan"],
    "poi":      ["fliggy", "meituan"],
    "food":     ["fliggy", "meituan"],
    "transport":["fliggy"],
}

async def search(category, params, preferred_source=None):
    """
    按优先级依次尝试数据源，成功则返回
    失败时降级到下一个数据源
    """
    sources = ROUTE_MAP[category]
    if preferred_source:
        sources.insert(0, preferred_source)

    for source in sources:
        try:
            result = await call_tool(source, params)
            return result
        except MCPServerError:
            continue  # 降级到下一数据源

    raise AllSourcesFailed()
```

### 4.4 工具映射

```python
# 后端工具名 → MCP Server 工具名
TOOL_MAP = {
    # fliggy
    ("fliggy", "search_flight"): "search_flight",
    ("fliggy", "search_train"): "search_train",
    ("fliggy", "search_hotel"): "search_hotel",
    ("fliggy", "search_poi"): "search_poi",
    ("fliggy", "search_food"): "search_food",
    ("fliggy", "search_transport"): "search_transport",
    ("fliggy", "travel_plan"): "travel_plan",
    # meituan
    ("meituan", "search"): "meituan_travel_query",
    # hotel_smart
    ("hotel_smart", "search_hotel"): "search_hotels",
    ("hotel_smart", "search_marriott"): "search_marriott_hotels",
    # domestic_flight
    ("domestic_flight", "search_flight"): "search_flight",
}
```

---

## 5. 其他依赖服务

### 5.1 高德地图 API

**用途：** 天气查询、地理编码

**获取：** https://lbs.amap.com/ → 创建应用 → 获取 Web 服务 Key

**接口：**

| 接口 | 用途 |
|------|------|
| 天气查询 | `https://restapi.amap.com/v3/weather/weatherInfo` |
| 地理编码 | `https://restapi.amap.com/v3/geocode/geo` |

**后端封装：**
```python
# services/weather_service.py
class WeatherService:
    BASE_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

    async def get_current(self, city: str) -> dict:
        """获取当前天气"""

    async def get_forecast(self, city: str, days: int = 7) -> list:
        """获取天气预报"""
```

### 5.2 LLM API（智能规划）

**用途：** AI 行程规划推理

**支持的后端：**
- DeepSeek API（https://api.deepseek.com/v1）
- OpenAI 兼容接口（任何兼容 `/v1/chat/completions` 的服务）

**配置：**
```bash
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

### 5.3 短信服务

**Phase 1 默认使用 Mock**（开发环境输出到日志，不需真实短信）。

**切换到真实服务：**
```bash
# 阿里云短信
SMS_PROVIDER=aliyun
SMS_ACCESS_KEY_ID=LTAI5t...
SMS_ACCESS_KEY_SECRET=...
SMS_SIGN_NAME=智旅
SMS_TEMPLATE_CODE=SMS_123456789

# 腾讯云短信
SMS_PROVIDER=tencent
SMS_SECRET_ID=AKID...
SMS_SECRET_KEY=...
SMS_SDK_APP_ID=1400...
SMS_SIGN_NAME=智旅
SMS_TEMPLATE_ID=1234567
```

---

## 6. LLM Agent 工具描述

AI Agent 规划时使用的 Function Calling 工具定义（由 MCP Gateway 的 `list_tools()` 动态生成）：

```json
{
  "tools": [
    {
      "name": "search_flight",
      "description": "查询国内航班。输入 from(出发城市), to(到达城市), date(日期)。返回航班号、时间、价格。",
      "parameters": {
        "from": "出发城市（中文）",
        "to": "到达城市（中文）",
        "date": "出发日期 YYYY-MM-DD"
      }
    },
    {
      "name": "search_train",
      "description": "查询火车票。输入 from(出发城市), to(到达城市), date(日期)。返回车次、时间、座型、价格。",
      "parameters": { ... }
    },
    {
      "name": "search_hotel",
      "description": "搜索酒店。输入 city(城市), keyword(关键词描述)。返回酒店名称、星级、价格、位置。",
      "parameters": { ... }
    },
    {
      "name": "search_poi",
      "description": "搜索景点门票。输入 city(城市), keyword(关键词)。返回景点信息、门票价格。",
      "parameters": { ... }
    },
    {
      "name": "search_food",
      "description": "搜索美食。输入 city(城市), keyword(菜系/区域)。返回餐厅、人均、评分。",
      "parameters": { ... }
    },
    {
      "name": "search_transport",
      "description": "查询市内交通方案。输入 from(出发地), to(目的地)。返回地铁/公交/打车方案。",
      "parameters": { ... }
    },
    {
      "name": "get_weather",
      "description": "查询目的地天气。输入 city(城市)。返回当前天气和未来预报。",
      "parameters": { "city": "城市名称（中文）" }
    },
    {
      "name": "save_trip_plan",
      "description": "将最终行程方案保存到数据库。返回行程 ID。",
      "parameters": { "trip": "行程 JSON 对象" }
    }
  ]
}
```

---

## 7. 新增数据源指南

### 7.1 添加新的 MCP Server

1. 在 PyPI/ModelScope 找到 MCP Server 包名
2. 添加到 `MCP_SERVERS` 配置
3. 更新 `ROUTE_MAP` 路由
4. 更新 `TOOL_MAP` 工具映射
5. 更新 Agent 的 System Prompt（可选，让 LLM 知道新工具）

### 7.2 添加非 MCP 的外部 API

1. 在 `services/` 下新建服务文件
2. 实现 API 调用 + 错误处理 + 缓存
3. 在 `api/search.py` 中添加新路由
4. 如需 Agent 调用，在 `agent_service.py` 中注册为自定义 Function

### 7.3 工具可用性监控

```python
# MCP Gateway 内置健康检查
async def health_check():
    for server in servers:
        try:
            await server.call_tool("ping", {})  # 轻量探测
            server.status = "healthy"
        except:
            server.failures += 1
            if server.failures >= 3:
                server.status = "degraded"
```
