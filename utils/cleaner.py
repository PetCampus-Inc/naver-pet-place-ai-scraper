import re
import bs4

def clean_text(text: str) -> str:
    """텍스트의 공백 및 특수 문자를 정규화합니다."""
    if not text: return ""

    text = text.replace('\\n', ' ')  # 줄바꿈 문자를 공백으로
    text = text.replace('\\"', '"')   # 이스케이프된 따옴표
    text = text.replace('\xa0', ' ')  # Non-breaking space를 일반 공백으로

    text = re.sub(r'\\([^n"])', r'\1', text)  # 기타 이스케이프 문자 제거
    text = re.sub(r'\s+', ' ', text)    # 여러 개의 공백을 하나의 공백으로 줄임

    text = text.strip()
    return text

def clean_html(soup: bs4.BeautifulSoup):
    # 스크립트, 스타일 등 불필요한 태그 제거
    for tag in soup(['script', 'style', 'head', 'meta', 'noscript', 'iframe']):
        tag.decompose()
    
    # 주석 제거
    for comment in soup.find_all(text=lambda text: isinstance(text, bs4.Comment)):
        comment.extract()

    # 인라인 자바스크립트 이벤트 핸들러 제거
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.startswith('on') or (attr == 'href' and tag.get(attr) and tag.get(attr).startswith('javascript:')):
                del tag[attr]
                
    return soup