"""한글 서비스/카테고리 체크리스트 → info_new.json 스타일 영어 enum 매핑표.

이 파일의 매핑은 실제 output/info_new.json 435건을 전수 조사해서 뽑은 enum
어휘를 기준으로 작성됨. 데이터 자체에 존재했던 오타(AQUAL_FITNESS)나 모호한
중복(GENERAL vs DOG_FREE)은 그대로 베끼지 않고, service.md 체크리스트 항목
이름에 가장 부합하는 쪽 하나만 선택함.
"""

CATEGORY_MAP = {
    "유치원": "KINDERGARTEN",
    "호텔": "HOTEL",
    "훈련소": "TRAINING",
    "병원": "VETERINARY",
    "미용": "GROOMING",
    "카페": "CAFE",
    "놀이터": "PLAYGROUND",
    "피트니스": "FITNESS",
    "용품샵": "PET_SHOP",
}

DOG_BREED_MAP = {
    "견종 무관(일반)": "GENERAL",
    "소형견 전용": "SMALL_DOG_ONLY",
    "중대형견 전용": "MEDIUM_LARGE_DOG_ONLY",
    "고양이": "CAT",
}

# 서비스(보호자) + 시설(방문객) 두 섹션을 info_new.json의 visitor_amenities 하나로 합침
VISITOR_AMENITY_MAP = {
    "발렛파킹": "VALET",
    "유료 픽드랍": "PAID_PICKUP",
    "무료 픽드랍": "FREE_PICKUP",
    "1:1 알림장": "DIARY",
    "주차장": "PARKING",
    "강아지 카페": "DOG_CAFE",
    "강아지 용품": "DOG_SHOP",
}

DOG_SERVICE_MAP = {
    "24시간 상주": "STAY_24H",
    "성향분석": "TEMPERAMENT",
    "분반": "SPLIT_CLASS",
    "호텔링": "HOTEL",
    "데이케어": "DAYCARE",
    "목욕": "BATH_SERVICE",
    "수중 피트니스": "AQUA_FITNESS",
    "마사지": "MASSAGE",
    "미용": "GROOMING",
    "훈련": "TRAINING",
    "행동교정": "BEHAVIOR_CORRECTION",
    "산책": "WALK",
    "재활": "REHABILITATION",
    "병원 연계": "VET_LINKED",
}

DOG_SAFETY_FACILITY_MAP = {
    "미끄럼방지": "NON_SLIP",
    "CCTV": "CCTV",
    "실내 놀이터": "INDOOR_PLAYGROUND",
    "실외 놀이터": "PLAYGROUND",
    "루프탑": "ROOFTOP",
    "테라스": "TERRACE",
    "운동장": "EXERCISE_YARD",
    "마당": "YARD",
    "수영장": "SWIMMING_POOL",
    "개별 룸": "PRIVATE_ROOM",
}

LINK_CODE_MAP = {
    "인스타그램": "INSTAGRAM",
    "블로그": "BLOG",
    "밴드": "BAND",
    "홈페이지": "WEBSITE",
    "카카오톡": "KAKAO",
}

WEEKDAY_KO_TO_EN = {
    "월": "MONDAY",
    "화": "TUESDAY",
    "수": "WEDNESDAY",
    "목": "THURSDAY",
    "금": "FRIDAY",
    "토": "SATURDAY",
    "일": "SUNDAY",
}

# price_and_product.json용 service_type 키워드 (product_name + package 둘 다 검사).
# 우선순위대로 검사하고 아무것도 안 맞으면 ETC(실제 참고 데이터에도 존재하는 catch-all)
SERVICE_TYPE_KEYWORDS_DETAILED = [
    ("호텔링", "NIGHT_CARE"),
    ("호텔", "NIGHT_CARE"),
    ("데이케어", "DAYCARE"),
    ("유치원", "DAYCARE"),
    ("돌봄", "DAYCARE"),
    ("놀이터", "DAYCARE"),
    ("훈련", "TRAINING"),
    ("미용", "GROOMING"),
    ("목욕", "GROOMING"),
    ("픽드랍", "PICK_DROP"),
    ("드랍", "PICK_DROP"),
    ("픽업", "PICK_DROP"),
    ("체험", "EXPERIENCE_TICKET"),
    ("성향테스트", "EXPERIENCE_TICKET"),
    ("방문", "VISIT_CARE"),
]
SERVICE_TYPE_FALLBACK = "ETC"
