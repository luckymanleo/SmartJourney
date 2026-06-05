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
    """生成 6 位验证码（mock 模式用）"""
    return f"{random.randint(100000, 999999)}"


async def send_verify_code(phone: str, platform: str = "mobile") -> tuple[bool, str, str | None]:
    """发送验证码

    - mock: 生成验证码，存 Redis，debug 时返回 code
    - aliyun: 调用 Dypnsapi（##code## 占位符），存 OutId 到 Redis
    - 限流 key 按平台隔离，PC/手机各自独立 60 秒限制

    Returns:
        (success, message, debug_info)
        debug_info: mock=验证码, aliyun=OutId, 失败=None
    """
    # Mock 模式：固定验证码 9999，不限频，方便开发调试
    if settings.sms_provider == "mock":
        code = "9999"
        code_key = f"sms_code:{platform}:{phone}"
        await redis_client.setex(code_key, 300, code)
        logger.info(f"[MOCK SMS] 手机号 {phone} 验证码: {code}")
        return True, "验证码已发送", code

    # 频率限制：每平台 60 秒内只能发一次（仅正式 SMS 提供商）
    rate_key = f"sms_rate:{platform}:{phone}"
    if await redis_client.exists(rate_key):
        ttl = await redis_client.ttl(rate_key)
        return False, f"请 {ttl} 秒后再试", None

    # Aliyun Dypnsapi：系统自动生成验证码，用 OutId 关联
    if settings.sms_provider == "aliyun":
        from app.services.sms_service import send_verify_code as _ali_send

        success, msg, out_id = await _ali_send(phone)
        if not success:
            return False, msg, None

        # 存储 OutId 用于后续 CheckSmsVerifyCode（5分钟过期）
        outid_key = f"sms_outid:{platform}:{phone}"
        await redis_client.setex(outid_key, 300, out_id)
        await redis_client.setex(rate_key, 60, "1")
        # 真实验证码由阿里云生成，不返回给前端
        return True, msg, None

    logger.warning(f"[SMS] 未知提供商: {settings.sms_provider}，跳过发送")
    return False, "短信服务未配置", None


async def verify_code(phone: str, code: str, platform: str = "mobile") -> bool:
    """验证验证码

    - mock: 从 Redis 读取验证码比对
    - aliyun: 从 Redis 获取 OutId，调用 CheckSmsVerifyCode API
    """
    # Mock 模式
    if settings.sms_provider == "mock":
        code_key = f"sms_code:{platform}:{phone}"
        stored = await redis_client.get(code_key)
        if stored and stored == code:
            await redis_client.delete(code_key)
            return True
        return False

    # Aliyun Dypnsapi
    if settings.sms_provider == "aliyun":
        from app.services.sms_service import check_verify_code as _ali_check

        outid_key = f"sms_outid:{platform}:{phone}"
        out_id = await redis_client.get(outid_key)
        if not out_id:
            logger.warning(f"[SMS] 未找到 OutId for {phone}")
            return False

        valid, msg = await _ali_check(phone, code, out_id)
        if valid:
            await redis_client.delete(outid_key)
        return valid

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

    user = User(phone=phone, nickname=f"旅行者_{phone[-4:]}")
    db.add(user)
    await db.flush()
    return user, True


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
