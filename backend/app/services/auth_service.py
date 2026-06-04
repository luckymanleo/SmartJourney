"""
认证服务 — 手机号 + 验证码登录，JWT Token
"""

import logging
import random
import time
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import User
from app.redis_client import redis_client

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== 验证码 ====================

def _generate_code() -> str:
    """生成 6 位验证码"""
    return f"{random.randint(100000, 999999)}"


async def send_verify_code(phone: str) -> tuple[bool, str]:
    """发送验证码

    Returns:
        (success, message)
    """
    # 频率限制：60秒内只能发一次
    rate_key = f"sms_rate:{phone}"
    if await redis_client.exists(rate_key):
        ttl = await redis_client.ttl(rate_key)
        return False, f"请 {ttl} 秒后再试", None

    code = _generate_code()
    code_key = f"sms_code:{phone}"

    # Mock 模式：输出到日志
    if settings.sms_provider == "mock":
        logger.info(f"[MOCK SMS] 手机号 {phone} 验证码: {code}")
    else:
        # TODO: 接入真实短信服务（阿里云/腾讯云）
        logger.info(f"[SMS] 发送验证码到 {phone}: {code}")

    # 存储验证码（5分钟过期）
    await redis_client.setex(code_key, 300, code)
    # 频率限制（60秒）
    await redis_client.setex(rate_key, 60, "1")

    return True, "验证码已发送", code if settings.debug else None


async def verify_code(phone: str, code: str) -> bool:
    """验证验证码"""
    code_key = f"sms_code:{phone}"
    stored = await redis_client.get(code_key)
    if stored and stored == code:
        await redis_client.delete(code_key)
        return True
    return False


# ==================== JWT ====================

def create_access_token(user_id: str) -> str:
    """生成 JWT"""
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_expire_seconds)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """解析 JWT"""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


# ==================== 用户服务 ====================

async def get_or_create_user(db: AsyncSession, phone: str) -> tuple[User, bool]:
    """获取或创建用户

    Returns:
        (user, is_new)
    """
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if user:
        user.updated_at = datetime.utcnow()
        return user, False

    user = User(phone=phone)
    db.add(user)
    await db.flush()
    return user, True


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
