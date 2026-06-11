"""行程管理 API"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import (
    TripCreateRequest, TripUpdateRequest, TripItemCreateRequest,
    TripResponse, TripListResponse,
)
from app.services import trip_service

router = APIRouter()


@router.post("")
async def create_trip(
    req: TripCreateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trip = await trip_service.create_trip(db, user.id, req.model_dump(exclude_none=True))
    return {"code": 0, "message": "行程创建成功", "data": _trip_to_dict(trip)}


@router.get("")
async def list_trips(
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trips, total = await trip_service.list_trips(db, user.id, status, page, page_size)
    return {
        "code": 0,
        "data": {
            "items": [_trip_to_dict(t) for t in trips],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/{trip_id}")
async def get_trip(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trip = await trip_service.get_trip(db, trip_id, user.id)
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"code": 0, "data": _trip_to_dict(trip)}


@router.put("/{trip_id}")
async def update_trip(
    trip_id: str,
    req: TripUpdateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trip = await trip_service.update_trip(db, trip_id, user.id, req.model_dump(exclude_none=True))
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"code": 0, "message": "更新成功", "data": _trip_to_dict(trip)}


@router.delete("/{trip_id}")
async def delete_trip(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await trip_service.delete_trip(db, trip_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"code": 0, "message": "删除成功"}


@router.post("/{trip_id}/items")
async def add_trip_item(
    trip_id: str,
    req: TripItemCreateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await trip_service.add_trip_item(db, trip_id, user.id, req.model_dump(exclude_none=True))
    if not item:
        raise HTTPException(status_code=404, detail="行程不存在或无权限")
    return {"code": 0, "message": "添加成功", "data": _item_to_dict(item)}


@router.delete("/{trip_id}/items/{item_id}")
async def remove_trip_item(
    trip_id: str,
    item_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await trip_service.remove_trip_item(db, item_id, trip_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="行程项不存在")
    return {"code": 0, "message": "删除成功"}


@router.get("/{trip_id}/budget")
async def get_budget(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    budget = await trip_service.get_budget(db, trip_id, user.id)
    if budget is None:
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"code": 0, "data": budget}


def _trip_to_dict(trip) -> dict:
    return {
        "id": trip.id,
        "title": trip.title,
        "status": trip.status,
        "destination": trip.destination,
        "start_date": trip.start_date.isoformat() if trip.start_date else None,
        "end_date": trip.end_date.isoformat() if trip.end_date else None,
        "traveler_count": trip.traveler_count,
        "budget_total": float(trip.budget_total) if trip.budget_total else None,
        "cover_image": trip.cover_image,
        "route_tag": trip.route_tag,
        "weather_info": trip.weather_info,
        "summary": trip.summary,
        "tips": trip.tips,
        "special_notes": trip.special_notes,
        "notes": trip.notes,
        "created_at": trip.created_at.isoformat() if trip.created_at else None,
        "updated_at": trip.updated_at.isoformat() if trip.updated_at else None,
        "days": [
            {
                "id": d.id,
                "day_number": d.day_number,
                "date": d.date.isoformat() if d.date else None,
                "notes": d.notes,
                "weather": d.weather,
                "items": [_item_to_dict(i) for i in (d.items or [])],
            }
            for d in (trip.days or [])
        ],
    }


def _item_to_dict(item) -> dict:
    return {
        "id": item.id,
        "type": item.type,
        "title": item.title,
        "description": item.description,
        "start_time": item.start_time,
        "end_time": item.end_time,
        "duration_minutes": item.duration_minutes,
        "location": item.location,
        "lat": item.lat,
        "lng": item.lng,
        "price": float(item.price) if item.price else None,
        "currency": item.currency,
        "booking_url": item.booking_url,
        "booking_ref": item.booking_ref,
        "source": item.source,
        "status": item.status,
        "extra_data": item.extra_data,
        "photos": item.photos,
        "amap_poi_id": item.amap_poi_id,
        "sort_order": item.sort_order,
    }
