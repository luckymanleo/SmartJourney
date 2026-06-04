"""
异常处理与自动改签服务 — Phase 4

功能：
- 航班取消/延误后的替代方案搜索
- 智能改签推荐（最小时间损失 + 最小费用）
- 多机场周边搜索
- 权益提醒
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from app.services.mcp_gateway import gateway, MCPAllSourcesFailed

logger = logging.getLogger(__name__)


async def find_alternatives(
    from_city: str,
    to_city: str,
    original_date: str,
    transport_type: str = "flight",
    search_range_days: int = 2,
) -> dict:
    """
    查找替代交通方案

    当航班取消/延误时，搜索：
    1. 同日期其他航班
    2. 前后 N 天的航班
    3. 周边机场的航班
    4. 高铁作为替代方案

    Returns:
        {
            "original": {"from": "上海", "to": "三亚", "date": "2026-06-01"},
            "alternatives": [
                {
                    "type": "flight",
                    "date": "2026-06-01",
                    "airport": "浦东→凤凰",
                    "items": [...],
                    "tag": "同日期其他航班",
                },
                {
                    "type": "train",
                    "date": "2026-06-01",
                    "items": [...],
                    "tag": "高铁替代方案",
                },
            ],
            "recommendation": {...},
            "tips": ["建议优先选择同日期其他航班", "高铁直达也是一种选择"],
        }
    """
    alternatives = []

    if transport_type == "flight":
        # 1. 同日期其他航班
        try:
            result = await gateway.call_tool("flight", "search_flight", {
                "from_city": from_city, "to": to_city, "date_city": original_date,
            })
            items = _extract(result)
            if items:
                alternatives.append({
                    "type": "flight",
                    "date": original_date,
                    "airport": f"{from_city}→{to_city}",
                    "items": items[:5],
                    "tag": "同日期其他航班",
                })
        except MCPAllSourcesFailed:
            pass

        # 2. 前后 N 天
        orig_dt = date.fromisoformat(original_date)
        for offset in [-1, 1, -2, 2]:
            if len(alternatives) >= 4:
                break
            check_date = orig_dt + timedelta(days=offset)
            try:
                result = await gateway.call_tool("flight", "search_flight", {
                    "from_city": from_city, "to": to_city,
                    "date_city": check_date.isoformat(),
                })
                items = _extract(result)
                if items:
                    alternatives.append({
                        "type": "flight",
                        "date": check_date.isoformat(),
                        "airport": f"{from_city}→{to_city}",
                        "items": items[:3],
                        "tag": f"{'提前' if offset < 0 else '延后'} {abs(offset)} 天",
                    })
            except MCPAllSourcesFailed:
                continue

        # 3. 周边机场
        nearby_airports = _get_nearby_airports(from_city)
        for alt_airport in nearby_airports[:2]:
            try:
                result = await gateway.call_tool("flight", "search_flight", {
                    "from_city": alt_airport, "to": to_city, "date_city": original_date,
                })
                items = _extract(result)
                if items:
                    alternatives.append({
                        "type": "flight",
                        "date": original_date,
                        "airport": f"{alt_airport}→{to_city}",
                        "items": items[:3],
                        "tag": f"从 {alt_airport} 出发",
                    })
            except MCPAllSourcesFailed:
                continue

    # 4. 高铁替代
    try:
        result = await gateway.call_tool("train", "search_train", {
            "from_city": from_city, "to": to_city, "date_city": original_date,
        })
        items = _extract(result)
        if items:
            alternatives.append({
                "type": "train",
                "date": original_date,
                "items": items[:5],
                "tag": "高铁替代方案",
            })
    except MCPAllSourcesFailed:
        pass

    # 推荐
    recommendation = _pick_best_alternative(alternatives)

    return {
        "original": {"from": from_city, "to": to_city, "date": original_date, "type": transport_type},
        "alternatives": alternatives,
        "recommendation": recommendation,
        "tips": [
            "建议优先选择同日期同机场的其他航班",
            "高铁也是不错的替代选择",
            "改签前请确认退改签政策",
            "航班延误超过2小时可要求航司提供餐饮",
            "航班取消可要求全额退款或免费改签",
        ],
    }


def _extract(result: dict) -> list:
    items = result.get("items", [])
    if not items:
        items = result.get("data", {}).get("items", [])
    return items or []


def _get_nearby_airports(city: str) -> list:
    """获取周边机场城市"""
    nearby = {
        "上海": ["杭州", "南京", "无锡"],
        "北京": ["天津", "石家庄"],
        "广州": ["深圳", "珠海"],
        "成都": ["重庆"],
        "三亚": ["海口"],
    }
    return nearby.get(city, [])


def _pick_best_alternative(alternatives: list) -> Optional[dict]:
    """从替代方案中选最优"""
    same_day = [a for a in alternatives if a.get("tag") == "同日期其他航班"]
    if same_day:
        items = same_day[0].get("items", [])
        if items:
            cheapest = min(items, key=lambda x: x.get("price", 9999) or 9999)
            return {
                "type": "flight",
                "reason": "同日期最便宜替代",
                "item": cheapest,
            }

    if alternatives:
        return {
            "type": alternatives[0]["type"],
            "reason": alternatives[0]["tag"],
            "item": alternatives[0].get("items", [{}])[0] if alternatives[0].get("items") else None,
        }
    return None
