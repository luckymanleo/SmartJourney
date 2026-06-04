"""
多人协同服务 — Phase 3

功能：
- 组队创建/邀请/加入/退出
- 成员角色管理 (owner/editor/viewer)
- 位置共享
- 行程协作通知
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Trip, TripMember, User

logger = logging.getLogger(__name__)


def _generate_invite_code() -> str:
    return secrets.token_hex(4)[:8]


async def get_member_role(db: AsyncSession, trip_id: str, user_id: str) -> Optional[str]:
    """获取用户在行程中的角色"""
    result = await db.execute(
        select(TripMember.role).where(
            and_(TripMember.trip_id == trip_id, TripMember.user_id == user_id)
        )
    )
    row = result.first()
    return row[0] if row else None


async def ensure_member(db: AsyncSession, trip_id: str, user_id: str, required_role: str = "viewer"):
    """确保用户有指定权限，否则抛异常"""
    role = await get_member_role(db, trip_id, user_id)
    if not role:
        # 是 owner 吗？查 Trip
        trip = await db.execute(select(Trip.user_id).where(Trip.id == trip_id))
        owner = trip.scalar_one_or_none()
        if owner == user_id:
            return  # owner 有全部权限
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="你不是该行程的成员")

    role_hierarchy = {"owner": 3, "editor": 2, "viewer": 1}
    if role_hierarchy.get(role, 0) < role_hierarchy.get(required_role, 0):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="权限不足")


# ==================== 行程成员管理 ====================

async def create_collaboration(db: AsyncSession, trip_id: str, owner_id: str) -> dict:
    """为行程创建协作组（自动将 owner 加入）"""
    # 确保 Trip 存在且属于 owner
    trip = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.user_id == owner_id)
    )
    if not trip.scalar_one_or_none():
        return {"error": "行程不存在或无权限"}

    # 添加 owner 为成员
    existing = await db.execute(
        select(TripMember).where(
            and_(TripMember.trip_id == trip_id, TripMember.user_id == owner_id)
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "协作组已存在", "trip_id": trip_id}

    invite_code = _generate_invite_code()
    member = TripMember(
        trip_id=trip_id,
        user_id=owner_id,
        role="owner",
        invite_code=invite_code,
    )
    db.add(member)
    await db.flush()

    return {
        "trip_id": trip_id,
        "invite_code": invite_code,
        "members": [{"user_id": owner_id, "role": "owner"}],
    }


async def join_by_invite(db: AsyncSession, invite_code: str, user_id: str) -> dict:
    """通过邀请码加入行程"""
    result = await db.execute(
        select(TripMember).where(TripMember.invite_code == invite_code)
    )
    owner_member = result.scalar_one_or_none()
    if not owner_member:
        return {"error": "邀请码无效"}

    trip_id = owner_member.trip_id

    # 检查是否已是成员
    existing = await db.execute(
        select(TripMember).where(
            and_(TripMember.trip_id == trip_id, TripMember.user_id == user_id)
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "你已经是该行程的成员", "trip_id": trip_id}

    # 获取用户信息
    user = await db.execute(select(User).where(User.id == user_id))
    user_data = user.scalar_one_or_none()

    member = TripMember(
        trip_id=trip_id,
        user_id=user_id,
        role="editor",
        nickname=user_data.nickname if user_data else None,
        avatar_url=user_data.avatar_url if user_data else None,
    )
    db.add(member)
    await db.flush()

    return {
        "message": "加入成功",
        "trip_id": trip_id,
        "role": "editor",
    }


async def list_members(db: AsyncSession, trip_id: str) -> list[dict]:
    """列出行程所有成员"""
    result = await db.execute(
        select(TripMember, User.nickname, User.phone)
        .join(User, TripMember.user_id == User.id)
        .where(TripMember.trip_id == trip_id)
        .order_by(TripMember.joined_at)
    )
    rows = result.all()
    return [
        {
            "user_id": m.user_id,
            "role": m.role,
            "nickname": nickname or m.nickname or "旅行者",
            "phone": f"{phone[:3]}****{phone[-4:]}" if phone and len(phone) >= 7 else phone,
            "share_location": m.share_location,
            "last_lat": m.last_lat,
            "last_lng": m.last_lng,
            "location_updated_at": m.location_updated_at.isoformat() if m.location_updated_at else None,
        }
        for m, nickname, phone in rows
    ]


async def update_member_role(db: AsyncSession, trip_id: str, operator_id: str,
                             target_user_id: str, new_role: str) -> dict:
    """修改成员角色（仅 owner 可操作）"""
    await ensure_member(db, trip_id, operator_id, "owner")

    if new_role not in TripMember.ROLES:
        return {"error": f"无效角色，可选: {TripMember.ROLES}"}

    result = await db.execute(
        select(TripMember).where(
            and_(TripMember.trip_id == trip_id, TripMember.user_id == target_user_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return {"error": "成员不存在"}

    member.role = new_role
    await db.flush()
    return {"message": f"角色已更新为 {new_role}"}


async def leave_trip(db: AsyncSession, trip_id: str, user_id: str) -> dict:
    """退出行程"""
    result = await db.execute(
        select(TripMember).where(
            and_(TripMember.trip_id == trip_id, TripMember.user_id == user_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return {"error": "你不是该行程的成员"}

    if member.role == "owner":
        # Owner 不能直接退出，需先转让或删除行程
        return {"error": "行程创建者不能退出，可以转让所有权或删除行程"}

    await db.delete(member)
    await db.flush()
    return {"message": "已退出行程"}


async def remove_member(db: AsyncSession, trip_id: str, operator_id: str,
                        target_user_id: str) -> dict:
    """移除成员（owner 可移除任何人，editor 可移除 viewer）"""
    op_role = await get_member_role(db, trip_id, operator_id)
    # 检查是否为 trip owner
    trip = await db.execute(select(Trip.user_id).where(Trip.id == trip_id))
    owner_id = trip.scalar_one()
    if operator_id == owner_id:
        op_role = "owner"

    target_role = await get_member_role(db, trip_id, target_user_id)
    if not target_role:
        return {"error": "目标用户不是成员"}

    if op_role == "owner":
        pass  # owner 可移除任何人
    elif op_role == "editor" and target_role == "viewer":
        pass  # editor 可移除 viewer
    else:
        return {"error": "权限不足"}

    result = await db.execute(
        select(TripMember).where(
            and_(TripMember.trip_id == trip_id, TripMember.user_id == target_user_id)
        )
    )
    member = result.scalar_one_or_none()
    if member:
        await db.delete(member)
        await db.flush()
    return {"message": "已移除成员"}


# ==================== 位置共享 ====================

async def update_location(db: AsyncSession, trip_id: str, user_id: str,
                          lat: float, lng: float) -> dict:
    """更新成员位置"""
    result = await db.execute(
        select(TripMember).where(
            and_(TripMember.trip_id == trip_id, TripMember.user_id == user_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return {"error": "你不是该行程的成员"}

    member.last_lat = lat
    member.last_lng = lng
    member.share_location = True
    member.location_updated_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "位置已更新"}


async def get_member_locations(db: AsyncSession, trip_id: str, user_id: str) -> list[dict]:
    """获取所有开启位置共享的成员位置"""
    await ensure_member(db, trip_id, user_id)

    result = await db.execute(
        select(TripMember).where(
            and_(
                TripMember.trip_id == trip_id,
                TripMember.share_location == True,
                TripMember.last_lat.isnot(None),
            )
        )
    )
    members = result.scalars().all()
    return [
        {
            "user_id": m.user_id,
            "nickname": m.nickname or "旅行者",
            "lat": m.last_lat,
            "lng": m.last_lng,
            "updated_at": m.location_updated_at.isoformat() if m.location_updated_at else None,
        }
        for m in members
    ]


async def toggle_location_sharing(db: AsyncSession, trip_id: str, user_id: str,
                                  enabled: bool) -> dict:
    """开启/关闭位置共享"""
    result = await db.execute(
        select(TripMember).where(
            and_(TripMember.trip_id == trip_id, TripMember.user_id == user_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return {"error": "你不是该行程的成员"}

    member.share_location = enabled
    if not enabled:
        member.last_lat = None
        member.last_lng = None
    await db.flush()
    return {"message": f"位置共享已{'开启' if enabled else '关闭'}"}


# ==================== 邀请码管理 ====================

async def get_invite_code(db: AsyncSession, trip_id: str, user_id: str) -> dict:
    """获取邀请码"""
    result = await db.execute(
        select(TripMember).where(
            and_(TripMember.trip_id == trip_id, TripMember.user_id == user_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        # 检查是否是 trip owner
        trip = await db.execute(select(Trip.user_id).where(Trip.id == trip_id))
        owner_id = trip.scalar_one()
        if user_id == owner_id:
            # 自动成为 owner member
            code = _generate_invite_code()
            m = TripMember(trip_id=trip_id, user_id=user_id, role="owner", invite_code=code)
            db.add(m)
            await db.flush()
            return {"invite_code": code}
        return {"error": "无权限"}

    if not member.invite_code:
        member.invite_code = _generate_invite_code()
        await db.flush()

    return {"invite_code": member.invite_code}


async def refresh_invite_code(db: AsyncSession, trip_id: str, user_id: str) -> dict:
    """刷新邀请码"""
    result = await db.execute(
        select(TripMember).where(
            and_(TripMember.trip_id == trip_id, TripMember.user_id == user_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return {"error": "无权限"}

    member.invite_code = _generate_invite_code()
    await db.flush()
    return {"invite_code": member.invite_code}
