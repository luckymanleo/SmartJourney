"""
Phase 4 API — 偏好学习、异常改签、无障碍、多语言、公交/渡轮
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db

router = APIRouter()


# ==================== 偏好学习 ====================

@router.get("/preferences/learn")
async def learn_preferences(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """基于历史行程学习偏好"""
    from app.services.preference_learning import learn_from_history
    result = await learn_from_history(db, user.id)
    return {"code": 0, "data": result}


@router.get("/preferences/feed")
async def personalized_feed(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """个性化推荐流"""
    from app.services.preference_learning import get_personalized_feed
    result = await get_personalized_feed(db, user.id)
    return {"code": 0, "data": result}


# ==================== 异常处理 ====================

@router.get("/disruption/alternatives")
async def find_alternatives(
    from_city: str = Query(..., alias="from"),
    to: str = Query(...),
    date: str = Query(...),
    transport_type: str = Query("flight"),
    search_range: int = Query(2),
    user=Depends(get_current_user),
):
    """航班取消/延误后搜索替代方案"""
    from app.services.disruption_service import find_alternatives as fa
    result = await fa(from_city, to, date, transport_type, search_range)
    return {"code": 0, "data": result}


# ==================== 无障碍出行 ====================

@router.get("/accessibility/info")
async def accessibility_info(
    destination: str = Query(...),
    needs: str = Query(None, description="逗号分隔: wheelchair,elderly,visually_impaired,pregnant"),
    user=Depends(get_current_user),
):
    """无障碍出行信息"""
    from app.services.accessibility_service import get_accessibility_info
    needs_list = [n.strip() for n in needs.split(",")] if needs else []
    result = await get_accessibility_info(destination, needs_list)
    return {"code": 0, "data": result}


# ==================== 多语言/出入境 ====================

@router.get("/border/info")
async def border_info(
    destination: str = Query(...),
    nationality: str = Query("中国"),
    user=Depends(get_current_user),
):
    """出入境信息"""
    from app.services.accessibility_service import get_border_info
    result = await get_border_info(destination, nationality)
    return {"code": 0, "data": result}


@router.get("/translate/phrases")
async def translate_phrases(
    language: str = Query("en", description="目标语言: en/ja/ko/th"),
    category: str = Query("travel", description="场景: travel/food/emergency"),
    user=Depends(get_current_user),
):
    """获取常用语翻译卡片"""
    from app.services.accessibility_service import translate_phrases
    result = await translate_phrases(language, category)
    return {"code": 0, "data": {"phrases": result}}


# ==================== 公共交通深度集成 ====================

@router.get("/transit/metro")
async def metro_info(
    city: str = Query(...),
    from_station: str = Query(None, alias="from"),
    to_station: str = Query(None, alias="to"),
    user=Depends(get_current_user),
):
    """地铁线路查询"""
    return {
        "code": 0,
        "data": {
            "city": city,
            "message": f"{city}地铁线路查询将通过高德地图 API 深度接入",
            "tips": [
                "下载「{city}地铁」App 查看实时线路图",
                "支持支付宝/微信乘车码扫码进站",
            ],
        },
    }


@router.get("/transit/bus")
async def bus_info(
    city: str = Query(...),
    route: str = Query(None),
    user=Depends(get_current_user),
):
    """公交线路查询"""
    return {
        "code": 0,
        "data": {
            "city": city,
            "message": "公交线路查询将通过高德地图 API 接入",
        },
    }


@router.get("/transit/bike")
async def bike_info(
    city: str = Query(...),
    user=Depends(get_current_user),
):
    """共享单车信息"""
    providers = {
        "北京": ["美团单车", "哈啰单车", "青桔单车"],
        "上海": ["美团单车", "哈啰单车", "青桔单车"],
        "广州": ["美团单车", "哈啰单车", "青桔单车"],
        "深圳": ["美团单车", "哈啰单车"],
        "成都": ["美团单车", "哈啰单车", "青桔单车"],
        "杭州": ["美团单车", "哈啰单车"],
    }
    return {
        "code": 0,
        "data": {
            "city": city,
            "providers": providers.get(city, ["美团单车", "哈啰单车"]),
            "tips": [
                "使用支付宝/微信扫一扫即可开锁",
                "骑行前检查刹车和车胎",
                "请停放在指定区域避免扣费",
            ],
        },
    }


@router.get("/transit/walking")
async def walking_navigation(
    origin: str = Query(..., alias="from"),
    destination: str = Query(..., alias="to"),
    user=Depends(get_current_user),
):
    """步行导航"""
    return {
        "code": 0,
        "data": {
            "from": origin,
            "to": destination,
            "message": "步行导航将通过高德地图 DeepLink 打开",
            "deeplink": f"https://uri.amap.com/walk?from={origin}&to={destination}",
        },
    }


# ==================== 渡轮/游船 ====================

FERRY_DATA = {
    "厦门→鼓浪屿": {
        "routes": [
            {"departure": "厦门轮渡码头", "arrival": "鼓浪屿三丘田码头", "duration": 20, "price": 35, "frequency": "每20分钟"},
            {"departure": "厦门轮渡码头", "arrival": "鼓浪屿内厝澳码头", "duration": 25, "price": 35, "frequency": "每30分钟"},
        ],
        "tips": ["建议提前网上购票", "节假日需提前一周预订", "夜间航线 17:30 后从三丘田码头返回"],
    },
    "大连→烟台": {
        "routes": [
            {"departure": "大连港", "arrival": "烟台港", "duration": 360, "price": 180, "frequency": "每日2班"},
        ],
        "tips": ["航程约6小时", "可携带车辆上船", "建议购买卧铺票"],
    },
    "深圳→珠海": {
        "routes": [
            {"departure": "蛇口码头", "arrival": "珠海九洲港", "duration": 60, "price": 130, "frequency": "每30分钟"},
        ],
        "tips": ["航程约1小时", "比陆路快1小时以上"],
    },
}

@router.get("/ferry/search")
async def ferry_search(
    origin: str = Query(..., alias="from"),
    destination: str = Query(..., alias="to"),
    date: str = Query(None),
    user=Depends(get_current_user),
):
    """渡轮/游船查询"""
    key = f"{origin}→{destination}"
    data = FERRY_DATA.get(key)

    if data:
        return {"code": 0, "data": {"from": origin, "to": destination, **data}}

    # 尝试通过交通查询
    from app.services.mcp_gateway import gateway
    try:
        result = await gateway.call_tool("transport", "search_transport", {
            "from_location": origin,
            "to": destination,
        })
        items = result.get("items", [])
        ferry_items = [i for i in items if i.get("type") in ("ferry", "boat", "ship")]
        if ferry_items:
            return {"code": 0, "data": {"from": origin, "to": destination, "routes": ferry_items}}
    except Exception:
        pass

    return {
        "code": 0,
        "data": {
            "from": origin,
            "to": destination,
            "routes": [],
            "message": f"暂未收录 {origin}→{destination} 的渡轮信息",
            "tips": ["尝试搜索周边城市渡轮", "部分海岛航线可通过当地客运码头查询"],
        },
    }
