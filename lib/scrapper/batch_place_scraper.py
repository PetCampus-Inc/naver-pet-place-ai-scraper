import time
import concurrent.futures

from typing import List, Tuple, Dict
from utils.get_workers import get_optimal_workers
from lib.logger import get_logger
from lib.scrapper.naver_place_scraper import NaverPlaceScraper


log = get_logger(__name__)

class BatchPlaceScraper:
    def __init__(self, max_retries: int = 3, retry_delay: int = 2):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def parallel_scrape(self, place_ids: List[str]) -> List[Dict]:
        """배치 단위로 병렬 스크래핑을 수행하고 결과를 병합하는 함수"""

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
                    for place_id, scrape_result in batch_results:
                        results.append({"id": place_id, **scrape_result})
                        
                        # 진행 상태 로깅
                        completed += 1
                        if completed % 10 == 0 or completed == total:
                            log.info(f"[{completed}/{total}] 스크래핑 진행 중... ({(completed/total*100):.1f}%)")
                except Exception as e:
                    log.error(f"배치 {batch_index} 결과 처리 중 오류 발생: {e}")

        return results

    def _get_batches(self, place_ids: List[str], max_workers: int) -> List[List[str]]:
        """장소 ID 배치 생성 함수"""

        batch_size = max(3, min(15, len(place_ids) // max_workers))
        batches = [place_ids[i:i+batch_size] for i in range(0, len(place_ids), batch_size)]

        log.info(f"배치 크기: {batch_size}, 총 배치 수: {len(batches)}")
        return batches

    def _process_batch(self, place_ids: List[str]) -> List[Tuple[str, Dict]]:
        """스크래핑 배치 처리 함수"""
        results = []
        log.info(f"배치 처리 시작 - {len(place_ids)}개 장소")
        
        for place_id in place_ids:
            retry_count = 0
            while retry_count < self.max_retries:
                try:
                    # NaverPlaceScraper 인스턴스 생성 및 스크래핑
                    scraper = NaverPlaceScraper()
                    result = scraper.scrape(place_id)
                    
                    if result:
                        results.append((place_id, result))
                        log.debug(f"ID {place_id} 스크래핑 성공")
                    break

                except Exception as e:
                    # 스크래핑 실패 시, 재시도
                    retry_count += 1
                    if retry_count >= self.max_retries:
                        log.error(f"ID {place_id} 스크래핑 실패 (최대 재시도 횟수 초과): {e}")
                        # 실패한 경우 빈 결과라도 추가 (선택사항)
                        results.append((place_id, {}))
                    else:
                        log.warning(f"ID {place_id} 스크래핑 오류, {retry_count}/{self.max_retries} 재시도 중: {e}")
                        time.sleep(self.retry_delay)  # 재시도 전 딜레이
        
        log.info(f"배치 처리 완료 - {len(results)}개 결과")
        return results

    def scrape_places(self, place_ids: List[str], output_file: str = None) -> List[Dict]:
        """장소 ID 리스트를 받아 배치 스크래핑 수행"""
        log.info(f"배치 스크래핑 시작 - 총 {len(place_ids)}개 장소")
        start_time = time.time()
        
        results = self.parallel_scrape(place_ids)
        
        elapsed_time = time.time() - start_time
        log.info(f"배치 스크래핑 완료 - {len(results)}개 결과, 소요시간: {elapsed_time:.2f}초")
        
        # 결과를 파일로 저장 (선택사항)
        if output_file:
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            log.info(f"결과를 {output_file}에 저장했습니다")
        
        return results
