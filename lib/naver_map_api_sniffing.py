import requests

from lib.logger import get_logger

log = get_logger()

def get_naver_place_list(location, keywords):
    """네이버 지도 검색 API 스니핑 메인 함수"""
    # 1. 데이터 수집
    place_list = _fetch_naver_places(location, keywords)
    
    # 2. 데이터 필터링
    filtered_places = _filter_places(place_list, location)
    
    # 3. 필요한 데이터만 추출 후 반환
    return [_parse_data(place) for place in filtered_places]

def _filter_places(place_list, location):
    """장소 데이터 필터링 (중복 제거, 지역 일치)"""
    filtered_data = []
    seen_ids = set()
    
    for item in place_list:
        # ID가 중복이거나, 지역 일치하지 않는 경우는 제외
        if item['id'] not in seen_ids and location in item['address']:
            filtered_data.append(item)
            seen_ids.add(item['id'])
    
    return filtered_data

def _parse_data(data: dict):
    return {
        "id": data['id'],
        "name": data['name'],
        "tel": data['tel'],
        "address": data['address'],
        "road_address": data['roadAddress'],
        "lat": data['latitude'],
        "lng": data['longitude'],
        "thumbnail_url": data['thumbUrl'],
    }

def _fetch_naver_places(location, keywords):
    """네이버 지도 검색 API의 결과를 반환하는 함수"""

    endpoint_url = f"https://svc-api.map.naver.com/v1/fusion-search/all"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Referer': 'https://m.map.naver.com/'
    }
    params = {
        'siteSort': 'relativity',
        'petrolType': 'all'
    }
    
    raw_results = []

    # 키워드에 대한 모든 검색 결과 가져오기
    for keyword in keywords:
        params['query'] = f"{location}+{keyword}"

        try:
            response = requests.get(endpoint_url, headers=headers, params=params)
            response.raise_for_status()

            data_list = response.json()["items"]
            raw_results.extend(data_list)
        except (requests.RequestException, KeyError, ValueError) as e:
            log.error(f"네이버 지도 API 스니핑 실패 ({location} {keyword}): {e}")

    return raw_results