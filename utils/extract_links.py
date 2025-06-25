import requests
import re

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from lib.logger import get_logger
from utils.fetch import fetch_url

log = get_logger(__name__)

def extract_links(base_url: str) -> list[str]:
    """페이지에서 모든 링크를 추출하는 함수"""

    excluded_text_patterns = ["개인정보", "이용약관", "고객지원", "리뷰", "문의"]
    base_domain = urlparse(base_url).netloc

    links = set()

    if _is_valid_url(base_url, base_domain):
        links.add(base_url)

    try:
        response = fetch_url(base_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 리다이렉션 처리
        redirect_url = _redirect(soup, response, base_url)
        if redirect_url:
            return extract_links(redirect_url)
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            full_url = urljoin(base_url, href)

            if not _is_valid_url(full_url, base_domain):
                continue

            # a 태그 텍스트에 제외 텍스트가 포함되어 있으면 스킵
            if any(pattern in a_tag.get_text(strip=True) for pattern in excluded_text_patterns):
                continue

            links.add(full_url.rstrip('/'))
        
        if len(links) > 0: log.info(f"{base_url}: {len(links)}개의 유효한 링크 추출")
        
        return list(links)
        
    except Exception as e:
        log.error(f"{base_url}: {e}")
        return []

def _is_valid_url(url: str, base_domain: str):
    excluded_url_patterns = ["blog", "profile", "board", "shop", "product", "kakao", "naver", "store", "login", "logout", "signin",
                             "facebook", "instagram", "facebook", "youtube", "linktr", "policy", "privacy"]
    parsed_url = urlparse(url)

    # 링크가 목표 도메인과 다른 경우 스킵
    if not parsed_url.netloc or parsed_url.netloc != base_domain:
        return False

    # 링크가 자바스크립트, 메일, 앵커 링크인 경우 스킵
    if url.startswith(('javascript:', 'mailto:', '#')):
        return False

    # path에 숫자만 있거나 한글이 포함된 경우 제외
    path_list = parsed_url.path.split("/")
    if any(re.search(r'^[0-9]+$|[가-힣]', segment) for segment in path_list if segment):
        return False

    # 링크에 제외 패턴이 포함되어 있으면 스킵
    if any(pattern in url.lower() for pattern in excluded_url_patterns):
        return False

    return True

def _client_redirect(soup: BeautifulSoup, base_url: str) -> str:
    """HTML meta refresh 태그가 있는지 확인하고 리다이렉션 URL을 반환하는 함수"""
    meta_refresh = soup.find('meta', attrs={'http-equiv': lambda x: x and x.lower() == 'refresh'})
    if not meta_refresh:
        return None
    
    content = meta_refresh.get('content', '')
    if not content or ';' not in content:
        return None
    
    try:
        # 정규식을 사용 URL 추출
        url_match = re.search(r'url\s*=\s*(["\']?)([^"\'>\s]+)\1', content.split(';', 1)[1], re.IGNORECASE)
        if not url_match:
            return None
            
        redirect_url = url_match.group(2)
        
        # 상대 URL을 절대 URL로 변환
        if not redirect_url.startswith(('http://', 'https://')):
            redirect_url = urljoin(base_url, redirect_url)
        
        log.info(f"{base_url}: 메타 태그 리다이렉트 감지됨 -> {redirect_url}")
        return redirect_url
    except Exception as e:
        log.error(f"메타 태그 파싱 오류: {e}")
    
    return None

def _server_redirect(response: requests.Response, base_url: str):
    # HTTP 리다이렉트 처리 (300번대 상태 코드)
    redirect_url = None
    if 300 <= response.status_code < 400 and 'location' in response.headers:
        redirect_url = response.headers['location']
        
        # 상대 URL을 절대 URL로 변환
        if not redirect_url.startswith(('http://', 'https://')):
            redirect_url = urljoin(base_url, redirect_url)
            
        log.info(f"{base_url}: HTTP 리다이렉트 감지됨 -> {redirect_url}")
        
    return redirect_url

def _redirect(soup: BeautifulSoup, response: requests.Response, base_url: str):
    redirect_url = _server_redirect(response, base_url)
    if not redirect_url:
        redirect_url = _client_redirect(soup, base_url)

    return redirect_url