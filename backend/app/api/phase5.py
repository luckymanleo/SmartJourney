"""
管理后台 API — Phase 4+: 用户管理/行程统计/平台数据
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.auth import get_current_user
from app.database import get_db
from app.models import User, Trip, TripMember, Transaction, Wallet
from app.services import wallet_service

router = APIRouter()


@router.get("/admin/stats")
async def platform_stats(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """平台概览统计"""
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_trips = (await db.execute(select(func.count(Trip.id)))).scalar() or 0
    active_trips = (await db.execute(select(func.count(Trip.id)).where(Trip.status == "active"))).scalar() or 0
    completed_trips = (await db.execute(select(func.count(Trip.id)).where(Trip.status == "completed"))).scalar() or 0
    total_transactions = (await db.execute(select(func.count(Transaction.id)))).scalar() or 0
    total_wallet_balance = (await db.execute(select(func.sum(Wallet.balance)))).scalar() or 0

    return {"code": 0, "data": {
        "users": total_users,
        "trips": {"total": total_trips, "active": active_trips, "completed": completed_trips},
        "transactions": total_transactions,
        "total_balance": float(total_wallet_balance or 0),
    }}


@router.get("/admin/trips")
async def admin_trips(page: int = 1, page_size: int = 20,
                      user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """全部行程列表"""
    total = (await db.execute(select(func.count(Trip.id)))).scalar() or 0
    q = select(Trip).order_by(Trip.created_at.desc()).offset((page-1)*page_size).limit(page_size)
    result = await db.execute(q)
    items = [
        {"id": t.id, "title": t.title, "destination": t.destination, "status": t.status,
         "user_id": t.user_id, "budget_total": float(t.budget_total) if t.budget_total else None,
         "created_at": t.created_at.isoformat() if t.created_at else None}
        for t in result.scalars().all()
    ]
    return {"code": 0, "data": {"items": items, "total": total, "page": page}}


@router.get("/admin/users")
async def admin_users(page: int = 1, page_size: int = 20,
                      user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """全部用户列表"""
    total = (await db.execute(select(func.count(User.id)))).scalar() or 0
    q = select(User).order_by(User.created_at.desc()).offset((page-1)*page_size).limit(page_size)
    result = await db.execute(q)
    items = [
        {"id": u.id, "phone": f"{u.phone[:3]}****{u.phone[-4:]}" if len(u.phone)>=7 else u.phone,
         "nickname": u.nickname, "created_at": u.created_at.isoformat() if u.created_at else None}
        for u in result.scalars().all()
    ]
    return {"code": 0, "data": {"items": items, "total": total, "page": page}}


# ==================== 钱包接口 ====================

@router.get("/wallet/balance")
async def wallet_balance(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return {"code": 0, "data": await wallet_service.get_balance(db, user.id)}


@router.post("/wallet/charge")
async def wallet_charge(amount: float, description: str = "充值",
                         user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if amount <= 0:
        raise HTTPException(400, "充值金额必须大于0")
    if amount > 10000:
        raise HTTPException(400, "单次充值上限 ¥10,000")
    result = await wallet_service.charge(db, user.id, amount, description)
    return {"code": 0, "data": result}


@router.post("/wallet/pay")
async def wallet_pay(amount: float, trip_id: str = None, description: str = "消费",
                      user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await wallet_service.pay(db, user.id, amount, trip_id, description)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return {"code": 0, "data": result}


@router.get("/wallet/transactions")
async def wallet_transactions(page: int = 1, page_size: int = 20,
                               user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return {"code": 0, "data": await wallet_service.get_transactions(db, user.id, page, page_size)}
