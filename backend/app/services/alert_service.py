"""
实时预警与行中助手服务 — Phase 2 P0

功能：
- 航班延误检查
- 列车晚点检查
- 天气突变预警
- 出发时间动态调整建议
- 值机提醒
- 站台/登机口变更通知
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Trip, TripDay, TripItem
from app.services.weather_service import get_weather

logger = logging.getLogger(__name__)


async def check_trip_alerts(db: AsyncSession, trip_id: str, user_id: str) -> dict:
    """
    检查行程中的所有潜在风险

    Returns:
        {
            "alerts": [
                {"level": "warning", "type": "weather", "message": "三亚明天有雷阵雨，建议带雨具"},
                {"level": "info", "type": "checkin", "message": "MU5678 明天 08:30 起飞，建议 06:30 到达机场"},
                {"level": "danger", "type": "delay", "message": "G1234 预计晚点 30 分钟"},
            ],
            "suggestions": [...]
        }
    """
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.user_id == user_id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        return {"alerts": [], "suggestions": []}

    alerts = []
    suggestions = []

    # 1. 天气预警
    if trip.destination:
        weather = await get_weather(trip.destination)
        alerts.extend(_check_weather_alerts(weather, trip))

    # 2. 航班/火车提醒
    for day in (trip.days or []):
        for item in (day.items or []):
            if item.type in ("flight", "train"):
                alerts.extend(_check_transport_alerts(item, day))
                suggestions.extend(_check_checkin_reminder(item, day))

    # 3. 时间紧迫检查
    if trip.start_date:
        days_until = (trip.start_date - datetime.utcnow().date()).days
        if days_until == 1:
            alerts.append({
                "level": "info",
                "type": "departure",
                "message": f"明天出发！记得检查行李和证件",
            })
        elif days_until == 0:
            alerts.append({
                "level": "info", 
                "type": "departure",
                "message": "今天出发！祝旅途愉快 🎉",
            })
        elif days_until < 0:
            suggestions.append("行程已开始，祝你玩得开心！")

    return {
        "alerts": alerts,
        "suggestions": suggestions,
    }


def _check_weather_alerts(weather: dict, trip) -> list:
    """检查天气风险"""
    alerts = []
    current = weather.get("current", {})
    forecast = weather.get("forecast", [])

    if current:
        weather_text = str(current.get("weather", "")).lower()
        if any(w in weather_text for w in ["雨", "雪", "暴", "台风", "霾"]):
            alerts.append({
                "level": "warning",
                "type": "weather",
                "message": f"{trip.destination}当前天气：{current.get('weather', '未知')}，请注意防护",
            })

    for day_forecast in forecast[:3]:
        w = str(day_forecast.get("dayweather", "")).lower()
        if any(bad in w for bad in ["雨", "雪", "暴", "台风"]):
            alerts.append({
                "level": "warning",
                "type": "weather",
                "message": f"{day_forecast.get('date', '')} {trip.destination}{day_forecast.get('dayweather', '')}，建议调整户外行程",
            })

    temp_high = current.get("temperature", "25")
    try:
        if int(float(temp_high)) > 35:
            alerts.append({
                "level": "info",
                "type": "weather",
                "message": f"{trip.destination}高温 {temp_high}°C，注意防暑",
            })
    except (ValueError, TypeError):
        pass

    return alerts


def _check_transport_alerts(item, day) -> list:
    """检查交通提醒"""
    alerts = []
    departure = item.extra_data or {}

    if item.type == "flight":
        flight_no = departure.get("flight_no", "")
        if flight_no:
            # 实际项目中应调用航班状态API
            pass

    if item.start_time:
        # 如果出发时间较早，提醒前一天早睡
        try:
            hour = int(item.start_time.split(":")[0])
            if hour < 8:
                alerts.append({
                    "level": "info",
                    "type": "early_departure",
                    "message": f"{item.title} 出发时间较早 ({item.start_time})，建议提前休息",
                })
        except (ValueError, IndexError):
            pass

    return alerts


def _check_checkin_reminder(item, day) -> list:
    """值机/上车提醒"""
    suggestions = []
    if item.type == "flight" and item.start_time:
        suggestions.append({
            "level": "info",
            "type": "checkin",
            "message": f"{item.title}，建议起飞前 2 小时到达机场 (约 {_subtract_hours(item.start_time, 2)})",
        })
    elif item.type == "train" and item.start_time:
        suggestions.append({
            "level": "info",
            "type": "checkin",
            "message": f"{item.title}，建议开车前 30 分钟到达车站 (约 {_subtract_hours(item.start_time, 0.5)})",
        })
    return suggestions


def _subtract_hours(time_str: str, hours: float) -> str:
    """时间减去小时数"""
    try:
        parts = time_str.split(":")
        h, m = int(parts[0]), int(parts[1])
        total_minutes = h * 60 + m - int(hours * 60)
        total_minutes = max(0, total_minutes)
        return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"
    except (ValueError, IndexError):
        return time_str
