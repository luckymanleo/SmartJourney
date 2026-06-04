"""
钱包服务 — Phase 4+: 虚拟钱包充值/支付/退款/提现
"""
import logging
from datetime import datetime
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Wallet, Transaction, User

logger = logging.getLogger(__name__)


async def get_or_create_wallet(db: AsyncSession, user_id: str) -> Wallet:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    w = result.scalar_one_or_none()
    if not w:
        w = Wallet(user_id=user_id)
        db.add(w)
        await db.flush()
    return w


async def get_balance(db: AsyncSession, user_id: str) -> dict:
    w = await get_or_create_wallet(db, user_id)
    return {
        "balance": float(w.balance),
        "frozen_balance": float(w.frozen_balance),
        "available": float(w.balance) - float(w.frozen_balance),
        "currency": w.currency,
    }


async def charge(db: AsyncSession, user_id: str, amount: float, description: str = "充值") -> dict:
    w = await get_or_create_wallet(db, user_id)
    w.balance += amount
    t = Transaction(user_id=user_id, type="charge", amount=amount, balance_after=float(w.balance),
                    description=description, status="completed")
    db.add(t)
    await db.flush()
    return {"balance": float(w.balance), "transaction_id": t.id}


async def pay(db: AsyncSession, user_id: str, amount: float, trip_id: str = None, description: str = "消费") -> dict:
    w = await get_or_create_wallet(db, user_id)
    available = float(w.balance) - float(w.frozen_balance)
    if available < amount:
        return {"error": f"余额不足 (可用: ¥{available:.2f})"}
    w.balance -= amount
    t = Transaction(user_id=user_id, type="payment", amount=-amount, balance_after=float(w.balance),
                    related_trip_id=trip_id, description=description, status="completed")
    db.add(t)
    await db.flush()
    return {"balance": float(w.balance), "transaction_id": t.id}


async def refund(db: AsyncSession, user_id: str, amount: float, description: str = "退款") -> dict:
    w = await get_or_create_wallet(db, user_id)
    w.balance += amount
    t = Transaction(user_id=user_id, type="refund", amount=amount, balance_after=float(w.balance),
                    description=description, status="completed")
    db.add(t)
    await db.flush()
    return {"balance": float(w.balance), "transaction_id": t.id}


async def get_transactions(db: AsyncSession, user_id: str, page: int = 1, page_size: int = 20) -> dict:
    count_q = select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
    total = (await db.execute(count_q)).scalar() or 0

    q = select(Transaction).where(Transaction.user_id == user_id).order_by(desc(Transaction.created_at))\
        .offset((page-1)*page_size).limit(page_size)
    result = await db.execute(q)
    items = [
        {
            "id": t.id, "type": t.type, "amount": float(t.amount),
            "balance_after": float(t.balance_after), "description": t.description,
            "status": t.status, "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in result.scalars().all()
    ]
    return {"items": items, "total": total, "page": page}
