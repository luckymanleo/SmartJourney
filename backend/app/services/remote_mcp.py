"""
Remote HTTP MCP Client — ModelScope Streamable HTTP transport
"""

import json
import logging
import httpx

logger = logging.getLogger(__name__)


class RemoteMCPClient:
    """HTTP-based MCP client for ModelScope streamable HTTP endpoints"""

    def __init__(self, url: str):
        self.url = url
        self.session_id = None
        self.tools: list[dict] = []
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(90))
        return self._client

    async def connect(self) -> bool:
        """Initialize MCP session: handshake → list tools"""
        try:
            client = await self._get_client()
            headers = {"Accept": "application/json, text/event-stream"}

            # Step 1: Initialize
            r = await client.post(self.url, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "smartjourney", "version": "1.0"}
                }
            }, headers=headers)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                logger.error(f"MCP init error: {data['error']}")
                return False

            self.session_id = r.headers.get("Mcp-Session-Id", "")
            if not self.session_id:
                logger.error("No session ID in response")
                return False

            # Step 2: Send initialized notification
            sess_headers = {**headers, "Mcp-Session-Id": self.session_id}
            await client.post(self.url, json={
                "jsonrpc": "2.0", "method": "notifications/initialized"
            }, headers=sess_headers)

            # Step 3: List tools
            r = await client.post(self.url, json={
                "jsonrpc": "2.0", "id": 2,
                "method": "tools/list", "params": {}
            }, headers=sess_headers)
            tools_data = r.json()
            if "result" in tools_data:
                self.tools = tools_data["result"].get("tools", [])
                names = [t["name"] for t in self.tools]
                logger.info(f"Remote MCP connected: {len(self.tools)} tools — {names}")
                return True
            else:
                logger.error(f"tools/list failed: {tools_data.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Remote MCP connect: {e}")
            return False

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool and return parsed result"""
        try:
            client = await self._get_client()
            r = await client.post(self.url, json={
                "jsonrpc": "2.0", "id": 99,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments}
            }, headers={
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": self.session_id
            })
            data = r.json()

            if "error" in data:
                return {"error": str(data["error"].get("message", data["error"]))[:200], "items": []}

            # Detect expired/invalid session from ModelScope
            if data.get("Code") == "InvalidArgument":
                logger.warning(f"MCP session expired: {data.get('Message','')[:100]}")
                self.session_id = None  # Force reconnect
                return {"items": [], "note": "MCP session expired, retrying..."}

            content = data.get("result", {}).get("content", [])
            for c in content:
                if c.get("type") == "text":
                    text = c["text"]
                    # Try JSON first, fall back to markdown
                    try:
                        return json.loads(text)
                    except (json.JSONDecodeError, TypeError):
                        from app.services.markdown_parser import _parse_markdown_response
                        items = _parse_markdown_response(text, tool_name)
                        return {"items": items, "raw_markdown": text[:8000]}
            return {"raw": str(data)[:500], "items": []}
        except Exception as e:
            logger.warning(f"Remote MCP tool {tool_name} failed: {e}")
            return {"error": str(e)[:200], "items": []}

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
