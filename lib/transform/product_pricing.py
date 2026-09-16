"""price_and_product 행들을 업체×product_type별로 요약 → product_pricing.json 스타일.

**AI 미사용 — 순수 파이썬 집계.**

output/product_pricing.json 435건을 price_and_product.json과 직접 대조해서
검증한 규칙 (전부 실제 숫자로 손계산까지 확인함):
    - product_type은 DAYCARE/NIGHT_CARE/TRAINING/MEMBERSHIP 4종만 포함
      (GROOMING/PICK_DROP 등은 이 파일 범위 밖 — 제외)
    - min/max: 그룹(업체×product_type) 내에서 min_price/max_price 플래그가
      true인 실제 상품 객체 (COUNT_TICKET/MONTHLY_TICKET 섞어서 비교)
    - count_ticket_avg: 그룹 내 product_type=="COUNT_TICKET" 상품들의 price 평균
    - monthly_hourly_avg(그룹별 + 업체 전체 2곳에 존재): product_type=="MONTHLY_TICKET"
      상품들의 hourly_price 평균
    - count_hourly_avg(업체 전체만 존재): product_type=="COUNT_TICKET" 상품들의
      hourly_price 평균

한계: 우리 데이터엔 '멤버십' 가격 정보 자체가 없어서(가격 정책 섹션은 있음/없음
불리언일 뿐 가격이 없음) MEMBERSHIP 그룹은 실질적으로 만들어지지 않음.
"""

from collections import defaultdict

from lib.transform.duration_parser import parse_weight_range

ALLOWED_PRODUCT_TYPES = {"DAYCARE", "NIGHT_CARE", "TRAINING", "MEMBERSHIP"}


def _avg(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return round(sum(values) / len(values)) if values else 0


def _to_min_max_object(row):
    return {
        "name": row["product_name"],
        "price": row["price"],
        "unit": row["unit"],
        "unit_type": row["unit_type"],
        "weight_range": parse_weight_range(row.get("weight_range")),
    }


def build_product_pricing(place_id, rows: list) -> dict:
    place_rows = [r for r in rows if r["service_type"] in ALLOWED_PRODUCT_TYPES]

    grouped = defaultdict(list)
    for row in place_rows:
        grouped[row["service_type"]].append(row)

    products = []
    for product_type, group_rows in grouped.items():
        min_row = next((r for r in group_rows if r.get("min_price")), None)
        max_row = next((r for r in group_rows if r.get("max_price")), None)
        if min_row is None or max_row is None:
            continue

        count_prices = [r["price"] for r in group_rows if r["product_type"] == "COUNT_TICKET"]
        monthly_hourly = [
            r["hourly_price"] for r in group_rows
            if r["product_type"] == "MONTHLY_TICKET" and isinstance(r.get("hourly_price"), (int, float))
        ]

        products.append({
            "product_type": product_type,
            "min": _to_min_max_object(min_row),
            "max": _to_min_max_object(max_row),
            "count_ticket_avg": _avg(count_prices),
            "monthly_hourly_avg": _avg(monthly_hourly),
        })

    all_count_hourly = [
        r["hourly_price"] for r in place_rows
        if r["product_type"] == "COUNT_TICKET" and isinstance(r.get("hourly_price"), (int, float))
    ]
    all_monthly_hourly = [
        r["hourly_price"] for r in place_rows
        if r["product_type"] == "MONTHLY_TICKET" and isinstance(r.get("hourly_price"), (int, float))
    ]

    return {
        "id": place_id,
        "count_hourly_avg": _avg(all_count_hourly),
        "monthly_hourly_avg": _avg(all_monthly_hourly),
        "products": products,
    }
