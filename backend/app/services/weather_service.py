"""
天气服务 — 高德地图 API 封装
"""

import logging
from typing import Optional

import httpx

from app.config import get_settings
from app.redis_client import redis_client

logger = logging.getLogger(__name__)
settings = get_settings()

GAODE_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"


async def get_weather(city: str, days: int = 7) -> dict:
    """获取城市天气（带 Redis 缓存，30 分钟）"""
    cache_key = f"weather:{city}"
    cached = await redis_client.get(cache_key)
    if cached:
        import json
        return json.loads(cached)

    if not settings.gaode_api_key:
        return {"city": city, "error": "高德 API Key 未配置", "forecast": []}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(GAODE_WEATHER_URL, params={
                "key": settings.gaode_api_key,
                "city": city,
                "extensions": "all",  # 始终获取预报
            })
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "1":
                import json
                result = {
                    "city": city,
                    "current": data.get("lives", [{}])[0] if "lives" in data else None,
                    "forecast": data.get("forecasts", [{}])[0].get("casts", []) if "forecasts" in data else [],
                }
                await redis_client.setex(cache_key, 1800, json.dumps(result, ensure_ascii=False))
                return result
            else:
                return {"city": city, "error": data.get("info", "查询失败"), "forecast": []}
    except Exception as e:
        logger.error(f"Weather query failed: {e}")
        return {"city": city, "error": str(e), "forecast": []}
