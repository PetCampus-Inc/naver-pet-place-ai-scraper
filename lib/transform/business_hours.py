"""현재 상세 business_hours 구조를 info_new.json 스타일의 축약 구조로 변환.

입력 (lib/scrapper/naver_place_parser.py `_parse_business_hours`가 만드는 형태):
    {"name": str, "description": str, "is_24h": bool, "temporary_closure": bool,
     "regular_off_pattern": str|None, "days": {...}, "offdays": [...],
     "irregular_offdays": [...], "weekdays": "HH:MM - HH:MM"|None, "weekends": "HH:MM - HH:MM"|None}

출력:
    {"name": "DEFAULT"|enum, "weekdays": {"open","close"}|None,
     "weekends": {"open","close"}|None, "offdays": ["MONDAY", ...]}

주의: irregular_offdays(그 주만의 임시휴무)는 포함하지 않음 — offdays(정기휴무)만
"영구적인 정보"라는 기존 프롬프트의 데이터 품질 규칙과 일관되게 유지.
"""

from lib.transform.enum_maps import WEEKDAY_KO_TO_EN
from lib.transform.keyword_match import is_default_business_hours_name, match_categories_in_text


def _parse_time_range(compressed: str):
    """'10:00 - 19:00' -> {'open': '10:00', 'close': '19:00'}. 파싱 불가하면 None."""
    if not compressed:
        return None
    parts = compressed.split(" - ")
    if len(parts) != 2:
        return None
    open_time, close_time = parts[0].strip(), parts[1].strip()
    if not open_time or not close_time:
        return None
    return {"open": open_time, "close": close_time}


def _map_business_hours_name(raw_name: str) -> str:
    if is_default_business_hours_name(raw_name):
        return "DEFAULT"
    matched = match_categories_in_text(raw_name)
    return matched[0] if matched else "DEFAULT"


def to_final_business_hours(business_hours: list) -> list:
    result = []
    for entry in business_hours or []:
        offdays_en = [
            WEEKDAY_KO_TO_EN[d] for d in (entry.get("offdays") or []) if d in WEEKDAY_KO_TO_EN
        ]
        result.append({
            "name": _map_business_hours_name(entry.get("name", "")),
            "weekdays": _parse_time_range(entry.get("weekdays")),
            "weekends": _parse_time_range(entry.get("weekends")),
            "offdays": offdays_en,
        })
    return result
