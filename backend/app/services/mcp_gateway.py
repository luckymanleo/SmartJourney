"""
MCP 网关 — 管理所有 MCP Server 连接，提供统一工具调用接口

功能：
- 多 Server 连接管理（子进程 stdio transport）
- 数据源路由（主数据源 + 自动降级）
- 查询结果缓存（Redis 5min TTL）
- 熔断机制（连续3次失败 → degraded → 5min 后重试）
- 健康检查
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import get_settings
from app.redis_client import redis_client
from app.services.remote_mcp import RemoteMCPClient

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== 数据模型 ====================

class ServerStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: list[str]
    env: dict[str, str]
    enabled: bool = True
    priority: int = 1
    timeout: int = 15
    max_retries: int = 3
    # Remote HTTP MCP
    url: str = None
    transport_type: str = "stdio"  # "stdio" | "http"


@dataclass
class MCPServerState:
    config: MCPServerConfig
    status: ServerStatus = ServerStatus.HEALTHY
    failures: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    total_calls: int = 0
    session: Optional[ClientSession] = None
    _read_stream: Any = None
    _write_stream: Any = None
    _remote_client: Optional[RemoteMCPClient] = None  # HTTP transport


# ==================== MCP Server 配置表 ====================

MCP_SERVERS: list[MCPServerConfig] = [
    MCPServerConfig(
        name="fliggy",
        command="uvx",
        args=["mcp-fliggy-travel"],
        env={
            "FLYAI_API_KEY": settings.flyai_api_key,
            "FLYAI_SIGN_SECRET": settings.flyai_sign_secret,
            "GAODE_API_KEY": settings.gaode_api_key,
        },
        priority=1,
    ),
    MCPServerConfig(
        name="meituan",
        command="uvx",
        args=["mcp-meituan-travel"],
        env={},
        priority=2,
    ),
    MCPServerConfig(
        name="hotel_smart",
        command="uvx",
        args=["mcp-hotel-smart"],
        env={},
        priority=1,
    ),
    MCPServerConfig(
        name="domestic_flight",
        command="uvx",
        args=["mcp-domestic-flight"],
        env={},
        priority=2,
    ),
    MCPServerConfig(
        name="travel_smart_plan",
        command="uvx",
        args=["mcp-travel-smart-plan"],
        env={
            "FLYAI_API_KEY": settings.flyai_api_key,
            "FLYAI_SIGN_SECRET": settings.flyai_sign_secret,
        },
        priority=1,
    ),
    # Remote HTTP MCP - ModelScope 飞猪旅行（URL 来自 .env）
    MCPServerConfig(
        name="fliggy_remote",
        command="",
        args=[],
        env={},
        priority=0,
        transport_type="http",
        url="",  # filled in initialize() from settings
    ),
]

# 数据源路由表
ROUTE_MAP: dict[str, list[str]] = {
    "flight":    ["fliggy_remote", "fliggy", "domestic_flight", "meituan"],
    "train":     ["fliggy_remote", "fliggy", "meituan"],
    "hotel":     ["fliggy_remote", "fliggy", "hotel_smart", "meituan"],
    "poi":       ["fliggy_remote", "fliggy", "meituan"],
    "food":      ["fliggy_remote", "fliggy", "meituan"],
    "transport": ["fliggy_remote", "fliggy"],
    "plan":      ["fliggy_remote", "fliggy", "travel_smart_plan"],
}

# 工具名映射: (server_name, local_tool) → mcp_tool_name
TOOL_MAP: dict[tuple[str, str], str] = {
    ("fliggy", "search_flight"):     "search_flight",
    ("fliggy", "search_train"):      "search_train",
    ("fliggy", "search_hotel"):      "search_hotel",
    ("fliggy", "search_poi"):        "search_poi",
    ("fliggy", "search_food"):       "search_food",
    ("fliggy", "search_transport"):  "search_transport",
    ("fliggy", "travel_plan"):       "travel_plan",
    ("meituan", "search"):           "meituan_travel_query",
    ("hotel_smart", "search_hotel"):   "search_hotels",
    ("hotel_smart", "search_marriott"): "search_marriott_hotels",
    ("domestic_flight", "search_flight"): "search_flight",
    ("travel_smart_plan", "plan"):    "travel_plan",
}


# ==================== MCP Gateway ====================

class MCPGateway:
    """MCP 集成层核心网关"""

    def __init__(self):
        self._servers: dict[str, MCPServerState] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """启动所有已启用的 MCP Server"""
        if self._initialized:
            return

        # 从 .env 注入远程 MCP URL
        mcp_url = settings.mcp_fliggy_url
        if mcp_url:
            for cfg in MCP_SERVERS:
                if cfg.name == "fliggy_remote" and not cfg.url:
                    cfg.url = mcp_url

        for cfg in MCP_SERVERS:
            if not cfg.enabled:
                logger.info(f"MCP[{cfg.name}]: 已禁用，跳过")
                continue
            state = MCPServerState(config=cfg)
            self._servers[cfg.name] = state
            await self._connect(state)

        self._initialized = True
        healthy = sum(1 for s in self._servers.values() if s.status == ServerStatus.HEALTHY)
        logger.info(f"MCP Gateway: {healthy}/{len(self._servers)} servers healthy")

    async def _connect(self, state: MCPServerState) -> None:
        """建立到 MCP Server 的连接"""
        cfg = state.config
        try:
            # HTTP transport（远程 MCP）
            if cfg.transport_type == "http" and cfg.url:
                client = RemoteMCPClient(cfg.url)
                ok = await asyncio.wait_for(client.connect(), timeout=15)
                if ok and client.tools:
                    state._remote_client = client
                    state.status = ServerStatus.HEALTHY
                    state.failures = 0
                    state.last_success_time = time.time()
                    tool_names = [t["name"] for t in client.tools]
                    logger.info(f"MCP[{cfg.name}]: HTTP已连接，可用工具: {tool_names}")
                else:
                    state.status = ServerStatus.OFFLINE
                    logger.warning(f"MCP[{cfg.name}]: HTTP连接失败（无工具或初始化错误）")
                return

            # stdio transport（本地子进程）
            required_keys = ["FLYAI_API_KEY", "FLYAI_SIGN_SECRET"]
            if any(k in cfg.env and not cfg.env[k] for k in required_keys):
                logger.warning(f"MCP[{cfg.name}]: API Key 未配置，跳过")
                state.status = ServerStatus.OFFLINE
                return

            params = StdioServerParameters(
                command=cfg.command,
                args=cfg.args,
                env={**cfg.env} if cfg.env else None,
            )
            ctx = stdio_client(params)
            read, write = await asyncio.wait_for(ctx.__aenter__(), timeout=10)
            state._read_stream = read
            state._write_stream = write
            state.session = ClientSession(read, write)
            await asyncio.wait_for(state.session.initialize(), timeout=10)

            tools = await asyncio.wait_for(state.session.list_tools(), timeout=10)
            tool_names = [t.name for t in tools.tools]
            state.status = ServerStatus.HEALTHY
            state.failures = 0
            state.last_success_time = time.time()
            logger.info(f"MCP[{cfg.name}]: 已连接，可用工具: {tool_names}")
        except asyncio.TimeoutError:
            state.status = ServerStatus.OFFLINE
            logger.warning(f"MCP[{cfg.name}]: 连接超时")
        except Exception as e:
            state.status = ServerStatus.OFFLINE
            state.failures += 1
            state.last_failure_time = time.time()
            logger.warning(f"MCP[{cfg.name}]: 连接失败 ({e})")

    async def _get_healthy_server(self, category: str, preferred: str = None) -> Optional[MCPServerState]:
        """按优先级获取可用 Server"""
        sources = ROUTE_MAP.get(category, [])
        if preferred:
            # 将首选数据源提到最前
            if preferred in sources:
                sources.remove(preferred)
            sources.insert(0, preferred)

        for name in sources:
            state = self._servers.get(name)
            if state and state.status == ServerStatus.HEALTHY:
                return state
        return None

    async def call_tool(
        self,
        category: str,
        tool_name: str,
        params: dict,
        preferred_source: str = None,
    ) -> dict:
        """
        调用 MCP 工具（带缓存 + 降级）
        """
        if not self._initialized:
            await self.initialize()

        # 快速检查：所有 server 都 offline 则立即返回
        all_offline = all(s.status == ServerStatus.OFFLINE for s in self._servers.values())
        if all_offline:
            return {"items": [], "source": "fallback", "note": "所有数据源未配置API Key"}

        cache_key = self._cache_key(category, tool_name, params)
        cached = await self._get_cache(cache_key)
        if cached is not None:
            return cached

        state = await self._get_healthy_server(category, preferred_source)
        if not state:
            return {"items": [], "source": "fallback", "note": "数据源暂不可用"}

        # 获取 MCP 工具名
        mcp_tool = TOOL_MAP.get((state.config.name, tool_name), tool_name)

        # 转换参数
        call_params = self._adapt_params(state.config.name, tool_name, params)

        # 调用
        start = time.time()
        try:
            # HTTP transport
            if state._remote_client is not None:
                result = await asyncio.wait_for(
                    state._remote_client.call_tool(mcp_tool, call_params),
                    timeout=state.config.timeout,
                )
                elapsed = time.time() - start
                state.failures = 0
                state.last_success_time = time.time()
                state.total_calls += 1
                logger.info(f"MCP[{state.config.name}].{mcp_tool} OK ({elapsed:.1f}s)")
                await self._set_cache(cache_key, result)
                return result

            # stdio transport
            result = await asyncio.wait_for(
                state.session.call_tool(mcp_tool, call_params),
                timeout=state.config.timeout,
            )
            elapsed = time.time() - start
            state.failures = 0
            state.last_success_time = time.time()
            state.total_calls += 1

            # 解析结果
            output = self._parse_result(result)
            logger.info(f"MCP[{state.config.name}].{mcp_tool} OK ({elapsed:.1f}s)")

            # 写入缓存
            await self._set_cache(cache_key, output)

            return output

        except asyncio.TimeoutError:
            state.failures += 1
            state.last_failure_time = time.time()
            logger.warning(f"MCP[{state.config.name}].{mcp_tool} TIMEOUT")
            return await self._fallback(category, tool_name, params, state.config.name)

        except Exception as e:
            state.failures += 1
            state.last_failure_time = time.time()
            logger.error(f"MCP[{state.config.name}].{mcp_tool} ERROR: {e}")

            # 熔断检查
            if state.failures >= state.config.max_retries:
                state.status = ServerStatus.DEGRADED
                logger.warning(f"MCP[{state.config.name}]: DEGRADED (连续 {state.failures} 次失败)")
                # 5 分钟后自动重试
                asyncio.create_task(self._auto_recover(state.config.name))

            return await self._fallback(category, tool_name, params, state.config.name)

    async def _fallback(self, category: str, tool_name: str, params: dict, failed_source: str) -> dict:
        """降级到备用数据源"""
        state = await self._get_healthy_server(category)
        if state and state.config.name != failed_source:
            logger.info(f"Fallback: {failed_source} → {state.config.name}")
            return await self.call_tool(category, tool_name, params)
        raise MCPAllSourcesFailed(f"所有数据源不可用: category={category}")

    async def _auto_recover(self, server_name: str, delay: int = 300):
        """自动恢复 degraded Server"""
        await asyncio.sleep(delay)
        state = self._servers.get(server_name)
        if state and state.status == ServerStatus.DEGRADED:
            logger.info(f"MCP[{server_name}]: 尝试自动恢复...")
            await self._connect(state)

    # ==================== 缓存 ====================

    def _cache_key(self, category: str, tool: str, params: dict) -> str:
        raw = json.dumps({"c": category, "t": tool, "p": params}, sort_keys=True, ensure_ascii=False)
        h = hashlib.md5(raw.encode()).hexdigest()
        return f"mcp:{h}"

    async def _get_cache(self, key: str) -> Optional[dict]:
        try:
            data = await redis_client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def _set_cache(self, key: str, value: dict) -> None:
        try:
            await redis_client.setex(key, settings.mcp_cache_ttl_seconds, json.dumps(value, ensure_ascii=False))
        except Exception:
            pass

    # ==================== 参数适配 ====================

    def _adapt_params(self, server: str, tool: str, params: dict) -> dict:
        """将统一参数转换为各 MCP Server 的特定格式"""
        if server == "fliggy":
            return self._adapt_fliggy(tool, params)
        elif server == "meituan":
            return self._adapt_meituan(tool, params)
        elif server == "hotel_smart":
            return self._adapt_hotel_smart(tool, params)
        return params

    def _adapt_fliggy(self, tool: str, params: dict) -> dict:
        """飞猪 MCP 工具参数适配"""
        if tool == "search_flight":
            return {
                "from": params.get("from_city", params.get("from", "")),
                "to": params.get("to", ""),
                "date": params.get("date_city", params.get("date", "")),
            }
        elif tool == "search_train":
            return {
                "from": params.get("from_city", params.get("from", "")),
                "to": params.get("to", ""),
                "date": params.get("date_city", params.get("date", "")),
            }
        elif tool == "search_hotel":
            city = params.get("city", "")
            keyword = params.get("keyword", "")
            return {"city": city, "keyword": keyword}
        elif tool == "search_poi":
            return {
                "city": params.get("city", ""),
                "keyword": params.get("keyword", ""),
            }
        elif tool == "search_food":
            return {
                "city": params.get("city", ""),
                "keyword": params.get("keyword", ""),
            }
        elif tool == "search_transport":
            return {
                "from": params.get("from_location", params.get("from", "")),
                "to": params.get("to", ""),
            }
        return params

    def _adapt_meituan(self, tool: str, params: dict) -> dict:
        city = params.get("city", params.get("from_city", params.get("from", "")))
        query_parts = []
        if params.get("from_city"):
            query_parts.append(f"{params['from_city']}到{params.get('to', '')}的")
            category_map = {
                "search_flight": "机票", "search_train": "火车票",
                "search_hotel": "酒店", "search_poi": "景点门票",
            }
            query_parts.append(category_map.get(tool, ""))
        elif tool == "search_hotel":
            query_parts.append(f"{params.get('keyword', '')}酒店")
        else:
            query_parts.append(params.get("keyword", params.get("query", "")))
        return {"city": city, "query": " ".join(filter(None, query_parts))}

    def _adapt_hotel_smart(self, tool: str, params: dict) -> dict:
        keyword = params.get("keyword", "")
        city = params.get("city", "")
        query = f"{city} {keyword}".strip()
        return {"query": query}

    # ==================== 结果解析 ====================

    def _parse_result(self, result) -> dict:
        """解析 MCP 工具返回结果"""
        if hasattr(result, "content") and result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    try:
                        return json.loads(content.text)
                    except json.JSONDecodeError:
                        return {"raw": content.text}
        if hasattr(result, "structuredContent") and result.structuredContent:
            return result.structuredContent
        return {"raw": str(result)}

    # ==================== 健康检查 ====================

    def get_health(self) -> dict:
        servers = {}
        for name, state in self._servers.items():
            servers[name] = {
                "status": state.status.value,
                "priority": state.config.priority,
                "failures": state.failures,
                "total_calls": state.total_calls,
            }
        return {"servers": servers}

    async def shutdown(self) -> None:
        """关闭所有 MCP Server 连接"""
        for state in self._servers.values():
            if state._remote_client:
                try:
                    await state._remote_client.close()
                except Exception:
                    pass
            if state._read_stream and state._write_stream:
                try:
                    pass
                except Exception:
                    pass
        logger.info("MCP Gateway: 已关闭")


class MCPAllSourcesFailed(Exception):
    """所有数据源不可用"""
    pass


# 全局单例
gateway = MCPGateway()
