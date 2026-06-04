"""
Phase 3 API — 多人协同、分账、分享、行李、保险、接送机
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.services import collaboration_service as collab
from app.services import expense_service as expense_svc
from app.services import sharing_service

router = APIRouter()


# ==================== 行程协作 ====================

@router.post("/trips/{trip_id}/collaboration")
async def create_collaboration(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """为行程创建协作组"""
    result = await collab.create_collaboration(db, trip_id, user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


@router.post("/collaboration/join")
async def join_by_invite(
    invite_code: str = Body(..., embed=True),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """通过邀请码加入行程"""
    result = await collab.join_by_invite(db, invite_code, user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


@router.get("/trips/{trip_id}/members")
async def list_members(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出成员"""
    members = await collab.list_members(db, trip_id)
    return {"code": 0, "data": {"members": members}}


@router.put("/trips/{trip_id}/members/{target_user_id}/role")
async def update_member_role(
    trip_id: str,
    target_user_id: str,
    new_role: str = Body(..., embed=True),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改成员角色"""
    result = await collab.update_member_role(db, trip_id, user.id, target_user_id, new_role)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


@router.post("/trips/{trip_id}/leave")
async def leave_trip(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """退出行程"""
    result = await collab.leave_trip(db, trip_id, user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


@router.delete("/trips/{trip_id}/members/{target_user_id}")
async def remove_member(
    trip_id: str,
    target_user_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """移除成员"""
    result = await collab.remove_member(db, trip_id, user.id, target_user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


@router.get("/trips/{trip_id}/invite-code")
async def get_invite_code(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取邀请码"""
    result = await collab.get_invite_code(db, trip_id, user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


@router.post("/trips/{trip_id}/invite-code/refresh")
async def refresh_invite_code(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """刷新邀请码"""
    result = await collab.refresh_invite_code(db, trip_id, user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


# ==================== 位置共享 ====================

@router.put("/trips/{trip_id}/location")
async def update_location(
    trip_id: str,
    lat: float = Body(...),
    lng: float = Body(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新位置"""
    result = await collab.update_location(db, trip_id, user.id, lat, lng)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


@router.get("/trips/{trip_id}/locations")
async def get_locations(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取成员位置"""
    locations = await collab.get_member_locations(db, trip_id, user.id)
    return {"code": 0, "data": {"members": locations}}


@router.put("/trips/{trip_id}/location-sharing")
async def toggle_location(
    trip_id: str,
    enabled: bool = Body(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """开关位置共享"""
    result = await collab.toggle_location_sharing(db, trip_id, user.id, enabled)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


# ==================== 账单分账 ====================

@router.post("/trips/{trip_id}/expenses")
async def add_expense(
    trip_id: str,
    category: str = Body(...),
    amount: float = Body(...),
    description: str = Body(None),
    split_type: str = Body("equal"),
    split_details: dict = Body(None),
    expense_date: str = Body(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加消费记录"""
    from datetime import date as dt_date
    ed = dt_date.fromisoformat(expense_date) if expense_date else None
    result = await expense_svc.add_expense(
        db, trip_id, user.id, category, amount,
        description, split_type, split_details, ed,
    )
    return {"code": 0, "data": result}


@router.get("/trips/{trip_id}/expenses")
async def list_expenses(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """消费记录列表"""
    expenses = await expense_svc.list_expenses(db, trip_id)
    return {"code": 0, "data": {"items": expenses}}


@router.delete("/trips/{trip_id}/expenses/{expense_id}")
async def delete_expense(
    trip_id: str,
    expense_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除消费记录"""
    result = await expense_svc.delete_expense(db, expense_id, user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


@router.get("/trips/{trip_id}/settlement")
async def get_settlement(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """结算汇总"""
    result = await expense_svc.get_settlement(db, trip_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


# ==================== 分享 ====================

@router.post("/trips/{trip_id}/share")
async def share_trip(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成分享链接"""
    result = await sharing_service.generate_share_link(db, trip_id, user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


@router.get("/trips/{trip_id}/poster")
async def poster_data(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取行程海报数据"""
    result = await sharing_service.generate_poster_data(db, trip_id, user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


@router.get("/trips/{trip_id}/travelogue")
async def travelogue(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成游记"""
    result = await sharing_service.generate_travelogue(db, trip_id, user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "data": result}


# ==================== 辅助服务 ====================

@router.get("/services/luggage")
async def luggage_service(
    city: str = Query(...),
    location: str = Query(None),
    user=Depends(get_current_user),
):
    """行李寄存点查询"""
    return {
        "code": 0,
        "data": {
            "message": "行李寄存服务将通过第三方 API 接入",
            "city": city,
            "items": [],
        },
    }


@router.get("/services/insurance")
async def insurance_recommend(
    trip_id: str = Query(None),
    days: int = Query(3),
    destination: str = Query("国内"),
    user=Depends(get_current_user),
):
    """旅行保险推荐"""
    plans = [
        {"name": "基础保障", "coverage": "意外伤害 10万 + 医疗 2万", "price": 15, "per": "天"},
        {"name": "全面保障", "coverage": "意外 30万 + 医疗 5万 + 航班延误", "price": 30, "per": "天"},
        {"name": "至尊保障", "coverage": "意外 50万 + 医疗 10万 + 行李丢失 + 紧急救援", "price": 60, "per": "天"},
    ]
    for p in plans:
        p["total_price"] = p["price"] * days
        p["days"] = days
    return {"code": 0, "data": {"plans": plans, "recommended": plans[1]["name"]}}


@router.get("/services/airport-transfer")
async def airport_transfer(
    airport: str = Query(...),
    destination: str = Query(...),
    date: str = Query(None),
    user=Depends(get_current_user),
):
    """接送机服务查询"""
    from app.services.mcp_gateway import gateway
    try:
        result = await gateway.call_tool("transport", "search_transport", {
            "from_location": airport,
            "to": destination,
        })
        items = result.get("items", [])
        return {"code": 0, "data": {"items": items}}
    except Exception:
        return {
            "code": 0,
            "data": {
                "message": "接送机服务将通过 MCP 工具查询",
                "items": [],
            },
        }
