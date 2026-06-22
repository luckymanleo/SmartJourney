"""
行程服务 — 业务逻辑层
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, case, extract
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


# ==================== 首页统计聚合 ====================

from datetime import date as date_type

async def get_trip_stats(
    db: AsyncSession,
    user_id: str,
    year: int,
    period: str = "year",  # year | quarter | month
    period_value: int | None = None,  # 季度 1-4 或 月份 1-12
) -> dict:
    """首页统计：按时间段聚合行程数据

    Returns:
        {
            "total_trips": int,        # 该时间段行程总数
            "active_trips": int,       # 进行中（planning + active）
            "total_budget": float,     # 总预算
            "monthly_trend": [...],    # 月度趋势（每个月 trip 数 + 预算）
            "category_breakdown": [...]  # 消费分类占比
        }
    """
    # 时间范围
    if period == "year":
        start = date_type(year, 1, 1)
        end = date_type(year, 12, 31)
    elif period == "quarter":
        if not period_value or period_value < 1 or period_value > 4:
            period_value = 1
        q_start_month = (period_value - 1) * 3 + 1
        start = date_type(year, q_start_month, 1)
        q_end_month = q_start_month + 2
        if q_end_month == 12:
            end = date_type(year, 12, 31)
        else:
            end = date_type(year, q_end_month + 1, 1) - timedelta(days=1)
    elif period == "month":
        if not period_value or period_value < 1 or period_value > 12:
            period_value = 1
        start = date_type(year, period_value, 1)
        if period_value == 12:
            end = date_type(year, 12, 31)
        else:
            end = date_type(year, period_value + 1, 1) - timedelta(days=1)
    else:
        start = date_type(year, 1, 1)
        end = date_type(year, 12, 31)

    # 1) 时间段内 trip 的基础统计
    trip_result = await db.execute(
        select(
            func.count(Trip.id),
            func.sum(Trip.budget_total),
            func.sum(
                case((Trip.status.in_(["planning", "active"]), 1), else_=0)
            ),
        ).where(
            Trip.user_id == user_id,
            Trip.start_date >= start,
            Trip.start_date <= end,
        )
    )
    total_trips, total_budget, active_trips = trip_result.one()
    total_trips = total_trips or 0
    total_budget = float(total_budget) if total_budget else 0
    active_trips = active_trips or 0

    # 2) 月度趋势 — 时间段内按月份分组
    trend_result = await db.execute(
        select(
            extract("month", Trip.start_date).label("month"),
            func.count(Trip.id).label("count"),
            func.coalesce(func.sum(Trip.budget_total), 0).label("budget"),
        ).where(
            Trip.user_id == user_id,
            Trip.start_date >= start,
            Trip.start_date <= end,
        ).group_by(extract("month", Trip.start_date)).order_by("month")
    )
    trend_map = {}
    for row in trend_result:
        m = int(row.month)
        trend_map[m] = {
            "month": m,
            "count": row.count,
            "budget": float(row.budget),
        }
    # 填充缺失月份
    months_range = range(start.month, end.month + 1)
    monthly_trend = [
        trend_map.get(m, {"month": m, "count": 0, "budget": 0})
        for m in months_range
    ]

    # 3) 消费分类占比 — 时间段内所有 trip_items.price 按 type 分组
    cat_result = await db.execute(
        select(
            TripItem.type.label("item_type"),
            func.coalesce(func.sum(TripItem.price), 0).label("total_price"),
        ).select_from(TripItem).join(TripDay, TripItem.trip_day_id == TripDay.id).join(
            Trip, TripDay.trip_id == Trip.id
        ).where(
            Trip.user_id == user_id,
            Trip.start_date >= start,
            Trip.start_date <= end,
        ).group_by(TripItem.type)
    )
    # 类型映射
    TYPE_LABELS = {
        "flight": "交通", "train": "交通", "bus": "交通",
        "car_rental": "交通", "ferry": "交通", "transport": "交通",
        "hotel": "住宿",
        "food": "餐饮",
        "poi": "门票",
    }
    merged: dict[str, float] = {}
    for row in cat_result:
        item_type = row.item_type
        price = float(row.total_price)
        label = TYPE_LABELS.get(item_type, "其他")
        merged[label] = merged.get(label, 0) + price
    # 保证 5 个分类都存在
    all_labels = ["交通", "住宿", "餐饮", "门票", "其他"]
    category_breakdown = [
        {"category": label, "amount": merged.get(label, 0)}
        for label in all_labels
    ]

    return {
        "total_trips": total_trips,
        "active_trips": active_trips,
        "total_budget": total_budget,
        "monthly_trend": monthly_trend,
        "category_breakdown": category_breakdown,
    }
