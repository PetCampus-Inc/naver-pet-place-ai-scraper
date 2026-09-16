"""menus(개별 이용권 목록) → price_and_product.json 스타일 상세 상품 테이블.

**AI 미사용 — 정규식/사전 매핑/사칙연산만으로 동작하는 순수 파이썬 변환기.**

price_and_product.json을 실측 분석해서 나온 규칙:
    - min_price / max_price: 같은 업체(kindergarten_id) 안에서 service_type별로
      그룹을 나눠, 그룹 내 최저가/최고가 항목에 true (실제 데이터로 검증함)
    - business_hours_str/minutes: 상품명에 "HH:MM~HH:MM"나 "(NH)" 같은 시간이
      명시된 경우에만 계산. "산책=0.5시간"처럼 텍스트 근거 없이 업종 지식으로
      채워야 하는 기본값은 원본 텍스트 어디에도 없어서 **재현 불가 판단, null로
      남김** (사용자 확인: 이 부분 없어도 됨)
"""

from collections import defaultdict

from lib.transform.enum_maps import (
    SERVICE_TYPE_KEYWORDS_DETAILED,
    SERVICE_TYPE_FALLBACK,
)
from lib.transform.duration_parser import (
    parse_unit,
    parse_explicit_duration_minutes,
    minutes_to_hour_str,
)


def _match_service_type_detailed(name: str, package: str) -> str:
    haystack = f"{name or ''} {package or ''}"
    for keyword, service_type in SERVICE_TYPE_KEYWORDS_DETAILED:
        if keyword in haystack:
            return service_type
    return SERVICE_TYPE_FALLBACK


def _resolve_product_type(menu_type: str, unit_type: str) -> str:
    if menu_type == "정기권":
        return "MONTHLY_TICKET"
    if unit_type == "HOUR":
        return "TIME_TICKET"
    return "COUNT_TICKET"


def _build_row(place_id, place_name: str, menu: dict) -> dict:
    name = menu.get("name")
    unit, unit_type = parse_unit(name)

    if unit_type == "HOUR" and unit:
        duration_minutes = unit * 60
    elif unit_type == "NIGHT" and unit:
        # '박'은 숙박업 관례상 1박 = 24시간으로 정의가 고정되어 있어 텍스트에
        # 시간이 명시되지 않아도 추측이 아니라 단위 자체의 정의로 계산함
        # (실제 참고 데이터(price_and_product.json/product_pricing.json)로 교차검증함)
        duration_minutes = unit * 24 * 60
    else:
        duration_minutes = parse_explicit_duration_minutes(name)

    price = menu.get("price")
    hourly_price = None
    if duration_minutes and isinstance(price, (int, float)):
        hourly_price = price / (duration_minutes / 60)

    return {
        "kindergarten_id": place_id,
        "name": place_name,
        "product_type": _resolve_product_type(menu.get("type"), unit_type),
        "service_type": _match_service_type_detailed(name, menu.get("package")),
        "product_name": name,
        "unit_str": None if unit is None else _format_unit_str(unit, unit_type),
        "unit": unit,
        "unit_type": unit_type,
        "weight_range": menu.get("weight_range"),
        "price": price,
        "hourly_price": hourly_price,
        "business_hours_minutes": duration_minutes,
        "total_duration_minutes": duration_minutes,
        "business_hours_str": minutes_to_hour_str(duration_minutes),
        "total_duration_str": minutes_to_hour_str(duration_minutes),
        # min_price / max_price는 업체 단위로 다 모은 뒤 별도 계산 (_apply_min_max)
    }


_UNIT_SUFFIX = {"HOUR": "시간", "NIGHT": "박", "DAY": "일", "COUNT": "회"}


def _format_unit_str(unit: float, unit_type: str) -> str:
    suffix = _UNIT_SUFFIX.get(unit_type, "")
    unit_num = int(unit) if unit == int(unit) else unit
    return f"{unit_num}{suffix}"


def _apply_min_max(rows: list) -> None:
    groups = defaultdict(list)
    for row in rows:
        if isinstance(row.get("price"), (int, float)):
            groups[(row["kindergarten_id"], row["service_type"])].append(row)

    for group_rows in groups.values():
        prices = [r["price"] for r in group_rows]
        min_price, max_price = min(prices), max(prices)
        for row in group_rows:
            row["min_price"] = row["price"] == min_price
            row["max_price"] = row["price"] == max_price

    for row in rows:
        row.setdefault("min_price", False)
        row.setdefault("max_price", False)


def to_price_and_product_rows(place_id, place_name: str, menus: list) -> list:
    return [_build_row(place_id, place_name, menu) for menu in (menus or [])]


def apply_min_max_across_places(all_rows: list) -> list:
    """여러 업체의 행을 한 번에 받아 min/max를 계산 (업체 단위 그룹핑이라
    업체별로 따로 호출해도 되고, 한 지역 전체를 모아서 호출해도 결과는 같음)."""
    _apply_min_max(all_rows)
    return all_rows
