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
from datetime import date, timedelta
from typing import AsyncGenerator, Optional

import httpx
from sse_starlette.sse import ServerSentEvent
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.config_loader import feature
from app.services import mcp_manager
from app.database import async_session_factory
from app.services.route_strategies import ROUTE_STRATEGIES

logger = logging.getLogger(__name__)
settings = get_settings()

# ==================== Agent System Prompt ====================

SYSTEM_PROMPT = """你是 SmartJourney（智旅）的智能旅行规划师。基于已搜索到的真实数据，生成一份完整的 JSON 旅行计划。

## 规则

- 每天安排 2-3 个景点，上午 1 个、下午 1-2 个
- 每个景点之间预留 30-60 分钟交通时间
- 午餐 12:00-13:00，晚餐 18:00-19:00
- 根据用户出行需求中的具体偏好安排合适的景点类型和节奏，不要凭空添加用户未提及的出行主题
- 总预算不超过用户预算的 110%
- 搜索结果中如有 booking_url 务必包含在行程中，无则设为空字符串 ""，严禁编造链接

## 输出格式

只输出如下 JSON，不要任何解释文字：

{
  "title": "出发地→目的地 M人N日游（严格格式：出发地→目的地+人数+天数，如\"深圳→上海 5人4日游\"，禁止在 title 中添加任何修饰性主题词）",
  "summary": "2-3句话概要",
  "tips": ["提示1", "提示2"],
  "days": [
    {
      "day_number": 1,
      "date": "2026-06-03",
      "items": [
        {"type": "flight|train|hotel|poi|food|transport|other", "title": "...", "start_time": "08:00", "end_time": "10:00", "price": 0, "booking_url": ""}
      ]
    }
  ],
  "budget": {"transport": 0, "lodging": 0, "food": 0, "tickets": 0, "other": 0}
}
"""

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
        _request = None,  # FastAPI Request — 用于检测客户端断开
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """
        生成行程规划 — SSE 流式返回
        v3: 后端主动构造查询 → 并行 MCP → 汇聚 → LLM 一次生成 → 异步保存
        """
        start_time = time.time()

        # 1. 构建用户消息
        user_message = self._build_user_message(
            query, origin, destination, start_date, end_date,
            traveler_count, budget_total, preferences,
        )
        yield self._sse_event("step", {"step": "analyzing", "text": "正在分析出行需求..."})

        # 2. 构造所有查询（往返交通 + 目的地信息 + 天气）
        queries = self._build_all_queries(origin, destination, start_date, end_date)
        yield self._sse_event("step", {
            "step": "searching",
            "text": f"正在并行搜索 {len(queries)} 个数据源..."
        })

        # 3. 并行执行所有查询（Semaphore(3) 控制并发，空结果自动重试1次）
        async def _run_one(name, q):
            try:
                result = await mcp_manager.call_tool(name, q)
                # 空结果重试一次（MCP 服务器间歇性不稳定）
                items = result.get("items", [])
                if not items and not result.get("error"):
                    logger.info(f"Retrying {name} (first attempt returned 0 items)")
                    await asyncio.sleep(1)
                    result = await mcp_manager.call_tool(name, q)
                return (name, q, result, None)
            except Exception as e:
                return (name, q, {"items": [], "note": str(e)[:80]}, str(e))

        # 工具调用事件
        for name, mcp_query in queries:
            yield self._sse_event("tool_call", {
                "name": name,
                "args": {"query": mcp_query},
            })

        results = await asyncio.gather(*[
            _run_one(name, q) for name, q in queries
        ])

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
        yield self._sse_event("step", {"step": "generating", "text": "正在汇总搜索结果生成行程..."})

        compact_results = []
        train_dep_items = []   # 去程火车
        train_ret_items = []   # 返程火车
        train_dep_count = train_ret_count = 0

        for name, mcp_query, result, error in results:
            summary = self._summarize_result(name, result)
            yield self._sse_event("tool_result", {"name": name, "summary": summary})

            if name == "search_train":
                # 按方向合并火车结果
                items = result.get("items", [])
                if "返" in mcp_query or destination in mcp_query.split("到")[0]:
                    train_ret_items.extend(items)
                    train_ret_count += 1
                else:
                    train_dep_items.extend(items)
                    train_dep_count += 1
            else:
                compact = self._compact_tool_result(name, result)
                compact_results.append(f"[{name}] {compact}")

        # 合并后的火车结果
        if train_dep_count:
            merged_dep = {"items": train_dep_items, "note": f"合并自 {train_dep_count} 次查询"}
            compact_results.append(f"[search_train 去程] {self._compact_tool_result('search_train', merged_dep)}")
        if train_ret_count:
            merged_ret = {"items": train_ret_items, "note": f"合并自 {train_ret_count} 次查询"}
            compact_results.append(f"[search_train 返程] {self._compact_tool_result('search_train', merged_ret)}")

        # 6. 构建 LLM prompt（一次性，不通过 tool_calls）
        search_context = "\n\n".join(compact_results)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
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
            resp = await self._call_llm(msg_copy, None)
            if resp:
                content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                tj = self._extract_json(content)
                if tj:
                    tj["route_tag"] = strategy["tag"]
                    tj["route_index"] = idx
                return tj or {"error": "parse_failed", "raw": content[:200]}
            return {"error": "llm_failed"}

        if strategies:
            gen_results = await asyncio.gather(*[
                _gen_one(s, i) for i, s in enumerate(strategies)
            ])
            for s, r in zip(strategies, gen_results):
                if r and not r.get("error") and r.get("days"):
                    trip_jsons.append(r)
                    yield self._sse_event("trip_data", r)
        else:
            resp = await self._call_llm(messages, None)
            if resp:
                content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                trip_json = self._extract_json(content)
                if trip_json:
                    if not trip_json.get("days"):
                        trip_json["days"] = []
                    trip_jsons.append(trip_json)
                    yield self._sse_event("trip_data", trip_json)
                elif content:
                    yield self._sse_event("chunk", {"text": content[:500]})

        if not trip_jsons:
            yield self._sse_event("chunk", {"text": "行程生成遇到问题，请重新规划"})

        elapsed = time.time() - start_time
        yield self._sse_event("done", {
            "elapsed_seconds": round(elapsed, 1),
            "routes_generated": len(trip_jsons),
            "route_count": route_count,
        })

        # 8. 异步保存（不阻塞 SSE 流）
        if trip_jsons and save_as_trip:
            async def _save_all():
                try:
                    async with async_session_factory() as save_db:
                        async with save_db.begin():
                            for tj in trip_jsons:
                                try:
                                    await self._save_trip(save_db, user_id, tj, origin, destination, start_date, end_date, traveler_count, budget_total, weather_summary)
                                except Exception as e:
                                    logger.error(f"Failed to save route {tj.get('route_tag')}: {e}")
                    logger.info(f"Async save complete: {len(trip_jsons)} routes")
                except Exception as e:
                    logger.error(f"Async save failed: {e}")
            asyncio.create_task(_save_all())

    # ==================== 私有方法 ====================

    def _build_user_message(self, query, origin, destination, start_date, end_date,
                            traveler_count, budget_total, preferences) -> str:
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

        parts.append("\n请按流程搜索并生成行程，最终输出完整的 JSON 行程方案。")
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

    def _build_all_queries(self, origin, destination, start_date, end_date) -> list[tuple[str, str]]:
        """从用户输入构造所有 MCP 查询列表（往返交通按类型拆分 + 目的地信息）"""
        queries = []
        dep_date = self._to_cn_date(start_date)
        ret_date = self._to_cn_date(end_date)

        if origin and destination:
            # 去程机票
            queries.append(("search_flight", f"{origin}到{destination}{dep_date}机票"))
            # 返程机票
            if ret_date:
                queries.append(("search_flight", f"{destination}到{origin}{ret_date}机票"))

            # 去程火车 — 按类型拆分（高铁/动车/普速各一次，结果更全）
            for ttype in ["高铁", "动车", "火车票"]:
                queries.append(("search_train", f"{origin}到{destination}{dep_date}{ttype}"))
            # 返程火车
            if ret_date:
                for ttype in ["高铁", "动车", "火车票"]:
                    queries.append(("search_train", f"{destination}到{origin}{ret_date}{ttype}"))

        if destination:
            queries.append(("search_hotel", f"{destination}酒店"))
            queries.append(("search_poi", f"{destination}景点"))
            queries.append(("search_food", f"{destination}美食"))

        return queries

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
                body["tool_choice"] = "none"  # 显式禁止工具调用，确保输出文本

            # 每次调用使用独立 client，避免 event loop 污染
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
        if not items:
            return json.dumps({"tool": tool_name, "count": 0, "note": result.get("note", "无结果")}, ensure_ascii=False)

        # 每种工具提取关键字段
        compact = {"tool": tool_name, "count": len(items), "items": []}
        key_fields = {
            "search_flight": ["title", "description", "price"],
            "search_train": ["title", "description", "price"],
            "search_hotel": ["title", "stars", "price_per_night", "location"],
            "search_poi": ["title", "level", "ticket_price", "description"],
            "search_food": ["title", "cuisine", "avg_price", "description"],
            "search_transport": ["title", "type", "duration", "price"],
        }
        fields = key_fields.get(tool_name, ["title", "description"])

        for item in items[:20]:  # 安全上限，覆盖几乎全部结果
            entry = {}
            for f in fields:
                val = item.get(f)
                if val is not None:
                    # 描述截断
                    if f == "description" and isinstance(val, str):
                        val = val[:120]
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

    async def _save_trip(self, db, user_id, trip_json, origin, destination, start_date, end_date, traveler_count, budget_total, weather_info=""):
        """保存行程、行程项、预算到数据库"""
        from app.services.trip_service import create_trip, add_trip_item
        trip = await create_trip(db, user_id, {
            "title": trip_json.get("title", f"{destination or '未命名'}旅行"),
            "origin": origin or trip_json.get("origin"),
            "destination": destination or trip_json.get("destination"),
            "start_date": start_date,
            "end_date": end_date,
            "traveler_count": traveler_count,
            "budget_total": budget_total,
            "route_tag": trip_json.get("route_tag") or None,
            "weather_info": weather_info or None,
        })
        trip_json["trip_id"] = trip.id
        for day_data in trip_json.get("days", []):
            day_num = day_data.get("day_number", 1)
            target_day = next((d for d in trip.days if d.day_number == day_num), None)
            if not target_day:
                continue
            for item_data in day_data.get("items", []):
                await add_trip_item(db, trip.id, user_id, {
                    "day_id": target_day.id,
                    "type": item_data.get("type", "other"),
                    "title": item_data.get("title", ""),
                    "start_time": item_data.get("start_time"),
                    "end_time": item_data.get("end_time"),
                    "price": item_data.get("price"),
                    "booking_url": item_data.get("booking_url"),
                    "extra_data": item_data.get("extra_data"),
                })
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
