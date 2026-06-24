"""
AI Agent 智能规划服务 — 通过 LLM Function Calling 调用 MCP 工具生成行程

流程:
1. 解析用户意图 → System Prompt + 可用工具列表
2. LLM 自主决策 Function Calling → MCP Gateway 执行
3. 聚合结果 → 结构化行程 JSON
4. SSE 流式返回进度 + 结果
"""

import asyncio
import json
import logging
import re
import time
import uuid
from datetime import date, timedelta
from typing import AsyncGenerator, Optional

import httpx
from sse_starlette.sse import ServerSentEvent
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.config_loader import feature, city_search_aliases, discontinued_stations
from app.services import mcp_manager
from app.database import async_session_factory
from app.services.route_strategies import ROUTE_STRATEGIES

logger = logging.getLogger(__name__)
settings = get_settings()

# ==================== Agent System Prompt ====================

SYSTEM_PROMPT = """你是 SmartJourney（智旅）的智能旅行规划师。基于已搜索到的真实数据，生成一份完整的 JSON 旅行计划。

## 核心铁律

- **价格必须从搜索结果逐项提取，严禁全部填0或使用示例中的默认值**
- **搜索结果中有 booking_url 必须如实填入，无则填 ""**
- **每个 item 的 title 必须使用搜索结果中的具体名称（如"7天连锁酒店"非"经济型酒店"、"深圳北站→7天酒店（地铁）"非"深圳北站到酒店（地铁/公交）"），严禁使用模糊描述或占位文字**
- **当搜索结果为空时，也必须基于常识给出具体的商家名称（如"如家酒店(深圳东站店)"非"深圳东站附近经济型酒店"、"湘赣人家(深圳东站店)"非"深圳东站附近晚餐"、"永和豆浆(深圳东站店)"非"深圳东站附近早餐"），严禁使用泛指描述**
- **transport 节点的标题必须与前后节点连贯，起点/终点使用前一个节点的具体名称而非泛指（如"7天连锁酒店(深圳北站民治店)→莲花山公园 地铁"非"酒店→莲花山公园 地铁"），确保每个节点可独立识别位置**
- 严禁编造链接或价格

## 规则

- 每天安排 2-3 个景点，上午 1 个、下午 1-2 个
- **每天至少包含 5-6 个行程项（含景点、餐饮、交通），从早 08:00 覆盖到晚 20:00，充分利用时间**
- **最后一天：返程交通前也必须安排上午活动（景点/美食）+ 午餐，不能只有返程一项**
- 每个景点之间预留 30-60 分钟交通时间
- 午餐 12:00-13:00，晚餐 18:00-19:00，早餐 07:30-08:30
- **早餐必须指定具体店名（可复用前几天早餐店或附近知名连锁，如"永和豆浆(深圳北站店)"），严禁"酒店周边早餐""酒店早餐"等模糊描述**
- 根据用户出行需求中的具体偏好安排合适的景点类型和节奏，不要凭空添加用户未提及的出行主题
- 总预算允许 ±{budget_strict}% 浮动（严格预算则填此范围），宽松预算可浮动 ±{budget_loose}%。预算不足时优先压缩住宿和餐饮，保证交通和门票
- items 中每个对象的 price 和 booking_url 必须直接复制搜索结果的对应字段值，一字不改。price 为数值（元）
- 每天 items 数组必须按 start_time 从早到晚排序（09:00 在前，19:00 在后），禁止时间倒序
- items 中每个对象的 price 和 booking_url 必须从搜索结果中逐一提取。price 为数值（元），搜索结果中未找到价格时方可填 0
- **如有特殊要求（花粉过敏、素食、行动不便等），必须严格遵守：避开相关场所（花卉公园/植物园→花粉过敏），选择适配的替代方案，并在 tips 中提示用户**

## 跨城交通规则（必须遵守）

- 第1天的第一个行程项必须是跨城交通（flight 或 train），从出发地到目的地
- 最后1天的最后一个行程项必须是返程跨城交通，从目的地返回出发地（若只有去程信息则至少包含去程）
- 抵达目的地后，用 transport 类型衔接市内交通（地铁/公交/打车到酒店）
- Day 1 跨城交通出发前如有 ≥4 小时空档，必须安排出发地 1-2 个景点/美食（即使搜索结果为空也应基于常识补全，如城市公园、博物馆、本地小吃）。出发前预留 1.5-2h 前往车站/机场。Day 2 如为在途日，抵达后应从酒店入住开始安排
- 跨城交通优先使用搜索结果中真实存在的航班/车次，价格和 booking_url 如实填写；搜索结果为空时可基于常识补全车次但 price 也需根据常识估算（如高铁二等座约 0.5元/km）

## 停运火车站排除（必须遵守）

以下火车站已停运/废弃，严禁作为出发或到达站：{discontinued}。此外，根据你的常识（截至2025年），还需排除其他已知停运的普速/货运站（如北京东站普速场等），只选用正常运营的高铁/动车/普速客运站。

## 输出格式

只输出如下 JSON，不要任何解释文字。**注意：示例中的 0 和 "" 仅为占位符，实际输出中必须替换为搜索结果中的真实值。**

{
  "title": "出发地→目的地 M人N日游（严格格式：出发地→目的地+人数+天数，如"深圳→上海 5人4日游"，禁止在 title 中添加任何修饰性主题词）",
  "summary": "2-3句话概要",
  "tips": ["提示1", "提示2"],
  "days": [
    {
      "day_number": 1,
      "date": "2026-06-03",
      "items": [
        {"type": "flight|train|hotel|poi|food|transport|other", "title": "...", "start_time": "08:00", "end_time": "10:00", "price": "从搜索结果复制实际价格（数值），无则填估算值", "booking_url": "从搜索结果复制，无则留空"}
      ]
    }
  ],
  "budget": {"transport": "交通总价", "lodging": "住宿总价", "food": "餐饮总价", "tickets": "门票总价", "other": "其他总价"}
}

**再次强调：搜索结果中每个 item 都有 price 字段，你必须逐一复制到输出的对应 item 中。train/flight/hotel 的 price 绝不能为 0，无搜索结果的该项应基于常识估算（高铁 0.5元/km，经济酒店 150-300元/晚，景点门票 30-150元）。严禁输出全部 price=0 的行程。**"""

# ==================== Function Definitions for LLM ====================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_flight",
            "description": "查询国内航班。输入出发城市、到达城市、日期。返回航班号、起降时间、价格、预订链接。",
            "parameters": {
                "type": "object",
                "properties": {
                    "from": {"type": "string", "description": "出发城市（中文）"},
                    "to": {"type": "string", "description": "到达城市（中文）"},
                    "date": {"type": "string", "description": "出发日期 YYYY-MM-DD"},
                },
                "required": ["from", "to", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_train",
            "description": "查询火车票（高铁/动车/普速）。输入出发城市、到达城市、日期。返回车次、时间、座型、价格、预订链接。",
            "parameters": {
                "type": "object",
                "properties": {
                    "from": {"type": "string", "description": "出发城市（中文）"},
                    "to": {"type": "string", "description": "到达城市（中文）"},
                    "date": {"type": "string", "description": "出发日期 YYYY-MM-DD"},
                },
                "required": ["from", "to", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotel",
            "description": "搜索酒店。输入城市和关键词描述。返回酒店名称、星级、价格、位置、预订链接。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "目标城市"},
                    "keyword": {"type": "string", "description": "搜索关键词（如：亲子、4星、亚龙湾、500以内）"},
                },
                "required": ["city", "keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_poi",
            "description": "搜索景点和门票。输入城市和关键词。返回景点名称、等级、门票价格、开放时间、预订链接。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "目标城市"},
                    "keyword": {"type": "string", "description": "搜索关键词（如：5A、海边、博物馆、亲子）"},
                },
                "required": ["city", "keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_food",
            "description": "搜索美食。输入城市和关键词。返回餐厅名称、菜系、人均、评分、地址。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "目标城市"},
                    "keyword": {"type": "string", "description": "搜索关键词（如：火锅、海鲜、川菜、南京路）"},
                },
                "required": ["city", "keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_transport",
            "description": "查询市内交通方案。输入出发地和目的地。返回地铁/公交/打车方案及预估时间和价格。",
            "parameters": {
                "type": "object",
                "properties": {
                    "from": {"type": "string", "description": "出发地点（如：浦东机场）"},
                    "to": {"type": "string", "description": "到达地点（如：外滩）"},
                },
                "required": ["from", "to"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询目的地天气。返回当前天气和未来几天预报。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称（中文）"},
                },
                "required": ["city"],
            },
        },
    },
]


# ==================== Agent Service ====================

class AgentService:
    """AI 行程规划 Agent"""

    def __init__(self):
        pass  # 每次 LLM 调用使用独立 httpx client，避免 event loop 问题

    async def generate_plan(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        traveler_count: int = 1,
        budget_total: Optional[float] = None,
        preferences: Optional[dict] = None,
        save_as_trip: bool = True,
        use_weather: bool = True,
        route_count: int = 1,
        route_strategy: int = -1,
        special_notes: Optional[str] = None,
        _request = None,  # FastAPI Request — 用于检测客户端断开
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """
        生成行程规划 — SSE 流式返回
        v3: 后端主动构造查询 → 并行 MCP → 汇聚 → LLM 一次生成 → 异步保存
        """
        start_time = time.time()
        logger.info(f"Plan start: user={user_id}, {origin}→{destination}, {traveler_count}p, ¥{budget_total or 0}")

        # 1. 构建用户消息
        user_message = self._build_user_message(
            query, origin, destination, start_date, end_date,
            traveler_count, budget_total, preferences, special_notes,
        )
        yield self._sse_event("step", {"step": "analyzing", "text": "正在分析出行需求..."})

        # 2. 构造所有查询（往返交通 + 目的地信息 + 天气）
        queries, is_cross_city = self._build_all_queries(origin, destination, start_date, end_date)
        yield self._sse_event("step", {
            "step": "searching",
            "text": f"正在分批搜索 {len(queries)} 个数据源..."
        })

        # 3. 分批并发执行（避免 MCP 免费层限流，酒店/景点先出结果）
        BATCH_DELAY = 5.0  # 批次间冷却秒数（MCP 免费层限流复位）

        async def _run_one(name, q, retries=None):
            t0 = time.time()
            try:
                result = await mcp_manager.call_tool(name, q, max_retries=retries)
                elapsed = time.time() - t0
                items = result.get("items", [])
                logger.info(f"MCP {name}: {len(items)} items, {elapsed:.1f}s, query={q[:50]}")
                return (name, q, result, None, round(elapsed, 1))
            except Exception as e:
                return (name, q, {"items": [], "note": str(e)[:80]}, str(e), 0)

        # 工具调用事件 — 先推送给前端
        for name, mcp_query in queries:
            yield self._sse_event("tool_call", {
                "name": name,
                "args": {"query": mcp_query},
            })

        results = []

        # 批次 1: 酒店 + 景点 + 美食（重要数据，重试 2 次）
        batch1 = [(n, q) for n, q in queries if n in ("search_hotel", "search_poi", "search_food")]
        if batch1:
            b1 = await asyncio.gather(*[_run_one(n, q, retries=2) for n, q in batch1])
            results.extend(b1)

        # 批次 2: 机票（限流敏感，不重试）
        batch2 = [(n, q) for n, q in queries if n == "search_flight"]
        if batch2:
            await asyncio.sleep(BATCH_DELAY)
            b2 = await asyncio.gather(*[_run_one(n, q, retries=0) for n, q in batch2])
            results.extend(b2)

        # 批次 3: 火车（限流敏感，不重试）
        batch3 = [(n, q) for n, q in queries if n == "search_train"]
        if batch3:
            await asyncio.sleep(BATCH_DELAY)
            b3 = await asyncio.gather(*[_run_one(n, q, retries=0) for n, q in batch3])
            results.extend(b3)

        # 4. 天气查询 — 出发地 + 目的地异步并行
        weather_summary = ""
        origin_weather = dest_weather = ""
        if use_weather:
            from app.services.weather_service import get_weather
            cities = []
            if origin:
                cities.append(("origin", origin))
            if destination:
                cities.append(("dest", destination))
            if cities:
                weather_tasks = {label: get_weather(city) for label, city in cities}
                weather_results = dict(zip(weather_tasks.keys(),
                    await asyncio.gather(*weather_tasks.values())))
                for label, data in weather_results.items():
                    if data and not data.get("error"):
                        fmt = self._format_weather_for_prompt(data, start_date, end_date)
                        if label == "origin":
                            origin_weather = fmt
                        else:
                            dest_weather = fmt

        # 组装天气摘要
        weather_parts = []
        if origin_weather:
            weather_parts.append(f"## 🌤️ {origin}（出发地）\n{origin_weather}")
        if dest_weather:
            weather_parts.append(f"## 🌤️ {destination}（目的地）\n{dest_weather}")
        weather_summary = "\n\n".join(weather_parts)
        if weather_summary:
            yield self._sse_event("step", {"step": "weather_done", "text": f"天气: {weather_summary[:80]}..."})
            yield self._sse_event("weather", {
                "origin": origin,
                "dest": destination,
                "origin_weather": origin_weather,
                "dest_weather": dest_weather,
            })

        # 5. 汇总结果：tool_result 逐个推送前端，train 合并后给 LLM
        yield self._sse_event("step", {"step": "generating", "text": "正在汇总搜索结果..."})

        compact_results = []
        train_dep_items = []   # 去程火车
        train_ret_items = []   # 返程火车
        train_dep_count = train_ret_count = 0

        # 获取城市所有可能的火车站名（用于方向检测）
        aliases = city_search_aliases()
        def _train_names(city: str | None) -> list[str]:
            if not city:
                return []
            a = aliases.get(city, {})
            v = a.get("train", city)
            return v if isinstance(v, list) else [v]

        dest_train_names = _train_names(destination)
        origin_train_names = _train_names(origin)

        for name, mcp_query, result, error, elapsed in results:
            summary = self._summarize_result(name, result)
            sse_data = {"name": name, "summary": summary}
            if elapsed:
                sse_data["elapsed"] = elapsed
            yield self._sse_event("tool_result", sse_data)

            if name == "search_train":
                # 按方向合并火车结果（用所有可能站名判断方向）
                items = result.get("items", [])
                first_part = mcp_query.split("到")[0] if "到" in mcp_query else ""
                is_return = "返" in mcp_query \
                    or (destination and destination in first_part) \
                    or any(s in first_part for s in dest_train_names)
                if is_return:
                    train_ret_items.extend(items)
                    train_ret_count += 1
                else:
                    train_dep_items.extend(items)
                    train_dep_count += 1
            else:
                compact = self._compact_tool_result(name, result)
                compact_results.append(f"[{name}] {compact}")

        # 火车结果：双向合并，单向逐条显示
        if train_dep_count and train_ret_count:
            merged_dep = {"items": train_dep_items, "note": f"合并自 {train_dep_count} 次查询"}
            compact_results.append(f"[search_train 去程] {self._compact_tool_result('search_train', merged_dep)}")
            merged_ret = {"items": train_ret_items, "note": f"合并自 {train_ret_count} 次查询"}
            compact_results.append(f"[search_train 返程] {self._compact_tool_result('search_train', merged_ret)}")
        else:
            # 单向：逐条显示，不合并
            label = "去程" if train_dep_count else "返程"
            items = train_dep_items or train_ret_items
            for item in items:
                compact = self._compact_tool_result('search_train', {"items": [item]})
                compact_results.append(f"[search_train {label}] {compact}")

        # 搜索阶段完成
        yield self._sse_event("step", {"step": "search_done", "text": "搜索已完成，正在生成行程方案..."})

        # 6. 构建 LLM prompt（一次性，不通过 tool_calls）
        search_context = "\n\n".join(compact_results)
        disc_list = discontinued_stations()
        disc_str = "、".join(disc_list) if disc_list else "无"
        budget_strict = feature("budget_strict_pct", 30)
        budget_loose = feature("budget_loose_pct", 50)
        system_prompt = SYSTEM_PROMPT.replace("{discontinued}", disc_str)
        system_prompt = system_prompt.replace("{budget_strict}", str(budget_strict))
        system_prompt = system_prompt.replace("{budget_loose}", str(budget_loose))
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
            {"role": "user", "content": (
                f"## 搜索结果\n\n{search_context}\n\n"
                "请基于以上搜索结果，立即输出完整的 JSON 行程方案。\n\n"
                "重要规则：\n"
                "1. 只输出 JSON，不要输出任何解释文字\n"
                "2. JSON 必须包含 title, summary, tips, days（每天含 items），budget（transport/lodging/food/tickets/other）\n"
                "3. 即使某些搜索结果为空，也基于你的知识补全\n"
                "4. days 按日期排列，每天包含合理的行程安排\n"
                + (f"5. 目的地天气：{weather_summary}\n" if weather_summary else "")
                + ("6. 跨城旅行：第1天首个行程必须是跨城交通（flight/train），最后1天末个行程必须是返程交通\n" if is_cross_city else "6. 同城旅行：无需跨城交通，使用 transport 安排市内出行即可\n")
            )},
        ]

        # 7. 策略路由
        base_gen = ""
        if weather_summary:
            base_gen += (
                f"\n目的地天气（必须参考！）：\n{weather_summary}\n"
                "天气决策规则：\n"
                "- 下雨/暴雨/大雪 → 优先室内景点\n"
                "- 晴天 15-28°C → 优先户外景点\n"
                "- 晴天 >32°C → 上午户外，中午室内\n"
                "- 大风 ≥6级/台风 → 避免户外和水上\n"
            )

        if route_strategy >= 0:
            strategies = [ROUTE_STRATEGIES[route_strategy]]
        elif route_count > 1:
            strategies = ROUTE_STRATEGIES[:route_count]
        else:
            strategies = []

        trip_jsons = []

        async def _gen_one(strategy, idx):
            msg_copy = [dict(m) for m in messages]
            strat_prompt = f"\n## 你的规划策略\n{strategy['emphasis']}"
            if base_gen:
                strat_prompt = base_gen + strat_prompt
            msg_copy.append({"role": "user", "content": strat_prompt})
            t0 = time.time()
            logger.info(f"LLM call start: strategy={strategy['tag']}, tokens_est={sum(len(str(m.get('content',''))) for m in msg_copy)//4}")
            try:
                resp = await self._call_llm(msg_copy, None)
                elapsed = time.time() - t0
                if resp:
                    content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                    logger.info(f"LLM call done: {elapsed:.1f}s, content_len={len(content)}")
                    tj = self._extract_json(content)
                    if tj:
                        tj["route_tag"] = strategy["tag"]
                        tj["route_index"] = idx
                    return tj or {"error": "parse_failed", "raw": content[:200]}
                return {"error": "llm_failed"}
            except Exception as e:
                logger.error(f"LLM call exception: {e}", exc_info=True)
                return {"error": f"llm_exception: {str(e)[:100]}"}

        if strategies:
            gen_results = await asyncio.gather(*[
                _gen_one(s, i) for i, s in enumerate(strategies)
            ])
            for s, r in zip(strategies, gen_results):
                if r and not r.get("error") and r.get("days"):
                    if not r.get("trip_id"):
                        r["trip_id"] = str(uuid.uuid4())
                    trip_jsons.append(r)
                    yield self._sse_event("trip_data", r)
        else:
            # 流式 LLM 生成 → chunk 打字机效果
            content = ""
            yield self._sse_event("step", {"step": "llm_stream", "text": "AI 正在规划行程..."})
            async for item in self._call_llm_stream(messages):
                if isinstance(item, tuple) and item[0] == "__FULL__":
                    content = item[1]
                elif isinstance(item, str):
                    yield self._sse_event("chunk", {"text": item})
            if content:
                trip_json = self._extract_json(content)
                if trip_json:
                    if not trip_json.get("days"):
                        trip_json["days"] = []
                    if not trip_json.get("trip_id"):
                        trip_json["trip_id"] = str(uuid.uuid4())
                    trip_jsons.append(trip_json)
                    yield self._sse_event("trip_data", trip_json)
                else:
                    yield self._sse_event("chunk", {"text": content[:500]})

        if not trip_jsons:
            elapsed = time.time() - start_time
            logger.warning(f"Plan done: 0 routes generated, {elapsed:.1f}s")
            yield self._sse_event("chunk", {"text": "行程生成遇到问题，请重新规划"})

        elapsed = time.time() - start_time
        logger.info(f"Plan done: {len(trip_jsons)} routes, {elapsed:.1f}s")
        yield self._sse_event("done", {
            "elapsed_seconds": round(elapsed, 1),
            "routes_generated": len(trip_jsons),
            "route_count": route_count,
        })

        # 8. 实时地图预览：逐 POI geocode + SSE 推送坐标 + 收集供持久化
        all_coords: list[dict] = []  # 每个 trip_json 对应一个 {(day, idx): (lng, lat)}
        for tj in trip_jsons:
            coords: dict = {}
            async for ev in self._emit_poi_coordinates(tj, origin or "", destination or "", coords):
                yield ev
            all_coords.append(coords)

        # 异步保存（不阻塞 SSE 流）
        if trip_jsons and save_as_trip:
            async def _save_all():
                try:
                    async with async_session_factory() as save_db:
                        async with save_db.begin():
                            for tj, coords in zip(trip_jsons, all_coords):
                                try:
                                    await self._save_trip(save_db, user_id, tj, origin, destination, start_date, end_date, traveler_count, budget_total, special_notes, weather_summary, coords=coords)
                                except Exception as e:
                                    logger.error(f"Failed to save route {tj.get('route_tag')}: {e}")
                    logger.info(f"Async save complete: {len(trip_jsons)} routes")
                except Exception as e:
                    logger.error(f"Async save failed: {e}")
            asyncio.create_task(_save_all())

    # ==================== 私有方法 ====================

    async def _emit_poi_coordinates(self, trip_json: dict, origin: str, destination: str,
                                     coords_out: dict | None = None):
        """逐 POI geocode → SSE poi_coord 事件 + 收集坐标到 coords_out {(day, idx): (lng, lat)}"""
        from app.services.map_service import geocode
        import re as _re
        titles: list[tuple[str, str, int, int]] = []  # (title, type, day, idx)
        for day_data in trip_json.get("days", []):
            day_num = day_data.get("day_number", 1)
            items = day_data.get("items", [])
            # 按 start_time 排序，与 _save_trip 保持一致，确保 idx 对齐
            items.sort(key=lambda i: i.get("start_time", "99:99"))
            for idx, item in enumerate(items):
                title = item.get("title", "").strip()
                if title:
                    titles.append((title, item.get("type", ""), day_num, idx))

        if not titles:
            return

        sem = asyncio.Semaphore(5)
        count = 0

        async def _geo_one(title: str, typ: str, day: int, idx: int, city: str):
            nonlocal count
            async with sem:
                try:
                    is_transport = typ in ("flight", "train", "transport")
                    if is_transport:
                        query = title
                        if '→' in title:
                            side = title.split('→')[0].strip()
                            dest = title.split('→')[1].strip()
                            # clean transport suffix from dest
                            dest = _re.sub(r'\s*(地铁|公交|步行|打车|网约车|专车|出租车)(\d*号线?(转\d*号线?)?)?(\s*\([^)]*\))?\s*$', '', dest)
                        else:
                            side = title
                            dest = ''
                        m = _re.search(r'([\u4e00-\u9fa5]{2,8}(?:东|西|南|北)(?:站|机场)?|[\u4e00-\u9fa5]{2,8}(?:站|机场))', side)
                        if m:
                            query = m.group(1)
                        elif dest:
                            query = dest  # fallback to destination (non-station places)
                        result = await geocode(query, city)
                    else:
                        # Replace parentheses with spaces before geocoding (Amap rejects them)
                        clean_title = _re.sub(r'[（(]', ' ', title)
                        clean_title = _re.sub(r'[）)]', ' ', clean_title)
                        clean_title = _re.sub(r'\s+', ' ', clean_title).strip()
                        result = await geocode(f"{city} {clean_title}" if city else clean_title, city)
                    if result and "lng" in result and "lat" in result:
                        return {
                            "title": title, "day": day, "idx": idx,
                            "lng": result["lng"], "lat": result["lat"],
                        }
                    # Fallback: clean title (remove parentheticals & meal suffixes)
                    cleaned = _re.sub(r'[（(][^)）]*[)）]', '', title)
                    cleaned = _re.sub(r'(午餐|晚餐|早餐|中餐|晚饭|早饭|午饭)\s*$', '', cleaned)
                    cleaned = cleaned.strip()
                    if cleaned and cleaned != title:
                        result = await geocode(f"{city} {cleaned}" if city else cleaned, city)
                        if result and "lng" in result and "lat" in result:
                            return {
                                "title": title, "day": day, "idx": idx,
                                "lng": result["lng"], "lat": result["lat"],
                            }
                except Exception as e:
                    logger.debug(f"Live geocode failed: {title[:30]} — {e}")
                return None

        # 按天遍历，跨天后不重置 seen_transit（一旦出发到达目的地，后续天都在目的地）
        current_day = 0
        seen_transit = False
        for title, typ, day_num, idx in titles:
            if day_num != current_day:
                current_day = day_num
            city = destination if (seen_transit and destination) else (origin or destination)
            if typ in ('train', 'flight'):
                seen_transit = True
            tasks = [_geo_one(title, typ, day_num, idx, city)]
            for coro in asyncio.as_completed(tasks):
                coord = await coro
                if coord:
                    count += 1
                    if coords_out is not None:
                        coords_out[(coord["day"], coord["idx"])] = (coord["lng"], coord["lat"])
                    yield self._sse_event("poi_coord", coord)

        logger.info(f"Live geocode: {count}/{len(titles)} POIs geocoded")

    def _build_user_message(self, query, origin, destination, start_date, end_date,
                            traveler_count, budget_total, preferences, special_notes=None) -> str:
        parts = [query]

        if origin:
            parts.append(f"出发地：{origin}")
        if destination:
            parts.append(f"目的地：{destination}")
        if start_date:
            parts.append(f"出发日期：{start_date}")
            if end_date:
                days = (end_date - start_date).days + 1
                parts.append(f"返回日期：{end_date}（共 {days} 天）")
        if traveler_count > 1:
            parts.append(f"出行人数：{traveler_count} 人")
        if budget_total:
            parts.append(f"总预算：{budget_total:.0f} 元")
        if special_notes:
            parts.append(f"⚠️ 特殊要求（必须严格遵守）：{special_notes}")

        parts.append("\n请基于搜索结果生成完整的 JSON 行程方案。")
        parts.append("注意：第1天必须包含从出发地到目的地的跨城交通（flight/train），最后1天必须包含返程交通。")
        parts.append("第1天若跨城交通在下午/晚上出发，上车前有大量空档时间，务必安排出发地 1-2 个活动。")
        return "\n".join(parts)

    @staticmethod
    def _to_cn_date(iso_date) -> str:
        """Convert ISO date or date object to Chinese format"""
        if iso_date is None:
            return ""
        if hasattr(iso_date, 'strftime'):
            return f"{iso_date.year}年{iso_date.month}月{iso_date.day}日"
        try:
            parts = str(iso_date).split("-")
            if len(parts) == 3:
                return f"{parts[0]}年{int(parts[1])}月{int(parts[2])}日"
        except (ValueError, IndexError):
            pass
        return str(iso_date)

    def _build_all_queries(self, origin, destination, start_date, end_date) -> tuple[list[tuple[str, str]], bool]:
        """从用户输入构造所有 MCP 查询列表，返回 (查询列表, 是否跨城)"""
        queries = []
        dep_date = self._to_cn_date(start_date)
        ret_date = self._to_cn_date(end_date)

        # 判断是否跨城旅行
        is_cross_city = bool(origin and destination and origin != destination)

        if is_cross_city:
            # 应用城市→站名/机场名映射（小城市站名不一致时）
            aliases = city_search_aliases()
            a_origin = aliases.get(origin, {})
            a_dest = aliases.get(destination, {})
            flight_from = a_origin.get("flight", origin)
            flight_to = a_dest.get("flight", destination)
            # train 支持单站(字符串)或多站(数组)
            _from = a_origin.get("train", origin)
            _to = a_dest.get("train", destination)
            train_from_list = _from if isinstance(_from, list) else [_from]
            train_to_list = _to if isinstance(_to, list) else [_to]

            # 去程机票
            queries.append(("search_flight", f"{flight_from}到{flight_to}{dep_date}机票"))
            # 返程机票
            if ret_date:
                queries.append(("search_flight", f"{flight_to}到{flight_from}{ret_date}机票"))

            # 去程火车（站名 × 类型）
            for ttype in ["高铁", "动车", "火车票"]:
                for tf in train_from_list:
                    for tt in train_to_list:
                        queries.append(("search_train", f"{tf}到{tt}{dep_date}{ttype}"))
            # 返程火车
            if ret_date:
                for ttype in ["高铁", "动车", "火车票"]:
                    for tf in train_from_list:
                        for tt in train_to_list:
                            queries.append(("search_train", f"{tt}到{tf}{ret_date}{ttype}"))
        else:
            # 同城旅行：搜索市内交通
            city = destination or origin
            if city:
                queries.append(("search_transport", f"{city}市 市内交通"))

        if destination:
            queries.append(("search_hotel", f"{destination}酒店"))
            queries.append(("search_poi", f"{destination}景点"))
            queries.append(("search_food", f"{destination}美食"))

        # 跨城时，出发地也需要搜（Day 1 出发前可能有空档）
        if is_cross_city and origin:
            queries.append(("search_poi", f"{origin}景点"))
            queries.append(("search_food", f"{origin}美食"))

        return queries, is_cross_city

    async def _call_llm(self, messages: list, tools: list = None) -> dict | None:
        """调用 LLM API"""
        try:
            body = {
                "model": settings.llm_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 8192,
            }
            if tools:
                body["tools"] = tools
                body["tool_choice"] = "auto"
            else:
                body["tool_choice"] = "none"

            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
                resp = await client.post(
                    f"{settings.llm_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
            if resp.status_code != 200:
                logger.error(f"LLM error {resp.status_code}: {resp.text[:300]}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"LLM call failed ({type(e).__name__}): {e}")
            return None

    async def _call_llm_stream(self, messages: list):
        """调用 LLM API（流式），逐个 yield text chunk"""
        try:
            body = {
                "model": settings.llm_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 8192,
                "stream": True,
                "tool_choice": "none",
            }
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client:
                async with client.stream(
                    "POST",
                    f"{settings.llm_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                ) as resp:
                    if resp.status_code != 200:
                        logger.error(f"LLM stream error {resp.status_code}")
                        return
                    full_text = ""
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:].strip()
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                text = delta.get("content", "")
                                if text:
                                    full_text += text
                                    yield text
                            except (json.JSONDecodeError, KeyError):
                                pass
                    yield ("__FULL__", full_text)
        except Exception as e:
            logger.error(f"LLM stream failed ({type(e).__name__}): {e}")

    @staticmethod
    def _format_weather_for_prompt(weather_data: dict, start_date, end_date=None) -> str:
        """格式化天气数据为 LLM prompt 摘要 — 覆盖全部行程日，超出预报范围标注暂无"""
        if not weather_data:
            return ""
        forecasts = weather_data.get("forecast", [])
        if not forecasts:
            return ""

        # 构建预报字典 {date: forecast}
        fc_map = {fc.get("date", ""): fc for fc in forecasts}

        # 生成行程每一天的天气（含超出预报范围的日期）
        from datetime import date, timedelta
        parts = []
        if start_date and end_date:
            sd = start_date if isinstance(start_date, date) else date.fromisoformat(str(start_date))
            ed = end_date if isinstance(end_date, date) else date.fromisoformat(str(end_date))
            current = sd
            while current <= ed:
                ds = current.isoformat()
                fc = fc_map.get(ds)
                if fc:
                    parts.append(
                        f"- {ds}: {fc.get('dayweather','?')}/{fc.get('nightweather','?')} "
                        f"{fc.get('daytemp','?')}~{fc.get('nighttemp','?')}°C"
                    )
                else:
                    parts.append(f"- {ds}: 暂无天气预报（超出 API 预报范围）")
                current += timedelta(days=1)
        else:
            for fc in forecasts:
                fc_date = fc.get("date", "")
                if start_date and fc_date < str(start_date):
                    continue
                if end_date and fc_date > str(end_date):
                    continue
                parts.append(
                    f"- {fc_date}: {fc.get('dayweather','?')}/{fc.get('nightweather','?')} "
                    f"{fc.get('daytemp','?')}~{fc.get('nighttemp','?')}°C"
                )

        return "\n".join(parts) if parts else ""

    async def _execute_tool(self, name: str, args: dict) -> dict:
        """执行 MCP 工具或内置工具"""
        try:
            if name == "get_weather":
                from app.services.weather_service import get_weather
                return await get_weather(args.get("city", ""))

            # 优先使用远程 MCP Manager（HTTP，不破坏 event loop）
            from app.services import mcp_manager
            if mcp_manager.is_available():
                query = self._build_nl_query(name, args)
                try:
                    result = await asyncio.wait_for(
                        mcp_manager.call_tool(name, query),
                        timeout=feature("mcp_tool_timeout_seconds", 60),
                    )
                    return result
                except asyncio.TimeoutError:
                    logger.warning(f"MCP tool {name} timed out")

            return {"items": [], "note": "数据源不可用"}
        except Exception as e:
            logger.warning(f"Tool {name} failed: {e}")
            return {"items": [], "note": "工具暂时不可用"}

    def _build_nl_query(self, tool_name: str, args: dict) -> str:
        """将结构化参数转为自然语言 query"""
        if tool_name == "search_flight":
            return f"{args.get('from','')}到{args.get('to','')} {args.get('date','')} 机票"
        elif tool_name == "search_train":
            return f"{args.get('from','')}到{args.get('to','')} {args.get('date','')} 火车票"
        elif tool_name == "search_hotel":
            return f"{args.get('city','')} {args.get('keyword','')} 酒店"
        elif tool_name == "search_poi":
            return f"{args.get('city','')} {args.get('keyword','')} 景点"
        elif tool_name == "search_food":
            return f"{args.get('city','')} {args.get('keyword','')} 美食"
        elif tool_name == "search_transport":
            return f"从{args.get('from_location', args.get('from',''))}到{args.get('to','')} 交通"
        return str(args)

    def _compact_tool_result(self, tool_name: str, result: dict) -> str:
        """将工具结果压缩为 LLM 友好的紧凑 JSON，大幅减少 token 消耗"""
        items = result.get("items", []) or result.get("data", {}).get("items", [])

        # 过滤停运火车站（train 搜索结果，防止 LLM 选到已停运车站的车次）
        if tool_name == "search_train" and items:
            disc = discontinued_stations()
            if disc:
                filtered = []
                for item in items:
                    text = json.dumps(item, ensure_ascii=False)
                    if not any(s in text for s in disc):
                        filtered.append(item)
                if len(filtered) < len(items):
                    logger.info(f"Filtered {len(items)-len(filtered)} trains from discontinued stations")
                items = filtered

        if not items:
            return json.dumps({"tool": tool_name, "count": 0, "note": result.get("note", "无结果已过滤停运站" if tool_name == "search_train" else "无结果")}, ensure_ascii=False)

        # 每种工具提取关键字段
        compact = {"tool": tool_name, "count": len(items), "items": []}
        key_fields = {
            "search_flight": ["title", "description", "price", "booking_url"],
            "search_train": ["title", "description", "price", "booking_url"],
            "search_hotel": ["title", "stars", "price_per_night", "location", "booking_url"],
            "search_poi": ["title", "level", "ticket_price", "description", "booking_url"],
            "search_food": ["title", "cuisine", "avg_price", "description", "booking_url"],
            "search_transport": ["title", "type", "duration", "price"],
        }
        fields = key_fields.get(tool_name, ["title", "description"])

        # 价格字段名映射 — 统一为 price
        price_aliases = {"price", "ticket_price", "avg_price", "price_per_night", "price_range"}
        link_aliases = {"booking_url", "booking_link", "url", "link"}

        for item in items[:20]:  # 安全上限，覆盖几乎全部结果
            entry = {}
            for f in fields:
                val = item.get(f)
                if val is not None:
                    # 描述截断
                    if f == "description" and isinstance(val, str):
                        val = val[:120]
                    # 统一价格字段名
                    if f in price_aliases:
                        entry["price"] = val
                    elif f in link_aliases:
                        entry["booking_url"] = val
                    else:
                        entry[f] = val
            compact["items"].append(entry)

        return json.dumps(compact, ensure_ascii=False)

    def _summarize_result(self, tool_name: str, result: dict) -> str:
        """生成工具结果摘要"""
        items = result.get("items", []) or result.get("data", {}).get("items", [])
        count = len(items)
        if count == 0:
            # Check for raw_markdown (MCP markdown response)
            if result.get("raw_markdown"):
                return f"{tool_name}: 获取到详细数据"
            return f"{tool_name}: 未找到结果"
        if tool_name == "get_weather":
            current = result.get("current", {})
            return f"天气: {current.get('weather', '未知')} {current.get('temperature', '?')}°C"
        return f"{tool_name}: 找到 {count} 个结果"

    def _extract_json(self, text: str) -> dict | None:
        """从 LLM 输出中提取 JSON（容错）"""
        try:
            # 尝试提取 ```json 代码块
            if "```json" in text:
                start = text.index("```json") + 7
                end = text.index("```", start)
                json_str = text[start:end].strip()
            elif text.strip().startswith("{"):
                json_str = text.strip()
            else:
                return None

            # 尝试直接解析
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

            # 容错：常见 LLM 错误修复
            try:
                # 1. 将对象中错误格式的数组值转为数组
                import re
                # 修复 "extra_data": {"key1", "key2"} → "extra_data": ["key1", "key2"]
                fixed = re.sub(
                    r'"extra_data":\s*\{([^}]+)\}',
                    lambda m: '"extra_data": [' + re.sub(
                        r'"([^"]+)"', r'"\1"', m.group(1)
                    ) + ']',
                    json_str,
                )
                return json.loads(fixed)
            except (json.JSONDecodeError, ValueError):
                pass

            return None
        except (json.JSONDecodeError, ValueError):
            return None

    async def _save_trip(self, db, user_id, trip_json, origin, destination, start_date, end_date, traveler_count, budget_total, special_notes=None, weather_info="", coords: dict | None = None):
        """保存行程、行程项、预算到数据库。coords = {(day, idx): (lng, lat)} 来自 SSE 阶段 geocode"""
        from app.services.trip_service import create_trip, add_trip_item
        trip_id = trip_json.get("trip_id")
        trip_data = {
            "title": trip_json.get("title", f"{destination or '未命名'}旅行"),
            "origin": origin or trip_json.get("origin"),
            "destination": destination or trip_json.get("destination"),
            "start_date": start_date,
            "end_date": end_date,
            "traveler_count": traveler_count,
            "budget_total": budget_total,
            "route_tag": trip_json.get("route_tag") or None,
            "tips": trip_json.get("tips"),
            "summary": trip_json.get("summary"),
            "special_notes": special_notes,
            "weather_info": weather_info or None,
        }
        if trip_id:
            trip_data["id"] = trip_id
        trip = await create_trip(db, user_id, trip_data)
        trip_json["trip_id"] = trip.id
        for day_data in trip_json.get("days", []):
            day_num = day_data.get("day_number", 1)
            target_day = next((d for d in trip.days if d.day_number == day_num), None)
            if not target_day:
                continue
            items = day_data.get("items", [])
            # 按 start_time 排序，确保时间线按时间顺序展示
            items.sort(key=lambda i: i.get("start_time", "99:99"))
            for idx, item_data in enumerate(items):
                item_type = item_data.get("type", "other")
                lat_lng = coords.get((day_num, idx)) if coords else None
                await add_trip_item(db, trip.id, user_id, {
                    "day_id": target_day.id,
                    "type": item_type,
                    "title": item_data.get("title", ""),
                    "start_time": (item_data.get("start_time") or "")[:10] or None,
                    "end_time": (item_data.get("end_time") or "")[:10] or None,
                    "price": item_data.get("price"),
                    "booking_url": item_data.get("booking_url"),
                    "extra_data": item_data.get("extra_data"),
                    "sort_order": idx,
                    "lat": lat_lng[1] if lat_lng else None,
                    "lng": lat_lng[0] if lat_lng else None,
                })
        await db.flush()

        # ── POI 照片富化（异步后台，仅对已有坐标的 item 搜照片）──
        from app.services.map_service import enrich_poi_photos
        from sqlalchemy import select as _select
        from app.models import TripItem
        import asyncio as _asyncio

        trip_days = trip.days
        async def _enrich_items():
            try:
                async with async_session_factory() as enrich_db:
                    async with enrich_db.begin():
                        item_result = await enrich_db.execute(
                            _select(TripItem).where(
                                TripItem.trip_day_id.in_([d.id for d in trip_days])
                            )
                        )
                        for item in item_result.scalars().all():
                            if item.lat is None or item.lng is None:
                                continue  # SSE geocode 未成功，跳过照片富化
                            if item.photos and item.amap_poi_id:
                                continue
                            try:
                                photos, amap_id = await enrich_poi_photos(item.title, item.lng, item.lat)
                                if photos or amap_id:
                                    update_vals = {}
                                    if photos:
                                        update_vals["photos"] = photos
                                    if amap_id:
                                        update_vals["amap_poi_id"] = amap_id
                                    await enrich_db.execute(
                                        TripItem.__table__.update()
                                        .where(TripItem.id == item.id)
                                        .values(**update_vals)
                                    )
                                    logger.info(f"Enriched {item.type}:{item.title} with {len(photos or [])} photos")
                            except Exception as e:
                                logger.warning(f"Enrich failed for {item.title}: {e}")
                    logger.info(f"POI enrichment complete for trip {trip.id}")
            except Exception as e:
                logger.error(f"POI enrichment fatal: {e}")

        _asyncio.create_task(_enrich_items())

        budget_data = trip_json.get("budget", {})
        if budget_data:
            from sqlalchemy import select, update
            from app.models import Budget
            result = await db.execute(select(Budget).where(Budget.trip_id == trip.id))
            for b in result.scalars().all():
                if b.category in budget_data:
                    b.estimated = float(budget_data[b.category])
        await db.flush()
        logger.info(f"Trip saved: {trip.id} with {sum(len(d.get('items',[])) for d in trip_json.get('days',[]))} items")

    def _sse_event(self, event: str, data: dict) -> ServerSentEvent:
        return ServerSentEvent(
            event=event,
            data=json.dumps(data, ensure_ascii=False),
        )


# 全局单例
agent_service = AgentService()
