"""
MCP Markdown 响应解析器 v5 — 工具专属分派 + Bag-of-fields 提取

设计原则:
1. 每种工具用专属解析函数，不走优先级链
2. 每字段多正则并行（bag-of-fields），取首个命中
3. 机票双通道：bold 卡片 + 附表
4. 火车跳过 overview 表，提取个体车次
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── 通用工具函数 ──────────────────────────────────────────────

def _info_card(title: str, text: str) -> list[dict]:
    return [{"title": title, "description": text[:500],
             "source": "fliggy_remote", "extra_data": {"is_info": True}}]

def _error_card(text: str) -> list[dict]:
    return [{"title": "提示", "description": text[:500],
             "source": "fliggy_remote", "extra_data": {"is_error": True}}]

def _field(text: str, patterns: list[str]) -> str | None:
    """Bag-of-fields: try each regex, return first capture group match."""
    for pat in patterns:
        m = re.search(pat, text)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return None

def _split_bold_cards(text: str) -> list[str]:
    """Split markdown by bold-link headers: **[NAME](url)**"""
    # Match bold text containing a markdown link
    parts = re.split(r'\n(?=\*\*\[.+\]\(.+\)\*\*\s*\n)', text)
    if len(parts) <= 1:
        # Try alternative: bold text without link
        parts = re.split(r'\n(?=\*\*(?![*\s]).+?\*\*\s*\n)', text)
    return [p.strip() for p in parts if p.strip()]

def _extract_name_url(card: str) -> tuple[str | None, str | None]:
    """Extract name and URL from bold markdown link."""
    m = re.search(r'\*\*\[([^\]]+)\]\(([^)]+)\)\*\*', card)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # No URL — just bold text
    m = re.search(r'\*\*(.+?)\*\*', card)
    if m:
        name = re.sub(r'\*+', '', m.group(1)).strip()
        return name, None
    return None, None

def _section_header(text: str) -> str | None:
    """Extract section header from ### or ## prefix, even if followed by emoji."""
    m = re.search(r'^#{2,3}\s*(.+?)(?:\n|$)', text, re.MULTILINE)
    if m:
        header = m.group(1).strip()
        # Strip leading emoji/decoration but keep Chinese text
        header = re.sub(r'^[^\u4e00-\u9fff\w\s]+', '', header).strip()
        if header and len(header) <= 30:
            return header
    return None


def _find_section_for_card(card_text: str, full_text: str) -> str | None:
    """Find the nearest section header above this card in full text."""
    # Find position of card in full text
    pos = full_text.find(card_text[:80])
    if pos < 0:
        return _section_header(card_text)

    # Search backwards for ## or ### header
    before = full_text[:pos]
    headers = list(re.finditer(r'^#{2,3}\s*(.+?)$', before, re.MULTILINE))
    if headers:
        header = headers[-1].group(1).strip()
        header = re.sub(r'^[^\u4e00-\u9fff\w\s]+', '', header).strip()
        if header and len(header) <= 30:
            return header
    return None

def _parse_duration_min(dur_str: str) -> int | None:
    """Parse '2小时20分' / '2h20min' / '2h' to minutes."""
    if not dur_str:
        return None
    dur_str = dur_str.strip()
    total = 0
    # Chinese: X小时Y分
    hm = re.match(r'(\d+)\s*小时\s*(\d+)\s*分', dur_str)
    if hm:
        return int(hm.group(1)) * 60 + int(hm.group(2))
    # English: XhYmin or XhYm
    hm = re.match(r'(\d+)\s*h\s*(\d+)\s*(?:min|m)?', dur_str)
    if hm:
        return int(hm.group(1)) * 60 + int(hm.group(2))
    # Just hours: X小时 or Xh
    h = re.match(r'(\d+)\s*(?:小时|h)', dur_str)
    if h:
        return int(h.group(1)) * 60
    # Just minutes
    m = re.match(r'(\d+)\s*(?:分钟|min)', dur_str)
    if m:
        return int(m.group(1))
    # Pure number (assume minutes)
    m = re.match(r'(\d+)', dur_str)
    if m:
        return int(m.group(1))
    return None

def _strip_markdown(text: str) -> str:
    """Remove bold/italic markers from text."""
    return re.sub(r'\*+', '', text).strip()

# ── 1. 机票解析 ────────────────────────────────────────────────

AIRLINE_PATTERNS = [
    r'\*{0,2}航班\*{0,2}[：:]\s*(.+?)(?:\s*\||\n)',     # 变体A: **航班**：东方航空 MU5100
    r'\*{0,2}航司\*{0,2}[：:]\s*(.+?)(?:\s*\||\n)',     # 变体B: **航司**：西藏航空
    r'\*{0,2}航空公司\*{0,2}[：:]\s*(.+?)(?:\s*\||\n)', # 变体C: **航空公司**：金鹏航空
    r'\*\*([^*]+?(?:航空|航| Airlines?))\*\*',            # 变体D: **深圳航空** 裸bold
]

AIRCRAFT_PATTERNS = [
    r'\*{0,2}机型\*{0,2}[：:]\s*(.+?)(?:\s*\||\n|$)',
]

DEPART_TIME_PATTERNS = [
    r'\*{0,2}时间\*{0,2}[：:]\s*(\d{1,2}:\d{2})',       # 变体A/B/C: **时间**：07:00
    r'\*{0,2}起飞\*{0,2}[：:]*\s*(\d{1,2}:\d{2})',       # 变体D: **起飞** 07:05
    r'\*{0,2}参考时段\*{0,2}[：:]\s*(\d{1,2}:\d{2})',    # 变体F: **参考时段**：07:30 - 09:50
]

ARRIVE_TIME_PATTERNS = [
    r'[→→]\s*\*{0,2}\s*(\d{1,2}:\d{2})',                # ...→09:20
    r'\*{0,2}到达\*{0,2}[：:]*\s*(\d{1,2}:\d{2})',       # **到达** 08:55
    r'\d{1,2}:\d{2}\s*[-–]\s*(\d{1,2}:\d{2})',           # 变体F: 07:30 - 09:50 (dash-separated)
]

DURATION_PATTERNS = [
    r'[（(]\s*约\s*(.+?)\s*[）)]',        # （约2小时20分）
    r'约\s*(.+?)(?:\n|\||$)',             # 约2h20min
    r'\*{0,2}飞行时间\*{0,2}[：:]\s*约\s*(.+?)(?:\n|\||$)',  # 变体F: **飞行时间**：约2小时20分
]

DEPART_AIRPORT_PATTERNS = [
    r'\*{0,2}起降\*{0,2}[：:]\s*(.+?)\s*[→→]',     # 变体A: **起降**：北京首都 → 浦东
    r'\*{0,2}航线\*{0,2}[：:]\s*(.+?)\s*[→→]',      # 变体F: **航线**：深圳宝安 → 上海虹桥
    r'([^-→\n]{2,10}机场)\s*[→→]',                  # inline: 深圳宝安机场 → 重庆江北
]

ARRIVE_AIRPORT_PATTERNS = [
    r'[→→]\s*\*{0,2}\s*(.+?(?:机场|航站楼))',        # → 上海浦东机场
    r'\*{0,2}到达\*{0,2}[：:]\s*(.+?)(?:\n|$)',       # 变体C: **到达**：浦东国际机场
    r'\*{0,2}航线\*{0,2}[：:].+?[→→]\s*(.+?)(?:\s*\||\n|$)',  # 变体F: **航线**：... → 上海虹桥
]

HIGHLIGHT_PATTERNS = [
    r'\*{0,2}(?:特点|亮点|推荐理由)\*{0,2}[：:]\s*(.+?)(?:\n|$)',
]

TRADEOFF_PATTERNS = [
    r'\*{0,2}权衡\*{0,2}[：:]\s*(.+?)(?:\n|$)',
]


def _extract_route_airports(text: str) -> dict:
    """Extract departure/arrival airports from intro paragraph (fallback)."""
    airports = {}
    # "从深圳宝安国际机场出发"
    m = re.search(r'从\s*(.+?机场)', text)
    if m:
        airports["depart"] = m.group(1)
    # "均为直飞" → try route-specific context
    m = re.search(r'([\u4e00-\u9fa5]+(?:机场|航空港))', text)
    return airports


def _parse_table_flights(text: str) -> list[dict]:
    """Parse supplementary table flights (变体D's '其他可选航班' / 变体C's summary)."""
    flights = []
    # Match table: | 航班号 | 航司 | 起飞 | 到达 | 用时 |
    table_pattern = re.compile(
        r'\|\s*([A-Z0-9]{2,6})\s*\|\s*([^\|]+?)\s*\|\s*(\d{1,2}:\d{2})\s*\|\s*(\d{1,2}:\d{2})\s*\|\s*([^\|\n]+)',
        re.MULTILINE
    )
    for m in table_pattern.finditer(text):
        flight_no = m.group(1).strip()
        airline = m.group(2).strip()
        depart_time = m.group(3).strip()
        arrive_time = m.group(4).strip()
        dur_str = m.group(5).strip()
        duration_min = _parse_duration_min(dur_str)

        flights.append({
            "name": flight_no,
            "title": flight_no,
            "description": f"{airline} | {depart_time}→{arrive_time} | {dur_str}",
            "source": "fliggy_remote",
            "flight": {
                "flight_no": flight_no,
                "airline": airline,
                "aircraft": None,
                "depart_time": depart_time,
                "arrive_time": arrive_time,
                "depart_airport": "",
                "arrive_airport": "",
                "duration_min": duration_min,
                "highlight": None,
                "tradeoff": None,
                "section": None,
            },
        })
    return flights


def _parse_flight_table(text: str) -> list[dict] | None:
    """Parse flight data from markdown tables with bold-linked flight numbers (变体G).
    
    Format:
    | **HU7721** | 新海航/海南航空 | 78A | **09:15→11:45** | 2h30min | 浦东(PVG) |
    | 航班号 | 航空公司 | 机型 | 起飞→到达 | 时长 | 到达机场 |
    
    Returns None if no flight table found.
    """
    # Match table rows with bold flight numbers: | **FLIGHT_NO** | airline | aircraft | time | dur | airport |
    table_rows = re.findall(
        r'\|\s*\*\*([A-Z0-9]{2,6})\*\*\s*\|'
        r'\s*(.+?)\s*\|'
        r'\s*(.+?)\s*\|'
        r'\s*\*{0,2}(\d{1,2}:\d{2})[→→](\d{1,2}:\d{2})\*{0,2}\s*\|'
        r'\s*(.+?)\s*\|'
        r'\s*(.+?)\s*\|',
        text
    )
    if not table_rows:
        return None
    
    flights = []
    for flight_no, airline, aircraft, depart_time, arrive_time, dur_col, airport_col in table_rows:
        flight_no = flight_no.strip()
        airline = airline.strip()
        aircraft = aircraft.strip()
        dur_col = dur_col.strip()
        airport_col = airport_col.strip()
        
        duration_min = _parse_duration_min(dur_col) if dur_col else None
        
        # Clean airport: "浦东(PVG)" or "虹桥(SHA)" → expand to full name
        arrive_airport = airport_col
        
        flights.append({
            "name": flight_no,
            "title": flight_no,
            "description": f"{airline} | {aircraft} | {depart_time}→{arrive_time} | {dur_col} | {airport_col}",
            "source": "fliggy_remote",
            "flight": {
                "flight_no": flight_no,
                "airline": airline,
                "aircraft": aircraft,
                "depart_time": depart_time,
                "arrive_time": arrive_time,
                "depart_airport": "",  # extracted from intro text below
                "arrive_airport": arrive_airport,
                "duration_min": duration_min,
                "highlight": None,
                "tradeoff": None,
                "section": None,
            },
        })
    
    # Extract departure airport from intro text
    # "从深圳（宝安国际机场）→上海" / "从深圳宝安机场出发" / "从**深圳（宝安国际机场）→上海**"
    dep_match = re.search(r'从\s*\*{0,2}(.+?(?:机场|国际机场))', text)
    if dep_match:
        dep_airport = dep_match.group(1)
        # Clean: remove bold markers, parentheses, trailing arrows
        dep_airport = re.sub(r'\*+', '', dep_airport)
        dep_airport = re.sub(r'[（()）]', '', dep_airport)
        dep_airport = re.sub(r'\s*[→→].*$', '', dep_airport).strip()
        for f in flights:
            if not f["flight"]["depart_airport"]:
                f["flight"]["depart_airport"] = dep_airport
    
    return flights if flights else None


def _parse_flights(text: str) -> list[dict]:
    # 0. No-result detection
    if any(kw in text for kw in ['暂未查到', '暂无', '暂未查询到']):
        if '数据仅更新至' in text:
            return _info_card("数据范围提示", text)
        return _info_card("无直达航班", text)

    # 0.5 Try table format first (变体G: 航班号 | 航空公司 | 机型 | 起飞→到达 | 时长 | 到达机场)
    table_flights = _parse_flight_table(text)
    if table_flights and len(table_flights) >= 2:
        return table_flights

    flights = []

    # 1. Split by bold cards
    cards = _split_bold_cards(text)
    # Filter out intro/outro paragraphs (no bold link)
    cards = [c for c in cards if re.search(r'\*\*\[.+\]\(.+\)\*\*', c)]

    for card in cards:
        flight_no, booking_url = _extract_name_url(card)

        depart_time = _field(card, DEPART_TIME_PATTERNS)
        arrive_time = _field(card, ARRIVE_TIME_PATTERNS)
        dur_str = _field(card, DURATION_PATTERNS)
        duration_min = _parse_duration_min(dur_str) if dur_str else None

        depart_airport = _field(card, DEPART_AIRPORT_PATTERNS)
        arrive_airport = _field(card, ARRIVE_AIRPORT_PATTERNS)
        section = _find_section_for_card(card, text)

        flights.append({
            "name": flight_no or "",
            "title": flight_no or "",
            "description": card[:500],
            "source": "fliggy_remote",
            "booking_url": booking_url,
            "flight": {
                "flight_no": flight_no or "",
                "airline": _field(card, AIRLINE_PATTERNS) or "",
                "aircraft": _field(card, AIRCRAFT_PATTERNS),
                "depart_time": depart_time or "",
                "arrive_time": arrive_time or "",
                "depart_airport": depart_airport or "",
                "arrive_airport": arrive_airport or "",
                "duration_min": duration_min,
                "highlight": _field(card, HIGHLIGHT_PATTERNS),
                "tradeoff": _field(card, TRADEOFF_PATTERNS),
                "section": section,
            },
        })

    # 2. Supplementary table flights (变体D)
    table_flights = _parse_table_flights(text)
    existing_nos = {f["flight"]["flight_no"] for f in flights}
    for tf in table_flights:
        if tf["flight"]["flight_no"] not in existing_nos:
            flights.append(tf)

    # 3. Airport fallback
    route_airports = _extract_route_airports(text)
    for f in flights:
        fd = f["flight"]
        if not fd["depart_airport"] and route_airports.get("depart"):
            fd["depart_airport"] = route_airports["depart"]

    return flights if flights else [{"title": "搜索结果", "description": text[:500], "source": "fliggy_remote"}]


# ── 2. 火车票解析 ──────────────────────────────────────────────

# Route+time patterns (one must match for each train card)
ROUTE_TIME_CLEAN = re.compile(
    r'\*{0,2}([\u4e00-\u9fa5]+(?:站|北|南|东|西)?)\s*[→→]\s*'
    r'([\u4e00-\u9fa5]+(?:站|北|南|东|西)?)\*{0,2}\s*\|\s*'
    r'(\d{1,2}:\d{2})[→→](\d{1,2}:\d{2})'
)
ROUTE_TIME_EMOJI = re.compile(
    r'[\U0001F300-\U0001FFFF🚀-🛿]*\s*\*{0,2}'
    r'([\u4e00-\u9fa5]+(?:站|北|南|东|西)?)\s*(\d{1,2}:\d{2})\s*[→→]\s*'
    r'([\u4e00-\u9fa5]+(?:站|北|南|东|西)?)\s*(\d{1,2}:\d{2})'
)
ROUTE_IN_HIGHLIGHT = re.compile(
    r'([\u4e00-\u9fa5]+(?:站|北|南|东|西)?)[→→]'
    r'([\u4e00-\u9fa5]+(?:站|北|南|东|西)?)[，,]\s*约(\d+)分钟'
)

TRAIN_TYPE_PATTERNS = [
    r'\*{0,2}类型\*{0,2}[：:]\s*(.+?)(?:\n|$)',
]

HIGHLIGHT_TRAIN_PATTERNS = [
    r'\*{0,2}(?:推荐理由|亮点)\*{0,2}[：:]\s*(.+?)(?:\n|$)',
    r'[✅✓]\s*(.+?)(?:\n|$)',             # 变体C: ✅ 最早出发
]


def _has_overview_table(text: str) -> bool:
    """Detect overview table (变体A): header has '车型' + '车次举例'."""
    return bool(re.search(r'\|\s*车型\s*\|.*车次举例', text))


def _remove_overview_table(text: str) -> str:
    """Remove overview table section to avoid parsing as individual trains."""
    # Remove from "## 主要车型概览" or table start to next "##" or "---"
    text = re.sub(
        r'(?:#{1,3}\s*主要车型.*?\n)?\|[^\n]*车型[^\n]*\|[^\n]*\n\|[-:\|\s]+\n(?:.*?\n)*?(?=\n##|\n---|\n\*\*)',
        '', text, flags=re.DOTALL
    )
    return text


def _infer_train_type(card: str, section: str | None) -> str:
    """Infer train type from section header or explicit type field."""
    type_field = _field(card, TRAIN_TYPE_PATTERNS)
    if type_field:
        return type_field

    if section:
        section_lower = section.lower()
        if '高铁' in section or 'g字' in section_lower:
            return '高铁'
        if '动车' in section or 'd字' in section_lower:
            return '动车'
        if '普速' in section or '普快' in section or '特快' in section:
            return '普速'
        if '城际' in section or 'c字' in section_lower:
            return '城际'
        if '夜间' in section:
            return '夜间列车'

    # Infer from train number prefix
    if card:
        m = re.search(r'\*\*\[?([GDCZTK]\d+)', card)
        if m:
            prefix = m.group(1)[0].upper()
            return {'G': '高铁', 'D': '动车', 'C': '城际', 'Z': '直达特快', 'T': '特快', 'K': '普快'}.get(prefix, '')

    return ''


def _parse_train_table(text: str) -> list[dict] | None:
    """Parse train data from markdown tables (变体E + 变体H).
    
    Format E (with URL):  | **[G1](url)** | 北京南 → 上海虹桥 | 06:30→11:24 | 约4h54min |
    Format H (no URL):    | **G2942** | 深圳北 → 重庆西 | 约 **6小时22分** | 07:04→13:26 |
    
    Returns None if no train table found.
    """
    trains = []
    
    # Try Format E first: **[TRAIN](url)** with link
    rows_e = re.findall(
        r'\|\s*\*\*\[([A-Z0-9]+)\]\(([^)]+)\)\*\*\s*\|'
        r'\s*(.+?)\s*\|'
        r'\s*(.+?)\s*\|'
        r'\s*(.+?)\s*\|',
        text
    )
    if rows_e:
        for train_no, url, route_col, time_col, dur_col in rows_e:
            train_no = train_no.strip()
            route_col = route_col.strip()
            time_col_clean = time_col.strip()
            dur_col_clean = dur_col.strip()
            
            depart_station, arrive_station = "", ""
            rm = re.match(r'([\u4e00-\u9fa5]+(?:站|北|南|东|西)?)\s*[→→]\s*([\u4e00-\u9fa5]+(?:站|北|南|东|西)?)', route_col)
            if rm:
                depart_station, arrive_station = rm.group(1), rm.group(2)
            
            depart_time, arrive_time = "", ""
            tm = re.match(r'(\d{1,2}:\d{2})\s*[→→]\s*(\d{1,2}:\d{2})', time_col_clean)
            if tm:
                depart_time, arrive_time = tm.group(1), tm.group(2)
            
            duration_min = _parse_duration_min(dur_col_clean.split('（')[0].strip()) if dur_col_clean else None
            train_type = _infer_train_type(f"**[{train_no}]**", None)
            section = _find_section_for_card(f"**[{train_no}]", text)
            
            trains.append(_make_train_item(train_no, url, train_type, depart_station, arrive_station,
                                           depart_time, arrive_time, duration_min, section, dur_col_clean))
        if trains:
            return trains
    
    # Try Format H: **TRAIN** without URL, columns: train_no | stations | duration | time
    rows_h = re.findall(
        r'\|\s*\*\*([A-Z0-9/]+)\*\*\s*\|'
        r'\s*(.+?)\s*\|'
        r'\s*.+?\s*\|'     # duration column (parse separately)
        r'\s*(.+?)\s*\|',   # time column
        text
    )
    if rows_h:
        for train_no_raw, route_col, time_col in rows_h:
            train_no = train_no_raw.strip()
            route_col = route_col.strip()
            time_col_clean = re.sub(r'\*+', '', time_col).strip()
            
            depart_station, arrive_station = "", ""
            rm = re.match(r'([\u4e00-\u9fa5]+(?:站|北|南|东|西)?)\s*[→→]\s*([\u4e00-\u9fa5]+(?:站|北|南|东|西)?)', route_col)
            if rm:
                depart_station, arrive_station = rm.group(1), rm.group(2)
            
            # Parse time: "07:04→13:26" or "18:32→次日06:06" or "次日06:06"
            depart_time, arrive_time = "", ""
            # Standard: HH:MM→HH:MM
            tm = re.search(r'(\d{1,2}:\d{2})\s*[→→]\s*(?:次日\s*)?(\d{1,2}:\d{2})', time_col_clean)
            if tm:
                depart_time, arrive_time = tm.group(1), tm.group(2)
            elif re.search(r'次日', time_col_clean):
                # Only arrival time: "次日06:06"
                am = re.search(r'(\d{1,2}:\d{2})', time_col_clean)
                if am:
                    arrive_time = am.group(1)
            
            # Duration: extract from the same row via separate search on the full text
            # Pattern: "约 **6小时22分**" or "约 **11小时34分**"
            dur_min = None
            dur_match = re.search(
                r'\|\s*\*\*' + re.escape(train_no_raw.strip()) + r'\*\*\s*\|[^|]*\|[^|]*?约\s*\*{0,2}(.+?)\*{0,2}\s*\|',
                text
            )
            if dur_match:
                dur_str = re.sub(r'\*+', '', dur_match.group(1)).strip()
                dur_min = _parse_duration_min(dur_str)
            
            train_type = _infer_train_type(f"**[{train_no.split('/')[0]}]**", None)
            section = _find_section_for_card(f"**[{train_no}]", text)
            
            trains.append(_make_train_item(train_no, "", train_type, depart_station, arrive_station,
                                           depart_time, arrive_time, dur_min, section, time_col_clean))
        if trains:
            return trains
    
    return None


def _make_train_item(train_no, url, train_type, depart_station, arrive_station,
                     depart_time, arrive_time, duration_min, section, desc_extra=""):
    return {
        "name": train_no,
        "title": train_no,
        "description": f"{depart_station}→{arrive_station} | {depart_time}→{arrive_time} | {desc_extra}",
        "source": "fliggy_remote",
        "booking_url": url or None,
        "train": {
            "train_no": train_no,
            "train_type": train_type,
            "depart_station": depart_station,
            "arrive_station": arrive_station,
            "depart_time": depart_time,
            "arrive_time": arrive_time,
            "duration_min": duration_min,
            "highlight": None,
            "tradeoff": None,
            "section": section,
        },
    }


def _parse_trains(text: str) -> list[dict]:
    # 0. No-result
    if '暂未查到' in text or '暂无' in text:
        return _info_card("无直达车次", text)

    # 0.5 Try table format first (变体E: bold-linked train numbers in table rows)
    # Only accept if most rows have valid station data (quality gate)
    table_trains = _parse_train_table(text)
    if table_trains:
        valid_count = sum(1 for t in table_trains if t["train"].get("depart_station"))
        if valid_count >= len(table_trains) * 0.5 and valid_count >= 2:
            return table_trains
        # Low quality — fall through to bold card parsing

    # 1. Remove overview table if present (变体A)
    if _has_overview_table(text):
        text = _remove_overview_table(text)

    # 2. Split by bold cards
    cards = _split_bold_cards(text)
    cards = [c for c in cards if re.search(r'\*\*\[.+\]\(.+\)\*\*', c)]

    trains = []
    for card in cards:
        train_no, booking_url = _extract_name_url(card)
        section = _find_section_for_card(card, text)

        depart_station = ""
        arrive_station = ""
        depart_time = ""
        arrive_time = ""
        duration_min = None

        # Try station extraction from: **出发站**：北京站 → **到达站**：上海站 (变体D)
        st_match = re.search(
            r'\*{0,2}出发站\*{0,2}[：:]\s*(.+?)\s*[→→]\s*\*{0,2}到达站\*{0,2}[：:]\s*(.+?)(?:\n|$)',
            card
        )
        if st_match:
            depart_station = st_match.group(1).strip()
            arrive_station = st_match.group(2).strip()

        # Try time extraction from: **发车**：4月15日 **20:04** → 4月16日 **11:02** (变体D)
        tm_match = re.search(
            r'\*{0,2}发车\*{0,2}[：:]\s*(?:\d+月\d+日\s*)?\*{0,2}(\d{1,2}:\d{2})\*{0,2}\s*[→→]\s*'
            r'(?:\d+月\d+日\s*)?\*{0,2}(\d{1,2}:\d{2})\*{0,2}',
            card
        )
        if tm_match:
            depart_time = tm_match.group(1)
            arrive_time = tm_match.group(2)

        # If no station from specific fields, try route+time line patterns
        if not depart_station:
            # Extract route + time from first/second line
            # Priority: clean > emoji > highlight
            rt = ROUTE_TIME_CLEAN.search(card)
            if not rt:
                rt = ROUTE_TIME_EMOJI.search(card)
            if not rt:
                rt = ROUTE_IN_HIGHLIGHT.search(card)

            if rt:
                if ROUTE_TIME_CLEAN.search(card) or ROUTE_IN_HIGHLIGHT.search(card):
                    depart_station = rt.group(1)
                    arrive_station = rt.group(2)
                    depart_time = rt.group(3) if rt.lastindex and rt.lastindex >= 3 else ""
                    arrive_time = rt.group(4) if rt.lastindex and rt.lastindex >= 4 else ""
                    if rt.lastindex == 3:
                        depart_time = ""
                        arrive_time = ""
                        duration_min = int(rt.group(3)) if rt.group(3) else None
                else:
                    # ROUTE_TIME_EMOJI: station time station time
                    depart_station = rt.group(1)
                    depart_time = rt.group(2)
                    arrive_station = rt.group(3)
                    arrive_time = rt.group(4)

        # Duration from separate extraction
        dur_str = _field(card, DURATION_PATTERNS)
        if dur_str and duration_min is None:
            duration_min = _parse_duration_min(dur_str)
        # Also try ⏱ field (变体C)
        if duration_min is None:
            dm = re.search(r'⏱\s*约\s*\*{0,2}(.+?)\*{0,2}', card)
            if dm:
                duration_min = _parse_duration_min(dm.group(1))

        highlight = _field(card, HIGHLIGHT_TRAIN_PATTERNS)
        # If no highlight, use description line (non-structured text after route)
        if not highlight:
            lines = card.strip().split('\n')
            for i, line in enumerate(lines):
                if i >= 2:  # Skip bold name + route line
                    clean = re.sub(r'\*+|^[-•]\s*|💡.*$', '', line).strip()
                    if clean and not clean.startswith('⏱') and not clean.startswith('✅'):
                        if not re.match(r'^(?:推荐理由|亮点|权衡)', clean):
                            if len(clean) > 3 and len(clean) < 100:
                                highlight = clean
                                break

        tradeoff = _field(card, [r'\*{0,2}权衡\*{0,2}[：:]\s*(.+?)(?:\n|$)'])

        trains.append({
            "name": train_no or "",
            "title": train_no or "",
            "description": card[:500],
            "source": "fliggy_remote",
            "booking_url": booking_url,
            "train": {
                "train_no": train_no or "",
                "train_type": _infer_train_type(card, section),
                "depart_station": depart_station,
                "arrive_station": arrive_station,
                "depart_time": depart_time,
                "arrive_time": arrive_time,
                "duration_min": duration_min,
                "highlight": highlight,
                "tradeoff": tradeoff,
                "section": section,
            },
        })

    return trains if trains else [{"title": "搜索结果", "description": text[:500], "source": "fliggy_remote"}]


# ── 3. 酒店/景点解析（共享）────────────────────────────────────

HOTEL_POI_HIGHLIGHT = [r'\*{0,2}亮点\*{0,2}[：:]\s*(.+?)(?:\n|$)']
HOTEL_POI_RECOMMEND = [r'\*{0,2}推荐理由\*{0,2}[：:]\s*(.+?)(?:\n|$)']
HOTEL_POI_TRADEOFF = [r'\*{0,2}权衡\*{0,2}[：:]\s*(.+?)(?:\n|$)']
POI_DURATION = [r'\*{0,2}建议游玩\*{0,2}[：:]\s*(.+?)(?:\n|$)']
POI_HOURS = [r'\*{0,2}开放时间\*{0,2}[：:]\s*(.+?)(?:\n|$)']


def _parse_hotels_or_pois(text: str, kind: str) -> list[dict]:
    cards = _split_bold_cards(text)
    cards = [c for c in cards if re.search(r'\*\*\[.+\]\(.+\)\*\*', c)]

    items = []
    for card in cards:
        name, booking_url = _extract_name_url(card)
        section = _find_section_for_card(card, text)

        item = {
            "name": name or "",
            "title": name or "",
            "description": card[:500],
            "source": "fliggy_remote",
            "booking_url": booking_url,
        }

        if kind == "hotel":
            item["hotel"] = {
                "highlight": _field(card, HOTEL_POI_HIGHLIGHT) or "",
                "recommendation": _field(card, HOTEL_POI_RECOMMEND) or "",
                "tradeoff": _field(card, HOTEL_POI_TRADEOFF),
                "section": section,
            }
        else:  # poi
            is_free = bool(re.search(r'免费|无需购票|free', card, re.IGNORECASE))
            price_match = re.search(r'[¥￥](\d+\.?\d*)', card)
            item["poi"] = {
                "highlight": _field(card, HOTEL_POI_HIGHLIGHT) or "",
                "recommendation": _field(card, HOTEL_POI_RECOMMEND) or "",
                "suggested_duration": _field(card, POI_DURATION),
                "hours": _field(card, POI_HOURS),
                "is_free": is_free,
                "section": section,
            }
            if price_match and not is_free:
                item["price"] = float(price_match.group(1))

        items.append(item)

    return items if items else [{"title": "搜索结果", "description": text[:500], "source": "fliggy_remote"}]


# ── 4. 美食解析 ─────────────────────────────────────────────────

def _parse_foods(text: str) -> list[dict]:
    items = []

    # Each food item: "N. Name [Category]\n   ⭐X.X | 人均¥XX\n   📍 Address"
    for match in re.finditer(
        r'(?:^|\n)(\d+)\.\s*(.+?)(?:\s*\[([^\]]+)\]|\s*（([^）]+)）)?\s*\n'
        r'(.*?)(?=\n\d+\.\s|\n💡|\n\n|\Z)',
        text, re.DOTALL
    ):
        name = match.group(2).strip()
        category = (match.group(3) or match.group(4) or "").strip()
        detail_block = match.group(5).strip()

        rating = None
        rm = re.search(r'[⭐🌟](\d+\.?\d*)', detail_block)
        if rm:
            rating = float(rm.group(1))

        price_per_person = None
        pm = re.search(r'人均[¥￥](\d+\.?\d*)', detail_block)
        if pm:
            price_per_person = float(pm.group(1))

        address = None
        am = re.search(r'📍\s*(.+)', detail_block)
        if am:
            address = am.group(1).strip()

        items.append({
            "name": name,
            "title": name,
            "description": detail_block[:300],
            "source": "fliggy_remote",
            "price": price_per_person,
            "food": {
                "rating": rating,
                "price_per_person": price_per_person,
                "category": category,
                "address": address or "",
            },
        })

    return items if items else [{"title": "搜索结果", "description": text[:500], "source": "fliggy_remote"}]


# ── 5. 交通解析 ─────────────────────────────────────────────────

def _parse_transport(text: str) -> list[dict]:
    # Check for MCP errors
    if '无法解析' in text or '未找到' in text:
        return _error_card(text)

    items = []

    # Route header
    route_match = re.search(r'📍\s*(.+?)\s*(?:交通方式)?\s*\n', text)
    route_title = route_match.group(1).strip() if route_match else "交通路线"
    # Clean up route title (remove leading "市" artifact)
    route_title = re.sub(r'^\s*市\s+', '', route_title)

    # Split by section separators
    sections = re.split(r'━{3,}\s*(🚗|🚇|🚌|🚄|🚕|🛵|🚲).+?\s*━{3,}', text)

    for i in range(1, len(sections) - 1, 2):
        emoji = sections[i]
        content = sections[i + 1] if i + 1 < len(sections) else ""

        dist_match = re.search(r'距离(\d+\.?\d*)公里', content)
        time_match = re.search(r'约(\d+)分钟', content)
        cost_match = re.search(r'[¥￥](\d+\.?\d*)', content)

        mode_name = {
            "🚗": "打车/驾车", "🚕": "出租车",
            "🚇": "地铁/城轨", "🚌": "公交",
            "🚄": "铁路", "🛵": "电动车", "🚲": "自行车"
        }.get(emoji, "交通")

        # Extract route detail for bus lines
        route_detail = None
        rm = re.search(r'方案\d*[：:]\s*(.+?)(?:\n|$)', content)
        if rm:
            route_detail = rm.group(1).strip()

        item = {
            "name": f"{route_title} · {mode_name}",
            "title": mode_name,
            "description": content.strip()[:400],
            "source": "fliggy_remote",
            "transport": {
                "mode": mode_name,
                "distance_km": float(dist_match.group(1)) if dist_match else None,
                "duration_min": int(time_match.group(1)) if time_match else None,
                "cost": float(cost_match.group(1)) if cost_match else None,
                "route_detail": route_detail,
            },
        }
        if cost_match:
            item["price"] = float(cost_match.group(1))
        items.append(item)

    return items if items else [{"title": "搜索结果", "description": text[:500], "source": "fliggy_remote"}]


# ── 入口分派 ───────────────────────────────────────────────────

def _parse_markdown_response(text: str, tool_name: str) -> list[dict]:
    """Parse MCP markdown response into structured items, tool-specific dispatch."""

    if not text or not isinstance(text, str):
        return []

    if tool_name == "search_flight":
        return _parse_flights(text)
    elif tool_name == "search_train":
        return _parse_trains(text)
    elif tool_name == "search_hotel":
        return _parse_hotels_or_pois(text, "hotel")
    elif tool_name == "search_poi":
        return _parse_hotels_or_pois(text, "poi")
    elif tool_name == "search_food":
        return _parse_foods(text)
    elif tool_name == "search_transport":
        return _parse_transport(text)

    # Unknown tool — generic fallback
    if '无法解析' in text or '未找到' in text:
        return _error_card(text)
    return [{"title": "搜索结果", "description": text[:500], "source": "fliggy_remote"}]
