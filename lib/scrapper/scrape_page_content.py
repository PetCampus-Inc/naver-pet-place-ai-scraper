import bs4
from typing import List

from lib.scrapper.batch_scraper import BatchScraper
from lib.logger import get_logger
from utils.cleaner import clean_html, clean_text
from utils.text import text_to_sentence, remove_duplicate_texts
from utils.extract_links import extract_links

log = get_logger(__name__)

def scrape_page_content(business_urls: List[dict]) -> List[dict]:
    scraper = BatchScraper()

    result = []
    for business_url in business_urls:
        for place_id, urls in business_url.items():
            child_links = sum([extract_links(url) for url in urls], [])
            
            if child_links:
                contents = scraper.scrape_batch(child_links, _parse_text_content)
                merged_contents = [text for texts in contents for text in texts]
                page_content = " ".join(remove_duplicate_texts(merged_contents))
            else: page_content = ""

            result.append({
                "id": place_id,
                "page_content": page_content
            })

    return result

def _parse_text_content(page_source) -> list[str]:
    """웹 페이지의 텍스트 콘텐츠 추출 후, 문장 리스트로 반환"""
    # HTML 파싱
    soup = bs4.BeautifulSoup(page_source.content, 'lxml')

    # 불필요한 태그 제거
    cleaned_soup = clean_html(soup)

    # 유효한 텍스트를 가지고 있는 태그들만 추출
    text_tags = _extract_text_from_soup(cleaned_soup)
    
    # 각 태그에서 텍스트 추출 및 중복 제거
    all_text = []
    for tag in text_tags:
        text = tag.get_text(strip=True)
        cleaned_text = clean_text(text)

        if cleaned_text and len(cleaned_text) < 2: continue

        sentences = text_to_sentence(cleaned_text)
        all_text.extend(sentences)
    
    return all_text

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
            has_primary_parent = any(p_tag in parent_chain for p_tag in primary_tags)
            
            if not has_primary_parent and tag.get_text(strip=True):
                valid_tags.append(tag)

    return valid_tags

def _has_direct_text(tag: bs4.Tag) -> bool:
    """태그가 직접적인 텍스트 노드를 가지고 있는지 확인합니다."""
    for child in tag.children:
        if isinstance(child, bs4.NavigableString) and child.strip():
            return True
    return False