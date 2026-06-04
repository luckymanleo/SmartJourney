"""
无障碍出行 + 多语言/出入境服务 — Phase 4
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ==================== 无障碍出行 ====================

async def get_accessibility_info(destination: str, needs: list[str] = None) -> dict:
    """
    获取无障碍出行信息

    Args:
        destination: 目的地城市
        needs: 特殊需求列表 ["wheelchair", "elderly", "visually_impaired", "pregnant"]

    Returns:
        {
            "services": [...],
            "accessible_hotels": "搜索关键词建议",
            "transport_tips": [...],
            "emergency_contacts": {...},
        }
    """
    if needs is None:
        needs = []

    services = []
    tips = []

    if "wheelchair" in needs:
        services.append({
            "type": "wheelchair",
            "title": "轮椅服务",
            "description": "机场和火车站均提供免费轮椅服务，建议提前 48 小时预约",
            "how_to": "联系航司客服或 12306 预约",
        })
        tips.append("预订酒店时选择「无障碍房型」")
        tips.append("景点提前确认是否有无障碍通道")

    if "elderly" in needs:
        services.append({
            "type": "elderly",
            "title": "老年人优待",
            "description": f"{destination}大部分景区对 60 岁以上老人提供门票半价或免费",
            "how_to": "凭身份证在景区窗口购买",
        })
        tips.append("选择平缓的游览路线，避免大量爬坡")
        tips.append("随身携带常用药品和紧急联系人卡片")

    if "visually_impaired" in needs:
        services.append({
            "type": "visually_impaired",
            "title": "视障协助",
            "description": "机场/火车站提供引导服务",
            "how_to": "提前联系到达站点安排接站引导",
        })

    if "pregnant" in needs:
        services.append({
            "type": "pregnant",
            "title": "孕妇关怀",
            "description": "机场提供优先安检通道",
            "how_to": "值机时告知工作人员",
        })
        tips.append("避免长途飞行（超过 4 小时）")
        tips.append("选择靠近卫生间的座位")

    return {
        "destination": destination,
        "services": services,
        "accessible_hotels": f"{destination} 无障碍 酒店",
        "transport_tips": tips or ["提前规划路线，预留充足时间"],
        "emergency_contacts": {
            "急救": "120",
            "报警": "110",
            "火警": "119",
            "交通求助": "12306 (铁路) / 12326 (民航)",
        },
    }


# ==================== 多语言/出入境 ====================

async def get_border_info(destination: str, nationality: str = "中国") -> dict:
    """
    获取出入境信息

    Returns:
        {
            "visa_required": false,
            "visa_type": "免签",
            "passport_validity": "6个月以上",
            "customs_notes": [...],
            "health_requirements": [...],
            "currency": {...},
            "language": "中文",
            "useful_phrases": [...],
        }
    """
    # 国内目的地
    domestic_cities = [
        "北京", "上海", "广州", "深圳", "成都", "重庆", "杭州", "南京",
        "武汉", "西安", "长沙", "三亚", "厦门", "大理", "丽江", "桂林",
        "青岛", "大连", "哈尔滨", "昆明", "苏州", "天津",
    ]

    if any(destination.startswith(c) for c in domestic_cities):
        return {
            "visa_required": False,
            "visa_type": "国内出行",
            "passport_validity": None,
            "customs_notes": [],
            "health_requirements": [],
            "currency": {
                "code": "CNY",
                "symbol": "¥",
                "name": "人民币",
                "exchange_rate": 1.0,
            },
            "language": "中文",
            "useful_phrases": [],
            "tips": ["国内出行请携带身份证", "部分边境地区可能需要边防证"],
        }

    # 境外目的地（简化版）
    intl_info = {
        "日本": {
            "visa_required": True,
            "visa_type": "旅游签证",
            "currency": {"code": "JPY", "symbol": "¥", "name": "日元", "exchange_rate": 0.048},
            "language": "日语",
            "phrases": [
                {"zh": "你好", "local": "こんにちは (Konnichiwa)"},
                {"zh": "谢谢", "local": "ありがとう (Arigatou)"},
                {"zh": "多少钱", "local": "いくらですか (Ikura desu ka)"},
                {"zh": "卫生间在哪里", "local": "トイレはどこですか (Toire wa doko desu ka)"},
            ],
        },
        "泰国": {
            "visa_required": False,
            "visa_type": "免签 30 天",
            "currency": {"code": "THB", "symbol": "฿", "name": "泰铢", "exchange_rate": 0.21},
            "language": "泰语",
            "phrases": [
                {"zh": "你好", "local": "สวัสดี (Sawadee)"},
                {"zh": "谢谢", "local": "ขอบคุณ (Khop khun)"},
            ],
        },
        "韩国": {
            "visa_required": True,
            "visa_type": "旅游签证（济州岛免签）",
            "currency": {"code": "KRW", "symbol": "₩", "name": "韩元", "exchange_rate": 0.0055},
            "language": "韩语",
            "phrases": [
                {"zh": "你好", "local": "안녕하세요 (Annyeonghaseyo)"},
                {"zh": "谢谢", "local": "감사합니다 (Gamsahamnida)"},
            ],
        },
    }

    for country, info in intl_info.items():
        if destination.startswith(country):
            return {
                **info,
                "passport_validity": "6个月以上有效期",
                "customs_notes": ["遵守当地海关规定", "注意携带现金限额"],
                "health_requirements": ["建议购买旅行保险", "了解当地疫苗接种要求"],
                "useful_phrases": info.get("phrases", []),
                "tips": [
                    "提前准备护照复印件",
                    "开通手机国际漫游或购买当地 SIM 卡",
                    "记下中国驻当地使领馆联系方式",
                ],
            }

    return {
        "visa_required": None,
        "message": f"{destination} 的出入境信息暂未收录，建议查询外交部领事司网站",
        "tips": ["出行前请确认签证要求", "护照有效期需在 6 个月以上"],
    }


async def translate_phrases(language: str, category: str = "travel") -> list[dict]:
    """
    获取常用语翻译卡片

    Args:
        language: 目标语言 (ja/ko/th/en)
        category: 场景 (travel/food/emergency)
    """
    phrases_db = {
        "en": {
            "travel": [
                {"zh": "机场怎么走", "local": "How do I get to the airport?"},
                {"zh": "我要去这个地址", "local": "I need to go to this address"},
                {"zh": "哪里有WiFi", "local": "Where can I find WiFi?"},
                {"zh": "可以帮我拍照吗", "local": "Could you take a photo for me?"},
            ],
            "food": [
                {"zh": "这个菜不辣", "local": "Is this dish spicy?"},
                {"zh": "结账", "local": "Check, please"},
                {"zh": "菜单", "local": "Menu, please"},
            ],
            "emergency": [
                {"zh": "救命", "local": "Help!"},
                {"zh": "我需要医生", "local": "I need a doctor"},
                {"zh": "报警", "local": "Call the police"},
            ],
        },
        "ja": {
            "travel": [
                {"zh": "机场怎么走", "local": "空港への行き方を教えてください"},
                {"zh": "我要去这个地址", "local": "この住所に行きたいです"},
            ],
            "food": [
                {"zh": "这个菜不辣", "local": "これは辛くないですか"},
                {"zh": "结账", "local": "お会計お願いします"},
            ],
        },
    }

    lang_data = phrases_db.get(language, phrases_db.get("en", {}))
    return lang_data.get(category, lang_data.get("travel", []))
