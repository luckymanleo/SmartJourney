"""Redis 客户端 — 带连接检测和优雅降级"""

import logging
import time as _time
from typing import Optional

logger = logging.getLogger(__name__)


# 内存回退缓存
class _MemoryRedis:
    """内存缓存，Redis 不可用时的降级方案"""
    _cache: dict = {}

    async def get(self, key: str) -> Optional[str]:
        if key in self._cache:
            value, expiry = self._cache[key]
            if _time.time() < expiry:
                return value
            del self._cache[key]
        return None

    async def set(self, key: str, value: str, ex: int = None):
        self._cache[key] = (value, _time.time() + (ex or 300))

    async def setex(self, key: str, seconds: int, value: str):
        await self.set(key, value, ex=seconds)

    async def delete(self, key: str):
        self._cache.pop(key, None)

    async def exists(self, key: str) -> bool:
        if key in self._cache:
            _, expiry = self._cache[key]
            if _time.time() < expiry:
                return True
            del self._cache[key]
        return False

    async def ttl(self, key: str) -> int:
        if key in self._cache:
            _, expiry = self._cache[key]
            remaining = int(expiry - _time.time())
            return max(0, remaining)
        return -2


# 尝试创建 Redis 客户端并检测连通性
redis_client = _MemoryRedis()


async def _init_redis():
    """初始化 Redis 连接（在 lifespan 中调用）"""
    global redis_client
    try:
        import asyncio
        from redis.asyncio import Redis
        from app.config import get_settings
        settings = get_settings()
        r = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        # 连接检测
        await asyncio.wait_for(r.ping(), timeout=2)
        redis_client = r
        logger.info(f"Redis connected: {settings.redis_url}")
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}), using in-memory cache")
        redis_client = _MemoryRedis()


async def get_redis():
    return redis_client
