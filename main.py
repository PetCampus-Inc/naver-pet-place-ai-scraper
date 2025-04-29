import pandas as pd
import asyncio
import concurrent.futures
import os
import multiprocessing
import logging
from lib.naver_map_api_sniffing import fetch_naver_place_list
from lib.crawler.naver_place_crawler import NaverPlaceCrawler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s - %(name)s - %(levelname)s - %(message)s]'
)
logger = logging.getLogger(__name__)

# googleapiclient 경고 로그 비활성화
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

class Main:
    def __init__(self):
        self.location = input("검색할 지역을 입력하세요 (예: 서초구, 강남구, 대치동): ")
        self.keywords = ["강아지 유치원", "반려견 유치원", "강아지 호텔", "반려견 호텔", "애견 유치원", "애견 호텔"]
        
    def get_optimal_workers(self) -> int:
        """최적의 스레드 수를 계산하는 함수"""

        # CPU 코어 수 확인
        cpu_count = os.cpu_count() or multiprocessing.cpu_count()
        
        # 코어 수의 1.5배 (최소 2개, 최대 5개)
        return min(max(2, int(cpu_count * 1.5)), 5)

    def process_batch(self, place_ids: list[str]) -> list[tuple[str, dict]]:
        """크롤링 배치 처리 함수"""

        results = []
        
        with NaverPlaceCrawler() as crawler:
            for place_id in place_ids:
                try:
                    result = crawler.get_place_details(place_id)
                    if result:
                        results.append((place_id, result))
                except Exception as e:
                    logger.error(f"ID {place_id} 크롤링 처리 중 오류: {e}")
        
        return results
    
    def parallel_crawl(self, batches: list[list[str]], base_data: dict, max_workers: int) -> list[dict]:
        """배치 단위로 병렬 크롤링을 수행하고 결과를 병합하는 함수"""
        
        results = []
        total = sum(len(batch) for batch in batches)
        completed = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_batch = {
                executor.submit(self.process_batch, batch): i
                for i, batch in enumerate(batches)
            }
            
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_index = future_to_batch[future]
                try:
                    batch_results = future.result()
                    
                    # 배치 결과 처리
                    for place_id, crawl_result in batch_results:
                        if place_id in base_data:
                            merged_data = {**base_data[place_id], **crawl_result}
                            results.append(merged_data)
                            
                            # 진행 상태 로깅
                            completed += 1
                            logger.info(f"[{completed}/{total}] {base_data[place_id]['업체명']} 크롤링 완료")
                except Exception as e:
                    logger.error(f"배치 {batch_index} 결과 처리 중 오류 발생: {e}")
        

    async def run(self):
        # 네이버 지도 검색 결과 가져오기
        places_data = fetch_naver_place_list(self.location, self.keywords)
        if not places_data:
            logger.error("검색 결과가 없습니다.")
            return
        
        # 기본 데이터 추출
        base_data = {item['id']: item for item in places_data}
        place_ids = [item['id'] for item in places_data]
        
        logger.info(f"총 {len(place_ids)}개 장소 스니핑 완료, 크롤링 시작")
        
        # 최적의 스레드 수 계산
        max_workers = self.get_optimal_workers()
        logger.info(f"실행 스레드 수: {max_workers}")
        
        # 각 스레드가 처리할 ID 배치 생성
        batch_size = max(5, len(place_ids) // max_workers)
        batches = [place_ids[i:i+batch_size] for i in range(0, len(place_ids), batch_size)]
        
        try:
            # 병렬 크롤링 수행
            results = self.parallel_crawl(batches, base_data, max_workers)
            
            # 결과를 엑셀로 저장
            df = pd.DataFrame(results)
            df.to_excel('dog_kindergarten.xlsx', index=False)
            
            logger.info("엑셀 파일이 생성되었습니다.")
        except Exception as e:
            logger.error(f"에러 발생: {e}")


if __name__ == "__main__":
    main = Main()
    asyncio.run(main.run())