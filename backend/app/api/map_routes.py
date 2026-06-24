"""
地图 API — 地理编码、路径规划、POI 搜索、行程地图聚合
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.auth import get_current_user
from app.database import get_db
from app.models import Trip, TripDay, TripItem
from app.services import map_service

router = APIRouter()


# ── 地图配置 ────────────────────────────────────────────────────

@router.get("/config")
async def map_config():
    """获取地图前端 SDK 配置（Amap JS API Key）"""
    from app.config import get_settings
    settings = get_settings()
    return {
        "code": 0,
        "data": {
            "js_key": settings.gaode_api_key or "",
            "version": "2.0",
        },
    }


# ── 地理编码 ────────────────────────────────────────────────────

@router.get("/geocode")
async def geocode(
    address: str = Query(..., description="地址文本"),
    city: str = Query("", description="城市名（限范围）"),
    user=Depends(get_current_user),
):
    """地址 → 经纬度"""
    result = await map_service.geocode(address, city)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return {"code": 0, "data": result}


@router.post("/geocode/batch")
async def batch_geocode(body: dict, user=Depends(get_current_user)):
    """批量地址→经纬度（用于搜索结果地图标注 / 路线地图预览）"""
    addresses: list[str] = body.get("addresses", [])
    city: str = body.get("city", "")
    if not addresses:
        raise HTTPException(400, "addresses 不能为空")
    results = await map_service.batch_geocode_async(addresses, city)
    return {"code": 0, "data": {"results": results}}


@router.get("/regeocode")
async def regeocode(
    lng: float = Query(...),
    lat: float = Query(...),
    user=Depends(get_current_user),
):
    """经纬度 → 地址"""
    result = await map_service.regeocode(lng, lat)
    return {"code": 0, "data": result}


# ── 路径规划 ────────────────────────────────────────────────────

@router.get("/direction")
async def direction(
    from_addr: str = Query(None, description="起点地址（与lng/lat二选一）"),
    to_addr: str = Query(None, description="终点地址（与lng/lat二选一）"),
    from_lng: float = Query(None),
    from_lat: float = Query(None),
    to_lng: float = Query(None),
    to_lat: float = Query(None),
    mode: str = Query("walking", description="walking|bicycling|driving|transit"),
    user=Depends(get_current_user),
):
    """两点间路径规划"""
    # 地址模式
    if from_addr and to_addr:
        result = await map_service.direction_by_address(from_addr, to_addr, mode)
    # 坐标模式
    elif all(v is not None for v in (from_lng, from_lat, to_lng, to_lat)):
        result = await map_service.direction(from_lng, from_lat, to_lng, to_lat, mode)
    else:
        raise HTTPException(400, "请提供 (from_addr+to_addr) 或 (from_lng+from_lat+to_lng+to_lat)")

    if "error" in result:
        raise HTTPException(400, result["error"])
    return {"code": 0, "data": result}


# ── POI 搜索 ────────────────────────────────────────────────────

@router.get("/poi/text")
async def poi_text_search(
    keywords: str = Query(..., description="搜索关键词"),
    city: str = Query("", description="城市名"),
    offset: int = Query(20, le=50),
    user=Depends(get_current_user),
):
    """关键字搜索 POI"""
    result = await map_service.poi_text_search(keywords, city, offset=offset)
    return {"code": 0, "data": result}


@router.get("/poi/around")
async def poi_around_search(
    lng: float = Query(...),
    lat: float = Query(...),
    keywords: str = Query("", description="关键词（空=全部）"),
    radius: int = Query(2000, le=50000, description="搜索半径（米）"),
    offset: int = Query(20, le=50),
    user=Depends(get_current_user),
):
    """周边 POI 搜索"""
    result = await map_service.poi_around_search(lng, lat, keywords, radius, offset)
    return {"code": 0, "data": result}


@router.get("/poi/{poi_id}")
async def poi_detail(
    poi_id: str,
    user=Depends(get_current_user),
):
    """POI 详情"""
    result = await map_service.poi_detail(poi_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return {"code": 0, "data": result}


# ── 距离测量 ────────────────────────────────────────────────────

@router.get("/distance")
async def distance(
    origins: str = Query(..., description="起点坐标串: lng1,lat1|lng2,lat2"),
    destination: str = Query(..., description="终点坐标: lng,lat"),
    mode: int = Query(0, description="0=直线 1=驾车 2=公交 3=步行"),
    user=Depends(get_current_user),
):
    """批量距离测量"""
    result = await map_service.distance(origins, destination, mode)
    return {"code": 0, "data": result}


# ── 行程地图聚合 ────────────────────────────────────────────────

@router.get("/trip/{trip_id}")
async def trip_map(
    trip_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    行程地图数据聚合

    返回每日的 POI 坐标和路径，供前端在地图上渲染。
    如果 POI 缺少经纬度，自动调用 geocode 补充并回写数据库。
    """
    # 查行程
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(404, "行程不存在")

    # 查所有 day + items
    day_result = await db.execute(
        select(TripDay)
        .where(TripDay.trip_id == trip_id)
        .order_by(TripDay.day_number)
    )
    days = day_result.scalars().all()

    day_maps = []
    all_lngs = []
    all_lats = []

    for day in days:
        items_result = await db.execute(
            select(TripItem)
            .where(TripItem.trip_day_id == day.id)
            .order_by(TripItem.sort_order)
        )
        items = items_result.scalars().all()

        pois = []
        idx = 0
        dest_city = trip.destination or ""
        origin_city = trip.origin or ""
        import re as _re
        for item in items:
            lat = item.lat
            lng = item.lng
            # Auto-geocode items missing coordinates
            if lat is None or lng is None:
                try:
                    geo = None
                    # Transport items: geocode the departure station with origin city
                    if item.type in ('train', 'flight', 'transport'):
                        query = item.title
                        dest = ''
                        if '→' in query:
                            parts = query.split('→')
                            query = parts[0].strip()
                            dest = parts[1].strip() if len(parts) > 1 else ''
                        # Extract station/airport name
                        m = _re.search(r'([\u4e00-\u9fa5]{2,8}(?:东|西|南|北)(?:站|机场)?|[\u4e00-\u9fa5]{2,8}(?:站|机场))', query)
                        if m:
                            query = m.group(1)
                        elif dest:
                            # Fallback: use destination (non-station places)
                            query = _re.sub(r'\s*(地铁|公交|步行|打车|网约车|专车|出租车)(\d*号线?(转\d*号线?)?)?(\s*\([^)]*\))?\s*$', '', dest)
                        geo_city = origin_city if item.type in ('train', 'flight') else dest_city
                        geo = await map_service.geocode(query, city=geo_city)
                    else:
                        # Replace parentheses with spaces (Amap rejects them)
                        clean = item.title.replace('(', ' ').replace(')', ' ').replace('（', ' ').replace('）', ' ')
                        clean = _re.sub(r'\s+', ' ', clean).strip()
                        geo = await map_service.geocode(clean, city=dest_city)
                    # Fallback: clean title (remove parentheticals & meal suffixes)
                    if not (geo.get("lng") and geo.get("lat")):
                        cleaned = _re.sub(r'[（(][^)）]*[)）]', '', item.title)
                        cleaned = _re.sub(r'(午餐|晚餐|早餐|中餐|晚饭|早饭|午饭)\s*$', '', cleaned)
                        cleaned = cleaned.strip()
                        if cleaned and cleaned != item.title:
                            geo = await map_service.geocode(cleaned, city=dest_city)
                    if geo.get("lng") and geo.get("lat"):
                        lng = float(geo["lng"])
                        lat = float(geo["lat"])
                        item.lng = lng
                        item.lat = lat
                except Exception:
                    pass
            if lat is not None and lng is not None:
                pois.append({
                    "id": item.id,
                    "title": item.title,
                    "type": item.type,
                    "lng": lng,
                    "lat": lat,
                    "start_time": item.start_time,
                    "end_time": item.end_time,
                    "location": item.location,
                    "photos": item.photos,
                    "amap_poi_id": item.amap_poi_id,
                    "day_number": day.day_number,
                    "item_index": item.sort_order if item.sort_order is not None else idx,
                })
                idx += 1
                all_lngs.append(lng)
                all_lats.append(lat)

        day_maps.append({
            "day_number": day.day_number,
            "date": str(day.date) if day.date else "",
            "pois": pois,
        })

    # Persist any geocoded coordinates
    await db.commit()

    # 计算中心点
    center_lng = sum(all_lngs) / len(all_lngs) if all_lngs else 116.40
    center_lat = sum(all_lats) / len(all_lats) if all_lats else 39.90

    return {
        "code": 0,
        "data": {
            "trip_id": trip_id,
            "title": trip.title,
            "center": {"lng": round(center_lng, 6), "lat": round(center_lat, 6)},
            "days": day_maps,
        },
    }


@router.get("/trip/{trip_id}/day/{day_number}")
async def trip_day_map(
    trip_id: str,
    day_number: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    单天地图数据 — 含 POI 坐标 + POI 详情（图片、评分等）

    用于前端天选择器：切换天时只加载该天数据
    """
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(404, "行程不存在")

    day_result = await db.execute(
        select(TripDay)
        .where(TripDay.trip_id == trip_id, TripDay.day_number == day_number)
    )
    day = day_result.scalar_one_or_none()
    if not day:
        raise HTTPException(404, f"第{day_number}天不存在")

    items_result = await db.execute(
        select(TripItem)
        .where(TripItem.trip_day_id == day.id)
        .order_by(TripItem.sort_order)
    )
    items = items_result.scalars().all()

    pois = []
    idx = 0
    for item in items:
        if item.lat is not None and item.lng is not None:
            pois.append({
                "id": item.id,
                "title": item.title,
                "type": item.type,
                "lng": item.lng,
                "lat": item.lat,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "location": item.location,
                "price": float(item.price) if item.price else None,
                "booking_url": item.booking_url,
                "photos": item.photos,
                "amap_poi_id": item.amap_poi_id,
                "day_number": day_number,
                "item_index": item.sort_order if item.sort_order is not None else idx,
            })
            idx += 1

    await db.commit()

    # 计算该天中心点
    lngs = [p["lng"] for p in pois]
    lats = [p["lat"] for p in pois]
    center_lng = sum(lngs) / len(lngs) if lngs else 116.40
    center_lat = sum(lats) / len(lats) if lats else 39.90

    return {
        "code": 0,
        "data": {
            "trip_id": trip_id,
            "title": trip.title,
            "day_number": day_number,
            "date": str(day.date) if day.date else "",
            "center": {"lng": round(center_lng, 6), "lat": round(center_lat, 6)},
            "pois": pois,
        },
    }
