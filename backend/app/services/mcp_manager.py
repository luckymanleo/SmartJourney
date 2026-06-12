"""
MCP Manager — unified interface for remote HTTP MCP
v5: 连接池 30min 生命周期 + session 过期自动清池
"""

import hashlib
import json
import logging
import asyncio
import time as _time
from app.services.remote_mcp import RemoteMCPClient
from app.config_loader import mcp_url

logger = logging.getLogger(__name__)

REMOTE_MCP_URL = mcp_url("fliggy_travel")

# 连接池（每条连接最多存活 30 分钟）
_POOL_MAX_AGE = 1800  # 30 min
_POOL_SEMAPHORE = asyncio.Semaphore(4)
_pool: list[tuple[RemoteMCPClient, float]] = []  # (client, created_at)
_pool_lock = asyncio.Lock()

# 调用并发限制
_CALL_SEMAPHORE = asyncio.Semaphore(2)

# MCP 结果缓存 TTL（秒）
_CACHE_TTL = {
    "search_flight":    300,
    "search_train":     600,
    "search_hotel":     1800,
    "search_poi":       3600,
    "search_food":      1800,
    "search_transport": 1800,
}
_DEFAULT_TTL = 300

_MAX_RETRIES = 2
_BASE_BACKOFF = 3


def _cache_key(tool_name: str, query: str) -> str:
    h = hashlib.md5(query.encode()).hexdigest()[:12]
    return f"mcp:{tool_name}:{h}"


async def _clear_pool():
    """清空池中所有连接（session 过期时调用）"""
    async with _pool_lock:
        for client, _ in _pool:
            try:
                await client.close()
            except Exception:
                pass
        _pool.clear()
    logger.info("MCP pool cleared (session expired)")


async def _get_or_create_client() -> RemoteMCPClient:
    """从连接池获取或创建一个已连接的 client（自动淘汰过期连接）"""
    now = _time.time()

    async with _pool_lock:
        while _pool:
            client, created = _pool.pop()
            if client.session_id and (now - created) < _POOL_MAX_AGE:
                return client
            # 过期或无 session → 丢弃
            await client.close()

    # 池空 → 创建新连接
    async with _POOL_SEMAPHORE:
        client = RemoteMCPClient(REMOTE_MCP_URL)
        try:
            ok = await asyncio.wait_for(client.connect(), timeout=20)
            if ok:
                return client
        except Exception as e:
            logger.warning(f"MCP pool: new connection failed ({e})")
            await client.close()
            raise
        await client.close()
        raise RuntimeError("MCP connection failed")


async def _return_client(client: RemoteMCPClient):
    """归还连接到池（最多 4 个）"""
    async with _pool_lock:
        if len(_pool) < 4:
            _pool.append((client, _time.time()))
        else:
            await client.close()


async def init_remote_mcp():
    """Startup: 预热连接池"""
    try:
        client = await _get_or_create_client()
        await _return_client(client)
        logger.info(f"MCP Manager: pool ready ({len(client.tools)} tools)")
    except Exception as e:
        logger.warning(f"MCP Manager: pool init failed ({e})")


def is_available() -> bool:
    return len(_pool) > 0


async def ensure_connected() -> bool:
    return True


async def call_tool(tool_name: str, query: str, max_retries: int | None = None) -> dict:
    """
    Call a remote MCP tool with Redis cache + 指数退避重试.
    Session 过期自动清池重建。
    max_retries=None 时使用全局 _MAX_RETRIES；=0 表示仅1次尝试不重试。
    """
    key = _cache_key(tool_name, query)
    ttl = _CACHE_TTL.get(tool_name, _DEFAULT_TTL)

    # 1) 缓存
    try:
        from app.redis_client import redis_client
        cached = await redis_client.get(key)
        if cached:
            result = json.loads(cached)
            if result.get("items"):
                logger.info(f"MCP cache HIT: {tool_name} ({len(result['items'])} items)")
                return result
    except Exception as e:
        logger.debug(f"MCP cache read skipped: {e}")

    # 2) 调 MCP（指数退避）
    last_error = None
    retries = max_retries if max_retries is not None else _MAX_RETRIES
    async with _CALL_SEMAPHORE:
        for attempt in range(retries + 1):
            if attempt > 0:
                delay = _BASE_BACKOFF * (2 ** (attempt - 1))
                logger.info(f"MCP retry {attempt}/{retries} for {tool_name}, waiting {delay}s...")
                await asyncio.sleep(delay)

            client = None
            try:
                client = await _get_or_create_client()
                result = await client.call_tool(tool_name, {"query": query})

                items = result.get("items", [])
                if items and not result.get("error"):
                    try:
                        await redis_client.setex(key, ttl, json.dumps(result, ensure_ascii=False))
                        logger.info(f"MCP cache SET: {tool_name} ({len(items)} items, ttl={ttl}s)")
                    except Exception as e:
                        logger.debug(f"MCP cache write skipped: {e}")
                    await _return_client(client)
                    return result

                # Session 过期 — 清空整个池，重建连接
                if result.get("note") == "MCP session expired, retrying...":
                    await client.close()
                    await _clear_pool()
                    continue

                last_error = result.get("note") or result.get("error") or "no results"
                await _return_client(client)

            except asyncio.TimeoutError:
                last_error = "timeout"
                if client:
                    await client.close()
            except Exception as e:
                last_error = str(e)[:80]
                if client:
                    await client.close()

    logger.warning(f"MCP {tool_name} failed after {retries+1} attempts: {last_error}")
    return {"items": [], "note": f"MCP {tool_name}: {last_error}"}


async def shutdown():
    """关闭连接池"""
    async with _pool_lock:
        for client, _ in _pool:
            try:
                await client.close()
            except Exception:
                pass
        _pool.clear()
