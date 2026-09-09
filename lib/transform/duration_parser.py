"""상품명 텍스트에서 단위(unit/unit_type)와 소요시간을 정규식으로 파싱.

**AI를 전혀 사용하지 않음 — 100% 순수 파이썬 정규식/사칙연산.**

원본 텍스트에 명시적으로 없는 소요시간(예: "산책"에 별도 시간 언급 없이
암묵적으로 30분으로 가정하는 것 같은 업무 규칙)은 절대 추측해서 채우지
않고 None으로 남긴다.
"""

import re

# 우선순위대로 검사: 시간 > 박 > 일 > 회
_UNIT_PATTERNS = [
    (re.compile(r"(\d+(?:\.\d+)?)\s*시간"), "HOUR"),
    (re.compile(r"(\d+(?:\.\d+)?)\s*박"), "NIGHT"),
    (re.compile(r"(\d+(?:\.\d+)?)\s*일"), "DAY"),
    (re.compile(r"(\d+(?:\.\d+)?)\s*회"), "COUNT"),
]

# 상품명에 명시적으로 박혀있는 시간 범위/총 시간 표기만 파싱 (추측 없음)
_TIME_RANGE_PATTERN = re.compile(r"(\d{1,2}):(\d{2})\s*[~\-]\s*(\d{1,2}):(\d{2})")
_PAREN_HOUR_PATTERN = re.compile(r"\(\s*(\d+(?:\.\d+)?)\s*[Hh]\s*\)")


def parse_unit(text: str):
    """'5시간' -> (5.0, 'HOUR'), '1박' -> (1.0, 'NIGHT') 등. 매칭 실패 시 (None, None)."""
    if not text:
        return None, None
    for pattern, unit_type in _UNIT_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1)), unit_type
    return None, None


def parse_explicit_duration_minutes(text: str):
    """상품명에 명시적으로 박힌 시간 정보만 분 단위로 계산.
    ('08:00~21:00' 같은 시간대 표기, '(24H)' 같은 총 시간 표기)
    아무 패턴도 없으면 None (추측하지 않음).
    """
    if not text:
        return None

    range_match = _TIME_RANGE_PATTERN.search(text)
    if range_match:
        start_h, start_m, end_h, end_m = (int(g) for g in range_match.groups())
        start_total = start_h * 60 + start_m
        end_total = end_h * 60 + end_m
        diff = end_total - start_total
        if diff < 0:
            diff += 24 * 60  # 자정 넘어가는 경우
        return diff if diff > 0 else None

    hour_match = _PAREN_HOUR_PATTERN.search(text)
    if hour_match:
        return float(hour_match.group(1)) * 60

    return None


def minutes_to_hour_str(minutes):
    if minutes is None:
        return None
    hours = minutes / 60
    return f"{hours:g}시간"


_RANGE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:kg)?\s*[~\-]\s*(\d+(?:\.\d+)?)\s*kg?")
_UNDER_PATTERN = re.compile(r"^\s*~?\s*(\d+(?:\.\d+)?)\s*kg")
_OVER_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*kg\s*~\s*$")


def parse_weight_range(text: str):
    """'~5kg' -> [0, 5.0], '5.1kg~8kg' -> [5.1, 8.0], '15.1kg~' -> [15.1, 0].
    0은 '그쪽 경계 없음'을 뜻함 (product_pricing.json 실측 표기와 동일).
    파싱 불가('전체중' 등)하면 [0, 0].
    """
    if not text:
        return [0, 0]

    range_match = _RANGE_PATTERN.search(text)
    if range_match:
        return [float(range_match.group(1)), float(range_match.group(2))]

    over_match = _OVER_PATTERN.search(text)
    if over_match:
        return [float(over_match.group(1)), 0]

    under_match = _UNDER_PATTERN.search(text)
    if under_match:
        return [0, float(under_match.group(1))]

    return [0, 0]
