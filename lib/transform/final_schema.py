"""AI 배치 결과(한글, nested)를 info_new.json 스타일 스키마(영어 enum, flat 리스트)로
변환하는 최종 조립 함수.

입력으로 기대하는 place dict은 main.py의 6번 단계 직전(필드 정리 전) 상태 —
스크래핑 결과 + AI 결과가 이미 merge_dict_lists로 합쳐진 것.
"""

from lib.transform.enum_maps import (
    CATEGORY_MAP,
    DOG_BREED_MAP,
    VISITOR_AMENITY_MAP,
    DOG_SERVICE_MAP,
    DOG_SAFETY_FACILITY_MAP,
    LINK_CODE_MAP,
)
from lib.transform.business_hours import to_final_business_hours
from lib.transform.business_services import derive_business_services
from lib.transform.price_aggregation import to_avg_price_rows

REVIEW_COUNT_KEY_MAP = {
    "방문자리뷰": "visit_review_count",
    "블로그리뷰": "blog_review_count",
}


def _map_categories(categories: list) -> list:
    result = []
    for ko in categories or []:
        enum_value = CATEGORY_MAP.get(ko)
        if enum_value and enum_value not in result:
            result.append(enum_value)
    return result


def _true_keys_to_enum(section: dict, enum_map: dict) -> list:
    result = []
    for ko_key, value in (section or {}).items():
        enum_value = enum_map.get(ko_key)
        if enum_value and value is True and enum_value not in result:
            result.append(enum_value)
    return result


def _map_links(links: list) -> list:
    result = []
    for link in links or []:
        code = LINK_CODE_MAP.get(link.get("name"), "ETC")
        result.append({"code": code, "url": link.get("url")})
    return result


def _map_review_count(review_counts: dict) -> dict:
    result = {}
    for ko_key, value in (review_counts or {}).items():
        en_key = REVIEW_COUNT_KEY_MAP.get(ko_key)
        if en_key:
            result[en_key] = value
    return result


def to_final_schema(place: dict) -> dict:
    services = place.get("services") or {}

    visitor_amenities = _true_keys_to_enum(services.get("서비스(보호자)"), VISITOR_AMENITY_MAP)
    visitor_amenities += [
        v for v in _true_keys_to_enum(services.get("시설(방문객)"), VISITOR_AMENITY_MAP)
        if v not in visitor_amenities
    ]

    return {
        "id": place.get("id"),
        "name": place.get("name"),
        "categories": _map_categories(place.get("categories")),
        "tel": place.get("tel"),
        "thumbnail_s3_key": place.get("thumbnail_s3_key"),
        "menu_image_s3_keys": place.get("menu_image_s3_keys"),
        "address": place.get("address"),
        "road_address": place.get("road_address"),
        "lat": place.get("lat"),
        "lng": place.get("lng"),
        "links": _map_links(place.get("links")),
        "dog_breeds_accepted": _true_keys_to_enum(services.get("견종"), DOG_BREED_MAP),
        "dog_services": _true_keys_to_enum(services.get("서비스(강아지)"), DOG_SERVICE_MAP),
        "dog_safety_facilities": _true_keys_to_enum(services.get("시설(강아지)"), DOG_SAFETY_FACILITY_MAP),
        "visitor_amenities": visitor_amenities,
        "business_hours": to_final_business_hours(place.get("business_hours")),
        "business_services": derive_business_services(place.get("business_hours")),
        "review_count": _map_review_count(place.get("review_counts")),
    }


def to_avg_price_for_place(place: dict) -> list:
    return to_avg_price_rows(place.get("id"), place.get("name"), place.get("menus"))
