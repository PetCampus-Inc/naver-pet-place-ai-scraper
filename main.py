import asyncio
import time
from typing import Dict, List, Any

from lib.crawler.betch_process_crawler import BatchProcessCrawler
from lib.naver_map_api_sniffing import fetch_naver_place_list
from lib.upload_google_drive import UploadGoogleDrive
from utils.df_to_excel import dict_list_to_excel
from utils.merge_dict_list import merge_dict_lists_by_key
from lib.logger import get_logger


log = get_logger()

class Main:
    def __init__(self):
        self.location = input("검색할 지역을 입력하세요 (예: 서초구, 강남구 등): ")
        self.keywords = ["강아지 유치원", "반려견 유치원", "강아지 호텔", "반려견 호텔", "애견 유치원", "애견 호텔"]

        self.max_retries = 3    # 크롤링 실패 시, 재시도 횟수
        self.retry_delay = 1    # 재시도 전, 딜레이 (초 단위)

    async def run(self):
        log.info("크롤링 작업 시작")
        start_time = time.time()

        upload_google_drive = UploadGoogleDrive()
        upload_google_drive.google_drive_api_auth()
        
        # 네이버 지도 검색 결과 가져오기
        try:
            places_data = await self._fetch_place_data()
            if not places_data:
                log.info("검색 결과가 없습니다.")
                return
            
        except Exception as e:
            log.error(f"장소 데이터 검색 중 오류 발생: {e}")
            return

        place_ids = [item['id'] for item in places_data]
        log.info(f"총 {len(place_ids)}개 장소 검색 완료, 크롤링 시작")

        try:
            # 병렬 크롤링 수행
            batch_process_crawler = BatchProcessCrawler(self.max_retries, self.retry_delay)
            crawl_result = batch_process_crawler.parallel_crawl(place_ids)

            results = merge_dict_lists_by_key('id', places_data, crawl_result)

            # 결과를 엑셀로 저장
            dict_list_to_excel(results, self.location)
            
            # 실행 시간 로깅
            elapsed_time = time.time() - start_time
            log.info(f"크롤링 작업 완료. 총 {len(crawl_result)}개 항목, 소요 시간: {elapsed_time:.2f}초")
            
        except Exception as e:
            log.error(f"크롤링 중 오류 발생: {e}")


    async def _fetch_place_data(self) -> List[Dict[str, Any]]:
        """장소 데이터를 가져오는 함수"""
        return fetch_naver_place_list(self.location, self.keywords)
    

if __name__ == "__main__":
    main = Main()
    asyncio.run(main.run())