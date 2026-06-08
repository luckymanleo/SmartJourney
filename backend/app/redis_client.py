"""Redis 客户端 — 懒加载 + 优雅降级，多 worker 安全"""

import asyncio
import logging
import time as _time
from typing import Optional

logger = logging.getLogger(__name__)


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


_redis = _MemoryRedis()
_connected = False
_connect_lock = asyncio.Lock()
_connect_attempted = False


async def _ensure_connected():
    global _redis, _connected, _connect_attempted

    if _connected:
        return

    async with _connect_lock:
        if _connected or _connect_attempted:
            return
        _connect_attempted = True

        try:
            from redis.asyncio import Redis
            from app.config import get_settings
            settings = get_settings()
            r = Redis.from_url(settings.redis_connection_url, encoding="utf-8", decode_responses=True)
            await asyncio.wait_for(r.ping(), timeout=3)
            _redis = r
            _connected = True
            logger.info(f"Redis lazy-connected: {settings.redis_url}")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), using in-memory cache")
            _redis = _MemoryRedis()
            _connected = False


class _LazyRedisProxy:
    """代理对象，首次使用时自动连接 Redis"""

    async def _ensure(self):
        await _ensure_connected()
        return _redis

    async def get(self, key: str):
        return await (await self._ensure()).get(key)

    async def set(self, key: str, value: str, ex: int = None):
        return await (await self._ensure()).set(key, value, ex=ex)

    async def setex(self, key: str, seconds: int, value: str):
        return await (await self._ensure()).setex(key, seconds, value)

    async def delete(self, key: str):
        return await (await self._ensure()).delete(key)

    async def exists(self, key: str) -> bool:
        return await (await self._ensure()).exists(key)

    async def ttl(self, key: str) -> int:
        return await (await self._ensure()).ttl(key)


redis_client = _LazyRedisProxy()


async def _init_redis():
    """兼容旧调用（lifespan 中调用），触发懒加载"""
    await _ensure_connected()


async def get_redis():
    await _ensure_connected()
    return _redis
