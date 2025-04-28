import pandas as pd
import asyncio
import concurrent.futures
import os
import multiprocessing
from lib.naver_map_scraper import NaverMapScraper
from lib.crawler.naver_place_crawler import NaverPlaceCrawler

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

    # 단일 ID에 대한 크롤링 처리 함수 (스레드에서 실행)
    def crawl_place_detail(self, place_id):
        crawler = NaverPlaceCrawler()

        try:
            return crawler.get_place_details(place_id)
        except Exception as e:
            print(f"ID {place_id} 크롤링 처리 중 오류: {e}")
            return {}
        finally:
            crawler.close()  # 브라우저 종료

    async def run(self):
        # 모든 장소 데이터 스크래핑 (이미 구현된 API 호출)
        places_data = self.scraper.fetch_place_list()
        
        # 기본 데이터 추출
        base_data = {item['id']: item for item in places_data}
        place_ids = [item['id'] for item in places_data]
        
        print(f"총 {len(place_ids)}개 장소 스크래핑 완료, 크롤링 시작")
        
        # 시스템에 최적화된 스레드 수 계산
        max_workers = self.get_optimal_workers()
        print(f"병렬 처리 스레드 수: {max_workers}")
        
        try:
            # ID 리스트를 사용해 병렬 크롤링
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 진행 상황 추적을 위한 변수
                completed = 0
                total = len(place_ids)
                
                # ID 리스트에 대해 병렬 크롤링 작업 생성
                future_to_id = {
                    executor.submit(self.crawl_place_detail, place_id): place_id
                    for place_id in place_ids
                }
                
                # 작업이 완료되는 대로 결과 처리
                result = []
                for future in concurrent.futures.as_completed(future_to_id):
                    place_id = future_to_id[future]
                    try:
                        crawl_result = future.result()
                        
                        # 기본 데이터와 크롤링 상세 정보 병합
                        if place_id in base_data:
                            merged_data = {**base_data[place_id], **crawl_result}
                            result.append(merged_data)
                            
                            # 진행 상황 업데이트
                            completed += 1
                            print(f"[{completed}/{total}] {base_data[place_id]['업체명']} 크롤링 완료")
                    except Exception as e:
                        print(f"결과 처리 중 오류 발생: {e}")
                
                # 결과를 엑셀로 저장
                df = pd.DataFrame(result)
                df.to_excel('dog_kindergarten.xlsx', index=False)

                print("엑셀 파일이 생성되었습니다.")
                
        except Exception as e:
            print(f"에러 발생: {e}")


if __name__ == "__main__":
    main = Main()
    asyncio.run(main.run())