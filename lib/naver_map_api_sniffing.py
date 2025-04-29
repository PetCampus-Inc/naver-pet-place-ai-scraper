import requests
from logger import get_logger

log = get_logger()

def fetch_naver_place_list(location, keywords):
    """네이버 지도 검색 API 스니핑 함수"""

    endpoint_url = f"https://m.map.naver.com/search2/searchMore.naver"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Referer': 'https://m.map.naver.com/'
    }
    params = {
        'sm': 'clk',
        'style': 'v5',
        'page': 1,
        'displayCount': 1000,
        'type': 'SITE_1'
    }
    
    raw_results = []
    
    # 키워드에 대한 모든 검색 결과 가져오기
    for keyword in keywords:
        params['query'] = f"{location}+{keyword}"
        
        try:
            response = requests.get(endpoint_url, headers=headers, params=params)
            response.raise_for_status()
            
            data_list = response.json()["result"]["site"]["list"]
            raw_results.extend(data_list)
        except (requests.RequestException, KeyError, ValueError) as e:
            log.error(f"네이버 지도 API 스니핑 실패 ({location} {keyword}): {e}")

    filtered_data = []
    seen_ids = set()
    
    for item in raw_results:
        # self.location 지역 일치 체크, 중복 주소 필터링
        if item['id'] not in seen_ids and location in item['address']:
            # 필요한 데이터만 파싱
            parsed_data = {
                'id': item['id'],
                '업체명': item['name'],
                '등록업종': ', '.join(item['category']),
                '전화번호': item['tel'],
                '주소(도로명)': item['roadAddress'],
                'x': item['x'],
                'y': item['y']
            }

            filtered_data.append(parsed_data)
            seen_ids.add(item['id'])
    
    return filtered_data