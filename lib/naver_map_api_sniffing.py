import requests

from lib.logger import get_logger
from lib.s3_uploader import S3ImageUploader

log = get_logger()

async def get_naver_place_list(location, keywords):
    """네이버 지도 검색 API 스니핑 메인 함수"""
    # 1. 데이터 수집
    place_list = _fetch_naver_places(location, keywords)
    
    # 2. 데이터 필터링
    filtered_places = _filter_places(place_list, location)
    
    # 3. 이미지 업로드 및 데이터 변환
    processed_data = await _process_places_with_images(filtered_places, location)
    
    return processed_data

def _filter_places(place_list, location):
    """장소 데이터 필터링 (중복 제거, 지역 일치)"""
    filtered_data = []
    seen_ids = set()
    
    for item in place_list:
        if item['id'] not in seen_ids and location in item['address']:
            filtered_data.append(item)
            seen_ids.add(item['id'])
    
    return filtered_data

async def _process_places_with_images(places, location):
    """이미지 업로드 및 데이터 파싱"""
    s3_uploader = S3ImageUploader()
    processed_data = []
    
    for item in places:
        # S3 이미지 업로드
        s3_key = await _upload_thumbnail_to_s3(s3_uploader, item, location)
        
        # 데이터 파싱
        parsed_data = _parse_place_data(item, s3_key)
        processed_data.append(parsed_data)
    
    return processed_data

async def _upload_thumbnail_to_s3(s3_uploader, item, location):
    """썸네일 이미지 S3 업로드"""
    file_extension = item['thumbUrl'].split(".")[-1]
    key = f"{location}/{item['id']}/thumbnail.{file_extension}"
    
    s3_uploader.upload_image(item['thumbUrl'], key)
    log.info(f"S3 업로드 완료 - {key}")
    
    return key

def _parse_place_data(item, s3_key):
    """장소 데이터 파싱"""
    return {
        'id': item['id'],
        '업체명': item['name'],
        '등록업종': item['category'],
        '전화번호': item['tel'],
        '주소(도로명)': item['roadAddress'],
        'lat': item['latitude'],
        'lng': item['longitude'],
        '썸네일 이미지 S3 키': s3_key
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