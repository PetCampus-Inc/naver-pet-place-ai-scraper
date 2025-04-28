import pandas as pd
import asyncio
import concurrent.futures
import os
import multiprocessing
import logging
from lib.naver_map_scraper import NaverMapScraper
from lib.crawler.naver_place_crawler import NaverPlaceCrawler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# googleapiclient 경고 로그 비활성화
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

class Main:
    def __init__(self):
        self.location = "서초구"
        self.keywords = ["강아지 유치원", "반려견 유치원", "강아지 호텔", "반려견 호텔", "애견 유치원", "애견 호텔"]
        
        self.scraper = NaverMapScraper(self.location, self.keywords)
        
    # 시스템에 최적화된 스레드 수 계산
    def get_optimal_workers(self):
        # CPU 논리적 코어 수 확인
        cpu_count = os.cpu_count() or multiprocessing.cpu_count()
        
        # 코어 수의 1.5배, 최소 2개, 최대 8개
        default_workers = min(max(2, int(cpu_count * 1.5)), 8)
        
        # 서버 부하 고려하여 조정 (최대 5개로 제한)
        naver_safe_limit = min(default_workers, 5)
        
        return naver_safe_limit

    # 단일 ID에 대한 크롤링 처리 함수
    def crawl_place_detail(self, place_id):
        # 컨텍스트 매니저로 올바르게 사용
        with NaverPlaceCrawler() as crawler:
            try:
                return crawler.get_place_details(place_id)
            except Exception as e:
                logger.error(f"ID {place_id} 크롤링 처리 중 오류: {e}")
                return {}

    # 여러 ID를 배치로 처리하는 함수
    def process_batch(self, batch_ids):
        results = []
        
        # 하나의 브라우저 세션으로 여러 장소 처리
        with NaverPlaceCrawler() as crawler:
            for place_id in batch_ids:
                try:
                    result = crawler.get_place_details(place_id)
                    if result:
                        results.append((place_id, result))
                except Exception as e:
                    logger.error(f"ID {place_id} 크롤링 처리 중 오류: {e}")
        
        return results

    async def run(self):
        # 모든 장소 데이터 스크래핑
        places_data = self.scraper.fetch_place_list()
        
        # 기본 데이터 추출
        base_data = {item['id']: item for item in places_data}
        place_ids = [item['id'] for item in places_data]
        
        logger.info(f"총 {len(place_ids)}개 장소 스크래핑 완료, 크롤링 시작")
        
        # 시스템에 최적화된 스레드 수 계산
        max_workers = self.get_optimal_workers()
        logger.info(f"병렬 처리 스레드 수: {max_workers}")
        
        # 각 스레드가 처리할 ID 배치 생성 (브라우저 재사용)
        batch_size = max(5, len(place_ids) // max_workers)
        batches = [place_ids[i:i+batch_size] for i in range(0, len(place_ids), batch_size)]
        
        try:
            # 배치 단위로 병렬 크롤링
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 진행 상황 추적
                completed = 0
                total = len(place_ids)
                
                # 배치 단위로 병렬 처리
                future_to_batch = {
                    executor.submit(self.process_batch, batch): i
                    for i, batch in enumerate(batches)
                }
                
                # 결과 수집
                all_results = []
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch_index = future_to_batch[future]
                    try:
                        batch_results = future.result()
                        
                        for place_id, crawl_result in batch_results:
                            # 기본 데이터와 크롤링 상세 정보 병합
                            if place_id in base_data:
                                merged_data = {**base_data[place_id], **crawl_result}
                                all_results.append(merged_data)
                                
                                # 진행 상황 업데이트
                                completed += 1
                                logger.info(f"[{completed}/{total}] {base_data[place_id]['업체명']} 크롤링 완료")
                    except Exception as e:
                        logger.error(f"배치 {batch_index} 결과 처리 중 오류 발생: {e}")
                
                # 결과를 엑셀로 저장
                df = pd.DataFrame(all_results)
                df.to_excel('dog_kindergarten.xlsx', index=False)

                logger.info("엑셀 파일이 생성되었습니다.")
                
        except Exception as e:
            logger.error(f"에러 발생: {e}")


if __name__ == "__main__":
    main = Main()
    asyncio.run(main.run())