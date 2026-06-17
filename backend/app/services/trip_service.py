"""
行程服务 — 业务逻辑层
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Trip, TripDay, TripItem, Budget, UserPreference

logger = logging.getLogger(__name__)

BUDGET_CATEGORIES = ["transport", "lodging", "food", "tickets", "other"]


# ==================== 行程 CRUD ====================

async def create_trip(db: AsyncSession, user_id: str, data: dict) -> Trip:
    """创建行程并自动生成 TripDay"""
    trip = Trip(user_id=user_id, **data)
    db.add(trip)
    await db.flush()

    # 自动生成 TripDay
    if trip.start_date and trip.end_date:
        delta = (trip.end_date - trip.start_date).days + 1
        for i in range(delta):
            day_date = trip.start_date + timedelta(days=i)
            day = TripDay(
                trip_id=trip.id,
                day_number=i + 1,
                date=day_date,
            )
            db.add(day)

    # 自动生成 Budget 分类
    for cat in BUDGET_CATEGORIES:
        db.add(Budget(trip_id=trip.id, category=cat))

    await db.flush()
    # Refresh to load relationships eagerly before detaching
    await db.refresh(trip, ["days"])
    # Also load items for each day
    for day in trip.days:
        await db.refresh(day, ["items"])
    return trip


async def get_trip(db: AsyncSession, trip_id: str, user_id: str) -> Optional[Trip]:
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id, Trip.user_id == user_id)
        .options(
            selectinload(Trip.days).selectinload(TripDay.items),
            selectinload(Trip.budgets),
        )
    )
    return result.scalar_one_or_none()


async def list_trips(
    db: AsyncSession,
    user_id: str,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[Trip], int]:
    query = select(Trip).where(Trip.user_id == user_id)
    count_query = select(func.count(Trip.id)).where(Trip.user_id == user_id)

    if status:
        query = query.where(Trip.status == status)
        count_query = count_query.where(Trip.status == status)

    query = query.options(
        selectinload(Trip.days).selectinload(TripDay.items),
    ).order_by(Trip.sort_seq.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    trips = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return list(trips), total


async def update_trip(db: AsyncSession, trip_id: str, user_id: str, data: dict) -> Optional[Trip]:
    trip = await get_trip(db, trip_id, user_id)
    if not trip:
        return None
    for key, value in data.items():
        if value is not None and hasattr(trip, key):
            setattr(trip, key, value)
    trip.updated_at = datetime.utcnow()
    await db.flush()
    return trip


async def delete_trip(db: AsyncSession, trip_id: str, user_id: str) -> bool:
    trip = await get_trip(db, trip_id, user_id)
    if not trip:
        return False
    await db.delete(trip)
    await db.flush()
    return True


# ==================== 行程项 CRUD ====================

async def add_trip_item(db: AsyncSession, trip_id: str, user_id: str, data: dict) -> Optional[TripItem]:
    """添加行程项"""
    # 验证 trip 归属
    trip = await db.execute(
        select(Trip.id).where(Trip.id == trip_id, Trip.user_id == user_id)
    )
    if not trip.scalar_one_or_none():
        return None

    # 验证 day 归属
    day_id = data.pop("day_id")
    day = await db.execute(
        select(TripDay).where(TripDay.id == day_id, TripDay.trip_id == trip_id)
    )
    if not day.scalar_one_or_none():
        return None

    item = TripItem(trip_day_id=day_id, **data)
    db.add(item)
    await db.flush()
    return item


async def remove_trip_item(db: AsyncSession, item_id: str, trip_id: str, user_id: str) -> bool:
    """删除行程项"""
    result = await db.execute(
        select(TripItem)
        .join(TripDay, TripItem.trip_day_id == TripDay.id)
        .join(Trip, TripDay.trip_id == Trip.id)
        .where(TripItem.id == item_id, Trip.id == trip_id, Trip.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        return False
    await db.delete(item)
    await db.flush()
    return True


# ==================== 预算 ====================

async def get_budget(db: AsyncSession, trip_id: str, user_id: str) -> Optional[dict]:
    trip = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.user_id == user_id)
    )
    if not trip.scalar_one_or_none():
        return None

    result = await db.execute(
        select(Budget).where(Budget.trip_id == trip_id).order_by(Budget.category)
    )
    budgets = result.scalars().all()

    categories = []
    total_estimated = 0.0
    total_actual = 0.0
    for b in budgets:
        categories.append({
            "category": b.category,
            "estimated": float(b.estimated),
            "actual": float(b.actual),
            "currency": b.currency,
        })
        total_estimated += float(b.estimated)
        total_actual += float(b.actual)

    return {
        "total_estimated": total_estimated,
        "total_actual": total_actual,
        "categories": categories,
    }


# ==================== 时间冲突检测 ====================

def check_time_conflict(items: list[TripItem]) -> list[dict]:
    """检测行程项之间的时间冲突"""
    conflicts = []
    timed_items = [
        i for i in items
        if i.start_time and i.end_time and i.type != "hotel"
    ]
    timed_items.sort(key=lambda x: x.start_time)

    for i in range(len(timed_items) - 1):
        a, b = timed_items[i], timed_items[i + 1]
        if a.end_time > b.start_time:
            conflicts.append({
                "item_a": {"id": a.id, "title": a.title, "end_time": a.end_time},
                "item_b": {"id": b.id, "title": b.title, "start_time": b.start_time},
                "overlap": True,
            })

    return conflicts


# ==================== 用户偏好 ====================

async def get_preferences(db: AsyncSession, user_id: str) -> dict:
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    prefs = result.scalars().all()

    data = {
        "use_weather": True,
        "route_strategy": -1,
        "special_notes": "",
    }

    for p in prefs:
        if p.category == "general":
            if p.key == "use_weather":
                data["use_weather"] = p.value.lower() == "true"
            elif p.key == "route_strategy":
                try:
                    data["route_strategy"] = int(p.value)
                except (ValueError, TypeError):
                    pass
            elif p.key == "special_notes":
                data["special_notes"] = p.value

    return data


async def save_preferences(db: AsyncSession, user_id: str, data: dict) -> None:
    """保存用户偏好（全量替换）"""
    # 删除旧偏好 — 先 flush 确保 DB 侧清理完成，避免后续 INSERT 触发唯一约束冲突
    old = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    for p in old.scalars().all():
        await db.delete(p)
    await db.flush()

    # 写入新偏好
    if "use_weather" in data:
        db.add(UserPreference(user_id=user_id, category="general", key="use_weather",
                              value=str(data["use_weather"]).lower()))
    if "route_strategy" in data:
        db.add(UserPreference(user_id=user_id, category="general", key="route_strategy",
                              value=str(data["route_strategy"])))
    if "special_notes" in data and data["special_notes"]:
        db.add(UserPreference(user_id=user_id, category="general", key="special_notes",
                              value=data["special_notes"]))

    await db.flush()
