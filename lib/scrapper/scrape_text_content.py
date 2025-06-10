import bs4

from lib.logger import get_logger
from utils.cleaner import clean_html, clean_text
from utils.text import text_to_sentence, remove_duplicate_texts
from utils.fetch import fetch_url

log = get_logger(__name__)

def scrape_text_content(url: str) -> list[str]:
    """웹 페이지에서 텍스트 콘텐츠를 추출합니다"""
        # URL 유효성 검사

    # HTML 파싱
    html_source = fetch_url(url)
    if not html_source: return []

    soup = bs4.BeautifulSoup(html_source.content, 'lxml')

    # 불필요한 태그 제거
    cleaned_soup = clean_html(soup)

    # 유효한 텍스트를 가지고 있는 태그들만 추출
    text_tags = _extract_text_from_soup(cleaned_soup)
    
    # 각 태그에서 텍스트 추출 및 중복 제거
    all_text = []
    for tag in text_tags:
        text = tag.get_text(strip=True)
        cleaned_text = clean_text(text)

        if text and len(text) < 2: continue

        sentences = text_to_sentence(cleaned_text)
        all_text.extend(sentences)
    
    # 중복 제거
    unique_text = remove_duplicate_texts(all_text)
    
    return unique_text

def _extract_text_from_soup(soup: bs4.BeautifulSoup) -> list[bs4.Tag]:
    """BeautifulSoup에서 유효한 텍스트를 가진 태그들을 반환합니다."""
    valid_tags = []

    primary_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']
    semantic_tags = ['article', 'section', 'aside']
    secondary_tags = ['a', 'span', 'strong', 'em', 'b', 'i', 'td', 'th']
    
    # 주요 태그 파싱
    for tag_name in primary_tags:
        for tag in soup.find_all(tag_name, recursive=True):
            valid_tags.append(tag)
    
    # 의미 태그 파싱 (직접적인 텍스트가 있는 경우만)
    for tag_name in semantic_tags:
        for tag in soup.find_all(tag_name, recursive=True):
            if not tag.find_all(primary_tags, recursive=False):
                if _has_direct_text(tag):
                    valid_tags.append(tag)
    
    # div 태그 파싱 (직접적인 텍스트가 있는 경우만)
    for div_tag in soup.find_all('div', recursive=True):
        if not div_tag.find_all(primary_tags + secondary_tags, recursive=False):
            if _has_direct_text(div_tag):
                valid_tags.append(div_tag)

    # a, span 등 부가 태그 처리
    for tag_name in secondary_tags:
        for tag in soup.find_all(tag_name, recursive=True):
            parent_chain = []
            current = tag.parent
            
            # 부모 태그 체인을 구성
            while current and len(parent_chain) < 5:
                parent_chain.append(current.name)
                current = current.parent
            
            # primary_tags 중 하나가 부모 체인에 있는지 확인
            is_child_of_primary = any(p_tag in parent_chain for p_tag in primary_tags)
            
            if not is_child_of_primary and tag.get_text(strip=True):
                valid_tags.append(tag)

    return valid_tags

def _has_direct_text(tag: bs4.Tag) -> bool:
    """태그가 직접적인 텍스트 노드를 가지고 있는지 확인합니다."""
    for child in tag.children:
        if isinstance(child, bs4.NavigableString) and child.strip():
            return True
    return False