"""
账单分账服务 — Phase 3

功能：
- 添加/删除消费记录
- AA 分账计算
- 结算汇总
"""

import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Trip, TripMember, TripExpense

logger = logging.getLogger(__name__)


async def add_expense(
    db: AsyncSession,
    trip_id: str,
    paid_by_user_id: str,
    category: str,
    amount: float,
    description: str = None,
    split_type: str = "equal",
    split_details: dict = None,
    expense_date: date = None,
) -> dict:
    """添加消费记录"""
    expense = TripExpense(
        trip_id=trip_id,
        paid_by_user_id=paid_by_user_id,
        category=category,
        description=description,
        amount=amount,
        split_type=split_type,
        split_details=split_details,
        expense_date=expense_date or datetime.utcnow().date(),
    )
    db.add(expense)
    await db.flush()

    return {
        "id": expense.id,
        "category": expense.category,
        "description": expense.description,
        "amount": float(expense.amount),
        "split_type": expense.split_type,
        "paid_by": paid_by_user_id,
    }


async def list_expenses(db: AsyncSession, trip_id: str) -> list[dict]:
    """列出所有消费记录"""
    result = await db.execute(
        select(TripExpense)
        .where(TripExpense.trip_id == trip_id)
        .order_by(TripExpense.created_at.desc())
    )
    expenses = result.scalars().all()
    return [
        {
            "id": e.id,
            "category": e.category,
            "description": e.description,
            "amount": float(e.amount),
            "currency": e.currency,
            "split_type": e.split_type,
            "split_details": e.split_details,
            "paid_by_user_id": e.paid_by_user_id,
            "expense_date": e.expense_date.isoformat() if e.expense_date else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in expenses
    ]


async def delete_expense(db: AsyncSession, expense_id: str, user_id: str) -> dict:
    """删除消费记录"""
    result = await db.execute(
        select(TripExpense).where(TripExpense.id == expense_id)
    )
    expense = result.scalar_one_or_none()
    if not expense:
        return {"error": "记录不存在"}

    # 只能删除自己支付的或具有 owner 权限
    if expense.paid_by_user_id != user_id:
        return {"error": "只能删除自己的消费记录"}

    await db.delete(expense)
    await db.flush()
    return {"message": "已删除"}


async def get_settlement(db: AsyncSession, trip_id: str) -> dict:
    """
    结算汇总 — 计算每人应付/应收

    Returns:
        {
            "total_expenses": 5000.00,
            "member_count": 3,
            "per_person_avg": 1666.67,
            "balances": [
                {
                    "user_id": "u1",
                    "nickname": "张三",
                    "paid": 3000.00,
                    "should_pay": 1666.67,
                    "balance": 1333.33,  # 正数=被欠，负数=欠别人
                }
            ],
            "settlements": [
                {"from": "u2", "to": "u1", "amount": 1333.33, "note": "请转账给张三"},
            ]
        }
    """
    # 获取所有消费
    result = await db.execute(
        select(TripExpense).where(TripExpense.trip_id == trip_id)
    )
    expenses = result.scalars().all()

    # 获取所有成员
    member_result = await db.execute(
        select(TripMember).where(TripMember.trip_id == trip_id)
    )
    members = member_result.scalars().all()

    if not members:
        return {"error": "没有成员"}

    member_count = len(members)
    total = sum(float(e.amount) for e in expenses)

    # 计算每人实际支付的金额
    paid_map: dict[str, float] = {}
    for m in members:
        paid_map[m.user_id] = 0.0

    for e in expenses:
        if e.split_type == "equal":
            per_person = float(e.amount) / member_count
            for m in members:
                paid_map[m.user_id] = paid_map.get(m.user_id, 0) + per_person
                if m.user_id == e.paid_by_user_id:
                    paid_map[m.user_id] = paid_map[m.user_id] - per_person + float(e.amount)
        elif e.split_type == "custom" and e.split_details:
            for uid, amt in e.split_details.items():
                paid_map[uid] = paid_map.get(uid, 0) + float(amt)
                if uid == e.paid_by_user_id:
                    paid_map[uid] = paid_map[uid] - float(amt)

    # 计算余额
    per_person_avg = total / member_count if member_count > 0 else 0
    balances = []
    for m in members:
        should_pay = per_person_avg
        paid = paid_map.get(m.user_id, 0)
        balances.append({
            "user_id": m.user_id,
            "nickname": m.nickname or "旅行者",
            "paid": round(paid, 2),
            "should_pay": round(should_pay, 2),
            "balance": round(paid - should_pay, 2),
        })

    # 生成结算建议
    settlements = _generate_settlements(balances)

    return {
        "total_expenses": round(total, 2),
        "member_count": member_count,
        "per_person_avg": round(per_person_avg, 2),
        "balances": balances,
        "settlements": settlements,
    }


def _generate_settlements(balances: list[dict]) -> list[dict]:
    """根据余额生成转账建议"""
    creditors = sorted(
        [b for b in balances if b["balance"] > 0.01],
        key=lambda x: -x["balance"],
    )
    debtors = sorted(
        [b for b in balances if b["balance"] < -0.01],
        key=lambda x: x["balance"],
    )

    settlements = []
    ci, di = 0, 0
    while ci < len(creditors) and di < len(debtors):
        credit = creditors[ci]
        debt = debtors[di]
        amount = min(credit["balance"], -debt["balance"])

        if amount > 0.01:
            settlements.append({
                "from_user_id": debt["user_id"],
                "from_nickname": debt["nickname"],
                "to_user_id": credit["user_id"],
                "to_nickname": credit["nickname"],
                "amount": round(amount, 2),
                "note": f"{debt['nickname']} 转账 {amount:.2f} 给 {credit['nickname']}",
            })

        creditors[ci]["balance"] -= amount
        debtors[di]["balance"] += amount

        if creditors[ci]["balance"] < 0.01:
            ci += 1
        if debtors[di]["balance"] > -0.01:
            di += 1

    return settlements
