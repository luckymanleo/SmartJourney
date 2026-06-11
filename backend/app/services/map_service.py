"""
地图服务 — 高德地图 Web API 封装

提供：地理编码、逆地理编码、路径规划（步行/骑行/驾车/公交）、
      POI 搜索（关键字/周边/详情）、距离测量

API 文档: https://lbs.amap.com/api/webservice/summary
"""

import hashlib
import json
import logging
import time
from typing import Optional

import httpx

from app.config import get_settings
from app.redis_client import redis_client

logger = logging.getLogger(__name__)
settings = get_settings()

# ── 高德 API 端点 ──────────────────────────────────────────────

_AMAP_BASE = "https://restapi.amap.com/v3"
_GEOCODE_URL = f"{_AMAP_BASE}/geocode/geo"
_REGEO_URL = f"{_AMAP_BASE}/geocode/regeo"
_DIRECTION_URL = f"{_AMAP_BASE}/direction"
_POI_TEXT_URL = f"{_AMAP_BASE}/place/text"
_POI_AROUND_URL = f"{_AMAP_BASE}/place/around"
_POI_DETAIL_URL = f"{_AMAP_BASE}/place/detail"
_DISTANCE_URL = f"{_AMAP_BASE}/distance"

# ── 缓存 TTL ───────────────────────────────────────────────────

_GEO_CACHE_TTL = 86400   # 24h — 地理坐标几乎不变
_POI_CACHE_TTL = 1800    # 30min
_DIR_CACHE_TTL = 300     # 5min — 路况可能变化

# ── 内部工具 ────────────────────────────────────────────────────

def _cache_key(prefix: str, *args) -> str:
    """生成缓存 key"""
    raw = "|".join(str(a) for a in args)
    h = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"map:{prefix}:{h}"


async def _cached_get(url: str, params: dict, ttl: int = _POI_CACHE_TTL) -> dict:
    """带缓存的 HTTP GET"""
    key = _cache_key("api", url, json.dumps(params, sort_keys=True))
    cached = await redis_client.get(key)
    if cached:
        try:
            return json.loads(cached)
        except (json.JSONDecodeError, TypeError):
            pass

    if not settings.gaode_api_key:
        return {"error": "高德 API Key 未配置"}

    params["key"] = settings.gaode_api_key
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "1":
                await redis_client.setex(key, ttl, json.dumps(data, ensure_ascii=False))
            return data
    except Exception as e:
        logger.error(f"Amap API error ({url}): {e}")
        return {"error": str(e)[:200]}


# ── 地理编码 ────────────────────────────────────────────────────

async def geocode(address: str, city: str = "") -> dict:
    """
    地址 → 经纬度

    Returns: {"lng": 116.397, "lat": 39.916, "address": "北京市东城区...", "adcode": "110101"}
    """
    params = {"address": address}
    if city:
        params["city"] = city

    data = await _cached_get(_GEOCODE_URL, params, _GEO_CACHE_TTL)
    geocodes = data.get("geocodes", [])
    if not geocodes:
        return {"error": f"未找到地址: {address}"}

    first = geocodes[0]
    location = first.get("location", "0,0").split(",")
    return {
        "lng": float(location[0]) if len(location) > 1 else 0,
        "lat": float(location[1]) if len(location) > 1 else 0,
        "address": first.get("formatted_address", address),
        "adcode": first.get("adcode", ""),
        "level": first.get("level", ""),
    }


async def regeocode(lng: float, lat: float) -> dict:
    """
    经纬度 → 地址

    Returns: {"address": "...", "city": "...", "district": "...", "pois": [...]}
    """
    params = {"location": f"{lng:.6f},{lat:.6f}", "extensions": "base"}
    data = await _cached_get(_REGEO_URL, params, _GEO_CACHE_TTL)

    regeo = data.get("regeocode", {})
    addr = regeo.get("addressComponent", {})
    return {
        "address": regeo.get("formatted_address", ""),
        "city": addr.get("city", "") or addr.get("province", ""),
        "district": addr.get("district", ""),
        "adcode": addr.get("adcode", ""),
        "pois": regeo.get("pois", [])[:10],
    }


# ── 路径规划 ────────────────────────────────────────────────────

_DIRECTION_MODES = {
    "walking": "walking",
    "bicycling": "bicycling",
    "driving": "driving",
    "transit": "transit",
}


async def direction(
    origin_lng: float,
    origin_lat: float,
    dest_lng: float,
    dest_lat: float,
    mode: str = "walking",
) -> dict:
    """
    两点间路径规划

    mode: walking | bicycling | driving | transit

    Returns: {"distance": 1200, "duration": 900, "steps": [...], "polyline": "..."}
    """
    if mode not in _DIRECTION_MODES:
        mode = "walking"

    url = f"{_DIRECTION_URL}/{_DIRECTION_MODES[mode]}"
    params = {
        "origin": f"{origin_lng:.6f},{origin_lat:.6f}",
        "destination": f"{dest_lng:.6f},{dest_lat:.6f}",
        "extensions": "base",
    }

    data = await _cached_get(url, params, _DIR_CACHE_TTL)
    route = data.get("route", {})

    # 不同模式返回结构略有不同
    if mode == "transit":
        paths = route.get("transits", [])
    else:
        paths = route.get("paths", [])

    if not paths:
        return {"error": "未找到路线", "mode": mode}

    best = paths[0]
    steps = [s.get("instruction", "") for s in best.get("steps", [])] if mode != "transit" else []

    return {
        "mode": mode,
        "distance": int(best.get("distance", 0)),
        "duration": int(best.get("duration", 0)),
        "steps": steps[:20],
        "polyline": best.get("polyline", ""),
    }


async def direction_by_address(
    origin_addr: str,
    dest_addr: str,
    mode: str = "walking",
) -> dict:
    """
    地址间路径规划（自动 geocode + direction）
    """
    orig = await geocode(origin_addr)
    dest = await geocode(dest_addr)

    if "error" in orig:
        return {"error": f"起点地址解析失败: {orig['error']}"}
    if "error" in dest:
        return {"error": f"终点地址解析失败: {dest['error']}"}

    result = await direction(orig["lng"], orig["lat"], dest["lng"], dest["lat"], mode)
    result["origin"] = {"address": origin_addr, "lng": orig["lng"], "lat": orig["lat"]}
    result["destination"] = {"address": dest_addr, "lng": dest["lng"], "lat": dest["lat"]}
    return result


# ── POI 搜索 ────────────────────────────────────────────────────

async def poi_text_search(
    keywords: str,
    city: str = "",
    citylimit: bool = False,
    offset: int = 20,
) -> dict:
    """
    关键字搜索 POI

    Returns: {"pois": [{"id": "...", "name": "...", "address": "...", "lng": ..., "lat": ..., ...}]}
    """
    params = {"keywords": keywords, "offset": min(offset, 50)}
    if city:
        params["city"] = city
    if citylimit:
        params["citylimit"] = "true"

    data = await _cached_get(_POI_TEXT_URL, params, _POI_CACHE_TTL)
    pois = data.get("pois", [])
    return {
        "total": int(data.get("count", 0)),
        "pois": [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("type", ""),
                "address": p.get("address", ""),
                "lng": float(p.get("location", "0,0").split(",")[0]) if p.get("location") else 0,
                "lat": float(p.get("location", "0,0").split(",")[1]) if p.get("location") and "," in p.get("location", "") else 0,
                "city": p.get("cityname", "") or p.get("city", ""),
                "distance": p.get("distance"),
                "tel": p.get("tel", ""),
                "rating": p.get("biz_ext", {}).get("rating") if isinstance(p.get("biz_ext"), dict) else None,
            }
            for p in pois
        ],
    }


async def poi_around_search(
    lng: float,
    lat: float,
    keywords: str = "",
    radius: int = 2000,
    offset: int = 20,
) -> dict:
    """
    周边 POI 搜索

    Returns: {"pois": [...], "center": {"lng": ..., "lat": ...}}
    """
    params = {
        "location": f"{lng:.6f},{lat:.6f}",
        "radius": min(radius, 50000),
        "offset": min(offset, 50),
    }
    if keywords:
        params["keywords"] = keywords

    data = await _cached_get(_POI_AROUND_URL, params, _POI_CACHE_TTL)
    pois = data.get("pois", [])
    return {
        "center": {"lng": lng, "lat": lat},
        "radius": radius,
        "total": int(data.get("count", 0)),
        "pois": [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("type", ""),
                "address": p.get("address", ""),
                "lng": float(p.get("location", "0,0").split(",")[0]) if p.get("location") else 0,
                "lat": float(p.get("location", "0,0").split(",")[1]) if p.get("location") and "," in p.get("location", "") else 0,
                "distance": int(p.get("distance", 0)),
                "tel": p.get("tel", ""),
            }
            for p in pois
        ],
    }


async def poi_detail(poi_id: str) -> dict:
    """POI 详情"""
    data = await _cached_get(_POI_DETAIL_URL, {"id": poi_id}, _POI_CACHE_TTL)
    pois = data.get("pois", [])
    if not pois:
        return {"error": f"POI not found: {poi_id}"}
    p = pois[0]
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "type": p.get("type", ""),
        "address": p.get("address", ""),
        "lng": float(p.get("location", "0,0").split(",")[0]) if p.get("location") else 0,
        "lat": float(p.get("location", "0,0").split(",")[1]) if p.get("location") and "," in p.get("location", "") else 0,
        "tel": p.get("tel", ""),
        "website": p.get("website", ""),
        "email": p.get("email", ""),
        "photos": [photo.get("url") for photo in p.get("photos", [])[:5]],
        "rating": p.get("biz_ext", {}).get("rating") if isinstance(p.get("biz_ext"), dict) else None,
        "deep_info": p.get("deep_info", {}),
    }


# ── 距离测量 ────────────────────────────────────────────────────

async def distance(origins: str, destination: str, mode: int = 0) -> dict:
    """
    批量距离测量

    origins:   "116.481,39.911|116.434,39.921|..."
    destination: "116.434,39.914"
    mode:       0=直线, 1=驾车, 2=公交, 3=步行

    Returns: {"results": [{"distance": 1234, "duration": 300}, ...]}
    """
    data = await _cached_get(_DISTANCE_URL, {
        "origins": origins,
        "destination": destination,
        "type": str(mode),
    }, _DIR_CACHE_TTL)
    results = data.get("results", [])
    return {
        "results": [
            {"distance": int(r.get("distance", 0)), "duration": int(r.get("duration", 0))}
            for r in results
        ],
    }


# ── 批量地理编码（行程用）─────────────────────────────────────────

async def batch_geocode(addresses: list[str]) -> list[dict]:
    """
    批量地理编码 — 用于行程中多个 POI 的坐标转换

    注意：高德 API 不支持真正的批量 geocode，此处用 asyncio.gather 并发请求
    """
    import asyncio
    results = await asyncio.gather(*[geocode(addr) for addr in addresses])
    return list(results)


# ── POI 照片富化 ───────────────────────────────────────────────

async def enrich_poi_photos(title: str, lng: float, lat: float) -> tuple[list[str] | None, str | None]:
    """
    用坐标 + 关键词搜索高德 POI，获取照片和 POI ID

    Returns: (photos: list[str] | None, amap_poi_id: str | None)
    """
    import re

    # 交通类用更大搜索半径和类型关键词
    transport_kw = None
    if any(kw in title for kw in ['机场', '航空', '航班']):
        transport_kw = '机场'
    elif any(kw in title for kw in ['站', '高铁', '动车', '火车']):
        transport_kw = '火车站'

    if transport_kw:
        result = await poi_around_search(lng, lat, transport_kw, radius=3000, offset=1)
    else:
        # 提取核心关键词（去掉括号、数字等）
        core = re.sub(r'[（(][^)）]*[)）]', '', title)
        core = re.sub(r'[GDTZK\\d]+\\d*次?', '', core).strip()
        result = await poi_around_search(lng, lat, core, radius=1000, offset=1)

    pois = result.get("pois", [])
    if not pois:
        return None, None

    best = pois[0]
    amap_id = best.get("id") or None

    # 获取详情（含照片）
    if amap_id:
        detail = await poi_detail(amap_id)
        if "error" not in detail:
            return detail.get("photos", []) or None, amap_id

    return None, amap_id
