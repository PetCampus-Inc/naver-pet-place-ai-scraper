import pandas as pd
import asyncio
import concurrent.futures
import os
import multiprocessing
import time
from typing import Dict, List, Tuple, Any

from lib.naver_map_api_sniffing import fetch_naver_place_list
from lib.crawler.naver_place_crawler import NaverPlaceCrawler
from logger import get_logger

log = get_logger()

class Main:
    def __init__(self):
        self.location = input("검색할 지역을 입력하세요 (예: 서초구, 강남구, 대치동): ")
        self.keywords = ["강아지 유치원", "반려견 유치원", "강아지 호텔", "반려견 호텔", "애견 유치원", "애견 호텔"]

        self.max_retries = 3    # 크롤링 실패 시, 재시도 횟수
        self.retry_delay = 2    # 재시도 전, 딜레이 (초 단위)
        self.chunk_size = 1000  # 데이터프레임 청크 크기
        
    async def run(self):
        """메인 실행 함수: 검색, 크롤링, 저장을 관리"""
        log.info("크롤링 작업 시작")
        start_time = time.time()
        
        # 네이버 지도 검색 결과 가져오기
        try:
            places_data = await self._fetch_place_data()
            if not places_data:
                log.error("검색 결과가 없습니다.")
                return
        except Exception as e:
            log.error(f"장소 데이터 검색 중 오류 발생: {e}")
            return
            
        # 기본 데이터 추출
        base_data = {item['id']: item for item in places_data}
        place_ids = list(base_data.keys())
        
        log.info(f"총 {len(place_ids)}개 장소 스니핑 완료, 크롤링 시작")
        
        # 최적의 스레드 수 계산
        max_workers = self.get_optimal_workers()
        log.info(f"실행 스레드 수: {max_workers}")
        
        # 각 스레드가 처리할 ID 배치 생성 - 적절한 배치 크기로 조정
        batch_size = max(5, min(20, len(place_ids) // max_workers))
        batches = [place_ids[i:i+batch_size] for i in range(0, len(place_ids), batch_size)]
        log.info(f"배치 크기: {batch_size}, 총 배치 수: {len(batches)}")

        try:
            # 병렬 크롤링 수행
            results = self.parallel_crawl(batches, base_data, max_workers)
            
            # 결과를 엑셀로 저장 (대용량 처리를 위한 최적화)
            await self._save_results(results)
            
            # 실행 시간 로깅
            elapsed_time = time.time() - start_time
            log.info(f"크롤링 작업 완료. 총 {len(results)}개 항목, 소요 시간: {elapsed_time:.2f}초")
            
        except Exception as e:
            log.error(f"크롤링 중 오류 발생: {e}")
        
    def get_optimal_workers(self) -> int:
        """최적의 스레드 수를 계산하는 함수"""
        # CPU 코어 수 확인
        cpu_count = os.cpu_count() or multiprocessing.cpu_count()
        
        # I/O 바운드 작업, 코어 수의 2배 (최소 4개, 최대 6개)
        return min(max(4, int(cpu_count * 2)), 6)

    def process_batch(self, place_ids: List[str]) -> List[Tuple[str, Dict]]:
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
    
    def parallel_crawl(self, batches: List[List[str]], base_data: Dict[str, Dict], max_workers: int) -> List[Dict]:
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
                            if completed % 10 == 0 or completed == total:
                                log.info(f"[{completed}/{total}] 크롤링 진행 중... ({(completed/total*100):.1f}%)")
                except Exception as e:
                    log.error(f"배치 {batch_index} 결과 처리 중 오류 발생: {e}")

        return results
    
    async def _fetch_place_data(self) -> List[Dict[str, Any]]:
        """장소 데이터를 가져오는 함수"""
        return fetch_naver_place_list(self.location, self.keywords)
        
    async def _save_results(self, results: List[Dict[str, Any]]):
        """결과를 파일로 저장하는 함수"""
        if not results:
            log.warning("저장할 결과가 없습니다.")
            return
            
        try:
            file_name = f"dog_service_{self.location}_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # 결과가 많을 경우 메모리 효율을 위해 청크 단위로 처리
            if len(results) > self.chunk_size:
                writer = pd.ExcelWriter(file_name, engine='xlsxwriter')
                
                # 청크 단위로 나누어 데이터프레임 생성 및 저장
                for i in range(0, len(results), self.chunk_size):
                    chunk = results[i:i+self.chunk_size]
                    chunk_df = pd.DataFrame(chunk)
                    
                    # 첫 번째 청크면 헤더 포함, 아니면 헤더 제외
                    chunk_df.to_excel(
                        writer, 
                        sheet_name='데이터', 
                        index=False,
                        startrow=(0 if i == 0 else writer.sheets['데이터'].max_row),
                        header=(i == 0)
                    )
                
                writer.close()
            else:
                # 결과가 적을 경우 간단히 저장
                df = pd.DataFrame(results)
                df.to_excel(file_name, index=False)
            
            log.info(f"엑셀 파일이 생성되었습니다: {file_name}")
        except Exception as e:
            log.error(f"결과 저장 중 오류 발생: {e}")
            # 에러 발생 시 CSV로 백업 저장 시도
            try:
                backup_file = f"backup_{time.strftime('%Y%m%d_%H%M%S')}.csv"
                pd.DataFrame(results).to_csv(backup_file, index=False)
                log.info(f"백업 CSV 파일이 생성되었습니다: {backup_file}")
            except Exception as backup_error:
                log.error(f"백업 저장 중 오류 발생: {backup_error}")


if __name__ == "__main__":
    main = Main()
    asyncio.run(main.run())