"""
MCP Manager — unified interface for remote HTTP MCP
v2: 每次 call_tool 使用独立临时 session，支持真并行
"""

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
    Call a remote MCP tool using a TEMPORARY independent session.
    通过 Semaphore(3) 控制并发度，平衡速度与服务器压力。
    """
    async with _call_semaphore:
        client = RemoteMCPClient(REMOTE_MCP_URL)
        try:
            ok = await asyncio.wait_for(client.connect(), timeout=25)
            if not ok:
                return {"items": [], "note": "MCP connection failed"}

            result = await client.call_tool(tool_name, {"query": query})
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
