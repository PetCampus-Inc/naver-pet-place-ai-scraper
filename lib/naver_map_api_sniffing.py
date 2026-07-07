import json
import re
import time
import urllib.parse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from lib.logger import get_logger

log = get_logger()

APOLLO_START_TOKEN = 'window.__APOLLO_STATE__'
PAGE_DISPLAY = 50
MAX_PAGES_PER_KEYWORD = 6  # 최대 300건/키워드


def get_naver_place_list(location, keywords, limit=None):
    """네이버 지도 검색을 Selenium으로 수행해 장소 리스트를 반환"""
    place_list = _fetch_naver_places(location, keywords, limit=limit)
    filtered_places = _filter_places(place_list, location)
    if limit is not None:
        filtered_places = filtered_places[:limit]
    return [_parse_data(place) for place in filtered_places]


def _filter_places(place_list, location):
    """장소 데이터 필터링 (중복 제거, 지역 일치)"""
    filtered_data = []
    seen_ids = set()
    location_normalized = location.replace(' ', '')

    for item in place_list:
        place_id = item.get('id')
        if not place_id or place_id in seen_ids:
            continue

        full_address = (item.get('fullAddress') or '') + ' ' + (item.get('commonAddress') or '') + ' ' + (item.get('roadAddress') or '') + ' ' + (item.get('address') or '')
        if location_normalized not in full_address.replace(' ', ''):
            continue

        filtered_data.append(item)
        seen_ids.add(place_id)

    return filtered_data


def _parse_data(data: dict):
    return {
        "id": int(data['id']),
        "name": data.get('name', ''),
        "tel": data.get('phone') or data.get('virtualPhone') or '',
        "address": data.get('fullAddress') or data.get('address', ''),
        "road_address": data.get('roadAddress', ''),
        "lat": data.get('y'),
        "lng": data.get('x'),
        "thumbnail_url": data.get('imageUrl', ''),
    }


def _fetch_naver_places(location, keywords, limit=None):
    """Selenium으로 pcmap.place.naver.com 검색 페이지를 렌더링 후 __APOLLO_STATE__ 파싱"""
    driver = _create_driver()
    raw_results = []

    try:
        for kw_idx, keyword in enumerate(keywords):
            if kw_idx > 0:
                time.sleep(3)  # rate limit 회피

            query = f"{location} {keyword}"
            for page in range(1, MAX_PAGES_PER_KEYWORD + 1):
                items = _fetch_one_page(driver, query, page)
                if items is None:
                    log.warning(f"페이지 응답 비정상 (kw={keyword}, page={page}) — 건너뜀")
                    break

                log.info(f"  [{keyword}] page={page} → {len(items)}개")
                raw_results.extend(items)

                if limit is not None and len(_filter_places(raw_results, location)) >= limit:
                    return raw_results

                if len(items) < PAGE_DISPLAY:
                    break  # 마지막 페이지

                time.sleep(2)

    finally:
        driver.quit()

    return raw_results


def _create_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1280,1024')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    driver.set_page_load_timeout(30)
    return driver


def _fetch_one_page(driver, query: str, page: int):
    encoded = urllib.parse.quote(query)
    url = f"https://pcmap.place.naver.com/place/list?query={encoded}&page={page}&display={PAGE_DISPLAY}"

    try:
        driver.get(url)
    except Exception as e:
        log.error(f"페이지 로드 실패: {e}")
        return None

    time.sleep(1.5)  # JS 렌더링 대기

    html = driver.page_source
    state_json = _extract_apollo_state(html)
    if state_json is None:
        if 'ncaptcha-all-search-no-result' in html:
            log.warning("CAPTCHA 페이지 감지됨")
            return None
        return []

    try:
        state = json.loads(state_json)
    except json.JSONDecodeError as e:
        log.error(f"APOLLO_STATE JSON 파싱 실패: {e}")
        return []

    return _extract_items_from_state(state)


def _extract_apollo_state(html: str) -> str:
    """HTML에서 window.__APOLLO_STATE__ = {...}; 의 JSON 부분을 brace 매칭으로 추출"""
    idx = html.find(APOLLO_START_TOKEN)
    if idx < 0:
        return None
    eq = html.find('=', idx)
    if eq < 0:
        return None
    start = html.find('{', eq)
    if start < 0:
        return None

    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(html)):
        c = html[i]
        if in_str:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return html[start:i + 1]
    return None


def _extract_items_from_state(state: dict) -> list:
    """Apollo state에서 PlaceListBusinessesItem 객체들을 추출"""
    root = state.get('ROOT_QUERY', {}) or {}

    placelist_key = next((k for k in root.keys() if k.startswith('placeList(')), None)
    if not placelist_key:
        return []

    placelist = root[placelist_key]
    if not isinstance(placelist, dict):
        return []

    businesses = placelist.get('businesses') or {}
    items = businesses.get('items') or []

    results = []
    for item in items:
        ref = item.get('__ref') if isinstance(item, dict) else None
        if not ref or ref not in state:
            continue
        results.append(state[ref])

    return results
