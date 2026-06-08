"""AI 智能规划 API — SSE 流式"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.auth import get_current_user
from app.database import get_db
from app.schemas import GeneratePlanRequest, OptimizePlanRequest
from app.services.agent_service import agent_service
from app.services import trip_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate")
async def generate_plan(
    req: GeneratePlanRequest,
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 智能生成行程规划（SSE 流式返回，支持取消）"""
    # 参数校验
    errors = []
    if not req.origin: errors.append("出发地")
    if not req.destination: errors.append("目的地")
    if not req.start_date: errors.append("出发日期")
    if not req.end_date: errors.append("返回日期")
    if not req.budget_total or req.budget_total <= 0: errors.append("预算")
    if not req.traveler_count or req.traveler_count < 1: errors.append("出行人数")
    if errors:
        raise HTTPException(status_code=400, detail=f"缺少必要参数：{'、'.join(errors)}")

    return EventSourceResponse(
        agent_service.generate_plan(
            db=db,
            user_id=user.id,
            query=req.query,
            origin=req.origin,
            destination=req.destination,
            start_date=req.start_date,
            end_date=req.end_date,
            traveler_count=req.traveler_count,
            budget_total=req.budget_total,
            preferences=req.preferences,
            save_as_trip=req.save_as_trip,
            use_weather=req.use_weather,
            route_count=req.route_count,
            route_strategy=req.route_strategy,
        )
    )


@router.post("/optimize")
async def optimize_plan(
    req: OptimizePlanRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """优化已有行程"""
    trip = await trip_service.get_trip(db, req.trip_id, user.id)
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")

    return EventSourceResponse(
        agent_service.generate_plan(
            db=db,
            user_id=user.id,
            query=req.query or "优化行程安排",
            origin=trip.origin or "",
            destination=trip.destination or "",
            start_date=trip.start_date.isoformat() if trip.start_date else "",
            end_date=trip.end_date.isoformat() if trip.end_date else "",
            traveler_count=trip.traveler_count,
            budget_total=float(trip.budget_total or 0),
            preferences=req.preferences,
            save_as_trip=True,
            use_weather=req.use_weather if req.use_weather is not None else True,
            route_count=1,
            route_strategy=-1,
        )
    )
