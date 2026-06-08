"""
MCP Manager — unified interface for remote HTTP MCP
v3: 每次 call_tool 使用独立临时 session + Redis 结果缓存
"""

import hashlib
import json
import logging
import asyncio
from app.services.remote_mcp import RemoteMCPClient
from app.config_loader import mcp_url

logger = logging.getLogger(__name__)

REMOTE_MCP_URL = mcp_url("fliggy_travel")

# Global instance — used for health checks and is_available()
remote_client: RemoteMCPClient | None = None
_connected = False
_reconnect_lock = asyncio.Lock()
_last_reconnect_attempt = 0.0
# 限制并发 MCP 连接数（MCP 服务端不能处理太多并发）
_call_semaphore = asyncio.Semaphore(6)

# MCP 结果缓存 TTL（秒）— 按工具类型分档
_CACHE_TTL = {
    "search_flight":    300,   # 5 min — 机票价格实时波动
    "search_train":     600,   # 10 min — 火车票较稳定
    "search_hotel":     1800,  # 30 min — 酒店信息不变
    "search_poi":       3600,  # 60 min — 景点几乎不变
    "search_food":      1800,  # 30 min — 餐厅信息稳定
    "search_transport": 1800,  # 30 min — 市内交通稳定
}
_DEFAULT_TTL = 300  # 5 min 兜底


def _cache_key(tool_name: str, query: str) -> str:
    """生成缓存 key"""
    h = hashlib.md5(query.encode()).hexdigest()[:12]
    return f"mcp:{tool_name}:{h}"


async def init_remote_mcp():
    """Initialize remote MCP connection (called at startup)"""
    global remote_client, _connected
    try:
        remote_client = RemoteMCPClient(REMOTE_MCP_URL)
        _connected = await asyncio.wait_for(remote_client.connect(), timeout=15)
        if _connected:
            logger.info(f"MCP Manager: Remote FliggyTravel connected ({len(remote_client.tools)} tools)")
        else:
            logger.warning("MCP Manager: Remote connection failed, will use fallback")
    except Exception as e:
        logger.warning(f"MCP Manager: init failed ({e})")
        _connected = False


def is_available() -> bool:
    return _connected and remote_client is not None and remote_client.session_id is not None


async def ensure_connected() -> bool:
    """确保 MCP 已连接，否则尝试重连"""
    global _connected, _last_reconnect_attempt
    import time

    if is_available():
        return True

    async with _reconnect_lock:
        if is_available():
            return True

        now = time.time()
        if now - _last_reconnect_attempt < 10:
            return False

        _last_reconnect_attempt = now
        logger.info("MCP Manager: attempting reconnect...")
        try:
            if remote_client:
                await remote_client.close()
            remote_client = RemoteMCPClient(REMOTE_MCP_URL)
            _connected = await asyncio.wait_for(remote_client.connect(), timeout=15)
            if _connected:
                logger.info(f"MCP Manager: reconnected ({len(remote_client.tools)} tools)")
            return _connected
        except Exception as e:
            logger.warning(f"MCP Manager: reconnect failed ({e})")
            _connected = False
            return False


async def call_tool(tool_name: str, query: str) -> dict:
    """
    Call a remote MCP tool with Redis cache.
    缓存命中直接返回，未命中则调 MCP 并缓存结果。
    """
    key = _cache_key(tool_name, query)
    ttl = _CACHE_TTL.get(tool_name, _DEFAULT_TTL)

    # 1) 尝试从缓存读取
    try:
        from app.redis_client import redis_client
        cached = await redis_client.get(key)
        if cached:
            result = json.loads(cached)
            items = result.get("items", [])
            if items:
                logger.info(f"MCP cache HIT: {tool_name} ({len(items)} items, ttl={ttl}s)")
                return result
    except Exception as e:
        logger.debug(f"MCP cache read skipped: {e}")

    # 2) 缓存未命中 — 调 MCP
    async with _call_semaphore:
        client = RemoteMCPClient(REMOTE_MCP_URL)
        try:
            ok = await asyncio.wait_for(client.connect(), timeout=30)
            if not ok:
                return {"items": [], "note": "MCP connection failed"}

            result = await client.call_tool(tool_name, {"query": query})

            # 3) 写入缓存（只有成功且有结果时才缓存）
            items = result.get("items", [])
            if items and not result.get("error"):
                try:
                    await redis_client.setex(key, ttl, json.dumps(result, ensure_ascii=False))
                    logger.info(f"MCP cache SET: {tool_name} ({len(items)} items, ttl={ttl}s)")
                except Exception as e:
                    logger.debug(f"MCP cache write skipped: {e}")

            return result
        except asyncio.TimeoutError:
            return {"items": [], "note": f"MCP tool {tool_name} timed out"}
        except Exception as e:
            logger.warning(f"MCP tool {tool_name} call failed: {e}")
            return {"items": [], "note": f"MCP call failed: {str(e)[:80]}"}
        finally:
            await client.close()


async def shutdown():
    global remote_client, _connected
    if remote_client:
        await remote_client.close()
    _connected = False
