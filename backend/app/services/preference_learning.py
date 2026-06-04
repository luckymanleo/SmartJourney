"""
深度偏好学习引擎 — Phase 4

基于用户历史行程和行为，自动学习出行偏好，提供个性化推荐
"""

import logging
from collections import Counter
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Trip, TripDay, TripItem, UserPreference

logger = logging.getLogger(__name__)


async def learn_from_history(db: AsyncSession, user_id: str) -> dict:
    """
    分析用户历史行程，学习偏好模式

    Returns:
        {
            "trip_count": 5,
            "preferred_destinations": ["三亚", "成都"],
            "preferred_travel_days": {"avg": 4.2, "median": 4},
            "budget_range": {"min": 3000, "max": 12000, "avg": 6800},
            "common_interests": ["beach", "nature", "food"],
            "travel_pace": "relaxed",  # 推断的节奏偏好
            "seasonal_preference": "summer",
            "hotel_preference": {"avg_stars": 4, "avg_price": 650},
            "transport_preference": "flight",  # 飞机 vs 高铁 比例
            "recommendations": ["三亚夏日亲子游", "成都美食之旅"],
        }
    """
    result = await db.execute(
        select(Trip)
        .where(Trip.user_id == user_id)
        .options(selectinload(Trip.days).selectinload(TripDay.items))
        .order_by(Trip.created_at.desc())
        .limit(20)
    )
    trips = result.scalars().all()

    if not trips:
        return {
            "trip_count": 0,
            "message": "还没有出行记录，多出去走走获取个性化推荐吧！",
            "recommendations": ["三亚经典5日游", "成都美食3日游", "西安文化4日游"],
        }

    # 分析目的地偏好
    destinations = [t.destination for t in trips if t.destination]
    dest_counter = Counter(destinations)

    # 分析旅行天数
    days_list = []
    for t in trips:
        if t.start_date and t.end_date:
            delta = (t.end_date - t.start_date).days + 1
            days_list.append(delta)

    # 分析预算
    budgets = [float(t.budget_total) for t in trips if t.budget_total]

    # 分析行程项目类型偏好
    item_types = []
    hotel_prices = []
    hotel_stars = []
    for t in trips:
        for day in (t.days or []):
            for item in (day.items or []):
                item_types.append(item.type)
                if item.type == "hotel":
                    if item.price:
                        hotel_prices.append(float(item.price))
                    if item.extra_data:
                        stars = item.extra_data.get("stars") or item.extra_data.get("star")
                        if stars:
                            try:
                                hotel_stars.append(int(stars))
                            except (ValueError, TypeError):
                                pass

    type_counter = Counter(item_types)
    flight_count = type_counter.get("flight", 0)
    train_count = type_counter.get("train", 0)

    # 分析兴趣
    interests = []
    if "beach" in str(destinations).lower() or "三亚" in str(destinations):
        interests.append("beach")
    if any(c in str(destinations) for c in ["成都", "重庆", "长沙"]):
        interests.append("food")
    if any(c in str(destinations) for c in ["西安", "北京", "南京"]):
        interests.append("history")
    if any(c in str(destinations) for c in ["丽江", "大理", "桂林"]):
        interests.append("nature")

    # 推断旅行节奏
    items_per_day = []
    for t in trips:
        total_items = sum(len(day.items) for day in (t.days or []))
        total_days = len(t.days) if t.days else 1
        items_per_day.append(total_items / total_days)

    avg_items = sum(items_per_day) / len(items_per_day) if items_per_day else 0
    if avg_items <= 3:
        pace = "relaxed"
    elif avg_items <= 5:
        pace = "moderate"
    else:
        pace = "intense"

    # 生成推荐
    recommendations = _generate_recommendations(dest_counter, interests, budgets)

    # 同步到用户偏好表
    await _sync_preferences(db, user_id, {
        "flight_cabin": "economy",
        "train_type": "G" if train_count > flight_count else None,
        "hotel_stars": str(round(sum(hotel_stars) / len(hotel_stars))) if hotel_stars else None,
        "travel_pace": pace,
        "interests": interests,
        "budget_range": f"{min(budgets):.0f}-{max(budgets):.0f}" if budgets else None,
    })

    return {
        "trip_count": len(trips),
        "preferred_destinations": [d for d, _ in dest_counter.most_common(5)],
        "preferred_travel_days": {
            "avg": round(sum(days_list) / len(days_list), 1) if days_list else 0,
            "min": min(days_list) if days_list else 0,
            "max": max(days_list) if days_list else 0,
        },
        "budget_range": {
            "min": min(budgets) if budgets else 0,
            "max": max(budgets) if budgets else 0,
            "avg": round(sum(budgets) / len(budgets)) if budgets else 0,
        },
        "common_interests": interests,
        "travel_pace": pace,
        "transport_preference": "flight" if flight_count >= train_count else "train",
        "hotel_preference": {
            "avg_stars": round(sum(hotel_stars) / len(hotel_stars), 1) if hotel_stars else None,
            "avg_price": round(sum(hotel_prices) / len(hotel_prices)) if hotel_prices else None,
        },
        "recommendations": recommendations,
    }


def _generate_recommendations(dest_counter: Counter, interests: list, budgets: list) -> list:
    """基于偏好生成推荐"""
    recs = []

    # 最常去的目的地
    for dest, count in dest_counter.most_common(2):
        if count >= 2:
            recs.append(f"{dest}深度{count+1}日游")

    # 基于兴趣推荐
    interest_map = {
        "beach": "厦门鼓浪屿3日游",
        "food": "长沙美食3日游",
        "history": "洛阳古都4日游",
        "nature": "张家界仙境4日游",
    }
    for interest in interests:
        if interest in interest_map:
            recs.append(interest_map[interest])

    # 预算范围内推荐
    if budgets:
        avg_budget = sum(budgets) / len(budgets)
        if avg_budget < 3000:
            recs.append("周边周末2日游")
        elif avg_budget < 8000:
            recs.append("云南丽江大理5日游")
        else:
            recs.append("新疆伊犁草原7日游")

    # 确保有至少3个推荐
    default_recs = ["三亚经典5日游", "成都美食3日游", "西安文化4日游", "杭州西湖2日游"]
    for r in default_recs:
        if len(recs) < 4 and r not in recs:
            recs.append(r)

    return recs[:4]


async def _sync_preferences(db: AsyncSession, user_id: str, learned: dict):
    """将学习到的偏好同步到用户偏好表（不覆盖用户手动设置的）"""
    existing = await db.execute(
        select(UserPreference).where(
            UserPreference.user_id == user_id,
            UserPreference.category == "general",
            UserPreference.key == "auto_learned",
        )
    )
    if existing.scalar_one_or_none():
        return  # 已经学习过，不重复写入

    import json
    db.add(UserPreference(
        user_id=user_id,
        category="general",
        key="auto_learned",
        value=json.dumps(learned, ensure_ascii=False),
    ))
    await db.flush()


async def get_personalized_feed(db: AsyncSession, user_id: str) -> dict:
    """
    个性化推荐流 — 基于偏好推荐特价/促销

    Returns:
        {
            "hot_deals": [
                {"type": "flight", "title": "上海→三亚 特价 ¥380", "url": "..."},
            ],
            "because_you_like": [...],
            "trending": [...],
        }
    """
    learned = await learn_from_history(db, user_id)

    hot_deals = []
    for dest in learned.get("preferred_destinations", [])[:2]:
        hot_deals.append({
            "type": "flight",
            "title": f"前往 {dest} 的特价机票",
            "action": f"/search/flights?to={dest}",
        })
        hot_deals.append({
            "type": "hotel",
            "title": f"{dest} 热门酒店推荐",
            "action": f"/search/hotels?city={dest}",
        })

    because_you_like = []
    for interest in learned.get("common_interests", [])[:2]:
        interest_map = {
            "beach": {"title": "海滨度假精选", "query": "海边度假"},
            "food": {"title": "美食之旅精选", "query": "美食之旅"},
            "history": {"title": "文化古迹探索", "query": "古迹文化"},
            "nature": {"title": "自然风光之旅", "query": "自然风光"},
        }
        if interest in interest_map:
            because_you_like.append(interest_map[interest])

    trending = [
        {"title": "🔥 2026端午小长假推荐", "query": "端午3天游"},
        {"title": "🎉 暑期亲子游热门目的地", "query": "暑期亲子游"},
        {"title": "💰 本周限时特价酒店", "query": "特价酒店"},
    ]

    return {
        "hot_deals": hot_deals,
        "because_you_like": because_you_like,
        "trending": trending,
        "user_insights": {
            "trip_count": learned.get("trip_count", 0),
            "favorite_destinations": learned.get("preferred_destinations", []),
            "travel_style": learned.get("travel_pace", "moderate"),
        },
    }
