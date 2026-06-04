"""
省市区三级数据服务 — 基于 eduosi/district CSV

数据: app/data/district.csv (3433行)
字段: id, name, parent_id, initial, initials, pinyin, extra, suffix, code, area_code, order

启动时加载到内存，提供:
- 级联查询 (pid → children)
- 拼音/首字母搜索
"""

import csv
import os
from functools import lru_cache

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "district.csv")

# 内存数据
_records: list[dict] = []
_children: dict[int, list[dict]] = {}  # parent_id → children
_by_id: dict[int, dict] = {}
_flat_search: list[dict] = []  # 所有城市+区县的扁平搜索列表


def _load():
    """加载 CSV 到内存"""
    global _records, _children, _by_id, _flat_search
    if _records:
        return

    with open(DATA_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        _records = list(reader)

    for r in _records:
        rid = int(r["id"])
        pid = int(r["parent_id"])
        _by_id[rid] = r
        _children.setdefault(pid, []).append(r)

    # 构建扁平搜索列表（市/区级 + 直辖市）
    provinces = _children.get(0, [])
    province_ids = {int(p["id"]) for p in provinces}
    
    # Add ALL province-level entities to search (直辖市 + 特别行政区 + 省)
    for p in provinces:
        p_copy = dict(p)
        p_copy["parent_name"] = ""
        _flat_search.append(p_copy)
    
    for r in _records:
        pid = int(r["parent_id"])
        # 市级 (parent 是省) 和 区级 (parent 是市，且市的 parent 是省)
        if pid in province_ids:
            _flat_search.append(r)
            parent = _by_id.get(pid)
            r["parent_name"] = parent["name"] if parent else ""

    # 为搜索列表补充省名
    for item in _flat_search:
        if "parent_name" not in item or not item["parent_name"]:
            parent = _by_id.get(int(item["parent_id"]))
            if parent:
                grand = _by_id.get(int(parent["parent_id"]))
                item["parent_name"] = parent["name"]
                if grand and int(grand["parent_id"]) == 0:
                    item["province_name"] = grand["name"]


_load()


def get_children(parent_id: int = 0) -> list[dict]:
    """获取某级下的子节点，按拼音排序"""
    nodes = _children.get(parent_id, [])
    result = [
        {
            "id": int(n["id"]),
            "name": n["name"],
            "initial": n["initial"],
            "initials": n["initials"],
            "pinyin": n["pinyin"],
            "suffix": n["suffix"],
            "code": n["code"],
        }
        for n in nodes
    ]
    # Sort by pinyin alphabetically
    result.sort(key=lambda x: x["pinyin"])
    return result


def get_provinces() -> list[dict]:
    """获取所有省/直辖市 (parent_id=0)"""
    return get_children(0)


def get_cities(province_id: int) -> list[dict]:
    """获取某省下的所有市"""
    return get_children(province_id)


def get_districts(city_id: int) -> list[dict]:
    """获取某市下的所有区县"""
    return get_children(city_id)


def search_locations(keyword: str, limit: int = 20) -> list[dict]:
    """
    拼音/汉字搜索城市和区县
    匹配规则: name / pinyin / initials / initial
    """
    if not keyword or len(keyword) < 1:
        return []

    kw = keyword.lower().strip()
    results = []

    for item in _flat_search:
        name = item["name"]
        pinyin = item.get("pinyin", "")
        initials = item.get("initials", "")
        initial = item.get("initial", "")

        # 汉字匹配
        if kw in name:
            score = 100 if name == kw else (90 if name.startswith(kw) else 80)
        # 全拼匹配
        elif kw in pinyin:
            score = 70 if pinyin.startswith(kw) else 60
        # 首字母匹配
        elif kw == initials or kw == initial:
            score = 50
        else:
            continue

        pid = int(item["parent_id"])
        parent = _by_id.get(pid, {})
        parent_name = parent.get("name", "")
        province_name = ""

        # 如果parent的parent是省，则parent是市
        if parent:
            grand_pid = int(parent.get("parent_id", 0))
            grand = _by_id.get(grand_pid, {})
            if grand_pid == 0 or grand.get("parent_id") == "0":
                province_name = grand.get("name", "") if grand_pid == 0 else parent_name
                parent_name = parent.get("name", "") if grand_pid == 0 else ""

        results.append({
            "id": int(item["id"]),
            "name": name,
            "pinyin": pinyin,
            "initials": initials,
            "suffix": item.get("suffix", ""),
            "parent_name": parent_name,
            "province_name": province_name,
            "_score": score,
        })

    # 按匹配度排序
    results.sort(key=lambda x: (-x["_score"], x["name"]))
    for r in results:
        del r["_score"]

    return results[:limit]
