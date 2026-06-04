"""
混合交通智能组合服务 — Phase 2 P0

功能：
- 自动生成"飞机 vs 高铁 vs 飞机+高铁"联程比价方案
- 换乘时间衔接优化
- 中转城市短暂停留推荐
"""

import logging
from typing import Optional

from app.services.mcp_gateway import gateway, MCPAllSourcesFailed

logger = logging.getLogger(__name__)


async def compare_routes(
    origin: str,
    destination: str,
    date: str,
    budget: Optional[float] = None,
    prefer_direct: bool = True,
) -> dict:
    """
    混合交通比价：同时搜索飞机和高铁，生成对比方案

    Returns:
        {
            "origin": "上海",
            "destination": "三亚",
            "date": "2026-06-01",
            "options": [
                {
                    "type": "flight",
                    "mode": "direct",
                    "items": [...],
                    "cheapest_price": 580,
                    "fastest_duration": 195,
                    "recommendation": "最快，3小时直达"
                },
                {
                    "type": "train",
                    "mode": "direct", 
                    "items": [...],
                    ...
                },
                {
                    "type": "multimodal",
                    "mode": "flight+train",
                    "items": [
                        {"segment": 1, "type": "train", "from": "上海", "to": "广州", ...},
                        {"segment": 2, "type": "flight", "from": "广州", "to": "三亚", ...},
                    ],
                    "transfer_city": "广州",
                    "transfer_time_minutes": 120,
                    "total_price": 850,
                    "total_duration": 480,
                }
            ],
            "recommended": "flight",  # AI 推荐的最佳方案
        }
    """
    result = {
        "origin": origin,
        "destination": destination,
        "date": date,
        "options": [],
        "recommended": None,
    }

    options = []

    # 1. 直飞方案
    try:
        flights = await gateway.call_tool("flight", "search_flight", {
            "from_city": origin, "to": destination, "date_city": date,
        })
        flight_items = _extract_items(flights)
        if flight_items:
            prices = [f.get("price", 9999) for f in flight_items if f.get("price")]
            durations = [f.get("duration_minutes", 9999) for f in flight_items if f.get("duration_minutes")]
            options.append({
                "type": "flight",
                "mode": "direct",
                "label": "🛫 直飞",
                "items": flight_items[:5],
                "cheapest_price": min(prices) if prices else None,
                "fastest_duration": min(durations) if durations else None,
                "recommendation": _recommend_flight(flight_items),
            })
    except MCPAllSourcesFailed:
        logger.warning("Flight search failed in compare_routes")

    # 2. 高铁方案
    try:
        trains = await gateway.call_tool("train", "search_train", {
            "from_city": origin, "to": destination, "date_city": date,
        })
        train_items = _extract_items(trains)
        if train_items:
            prices = [t.get("price", 9999) or (t.get("seats", [{}])[0].get("price", 9999)) for t in train_items]
            durations = [t.get("duration_minutes", 9999) for t in train_items if t.get("duration_minutes")]
            options.append({
                "type": "train",
                "mode": "direct",
                "label": "🚄 高铁直达",
                "items": train_items[:5],
                "cheapest_price": min(prices) if prices else None,
                "fastest_duration": min(durations) if durations else None,
                "recommendation": _recommend_train(train_items),
            })
    except MCPAllSourcesFailed:
        logger.warning("Train search failed in compare_routes")

    # 3. 飞机+高铁联程方案（通过中转城市）
    transfer_cities = _suggest_transfer_cities(origin, destination)
    multimodal_options = []
    for transfer in transfer_cities[:2]:  # 最多尝试2个中转城市
        try:
            seg1_flights = await gateway.call_tool("flight", "search_flight", {
                "from_city": origin, "to": transfer, "date_city": date,
            })
            seg2_trains = await gateway.call_tool("train", "search_train", {
                "from_city": transfer, "to": destination, "date_city": date,
            })
            f_items = _extract_items(seg1_flights)
            t_items = _extract_items(seg2_trains)
            if f_items and t_items:
                f_price = f_items[0].get("price", 0) or 0
                t_price = (t_items[0].get("seats", [{}])[0].get("price", 0)) or t_items[0].get("price", 0) or 0
                f_dur = f_items[0].get("duration_minutes", 0) or 0
                t_dur = t_items[0].get("duration_minutes", 0) or 0
                multimodal_options.append({
                    "type": "multimodal",
                    "mode": "flight+train",
                    "label": f"✈️+🚄 经{transfer}",
                    "transfer_city": transfer,
                    "transfer_time_minutes": 120,  # 建议留2小时换乘
                    "segments": [
                        {"order": 1, "type": "flight", "from": origin, "to": transfer, "item": f_items[0]},
                        {"order": 2, "type": "train", "from": transfer, "to": destination, "item": t_items[0]},
                    ],
                    "total_price": float(f_price) + float(t_price),
                    "total_duration": (f_dur or 0) + (t_dur or 0) + 120,
                    "recommendation": f"经{transfer}中转，总价¥{float(f_price)+float(t_price):.0f}",
                })
        except MCPAllSourcesFailed:
            continue

    # 也尝试 高铁+飞机
    for transfer in transfer_cities[:2]:
        try:
            seg1_trains = await gateway.call_tool("train", "search_train", {
                "from_city": origin, "to": transfer, "date_city": date,
            })
            seg2_flights = await gateway.call_tool("flight", "search_flight", {
                "from_city": transfer, "to": destination, "date_city": date,
            })
            t_items = _extract_items(seg1_trains)
            f_items = _extract_items(seg2_flights)
            if t_items and f_items:
                t_price = (t_items[0].get("seats", [{}])[0].get("price", 0)) or t_items[0].get("price", 0) or 0
                f_price = f_items[0].get("price", 0) or 0
                multimodal_options.append({
                    "type": "multimodal",
                    "mode": "train+flight",
                    "label": f"🚄+✈️ 经{transfer}",
                    "transfer_city": transfer,
                    "transfer_time_minutes": 120,
                    "segments": [
                        {"order": 1, "type": "train", "from": origin, "to": transfer, "item": t_items[0]},
                        {"order": 2, "type": "flight", "from": transfer, "to": destination, "item": f_items[0]},
                    ],
                    "total_price": float(t_price) + float(f_price),
                    "total_duration": (t_items[0].get("duration_minutes", 0) or 0) + (f_items[0].get("duration_minutes", 0) or 0) + 120,
                })
        except MCPAllSourcesFailed:
            continue

    # 去重+排序
    seen = set()
    unique = []
    for opt in multimodal_options:
        key = f"{opt['mode']}_{opt['transfer_city']}"
        if key not in seen:
            seen.add(key)
            unique.append(opt)
    unique.sort(key=lambda x: x["total_price"])
    options.extend(unique[:3])

    result["options"] = options

    # 智能推荐
    result["recommended"] = _pick_best(options, budget, prefer_direct)

    return result


def _extract_items(result: dict) -> list:
    """从 MCP 结果中提取 items"""
    items = result.get("items", [])
    if not items:
        items = result.get("data", {}).get("items", [])
    return items or []


def _recommend_flight(items: list) -> str:
    if not items:
        return ""
    cheapest = min(items, key=lambda x: x.get("price", 9999) or 9999)
    fastest = min(items, key=lambda x: x.get("duration_minutes", 9999) or 9999)
    if cheapest.get("price") and fastest.get("duration_minutes"):
        return f"最低 ¥{cheapest.get('price'):.0f}，最快 {fastest.get('duration_minutes')}分钟"
    return ""


def _recommend_train(items: list) -> str:
    if not items:
        return ""
    return f"共 {len(items)} 个车次可选"


def _suggest_transfer_cities(origin: str, destination: str) -> list:
    """根据出发/目的地推荐中转城市"""
    # 简化版：常见中转枢纽
    hubs = {
        "华东": ["南京", "杭州", "合肥"],
        "华南": ["广州", "深圳", "长沙"],
        "华北": ["北京", "天津", "石家庄"],
        "华中": ["武汉", "郑州", "南昌"],
        "西南": ["成都", "重庆", "昆明"],
        "西北": ["西安", "兰州"],
    }
    # 根据距离远近来选择跨区中转
    all_cities = []
    for cities in hubs.values():
        for city in cities:
            if city != origin and city != destination:
                all_cities.append(city)
    return all_cities[:5]


def _pick_best(options: list, budget: Optional[float], prefer_direct: bool) -> Optional[str]:
    """智能推荐最佳方案"""
    if not options:
        return None

    # 优先直飞
    if prefer_direct:
        for opt in options:
            if opt["type"] == "flight" and opt["mode"] == "direct":
                if not budget or (opt.get("cheapest_price") and opt["cheapest_price"] <= budget):
                    return "flight_direct"

    # 直飞超预算 → 考虑高铁
    for opt in options:
        if opt["type"] == "train" and opt["mode"] == "direct":
            if not budget or (opt.get("cheapest_price") and opt["cheapest_price"] <= budget):
                return "train_direct"

    # 联程最省钱
    mult_opts = [o for o in options if o["type"] == "multimodal"]
    if mult_opts:
        return f"multimodal_{mult_opts[0].get('transfer_city', '')}"

    return options[0]["type"] if options else None
