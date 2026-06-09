# SmartJourney 地图功能规划方案

> 日期: 2026-06-08 | 版本: 1.0

---

## 1. 数据源调研

### 1.1 ModelScope 官方可用地图 MCP

| MCP Server | 托管方式 | 功能 | 适用性 |
|-----------|---------|------|--------|
| **[DataV-Atlas](https://modelscope.cn/mcp/servers/@DataV-Atlas/atlas-tools-mcp-server)** | ModelScope 云端 | 地理可视化、多图层地图生成、空间分析 | ⭐⭐⭐ 地图展示 |
| **[车来了 MCP](https://lobehub.com/mcp/PeanutSplash)** | 自部署 | 实时公交/地铁到站、线路查询 | ⭐⭐ 市内交通 |

### 1.2 高德地图 (Amap) MCP — 推荐主方案

[GitHub: sugarforever/amap-mcp-server](https://github.com/sugarforever/amap-mcp-server)
[官方文档: lbs.amap.com/api/mcp-server](https://lbs.amap.com/api/mcp-server/gettingstarted)

**优势**: SmartJourney 已接入高德 API（天气），可直接复用现有 Key。

**提供的 8 类工具**:

| 工具 | 功能 | 旅行场景 |
|------|------|---------|
| `geocoding` | 地址 → 经纬度 | "北京故宫" → 116.397, 39.916 |
| `regeocoding` | 经纬度 → 地址 | 坐标反查位置名 |
| `direction_walking` / `*_address` | 步行路线规划(≤100km) | 景点间步行导航 |
| `direction_bicycling` / `*_address` | 骑行路线规划(≤500km) | 骑行游览路线 |
| `direction_driving` / `*_address` | 驾车路线规划 | 自驾游线路 |
| `direction_transit` / `*_address` | 公共交通路线 | 地铁/公交换乘方案 |
| `poi_search` (text/around/detail) | POI 搜索（关键字/周边/详情） | 搜索景点、酒店、餐厅 |
| `distance` | 两点距离测量 | 计算景点间距 |

**部署方式**: 自部署（Python `uvx` 或 Docker），需要高德 API Key。

### 1.3 百度地图 MCP — 备选

[lobehub: Baidu Map MCP](https://lobehub.com/mcp/baidu-maps)

- 需要百度地图 API Key
- 功能与高德类似，但高德在旅行场景更成熟
- **不确定稳定性、不确定 ModelScope 是否有托管端点**

### 1.4 ModelScope 是否有官方可用地图功能？

| 问题 | 结论 |
|------|------|
| ModelScope 有免费托管的 Amap MCP 吗？ | ❌ **没有**。Amap MCP 是开源项目，需自部署 + 自带 API Key |
| ModelScope 有免费托管的地图 MCP 吗？ | ⚠️ 只有 DataV-Atlas（地图可视化，不是功能型 API） |
| 推荐方案 | **自部署 Amap MCP Server**，复用现有高德 Key |

---

## 2. 功能规划

### 2.1 Phase 1 — 基础地图展示（低成本，高收益）

**目标**: 行程中关键位置在地图上可视化。

```
行程详情页 → 地图 Tab
  ├── Day 1 路线: 机场 → 酒店 → 景点A → 餐厅 → 景点B
  ├── Day 2 路线: ...
  └── 全程总览: 所有 POI 聚合
```

**依赖**: Amap MCP `geocoding`（地址→坐标） + 前端地图 SDK

**前端选型**:

| 方案 | 包大小 | 定制性 | 推荐 |
|------|--------|--------|------|
| **高德 JS API 2.0** | ~80KB | 高（原生） | ✅ 推荐 |
| Leaflet + 高德瓦片 | ~40KB | 高 | 备选 |
| Mapbox GL JS | ~200KB | 很高 | 需要 Mapbox token |

> 推荐高德 JS API 2.0：中文支持好、国内访问快、与 MCP 数据同源。

### 2.2 Phase 2 — 路线规划可视化（中等工作量）

**目标**: 展示景点间的实际交通路线。

```
景点A → 景点B: 
  ├── 步行: 1.2km, 15分钟
  ├── 公交: 乘坐82路, 3站, 20分钟
  └── 驾车: 2.5km, 8分钟
```

**依赖**: Amap MCP `direction_*` 系列工具

### 2.3 Phase 3 — 周边探索（增强体验）

**目标**: 出发前帮用户发现周边的吃喝玩乐。

```
酒店周边 1km:
  ├── 🍜 美食 × 12
  ├── ☕ 咖啡厅 × 5
  ├── 🏪 便利店 × 8
  └── 🚇 地铁站 × 2
```

**依赖**: Amap MCP `poi_search`（周边搜索）

### 2.4 Phase 4 — 实时交通（远期）

**目标**: 出行中实时查询路况、公交到站。

**依赖**: 车来了 MCP（公交实时）+ Amap 实时路况

---

## 3. 技术方案

### 3.1 自部署 Amap MCP Server

```bash
# 安装
pip install amap-mcp-server

# 或 uvx 运行（推荐，无安装污染）
uvx amap-mcp-server
```

**所需配置**:
```json
{
  "mcpServers": {
    "amap": {
      "command": "uvx",
      "args": ["amap-mcp-server"],
      "env": {
        "AMAP_MAPS_API_KEY": "<现有高德Key>"
      }
    }
  }
}
```

### 3.2 集成到 SmartJourney

由于 SmartJourney 后端是 Python FastAPI，有两条路径：

#### 方案 A: MCP 子进程（Hermes 式）

```
SmartJourney FastAPI
  └── subprocess: amap-mcp-server (stdio JSON-RPC)
      └── 高德 API
```

- 优点：复用标准 MCP 协议
- 缺点：FastAPI 需要管理子进程生命周期

#### 方案 B: 直接封装高德 API（推荐 ✅）

```
SmartJourney FastAPI
  └── app/services/amap_service.py
      └── 直接 HTTP 调用高德 REST API
```

- 优点：无额外进程依赖，复用现有 `httpx` 客户端模式
- 缺点：需自己封装（但高德 API 文档完善，工作量小）

> **推荐方案 B**：SmartJourney 已有 `weather_service.py` 直接调高德 API，延续同样模式添加 `map_service.py` 更一致。

### 3.3 架构

```
                    ┌─ 前端 ────────────────────────┐
                    │  Amap JS API 2.0               │
                    │  (地图渲染 + 交互)               │
                    └───────────┬────────────────────┘
                                │ GET /api/v1/map/*
                                ▼
┌─ 后端 ────────────────────────────────────────────┐
│  app/api/map.py              (新路由)              │
│  app/services/map_service.py (封装高德 REST API)   │
│    ├─ geocode(address) → {lng, lat}               │
│    ├─ direction(origin, dest, mode) → Route        │
│    ├─ poi_search(keyword, location) → [POI]        │
│    └─ distance(p1, p2) → meters                   │
│                                                    │
│  复用: 现有 GAODE_API_KEY (config.py)              │
│  复用: 现有 Redis 缓存模式（30min TTL）             │
└────────────────────────────────────────────────────┘
```

---

## 4. API 设计

### 4.1 地理编码

```
GET /api/v1/map/geocode?address=北京故宫
→ {
  "lng": 116.397026,
  "lat": 39.916042,
  "address": "北京市东城区故宫博物院",
  "adcode": "110101"
}
```

### 4.2 路径规划

```
GET /api/v1/map/direction?from=天安门&to=故宫&mode=walking
→ {
  "distance": 1200,         // 米
  "duration": 900,          // 秒
  "steps": [
    {"instruction": "从天安门出发，向南步行200米", "distance": 200},
    ...
  ],
  "polyline": "116.397,39.916;116.398,39.917;..."  // 地图折线
}
```

### 4.3 POI 搜索

```
GET /api/v1/map/poi?keyword=火锅&city=重庆&lng=106.55&lat=29.57&radius=2000
→ {
  "pois": [
    {"name": "晓宇火锅", "address": "...", "lng": ..., "lat": ..., "rating": 4.5},
    ...
  ]
}
```

### 4.4 行程地图聚合

```
GET /api/v1/map/trip/{trip_id}
→ {
  "center": {"lng": 116.4, "lat": 39.9},
  "days": [
    {
      "day": 1,
      "route": {"polyline": "...", "distance": 5200},
      "pois": [
        {"name": "机场", "lng": ..., "lat": ..., "type": "transport"},
        {"name": "酒店", "lng": ..., "lat": ..., "type": "hotel"},
        ...
      ]
    }
  ]
}
```

---

## 5. 实施优先级

| Phase | 功能 | 工作量 | 优先级 | 前端依赖 |
|-------|------|--------|--------|---------|
| **P0** | `map_service.py` 封装高德 API | 0.5d | 最高 | 无 |
| **P0** | 行程详情页嵌入地图 (高德 JS API) | 1d | 最高 | Amap JS API 2.0 |
| **P1** | 行程地图聚合 API (`/map/trip/{id}`) | 0.5d | 高 | Phase 0 |
| **P1** | 景点间路线展示 | 1d | 高 | Phase 1 |
| **P2** | 周边搜索 (酒店/餐厅/景点附近) | 0.5d | 中 | Phase 0 |
| **P2** | PC 端地图适配 | 0.5d | 中 | Phase 1 |
| **P3** | 实时公交/路况 | 1d | 低 | 车来了 MCP |

---

## 6. 现有资源复用

| 资源 | 用途 |
|------|------|
| `GAODE_API_KEY` (.env) | 高德 Web 服务 API Key（已配置） |
| `app/services/weather_service.py` | 参考现有高德 HTTP 调用模式 |
| `app/redis_client.py` | 复用 Redis 缓存（POI 搜索 30min TTL） |
| 行程数据 (trips + trip_items) | 经纬度存为 `extra_data` JSON 字段 |
| PC Web 布局 | 地图适合放在侧边栏内容区的独立 Tab |

---

> 相关文档：[架构文档](../architecture.md) · [DataV-Atlas MCP](https://modelscope.cn/mcp/servers/@DataV-Atlas/atlas-tools-mcp-server) · [高德 MCP Server](https://github.com/sugarforever/amap-mcp-server)
