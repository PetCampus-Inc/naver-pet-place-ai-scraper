import argparse
import asyncio
import json
import os
import time
from typing import List

from dotenv import load_dotenv

load_dotenv()

from lib.s3_uploader import S3ImageUploader
from lib.naver_map_api_sniffing import get_naver_place_list
from lib.scrapper.scrape_page_content import scrape_page_content
from lib.logger import get_logger
from lib.scrapper.scrape_naver_places import scrape_naver_places
from utils.dict_utils import merge_dict_lists
from lib.request_batch_api import request_batch_api
from utils.dict_utils import pick_fields
from lib.transform import (
    to_final_schema,
    to_price_and_product_rows,
    apply_min_max_across_places,
)

log = get_logger()

class Main:
    def __init__(self, location=None, collection_only=False, limit=None, output_dir="."):
        self.location = location or self._input_location()
        self.collection_only = collection_only
        self.limit = limit
        self.output_dir = output_dir
        self.keywords = ["강아지 유치원", "반려견 유치원", "강아지 호텔", "반려견 호텔", "애견 유치원", "애견 호텔"]

    async def run(self):
        start_time = time.time()

        # 1. 네이버 지도 검색 결과 가져오기 (API 스니핑)
        place_list = get_naver_place_list(self.location, self.keywords, limit=self.limit)
        log.info(f"총 {len(place_list)}개 장소 검색 됨")

        # 2. 상세 정보 스크랩핑 데이터 추가
        place_ids = [item['id'] for item in place_list]
        place_list = merge_dict_lists('id', place_list, scrape_naver_places(place_ids))

        # 3. 홈페이지 콘텐츠 추가
        place_link_map = [{ data["id"]: [i['url'] for i in data['links']] } for data in place_list]
        place_list = merge_dict_lists('id', place_list, scrape_page_content(place_link_map))

        if self.collection_only:
            # 로컬 수집 테스트에서는 외부 저장소와 유료 AI API를 호출하지 않는다.
            place_list = self._filter_collection_place_list(place_list)
        else:
            # 4. 이미지 S3 버킷 업로드
            upload_results = await self._upload_images(place_list)
            place_list = merge_dict_lists('id', place_list, upload_results)

            # 5. 배치 API 요청
            batch_api_response = request_batch_api(place_list)
            place_list = merge_dict_lists('id', place_list, batch_api_response)

            # 6. 필요한 데이터만 추출
            place_list = self._filter_place_list(place_list)

        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, f'{self.location}.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(place_list, f, ensure_ascii=False, indent=4)

        if not self.collection_only:
            # 7. 최종 스키마 변환 (기존 출력은 그대로 두고 별도 파일로 추가 생성)
            self._write_final_schema_outputs(place_list)

        elapsed_time = time.time() - start_time
        log.info(f"작업 완료 - 총 {len(place_list)}개 항목, 소요 시간: {elapsed_time:.2f}초")
        log.info(f"결과 파일: {output_path}")

    def _write_final_schema_outputs(self, place_list: List[dict]):
        final_list = [to_final_schema(place) for place in place_list]

        price_and_product_rows = []
        for place in place_list:
            price_and_product_rows.extend(
                to_price_and_product_rows(place.get("id"), place.get("name"), place.get("menus"))
            )
        apply_min_max_across_places(price_and_product_rows)

        final_path = os.path.join(self.output_dir, f'{self.location}_info_new.json')
        with open(final_path, 'w', encoding='utf-8') as f:
            json.dump(final_list, f, ensure_ascii=False, indent=4)

        price_and_product_path = os.path.join(self.output_dir, f'{self.location}_price_and_product.json')
        with open(price_and_product_path, 'w', encoding='utf-8') as f:
            json.dump(price_and_product_rows, f, ensure_ascii=False, indent=4)

        log.info(f"변환 결과 파일: {final_path}, {price_and_product_path}")

    def _filter_place_list(self, place_list: List[dict]):
        keys = ['id', 'name', 'tel', 'address', 'thumbnail_s3_key', 'menu_image_s3_keys', 'road_address', 'lat', 'lng', 'business_hours', 'menus', 'review_counts', 'links', 'categories', 'services']
        return [pick_fields(place, keys) for place in place_list]

    def _filter_collection_place_list(self, place_list: List[dict]):
        keys = [
            'id', 'name', 'tel', 'address', 'road_address', 'lat', 'lng',
            'business_hours', 'menus', 'review_counts', 'links', 'description',
            'keywords', 'conveniences', 'parking', 'valet_parking',
            'thumbnail_url', 'menu_image_urls', 'page_content'
        ]
        return [pick_fields(place, keys) for place in place_list]
    
    async def _upload_images(self, place_list: List[dict]):
        uploader = S3ImageUploader()

        results = []
        upload_image_map = []
        for place in place_list:
            base_key = f"{self.location}/{place['id']}"

            # 썸네일 (없으면 None으로 두고 업로드 건너뜀)
            thumbnail_url = place.get('thumbnail_url') or None
            if thumbnail_url:
                thumbnail_extension = thumbnail_url.split('.')[-1].split('?')[0]
                thumbnail_s3_key = f"{base_key}/thumbnail.{thumbnail_extension}"
                upload_image_map.append({
                    "url": thumbnail_url,
                    "key": thumbnail_s3_key
                })
            else:
                thumbnail_s3_key = None

            # 가격표 이미지
            menu_image_s3_keys = []
            for i, menu_image_url in enumerate(place.get('menu_image_urls') or []):
                if not menu_image_url:
                    continue
                menu_image_extension = menu_image_url.split('.')[-1].split('?')[0]
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
    parser = argparse.ArgumentParser(description="네이버 반려동물 업체 수집기")
    parser.add_argument("--location", help="수집할 지역명 (예: 강남구)")
    parser.add_argument("--limit", type=int, help="최대 수집 건수")
    parser.add_argument(
        "--collection-only",
        action="store_true",
        help="S3 업로드와 Anthropic API 호출 없이 JSON만 생성",
    )
    parser.add_argument("--output-dir", default=".", help="JSON 저장 폴더")
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit는 1 이상이어야 합니다.")

    main = Main(
        location=args.location,
        collection_only=args.collection_only,
        limit=args.limit,
        output_dir=args.output_dir,
    )
    asyncio.run(main.run())
