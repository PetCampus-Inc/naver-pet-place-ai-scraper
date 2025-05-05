import time
import concurrent.futures

from typing import List, Tuple, Dict
from lib.crawler.naver_place_crawler import NaverPlaceCrawler
from utils.get_workers import get_optimal_workers
from lib.logger import get_logger


log = get_logger()

class BatchProcessCrawler:
    def __init__(self, max_retries: int, retry_delay: int):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def parallel_crawl(self, place_ids: List[str]) -> List[Dict]:
        """배치 단위로 병렬 크롤링을 수행하고 결과를 병합하는 함수"""

        # 스레드 수 계산
        max_workers = get_optimal_workers()
        log.info(f"실행 스레드 수: {max_workers}")

        # 각 스레드가 처리할 ID 배치 생성 - 적절한 배치 크기로 조정
        batches = self._get_batches(place_ids, max_workers)

        results = []
        total = sum(len(batch) for batch in batches)
        completed = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_batch = {
                executor.submit(self._process_batch, batch): i
                for i, batch in enumerate(batches)
            }
            
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_index = future_to_batch[future]
                try:
                    batch_results = future.result()
                    
                    # 배치 결과 처리
                    for place_id, crawl_result in batch_results:
                        results.append({"id": place_id, **crawl_result})
                        
                        # 진행 상태 로깅
                        completed += 1
                        if completed % 10 == 0 or completed == total:
                            log.info(f"[{completed}/{total}] 크롤링 진행 중... ({(completed/total*100):.1f}%)")
                except Exception as e:
                    log.error(f"배치 {batch_index} 결과 처리 중 오류 발생: {e}")

        return results

    def _get_batches(self, place_ids: List[str], max_workers: int) -> List[List[str]]:
        """장소 ID 배치 생성 함수"""

        batch_size = max(5, min(20, len(place_ids) // max_workers))
        batches = [place_ids[i:i+batch_size] for i in range(0, len(place_ids), batch_size)]

        log.info(f"배치 크기: {batch_size}, 총 배치 수: {len(batches)}")
        return batches

    def _process_batch(self, place_ids: List[str]) -> List[Tuple[str, Dict]]:
        """크롤링 배치 처리 함수"""
        results = []
        log.info(f"process_batch 시작")
        
        with NaverPlaceCrawler() as crawler:
            for place_id in place_ids:
                retry_count = 0
                while retry_count < self.max_retries:
                    try:
                        # 크롤링
                        result = crawler.get_place_details(place_id)
                        if result:
                            results.append((place_id, result))
                        break

                    except Exception as e:
                        # 크롤링 실패 시, 재시도
                        retry_count += 1
                        if retry_count >= self.max_retries:
                            log.error(f"ID {place_id} 크롤링 실패 (최대 재시도 횟수 초과): {e}")
                        else:
                            log.warning(f"ID {place_id} 크롤링 오류, {retry_count}/{self.max_retries} 재시도 중: {e}")
                            time.sleep(self.retry_delay)  # 재시도 전 딜레이
        
        return results