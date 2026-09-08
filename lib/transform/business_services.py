"""business_services 파생 로직.

AI가 만드는 필드가 아니라, 스크래퍼가 네이버에서 그대로 가져온
business_hours[].name(업체가 직접 등록한 자유 텍스트 — 예: "미용실", "카페 이용")
에서 카테고리 키워드를 뽑아 만든다. default/기본 항목은 제외.

근거: lib/scrapper/naver_place_parser.py의 _parse_business_hours 주석 —
"여러 매장이 있을 경우 newBusinessHours도 여러 개 있음
(예: 1층 유치원, 2층 미용실 운영 시간이 다를 경우)"
"""

from lib.transform.keyword_match import is_default_business_hours_name, match_categories_in_text


def derive_business_services(business_hours: list) -> list:
    result = []
    for entry in business_hours or []:
        raw_name = entry.get("name", "")
        if is_default_business_hours_name(raw_name):
            continue
        for enum_value in match_categories_in_text(raw_name):
            if enum_value not in result:
                result.append(enum_value)
    return result
