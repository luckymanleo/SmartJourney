"""认证 API"""

import json
from pathlib import Path
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
    success, msg, code = await send_verify_code(req.phone, req.platform)
    if not success:
        # 限流 → 429，其他失败 → 500
        status = 429 if "秒后再试" in msg else 500
        raise HTTPException(status_code=status, detail=msg)
    resp = {"code": 0, "message": msg, "data": {"expire_seconds": 300}}
    if code:
        resp["data"]["code"] = code
    return resp


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    if not await verify_code(req.phone, req.code, req.platform):
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


# ==================== 敏感词过滤 ====================

_SENSITIVE_FILE = Path(__file__).resolve().parent.parent.parent / "sensitive_words.json"

def _load_sensitive_words() -> list[str]:
    """从配置文件加载敏感词列表"""
    try:
        with open(_SENSITIVE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

_SENSITIVE_WORDS: list[str] = []


def _validate_nickname(name: str) -> str | None:
    """校验昵称，合法返回 None，不合法返回错误消息"""
    global _SENSITIVE_WORDS
    if not _SENSITIVE_WORDS:
        _SENSITIVE_WORDS = _load_sensitive_words()
    if len(name) < 2 or len(name) > 20:
        return "昵称需在 2-20 个字符之间"
    lower = name.lower()
    for w in _SENSITIVE_WORDS:
        if w.lower() in lower:
            return "昵称包含敏感词"
    return None


@router.put("/profile")
async def update_profile(
    req: ProfileUpdateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.nickname is not None:
        err = _validate_nickname(req.nickname)
        if err:
            raise HTTPException(status_code=400, detail=err)
        user.nickname = req.nickname
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url
    await db.flush()
    return {"code": 0, "message": "更新成功"}
