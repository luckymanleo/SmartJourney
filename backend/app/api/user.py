"""用户相关 API — 偏好设置"""

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.services import trip_service

router = APIRouter()


@router.get("/preferences")
async def get_preferences(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await trip_service.get_preferences(db, user.id)
    return {"code": 0, "data": prefs}


@router.put("/preferences")
async def save_preferences(
    preferences: dict = Body(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await trip_service.save_preferences(db, user.id, preferences)
    return {"code": 0, "message": "偏好保存成功"}
