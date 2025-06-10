import requests
from urllib.parse import urlparse

from lib.logger import get_logger


log = get_logger(__name__)

# 페이지 소스 가져오기
def fetch_url(url: str) -> str | None:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("유효하지 않은 URL 형식입니다.")
    
        html_source = requests.get(url, timeout=10, headers=headers)
        html_source.raise_for_status()

        return html_source
    except requests.ConnectionError:
        log.error(f"서버 연결에 실패했습니다.")
        return None
    except (requests.RequestException, Exception) as e:
        log.error(f"HTML 요청 실패: {e}")
        return None