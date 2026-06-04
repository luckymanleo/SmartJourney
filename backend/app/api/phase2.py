"""
Phase 2 API — 混合交通、预警、票夹、补充出行方式
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.services.multimodal_service import compare_routes
from app.services.alert_service import check_trip_alerts
from app.services.ticket_service import get_ticket_wallet, generate_itinerary_summary

router = APIRouter()


# ==================== 混合交通比价 ====================

@router.get("/multimodal/compare")
async def multimodal_compare(
    origin: str = Query(..., description="出发城市"),
    destination: str = Query(..., description="到达城市"),
    date: str = Query(..., description="出发日期 YYYY-MM-DD"),
    budget: float = Query(None),
    prefer_direct: bool = Query(True),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """飞机 vs 高铁 vs 联程 智能比价"""
    result = await compare_routes(origin, destination, date, budget, prefer_direct)
    return {"code": 0, "data": result}


# ==================== 实时预警 ====================

@router.get("/alerts/{trip_id}")
async def trip_alerts(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """检查行程预警（天气/延误/值机提醒）"""
    result = await check_trip_alerts(db, trip_id, user.id)
    return {"code": 0, "data": result}


# ==================== 统一票夹 ====================

@router.get("/tickets/{trip_id}")
async def ticket_wallet(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取行程统一票夹"""
    result = await get_ticket_wallet(db, trip_id, user.id)
    if not result:
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"code": 0, "data": result}


@router.get("/itinerary/{trip_id}")
async def itinerary_summary(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成行程单摘要"""
    result = await generate_itinerary_summary(db, trip_id, user.id)
    if not result:
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"code": 0, "data": result}


# ==================== 补充出行方式搜索 ====================

@router.get("/search/bus")
async def search_bus(
    origin: str = Query(..., alias="from"),
    destination: str = Query(..., alias="to"),
    date: str = Query(...),
    user=Depends(get_current_user),
):
    """长途大巴/客运查询"""
    return {
        "code": 0,
        "data": {
            "message": "长途大巴查询将通过后续 MCP 工具接入",
            "source": "pending",
            "items": [],
        },
    }


@router.get("/search/car-rental")
async def search_car_rental(
    city: str = Query(...),
    pickup_date: str = Query(...),
    return_date: str = Query(...),
    user=Depends(get_current_user),
):
    """租车/自驾查询"""
    return {
        "code": 0,
        "data": {
            "message": "租车查询将通过后续 MCP 工具接入",
            "source": "pending",
            "items": [],
        },
    }


@router.get("/search/taxi")
async def search_taxi(
    origin: str = Query(..., alias="from"),
    destination: str = Query(..., alias="to"),
    city: str = Query(None),
    user=Depends(get_current_user),
):
    """打车/网约车预估"""
    # 复用市内交通查询
    from app.services.mcp_gateway import gateway
    try:
        result = await gateway.call_tool("transport", "search_transport", {
            "from_location": origin,
            "to": destination,
        })
        items = result.get("items", [])
        taxi_items = [i for i in items if i.get("type") in ("taxi", "ride_hailing")]
        return {"code": 0, "data": {"items": taxi_items or items}}
    except Exception:
        return {
            "code": 0,
            "data": {
                "message": "打车预估将通过 MCP 工具查询",
                "items": [],
            },
        }
