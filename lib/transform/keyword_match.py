"""스크래핑 원본의 자유 텍스트(business_hours[].name 등)에서 카테고리 키워드를
찾아내는 공용 헬퍼. business_hours 이름 변환과 business_services 파생 로직이
둘 다 이 함수를 공유해서 동일한 기준으로 매칭되도록 함.
"""

from lib.transform.enum_maps import CATEGORY_MAP

DEFAULT_NAME_MARKERS = {"default", "기본"}


def is_default_business_hours_name(raw_name: str) -> bool:
    return (raw_name or "").strip().lower() in DEFAULT_NAME_MARKERS


def match_categories_in_text(text: str) -> list:
    """자유 텍스트 안에 등장하는 카테고리 키워드를 전부 찾아 enum 리스트로 반환.
    일치하는 게 없으면 빈 리스트 (추측하지 않음).
    """
    if not text:
        return []

    matched = []
    for keyword, enum_value in CATEGORY_MAP.items():
        if keyword in text and enum_value not in matched:
            matched.append(enum_value)
    return matched
