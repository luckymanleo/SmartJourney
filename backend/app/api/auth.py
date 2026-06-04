"""认证 API"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    SendCodeRequest, LoginRequest, ProfileUpdateRequest,
    TokenResponse, UserResponse, ErrorResponse,
)
from app.services.auth_service import (
    send_verify_code, verify_code, get_or_create_user,
    create_access_token, decode_access_token, get_user_by_id,
)

router = APIRouter()


async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """依赖注入 — 获取当前登录用户"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    user = await get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


@router.post("/send-code")
async def send_code(req: SendCodeRequest):
    success, msg, code = await send_verify_code(req.phone)
    if not success:
        raise HTTPException(status_code=429, detail=msg)
    resp = {"code": 0, "message": msg, "data": {"expire_seconds": 300}}
    if code:
        resp["data"]["code"] = code  # Debug mode: return code for frontend
    return resp


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    if not await verify_code(req.phone, req.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    user, is_new = await get_or_create_user(db, req.phone)
    token = create_access_token(user.id)

    return {
        "code": 0,
        "message": "登录成功",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 604800,
            "user": {
                "id": user.id,
                "phone": f"{req.phone[:3]}****{req.phone[-4:]}",
                "nickname": user.nickname,
                "avatar_url": user.avatar_url,
                "is_new": is_new,
            },
        },
    }


@router.get("/me")
async def get_me(user: UserResponse = Depends(get_current_user)):
    return {
        "code": 0,
        "data": {
            "id": user.id,
            "phone": f"{user.phone[:3]}****{user.phone[-4:]}" if len(user.phone) == 11 else user.phone,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.put("/profile")
async def update_profile(
    req: ProfileUpdateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.nickname is not None:
        user.nickname = req.nickname
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url
    await db.flush()
    return {"code": 0, "message": "更新成功"}
