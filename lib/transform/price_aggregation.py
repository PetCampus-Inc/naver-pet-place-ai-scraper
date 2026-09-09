"""menus(개별 이용권 목록) → avg_price_per_time.json 스타일 평균가 집계.

output/avg_price_per_time.json 실측 스키마:
    {"kindergarten_id": int, "name": str, "product_type": str,
     "service_type": str, "average_price": number}

주의(의도적으로 원본과 다르게 만든 부분):
    실측 avg_price_per_time.json은 product_type × service_type 조합을 전부
    격자로 만들어서 데이터 없는 조합도 average_price: 0으로 채워 넣었는데,
    "0원"은 "실제로 무료"와 구분이 안 돼서 오해의 소지가 있음.
    → 여기서는 실제 menus 데이터가 있는 조합만 행으로 만든다.

    또한 avg_price_per_time.json의 service_type(DAYCARE/NIGHT_CARE/TRAINING/
    MEMBERSHIP) 중 NIGHT_CARE, MEMBERSHIP에 대응하는 한글 menus.package 근거가
    없어서 이 두 service_type은 절대 나오지 않는다 — 추측해서 채우지 않음.
"""

from collections import defaultdict

PRODUCT_TYPE_MAP = {
    "횟수권": "COUNT_TICKET",
    "정기권": "MONTHLY_TICKET",
    "단일권": "COUNT_TICKET",
}

SERVICE_TYPE_KEYWORDS = [
    ("데이케어", "DAYCARE"),
    ("유치원", "DAYCARE"),
    ("훈련", "TRAINING"),
]


def _match_service_type(package: str):
    if not package:
        return None
    for keyword, service_type in SERVICE_TYPE_KEYWORDS:
        if keyword in package:
            return service_type
    return None


def to_avg_price_rows(place_id, place_name: str, menus: list) -> list:
    buckets = defaultdict(list)

    for menu in menus or []:
        product_type = PRODUCT_TYPE_MAP.get(menu.get("type"))
        service_type = _match_service_type(menu.get("package"))
        price = menu.get("price")

        if product_type is None or service_type is None or not isinstance(price, (int, float)):
            continue

        buckets[(product_type, service_type)].append(price)

    rows = []
    for (product_type, service_type), prices in buckets.items():
        rows.append({
            "kindergarten_id": place_id,
            "name": place_name,
            "product_type": product_type,
            "service_type": service_type,
            "average_price": sum(prices) / len(prices),
        })
    return rows
