# 搜索结果解析器 — 最终实现

> 2026-06-03 | markdown_parser.py v5

## 设计原则

1. **工具专属分派**：6 种 MCP 工具各走独立解析函数，不走优先级链
2. **Bag-of-fields**：每字段多正则并行，取首个命中值
3. **双通道**：机票 bold 卡片 + 附表双通道；火车 bold 卡片 + 表格双通道
4. **前端零正则**：后端出结构化字段，前端卡片直接渲染

## 已覆盖变体

### 机票 (search_flight) — 6 种变体

| 变体 | 路线示例 | 航司字段 | 时间字段 | 机场字段 | 解析方式 |
|------|---------|---------|---------|---------|---------|
| A | 北京→上海 | `**航班**：东航 MU5100` | `**时间**：07:00→09:20` | `**起降**：首都→浦东` | bold bag-of-fields |
| B | 深圳→三亚 | `**航司**：西藏航空` | `**时间**：07:20→09:00` | 缺失(回退) | bold bag-of-fields |
| C | 深圳→上海 | `**航空公司**：金鹏` | `**时间**：06:15→08:50` | `**到达**：浦东` | bold + section |
| D | 深圳→重庆 | `**深圳航空**` 裸bold | `**起飞**→**到达**` | inline `宝安→江北` | bold + 附表去重 |
| F | 深圳→上海 | `**航空公司**：东航` | `**参考时段**：07:30-09:50` | `**航线**：宝安→虹桥` | bold + 新字段 |
| G | 深圳→上海 | `\| **HU7721** \| 海航 \|` | `09:15→11:45` | `浦东(PVG)` | **表格解析器** |

### 火车票 (search_train) — 6 种变体

| 变体 | 路线示例 | 格式特征 | 解析方式 |
|------|---------|---------|---------|
| A | 深圳→广州 | Overview表 + bold卡片 (G2957) | 跳过overview表，取bold卡片 |
| B | 北京→上海 | 分节bold卡片 `**北京站→上海站**` | bold + section |
| C | 深圳→重庆 | emoji前缀 `🚉 **深圳北 07:04→重庆西**` | bold + emoji strip |
| D | 广州→深圳 | flat bold + `**类型**：普速` | bold + 类型推断 |
| E | 北京→上海 | `\| **[G1](url)** \| 北京南→上海虹桥 \|` | **表格解析器(带链接)** |
| H | 深圳→重庆 | `\| **G2942** \| 深圳北→重庆西 \| 07:04→13:26 \|` | **表格解析器(无链接)** + `次日`处理 |

### 酒店/景点/美食/交通 — 格式稳定

| 工具 | 格式 | 提取字段 |
|------|------|---------|
| hotels | bold 卡片 | highlight, recommendation, tradeoff, section |
| pois | bold 卡片+分节 | highlight, recommendation, suggested_duration, hours, is_free |
| foods | 编号列表 | rating, price_per_person, category, address |
| transport | 📍+━━━分段 | mode, distance_km, duration_min, cost, route_detail |

## Bag-of-fields 核心正则

### 机票

```python
AIRLINE:  /航班[：:].../  /航司[：:].../  /航空公司[：:].../  /\*\*([^*]+航空)\*\*/
TIME:     /时间[：:]\s*(\d{1,2}:\d{2})/  /起飞[：:]*\s*(\d{1,2}:\d{2})/  /参考时段[：:]\s*(\d{1,2}:\d{2})/
ARRIVE:   /[→→]\s*\*{0,2}\s*(\d{1,2}:\d{2})/  /dash-sep: \d{1,2}:\d{2}\s*[-–]\s*(\d{1,2}:\d{2})/
AIRPORT:  /起降[：:]...→/  /航线[：:]...→/  /到达[：:].../
DURATION: /[（(]约(.+?)[）)]/  /约(.+?)/  /飞行时间[：:]约(.+?)/
```

### 火车

```python
ROUTE+TIME (4种正则并行):
  1. \*{0,2}站A\*{0,2}\s*→\s*站B\*{0,2}\s*\|\s*HH:MM→HH:MM     # 变体B/D
  2. emoji?\s*\*{0,2}站A\s*HH:MM\s*→\s*站B\s*HH:MM            # 变体C
  3. 站A→站B，约XX分钟                                          # 变体A
  4. 出发站[：:]站A→到达站[：:]站B  +  发车[：:]HH:MM→HH:MM   # 变体D

TABLE (2种):
  有链接: \|\s*\*\*\[TRAIN\]\(url\)\*\*\s*\|\s*route\s*\|\s*time\s*\|\s*dur\s*\|
  无链接: \|\s*\*\*TRAIN\*\*\s*\|\s*route\s*\|\s*dur\s*\|\s*time\s*\|
```

## 无结果检测

```
暂未查到 / 暂无 / 暂未查询到 / 数据仅更新至 → is_info 蓝色卡片
无法解析 / 未找到 → is_error 琥珀色卡片
```

## 前端卡片组件

`SearchCards.tsx` 导出 8 个组件：

| 组件 | 匹配条件 | 显示字段 |
|------|---------|---------|
| FlightCard | `item.flight` | ✈航司 🛩机型 航班号 → 🕐时间 ⏱时长 🛫航线 → 亮点 → 预订 |
| TrainCard | `item.train` | 🚄车次 [类型] → 🚉站→站 🕐时间 ⏱时长 → 亮点 → 预订 |
| HotelCard | `item.hotel` | 🏨名称 → ✨亮点 💡推荐 ⚠权衡 → 预订 |
| POICard | `item.poi` | 🎫名称 [免费] → 🕐建议游玩 ⏰时间 → ✨亮点 → 预订 |
| FoodCard | `item.food` | 🍜名称 [类型] → ⭐评分 💰人均 📍地址 |
| TransportCard | `item.transport` | 🚗模式 → 📏距离 ⏱时长 💰费用 |
| InfoBanner | `is_info` | ℹ️ 蓝色提示 |
| ErrorBanner | `is_error` | 💡 琥珀色错误 |

SearchPage 渲染仅 1 行：`results.map(item => renderSearchCard(item, idx))`
