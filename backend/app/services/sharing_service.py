"""
行程分享与游记服务 — Phase 3

功能：
- 行程海报数据生成
- 公开分享链接
- AI 游记生成
"""

import logging
import secrets
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Trip, TripDay, TripItem

logger = logging.getLogger(__name__)


async def generate_share_link(db: AsyncSession, trip_id: str, user_id: str) -> dict:
    """生成行程分享链接"""
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.user_id == user_id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        return {"error": "行程不存在"}

    share_code = secrets.token_urlsafe(8)
    # 实际项目应将 share_code 存储以便后续查询

    return {
        "share_url": f"/share/{share_code}",
        "share_code": share_code,
        "trip_title": trip.title,
    }


async def generate_poster_data(db: AsyncSession, trip_id: str, user_id: str) -> dict:
    """
    生成行程海报所需数据（适合前端渲染为图片）

    Returns:
        {
            "title": "...",
            "destination": "...",
            "dates": "...",
            "stats": {"days": 5, "cities": 2, "expenses": 5000},
            "highlights": [景点列表],
            "qr_url": "...",
        }
    """
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(
            selectinload(Trip.days).selectinload(TripDay.items),
        )
    )
    trip = result.scalar_one_or_none()
    if not trip:
        return {"error": "行程不存在"}

    # 验证权限
    is_owner = trip.user_id == user_id

    # 收集亮点
    highlights = []
    all_items = []
    for day in (trip.days or []):
        for item in (day.items or []):
            all_items.append(item.title)
            if item.type == "poi":
                highlights.append({
                    "name": item.title,
                    "day": day.day_number,
                })

    return {
        "title": trip.title,
        "destination": trip.destination,
        "dates": f"{trip.start_date} - {trip.end_date}" if trip.start_date else "待定",
        "travelers": trip.traveler_count,
        "stats": {
            "days": len(trip.days) if trip.days else 0,
            "items": len(all_items),
            "budget": float(trip.budget_total) if trip.budget_total else None,
        },
        "highlights": highlights[:6],
        "all_items": all_items[:20],
    }


async def generate_travelogue(db: AsyncSession, trip_id: str, user_id: str) -> dict:
    """
    生成游记文本（基于行程数据 + AI 润色提示）

    Returns:
        {
            "title": "三亚5天亲子游记",
            "content": "Day 1: ...\nDay 2: ...",
            "prompt_for_ai": "请帮我润色以下游记...",
        }
    """
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(
            selectinload(Trip.days).selectinload(TripDay.items),
        )
    )
    trip = result.scalar_one_or_none()
    if not trip:
        return {"error": "行程不存在"}

    sections = []
    sections.append(f"# {trip.title}\n")

    if trip.destination:
        sections.append(f"目的地：{trip.destination}")
    if trip.start_date:
        sections.append(f"时间：{trip.start_date} - {trip.end_date}")
    sections.append("")

    for day in (trip.days or []):
        sections.append(f"## Day {day.day_number}")
        if day.date:
            sections.append(f"_{day.date}_")
        sections.append("")

        for item in (day.items or []):
            icon = {
                "flight": "✈️", "train": "🚄", "hotel": "🏨",
                "poi": "🎫", "food": "🍽️", "transport": "🚗",
            }.get(item.type, "📍")

            line = f"{icon} **{item.title}**"
            if item.start_time:
                line += f" ({item.start_time}"
                if item.end_time:
                    line += f" - {item.end_time}"
                line += ")"
            if item.description:
                line += f"\n  {item.description}"
            sections.append(line)
        sections.append("")

    content = "\n".join(sections)

    # 生成 AI 润色提示
    prompt = f"""请帮我把以下旅行记录润色为一篇生动的游记，要求：
1. 保持原文的所有事实信息
2. 增加情感色彩和个人感受
3. 每段不要太长，适合手机阅读
4. 加入适当的旅行小贴士

原始记录：
{content}
"""

    return {
        "title": trip.title,
        "content": content,
        "prompt_for_ai": prompt,
    }
