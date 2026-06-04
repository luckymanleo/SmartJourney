"""
辅助信息 API — 天气、目的地、热门目的地、省市区联动
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.services.weather_service import get_weather
from app.services import mcp_manager
from app.config_loader import popular_destinations as get_popular_destinations
from app.services import location_service

router = APIRouter()

# 从 config.json 加载
POPULAR_DESTINATIONS = get_popular_destinations()


@router.get("/weather")
async def weather(
    city: str = Query(...),
    days: int = Query(7),
    user=Depends(get_current_user),
):
    result = await get_weather(city, days)
    return {"code": 0, "data": result}


@router.get("/popular")
async def popular_destinations(
    limit: int = Query(6, ge=1, le=20),
):
    """热门目的地列表（公开接口）"""
    return {
        "code": 0,
        "data": {
            "destinations": POPULAR_DESTINATIONS[:limit],
            "total": len(POPULAR_DESTINATIONS),
        },
    }


@router.get("/destination/{city}")
async def destination_info(
    city: str,
    user=Depends(get_current_user),
):
    """目的地综合信息（天气 + 静态信息）"""
    weather_data = await get_weather(city, 7)
    dest_info = next((d for d in POPULAR_DESTINATIONS if d["name"] == city), None)

    info = {
        "name": city,
        "image": dest_info["image"] if dest_info else "📍",
        "description": dest_info["description"] if dest_info else f"{city}是中国著名的旅游目的地",
        "best_season": dest_info["best_season"] if dest_info else "请根据天气信息判断",
        "tags": dest_info["tags"] if dest_info else [],
        "crowd_level": "medium",
        "tips": ["提前预订酒店和机票", "关注当地天气预报"],
        "visa_info": None,
        "currency": "CNY",
        "language": "中文",
        "weather": weather_data,
    }
    return {"code": 0, "data": info}


@router.get("/cities")
async def city_list(
    keyword: str = Query("", description="搜索关键词（支持拼音/首字母/汉字）"),
):
    """城市列表（兼容旧接口）"""
    if keyword:
        results = location_service.search_locations(keyword)
        return {"code": 0, "data": {"cities": [r["name"] for r in results], "results": results}}
    provinces = location_service.get_provinces()
    return {"code": 0, "data": {"provinces": provinces}}


@router.get("/locations")
async def locations(
    pid: int = Query(0, description="父级ID，0=省/直辖市"),
):
    """省市区级联查询"""
    children = location_service.get_children(pid)
    return {"code": 0, "data": children}


@router.get("/locations/search")
async def locations_search(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
):
    """拼音/汉字搜索城市和区县"""
    results = location_service.search_locations(keyword, limit)
    return {"code": 0, "data": results}
