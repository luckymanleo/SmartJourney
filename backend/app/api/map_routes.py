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


def _build_geocode_address(item, trip_destination: str | None) -> str | None:
    """构造 geocode 地址：优先 location，回退到 title+目的地"""
    import re
    if item.location:
        return item.location
    if item.title and trip_destination:
        # 交通类（train/flight/transport）：提取出发站/机场（用户需导航到出发站）
        if item.type in ('train', 'flight', 'transport'):
            # "K636 深圳东 → 武夷山" → "深圳东站"
            # "深圳航空 ZH2539 深圳→武夷山" → "深圳机场"
            before_arrow = item.title.split('→')[0].split('→')[0]
            m = re.search(r'([\u4e00-\u9fa5]{2,6}(?:东|西|南|北)?)\s*$', before_arrow)
            if m:
                station = m.group(1)
                suffix = '机场' if item.type == 'flight' else '站'
                if not station.endswith(suffix):
                    station += suffix
                return station
            return None
        return f"{trip_destination} {item.title}"
    return item.title or None


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
    need_geocode = []

    for day in days:
        items_result = await db.execute(
            select(TripItem)
            .where(TripItem.trip_day_id == day.id)
            .order_by(TripItem.sort_order)
        )
        items = items_result.scalars().all()

        pois = []
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
                    "photos": item.photos,
                    "amap_poi_id": item.amap_poi_id,
                })
                all_lngs.append(item.lng)
                all_lats.append(item.lat)
            elif item.location or (item.title and trip.destination):
                # 缺坐标，构造地址 geocode
                need_geocode.append((item, day))

        day_maps.append({
            "day_number": day.day_number,
            "date": str(day.date) if day.date else "",
            "pois": pois,
        })

    # 批量补充缺失经纬度
    if need_geocode:
        for item, day in need_geocode:
            try:
                addr = _build_geocode_address(item, trip.destination)
                geo = await map_service.geocode(addr or item.title)
                if "error" not in geo:
                    item.lat = geo["lat"]
                    item.lng = geo["lng"]
                    all_lngs.append(geo["lng"])
                    all_lats.append(geo["lat"])
                    # 回写数据库
                    await db.execute(
                        TripItem.__table__.update()
                        .where(TripItem.id == item.id)
                        .values(lat=geo["lat"], lng=geo["lng"])
                    )
                    # 添加到对应天的 pois
                    for dm in day_maps:
                        if dm["day_number"] == day.day_number:
                            dm["pois"].append({
                                "id": item.id,
                                "title": item.title,
                                "type": item.type,
                                "lng": geo["lng"],
                                "lat": geo["lat"],
                                "start_time": item.start_time,
                                "end_time": item.end_time,
                                "location": item.location,
                                "photos": item.photos,
                                "amap_poi_id": item.amap_poi_id,
                            })
                            break
            except Exception:
                pass  # geocode 失败不影响主流程
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
    for item in items:
        lat = item.lat
        lng = item.lng

        # 缺坐标 → 即时 geocode + 回写
        if (lat is None or lng is None) and (item.location or (item.title and trip.destination)):
            try:
                addr = _build_geocode_address(item, trip.destination)
                geo = await map_service.geocode(addr or item.title)
                if "error" not in geo:
                    lat, lng = geo["lat"], geo["lng"]
                    item.lat, item.lng = lat, lng
                    await db.execute(
                        TripItem.__table__.update()
                        .where(TripItem.id == item.id)
                        .values(lat=lat, lng=lng)
                    )
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
                "price": float(item.price) if item.price else None,
                "booking_url": item.booking_url,
                "photos": item.photos,
                "amap_poi_id": item.amap_poi_id,
            })

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
