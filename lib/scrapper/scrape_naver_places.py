import re
import json

from typing import List
from lib.scrapper.naver_place_parser import NaverPlaceParser
from lib.scrapper.batch_scraper import BatchScraper


APOLLO_PATTERN = r'window\.__APOLLO_STATE__\s*=\s*({.*?});'

def scrape_naver_places(place_ids: List[int]) -> List[dict]:
    """네이버 플레이스 배치 스크래핑"""
    naver_place_parser = NaverPlaceParser()
    
    def parse_place(page_source) -> dict:
        match = re.search(APOLLO_PATTERN, page_source.text, re.DOTALL)
        if match:
            apollo_state = json.loads(match.group(1))
            return naver_place_parser.parse(apollo_state)
    
    headers = {
        'Accept': 'text/html,application/xhtml+xml...',
        'Accept-Language': 'ko-KR,ko;q=0.9...',
    }
    
    scraper = BatchScraper(headers=headers)
    urls = [f"https://m.place.naver.com/place/{id}/home" for id in place_ids]
    
    return scraper.scrape_batch(urls, parse_place)