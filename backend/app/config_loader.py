"""
配置加载器 — 从 config.json 读取运行时可配置项
避免在代码中硬编码 URLs, 策略, 目的地等
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


def _config_path() -> Path:
    """按优先级查找 config.json"""
    paths = [
        Path(os.environ.get("SJ_CONFIG", "")),
        Path(__file__).parent.parent / "config.json",  # backend/config.json
    ]
    for p in paths:
        if p.is_file():
            return p
    raise FileNotFoundError("config.json not found")


@lru_cache(maxsize=1)
def load_config() -> dict:
    """加载完整配置（缓存）"""
    with open(_config_path(), "r", encoding="utf-8") as f:
        return json.load(f)


# ==================== 便捷访问函数 ====================

def mcp_url(name: str = "fliggy_travel") -> str:
    """获取 MCP 远程 URL"""
    return load_config()["mcp"]["remote"].get(name, "")


def popular_destinations() -> list[dict[str, Any]]:
    """热门目的地列表"""
    return load_config()["popular_destinations"]


def route_strategies() -> list[dict[str, str]]:
    """路线策略列表"""
    return load_config()["route_strategies"]


def cors_debug_origins() -> list[str]:
    """Debug 模式 CORS 白名单"""
    return load_config()["cors"]["debug_origins"]


def feature(key: str, default=None) -> Any:
    """功能配置项"""
    return load_config()["features"].get(key, default)


def city_search_aliases() -> dict[str, dict[str, str]]:
    """城市名→搜索词映射（小城市站名/机场名与城市名不一致时使用）"""
    return load_config().get("city_search_aliases", {})
