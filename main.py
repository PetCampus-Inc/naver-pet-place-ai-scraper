import asyncio
import json
import time
from typing import List

from lib.s3_uploader import S3ImageUploader
from lib.naver_map_api_sniffing import get_naver_place_list
from lib.scrapper.scrape_page_content import scrape_page_content
from lib.logger import get_logger
from lib.scrapper.scrape_naver_places import scrape_naver_places
from utils.dict_utils import merge_dict_lists
from lib.request_batch_api import request_batch_api
from utils.dict_utils import pick_fields

log = get_logger()

class Main:
    def __init__(self):
        self.location = self._input_location()
        self.keywords = ["강아지 유치원", "반려견 유치원", "강아지 호텔", "반려견 호텔", "애견 유치원", "애견 호텔"]

    async def run(self):
        start_time = time.time()

        # 1. 네이버 지도 검색 결과 가져오기 (API 스니핑)
        place_list = get_naver_place_list(self.location, self.keywords)
        log.info(f"총 {len(place_list)}개 장소 검색 됨")

        # 2. 상세 정보 스크랩핑 데이터 추가
        place_ids = [item['id'] for item in place_list]
        place_list = merge_dict_lists('id', place_list, scrape_naver_places(place_ids))

        # 3. 홈페이지 콘텐츠 추가
        place_link_map = [{ data["id"]: [i['url'] for i in data['links']] } for data in place_list]
        place_list = merge_dict_lists('id', place_list, scrape_page_content(place_link_map))

        # 4. 이미지 S3 버킷 업로드
        upload_results = await self._upload_images(place_list)
        place_list = merge_dict_lists('id', place_list, upload_results)

        # 5. 배치 API 요청
        batch_api_response = request_batch_api(place_list)
        place_list = merge_dict_lists('id', place_list, batch_api_response)

        # 7. 필요한 데이터만 추출
        place_list = self._filter_place_list(place_list)

        with open(f'{self.location}.json', 'w', encoding='utf-8') as f:
            json.dump(place_list, f, ensure_ascii=False, indent=4)

        elapsed_time = time.time() - start_time
        log.info(f"작업 완료 - 총 {len(place_list)}개 항목, 소요 시간: {elapsed_time:.2f}초")

    def _filter_place_list(self, place_list: List[dict]):
        keys = ['id', 'name', 'tel', 'address', 'thumbnail_s3_key', 'menu_image_s3_keys', 'road_address', 'lat', 'lng', 'business_hours', 'menus', 'review_counts', 'links', 'categories', 'services']
        return [pick_fields(place, keys) for place in place_list]
    
    async def _upload_images(self, place_list: List[dict]):
        uploader = S3ImageUploader()

        results = []
        upload_image_map = []
        for place in place_list:
            base_key = f"{self.location}/{place['id']}"

            # 썸네일
            thumbnail_extension = place['thumbnail_url'].split('.')[-1]
            thumbnail_s3_key = f"{base_key}/thumbnail.{thumbnail_extension}"
            upload_image_map.append({
                "url": place['thumbnail_url'],
                "key": thumbnail_s3_key
            })

            # 가격표 이미지
            menu_image_s3_keys = []
            for i, menu_image_url in enumerate(place['menu_image_urls']):
                menu_image_extension = menu_image_url.split('.')[-1]
                menu_image_s3_key = f"{base_key}/menu_images/{i}.{menu_image_extension}"
                menu_image_s3_keys.append(menu_image_s3_key)
                upload_image_map.append({
                    "url": menu_image_url,
                    "key": menu_image_s3_key
                })

            results.append({
                "id": place['id'],
                "thumbnail_s3_key": thumbnail_s3_key,
                "menu_image_s3_keys": menu_image_s3_keys
            })

        await uploader.upload_multiple_images(upload_image_map)

        return results

    def _input_location(self):
        while True:
            location = input("검색할 지역을 입력하세요 (예: 서초구, 강남구 등): ").strip()
            if location:
                break
            print("지역을 입력해주세요. 빈 값은 허용되지 않습니다.")
        return location
    

if __name__ == "__main__":
    main = Main()
    asyncio.run(main.run())