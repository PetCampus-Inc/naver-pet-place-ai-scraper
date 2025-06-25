from lib.logger import get_logger
from utils.find_by_prefix import find_by_prefix

log = get_logger(__name__)

class NaverPlaceParser:
    def __init__(self):
        self.apollo_data = None
        self.detail_data = None

    def parse(self, apollo_data: dict):
        self.apollo_data = apollo_data
        self.detail_data = self._get_detail()

        return {
            # 플레이스 ID
            "id": int(self._get_detail_base().get('id', '')),

            # 가격표 이미지
            "menu_image_urls": self._parse_menu_images(),
            # 영업 시간
            "business_hours": self._parse_business_hours(), 
            # 메뉴 (가격표)
            "menus": self._parse_menus(),
            # 리뷰 수
            "review_counts": self._parse_review_counts(),
            # 링크
            "links": self._parse_links(),

            # 소개
            "description": self._parse_description(),
            # 대표 키워드
            "keywords": self._parse_keywords(),
            # 편의시설 및 서비스
            "conveniences": self._get_detail_base().get('conveniences', []),
            # 주차 및 발렛
            **self._parse_parking_and_valet(),
        }

    # --- Get Data ---

    def _get_detail(self):
        # ROOT_QUERY -> placeDetail({...})
        return find_by_prefix(self.apollo_data.get('ROOT_QUERY', {}), 'placeDetail')

    def _get_detail_base(self):
        # apollo_data -> placeDetailBase({...})
        detail_base_key = self.detail_data.get('base', {}).get('__ref', '')
        return self.apollo_data.get(detail_base_key, {})

    # --- Parsing ---

    def _parse_menu_images(self):
        """[홈] 가격표 이미지"""
        return [img.get('imageUrl', '') for img in (self.detail_data.get('menuImages') or [])]

    # 영업 시간을 요일별로 가져오는 함수 (사용 X)
    def _parse_business_hours_2(self):
        """[홈] 영업 시간"""
        business_hours = []
        # 여러 매장이 있을 경우 newBusinessHours도 여러 개 있음 (예: 1층 유치원, 2층 미용실 운영 시간이 다를 경우)
        for business_hour in self.detail_data.get('newBusinessHours', []):
            hours = []

            # 영업 시간 파싱
            for hour in business_hour.get('businessHours', []):
                # 영업 시간이 있는 경우 시작 시간과 종료 시간을 반환 (예: 10:00 - 18:00)
                if hour.get('businessHours'):
                    bh = hour.get('businessHours', {})
                    value = f"{bh.get('start', '')} - {bh.get('end', '')}"
                # 영업 시간이 없는 경우 설명을 반환 (예: 휴무)
                else: value = hour.get('description', '')

                hours.append({
                    'day': hour.get('day', ''),
                    'hours': value,
                })
            business_hours.append({
                "name": business_hour.get('name', 'default') or 'default',
                "business_hours": hours,
            })
        return business_hours
    
    def _parse_business_hours(self):
        try:
            business_hours = []
            for business_hour in self.detail_data.get('newBusinessHours', []):
                weekday_times = []  # 월~금
                weekend_times = []  # 토~일
                offdays = []        # 휴무일

                for hour in business_hour.get('businessHours', []):
                    day = hour.get('day', '')

                    if hour.get('businessHours'):
                        bh = hour.get('businessHours', {})
                        start = bh.get('start', '')
                        end = bh.get('end', '')

                        if start and end:
                            time_str = f"{start} - {end}"
                            if day == '매일':
                                weekday_times.append(time_str)
                                weekend_times.append(time_str)
                            elif day in ['월', '화', '수', '목', '금']:
                                weekday_times.append(time_str)
                            elif day in ['토', '일']:
                                weekend_times.append(time_str)
                    else:
                        # start나 end가 빈 값이면 description 확인
                        description = hour.get('description', '')
                        if '정기휴무' in description:
                            offdays.append(day)

                weekdays = max(set(weekday_times), key=weekday_times.count) if weekday_times else None
                weekends = max(set(weekend_times), key=weekend_times.count) if weekend_times else None

                business_hours.append({
                    "name": business_hour.get('name', 'default') or 'default',
                    "weekdays": weekdays,
                    "weekends": weekends,
                    "offdays": offdays,
                })
            
            return business_hours

        except Exception as e:
            log.error(f"영업 시간 파싱 오류: {e}")
            raise e

    def _parse_menus(self):
        """[홈] 메뉴 (가격표)"""
        try:
            # 가격표 데이터의 key 값을 가져옴 (예: [Menu:1547862682_0, Menu:1547862682_1, ..])
            menus = self.detail_data.get('menus') or []

            # key 값을 통해 가격표 데이터를 가져옴
            result = []
            for menu in menus:
                if (menu_data := self.apollo_data.get(menu['__ref'], {})):
                    price_value = menu_data.get('price', 0)
                    # 빈 문자열이나 None인 경우 0으로 처리
                    try:
                        price = int(price_value) if price_value else 0
                    except (ValueError, TypeError):
                        price = 0
                    
                    result.append({
                        "name": menu_data.get('name', ''), 
                        "price": price
                    })
            
            return result
        except Exception as e:
            log.error(f"메뉴 파싱 오류: {e}")
            raise e

    def _parse_review_counts(self):
        """[홈] 리뷰 수"""
        try:
            return {
                "방문자리뷰": self._get_detail_base().get('visitorReviewsTotal', 0),
                "블로그리뷰": self.detail_data.get('fsasReviews', {}).get('total', 0),
            }
        except Exception as e:
            log.error(f"리뷰 수 파싱 오류: {e}")
            raise e

    def _parse_links(self):
        """[홈] 링크"""
        try:
            if not (place_detail := find_by_prefix(self.apollo_data.get('ROOT_QUERY', {}), 'placeDetail')): return []
            if not (homepages := find_by_prefix(place_detail, 'homepages')): return []

            links = homepages.get('etc', []) + ([homepages['repr']] if homepages.get('repr') else [])
            return [
                {"name": p.get('type', ''), "url": p.get('url', '')}
                for p in links
            ]
        except Exception as e:
            log.error(f"링크 파싱 오류: {e}")
            raise e

    def _parse_description(self):
        """[정보] 소개"""
        return find_by_prefix(self.detail_data, 'description')
    
    def _parse_keywords(self):
        """[정보] 대표 키워드"""
        return find_by_prefix(self.detail_data, 'informationTab').get('keywordList', [])

    def _parse_parking_and_valet(self):
        """[정보] 주차 및 발렛"""
        parking_info = find_by_prefix(self.detail_data, 'informationTab').get('parkingInfo', None)

        # 주차 정보가 없으면 주차/발렛 불가능
        if not parking_info: 
            return { "parking": False, "valet_parking": False }

        return {
            "parking": parking_info.get('basicParking') is not None,
            "valet_parking": parking_info.get('valetParking') is not None,
        }