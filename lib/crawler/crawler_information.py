from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re

class CrawlerInformation:
    def __init__(self, driver: webdriver.Chrome, wait: WebDriverWait, place_id: str):
        self.driver = driver
        self.wait = wait
        self.place_id = place_id
        self.url = f"https://m.place.naver.com/place/{self.place_id}/information"

    # 텍스트 가져오기
    def _safe_select(self, soup: BeautifulSoup, selector):
        element = soup.select_one(selector)
        return element.text if element else ""

    # 텍스트 리스트 가져오기
    def _safe_select_all(self, soup: BeautifulSoup, selector):
        elements = soup.select(selector)
        return [element.text for element in elements] if elements else []
    
    # 링크 리스트 가져오기
    def _get_links(self, soup: BeautifulSoup):
        elements = soup.select("a.eBr5V")
        
        links_dict = {}
        link_types = {
            "instagram.com": "인스타그램",
            "blog.naver.com": "블로그", 
            "youtube.com": "유튜브",
            "youtu.be": "유튜브"
        }
        
        for link in elements:
            href = link.get("href")
            if not href: continue
                
            # 링크 유형 결정
            link_type = "홈페이지"
            for domain, label in link_types.items():
                if domain in href:
                    link_type = label
                    break
            
            # 같은 유형의 링크가 여러 개 있을 경우 번호 추가
            base_key = link_type
            counter = 1
            key = base_key
            
            while key in links_dict:
                counter += 1
                key = f"{base_key} {counter}"
                
            links_dict[key] = href
        
        return links_dict
    
    # 주차, 발렛 정보 가져오기
    def _get_parking(self, soup: BeautifulSoup):
        parking_tags = soup.select("div.SGJcE *.TZ6eS")

        response = {"주차": "FALSE", "발렛파킹": "FALSE"}

        for parking_tag in parking_tags:
            if "주차가능" in parking_tag.text:
                response["주차"] = "TRUE"
            elif "발렛가능" in parking_tag.text:
                response["발렛파킹"] = "TRUE"
        
        return response

    def get_information(self):
        self.driver.get(self.url)
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        
        return {
            "소개": self._safe_select(soup, "div.T8RFa"),
            "편의시설 및 서비스": self._safe_select_all(soup, "div.owG4q"),
            "대표 키워드": self._safe_select_all(soup, "div.FbEj5 > *.RLvZP"),
            **self._get_links(soup),
            **self._get_parking(soup)
        }