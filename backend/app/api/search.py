"""
搜索 API — 使用远程 HTTP MCP（ModelScope FliggyTravel）
重构：不再使用 stdio MCP Gateway，避免 event loop 污染
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.services import mcp_manager

router = APIRouter()


def _to_cn_date(iso_date: str) -> str:
    """Convert ISO date '2026-06-02' to Chinese '2026年6月2日'"""
    try:
        parts = iso_date.split("-")
        if len(parts) == 3:
            y, m, d = parts
            return f"{y}年{int(m)}月{int(d)}日"
    except (ValueError, IndexError):
        pass
    return iso_date


def _handle_result(result, source="fliggy_remote"):
    """格式化搜索结果"""
    items = result.get("items", []) or result.get("data", {}).get("items", [])
    extra = {}
    if result.get("raw_markdown"):
        extra["raw_markdown"] = result["raw_markdown"][:10000]
    if result.get("note"):
        extra["note"] = result["note"]
    if result.get("error"):
        extra["error"] = str(result["error"])[:500]
    return {
        "code": 0,
        "data": {
            "source": source,
            "total": len(items),
            "items": items,
            **({"extra": extra} if extra else {}),
        },
    }


@router.get("/flights")
async def search_flights(
    from_city: str = Query(..., alias="from"),
    to: str = Query(...),
    date: str = Query(...),
    source: str = Query("fliggy"),
    cabin: str = Query(None),
    sort_by: str = Query("price"),
    direct_only: bool = Query(False),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not mcp_manager.is_available():
        await mcp_manager.ensure_connected()
    if not mcp_manager.is_available():
        raise HTTPException(status_code=503, detail="搜索服务暂不可用（MCP 未连接）")
    try:
        cn_date = _to_cn_date(date)
        query = f"{from_city}到{to}{cn_date}机票"
        result = await mcp_manager.call_tool("search_flight", query)
        return _handle_result(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/trains")
async def search_trains(
    from_city: str = Query(..., alias="from"),
    to: str = Query(...),
    date: str = Query(...),
    source: str = Query("fliggy"),
    train_type: str = Query(None),
    seat_type: str = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not mcp_manager.is_available():
        await mcp_manager.ensure_connected()
    if not mcp_manager.is_available():
        raise HTTPException(status_code=503, detail="搜索服务暂不可用")
    try:
        cn_date = _to_cn_date(date)
        query = f"{from_city}到{to}{cn_date}火车票"
        result = await mcp_manager.call_tool("search_train", query)
        return _handle_result(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/hotels")
async def search_hotels(
    city: str = Query(...),
    keyword: str = Query(None),
    source: str = Query("fliggy"),
    check_in: str = Query(None),
    check_out: str = Query(None),
    star_min: int = Query(None),
    price_min: float = Query(None),
    price_max: float = Query(None),
    brand: str = Query(None),
    sort_by: str = Query("rating"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not mcp_manager.is_available():
        await mcp_manager.ensure_connected()
    if not mcp_manager.is_available():
        raise HTTPException(status_code=503, detail="搜索服务暂不可用")
    try:
        query = city
        if keyword:
            query += keyword
        result = await mcp_manager.call_tool("search_hotel", query + "酒店")
        return _handle_result(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/pois")
async def search_pois(
    city: str = Query(...),
    keyword: str = Query(None),
    source: str = Query("fliggy"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not mcp_manager.is_available():
        await mcp_manager.ensure_connected()
    if not mcp_manager.is_available():
        raise HTTPException(status_code=503, detail="搜索服务暂不可用")
    try:
        query = city
        if keyword:
            query += keyword
        result = await mcp_manager.call_tool("search_poi", query + "景点")
        return _handle_result(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/foods")
async def search_foods(
    city: str = Query(...),
    keyword: str = Query(None),
    source: str = Query("fliggy"),
    price_min: float = Query(None),
    price_max: float = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not mcp_manager.is_available():
        await mcp_manager.ensure_connected()
    if not mcp_manager.is_available():
        raise HTTPException(status_code=503, detail="搜索服务暂不可用")
    try:
        query = city
        if keyword:
            query += keyword
        result = await mcp_manager.call_tool("search_food", query + "美食")
        return _handle_result(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/transport")
async def search_transport(
    from_location: str = Query(..., alias="from"),
    to: str = Query(...),
    city: str = Query(None),
    source: str = Query("fliggy"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not mcp_manager.is_available():
        await mcp_manager.ensure_connected()
    if not mcp_manager.is_available():
        raise HTTPException(status_code=503, detail="搜索服务暂不可用")
    try:
        # Use city+市 prefix for reliable MCP NLP parsing
        if city:
            from_full = f"{city}市 {from_location}"
            to_full = f"{city}市 {to}"
        else:
            from_full = from_location
            to_full = to
        query = f"{from_full} 到 {to_full}"
        result = await mcp_manager.call_tool("search_transport", query)
        return _handle_result(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
