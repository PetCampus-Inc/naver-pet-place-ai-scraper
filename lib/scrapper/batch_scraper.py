import time
import requests

from lib.logger import get_logger
from typing import List, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

log = get_logger(__name__)

class BatchScraper:
    def __init__(self, max_retries: int = 3, retry_delay: int = 1, max_workers: int = 10, headers: dict = {}):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_workers = max_workers

        self.session = self._create_session(headers)

    def _create_session(self, headers: dict = {}):
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=self.max_retries
        )

        session = requests.Session()
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            **headers
        }

        session.headers.update(default_headers)
        return session

    def scrape_batch(self, urls: List[str], scrape_fn: Callable[[str], Any]) -> List[Any]:
        """
        urls를 받아 각각 스크래핑된 결과를 반환
        """
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self._scraper, url, scrape_fn): url 
                for url in urls
            }
            
            # 완료된 작업들 처리
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    parsed_data = future.result()
                    if parsed_data: results.append(parsed_data)
                except Exception as e:
                    log.error(f"[{url}] 처리 중 에러: {e}")
        
        log.info(f"{len(results)}/{len(urls)} 스크래핑 완료 (소요 시간: {time.time() - start_time:.2f}초)")
        return results

    def _scraper(self, url: str, scrape_fn: Callable[[str], Any]) -> Optional[Any]:
        """
        단일 url에 대해 스크래핑 및 파싱 수행
        """
        # 실패 시, max_retries 횟수만큼 반복
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url)
                response.raise_for_status()
                response.encoding = 'utf-8'

                return scrape_fn(response)
            except Exception as e:
                if attempt < self.max_retries:
                    log.warning(f"[{url}] 재시도 {attempt + 1}/{self.max_retries}: 에러메시지[{e}]")
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    log.error(f"[{url}] 스크랩핑 실패: {e}")
                    return None
        
        return None