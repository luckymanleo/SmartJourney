"""
票夹与行程单服务 — Phase 2 P1

功能：
- 统一票夹：聚合行程中所有预订信息
- 行程单生成：导出为结构化数据（未来可生成 PDF）
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Trip, TripDay, TripItem


async def get_ticket_wallet(db: AsyncSession, trip_id: str, user_id: str) -> Optional[dict]:
    """
    获取统一票夹 — 聚合行程中所有交通和住宿票据

    Returns:
        {
            "trip_title": "...",
            "tickets": [
                {
                    "type": "flight",
                    "title": "MU5678 上海→三亚",
                    "date": "2026-06-01",
                    "time": "08:30-11:45",
                    "passenger": "旅行者",
                    "booking_ref": "...",
                    "booking_url": "...",
                    "price": 890.00,
                    "status": "confirmed",
                }
            ],
            "summary": {
                "total_tickets": 3,
                "total_amount": 2340.00,
            }
        }
    """
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id, Trip.user_id == user_id)
        .options(
            selectinload(Trip.days).selectinload(TripDay.items),
        )
    )
    trip = result.scalar_one_or_none()
    if not trip:
        return None

    tickets = []
    for day in (trip.days or []):
        for item in (day.items or []):
            if item.type in ("flight", "train", "hotel", "bus", "ferry"):
                tickets.append({
                    "type": item.type,
                    "title": item.title,
                    "date": day.date.isoformat() if day.date else None,
                    "time": f"{item.start_time or '--'}-{item.end_time or '--'}",
                    "price": float(item.price) if item.price else None,
                    "currency": item.currency,
                    "booking_ref": item.booking_ref,
                    "booking_url": item.booking_url,
                    "status": item.status,
                    "extra_data": item.extra_data,
                })

    total_amount = sum(t.get("price", 0) or 0 for t in tickets)

    return {
        "trip_id": trip.id,
        "trip_title": trip.title,
        "destination": trip.destination,
        "dates": {
            "start": trip.start_date.isoformat() if trip.start_date else None,
            "end": trip.end_date.isoformat() if trip.end_date else None,
        },
        "traveler_count": trip.traveler_count,
        "tickets": tickets,
        "summary": {
            "total_tickets": len(tickets),
            "total_amount": total_amount,
            "currency": "CNY",
        },
    }


async def generate_itinerary_summary(db: AsyncSession, trip_id: str, user_id: str) -> Optional[dict]:
    """
    生成行程单摘要 — 适合报销或分享

    Returns:
        {
            "header": {"title": "...", "destination": "...", "dates": "..."},
            "daily_breakdown": [...],
            "expense_summary": {...},
            "notes": "...",
        }
    """
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id, Trip.user_id == user_id)
        .options(
            selectinload(Trip.days).selectinload(TripDay.items),
            selectinload(Trip.budgets),
        )
    )
    trip = result.scalar_one_or_none()
    if not trip:
        return None

    daily = []
    total_cost = 0.0
    for day in (trip.days or []):
        items_list = []
        day_cost = 0.0
        for item in (day.items or []):
            price = float(item.price) if item.price else 0
            day_cost += price
            items_list.append({
                "type": item.type,
                "title": item.title,
                "time": f"{item.start_time or ''} - {item.end_time or ''}".strip(" -"),
                "price": price,
                "status": item.status,
            })
        total_cost += day_cost
        daily.append({
            "day": day.day_number,
            "date": day.date.isoformat() if day.date else None,
            "items": items_list,
            "day_total": day_cost,
        })

    expense = {}
    for b in (trip.budgets or []):
        expense[b.category] = {
            "estimated": float(b.estimated),
            "actual": float(b.actual),
        }

    return {
        "header": {
            "title": trip.title,
            "destination": trip.destination,
            "dates": f"{trip.start_date} - {trip.end_date}" if trip.start_date else "待定",
            "travelers": trip.traveler_count,
            "generated_at": datetime.utcnow().isoformat(),
        },
        "daily_breakdown": daily,
        "expense_summary": expense,
        "total_cost": total_cost,
        "budget_total": float(trip.budget_total) if trip.budget_total else None,
    }
