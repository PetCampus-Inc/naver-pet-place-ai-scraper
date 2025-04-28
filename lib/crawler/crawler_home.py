from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re

class CrawlerHome:
    def __init__(self, driver: webdriver.Chrome, wait: WebDriverWait, place_id: str):
        self.driver = driver
        self.wait = wait
        self.place_id = place_id
        self.url = f"https://m.place.naver.com/place/{self.place_id}/home"

    # 운영 시간 가져오기
    def _get_business_hours(self, soup: BeautifulSoup, has_business_hours_toggle: bool):
        days = ["월", "화", "수", "목", "금", "토", "일"]
        response = dict.fromkeys(days, "")

        # 영업 시간 더보기가 없을 경우
        if not has_business_hours_toggle:
            business_hours = soup.select_one("div.U7pYf").text

            if "매일" in business_hours:
                # 영업 시간만 가져오기 (예: '10:00 - 18:00')
                pattern = r'\d{2}:\d{2}\s*-\s*\d{2}:\d{2}'
                time_text = re.search(pattern, business_hours)

                if time_text:
                    hours_text = time_text.group()
                    return dict.fromkeys(days, hours_text)

            return response

        business_hour_tags = soup.select("a.gKP9i.RMgN0 *.A_cdD")

        def format_hours(hours_element):
            if hours_element.name != "ul":
                return hours_element.text
                
            return "\n".join([
                f"[{hour.find_all('span')[0].text}] {hour.find_all('span')[1].text}"
                for hour in hours_element
            ])

        for business_hour_tag in business_hour_tags:
            # 영업 시간 태그가 2개 미만일 경우 무시
            if len(business_hour_tag.contents) < 2: continue
    
            label, hours, *_ = business_hour_tag

            # label의 태그가 em일 경우 무시 (오늘 영업 안내 태그)
            if label.name == "em": continue

            formatted_content = format_hours(hours)
                
            if "매일" in label.text:
                response.update(dict.fromkeys(days, formatted_content))
                break
            elif label.text in days:
                response[label.text] = formatted_content

        return response
    
    # 가격표 이미지 가져오기
    def _get_price_images(self):
        # 가격 버튼 찾기 (a.place_bluelink.iBUwB 태그에서 "가격" 이라는 텍스트가 있는 요소)
        try:
            price_button = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'place_bluelink') and contains(@class, 'iBUwB') and starts-with(text(), '가격')]"))
            )
            price_button.click()
        except: return []
        
        # 이미지 최대 개수 가져오기
        image_count_max_tag = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.rCaLC"))
        )
        image_count_max = image_count_max_tag.text.split('/')[-1].strip()
        
        # 이미지 URL 저장할 리스트
        image_urls = []
        
        # 첫 번째 이미지 URL 가져오기
        image_tag = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.yJgpY._imgWrapperAreaRef > img"))
        )
        image_urls.append(image_tag.get_attribute("src"))
        
        # 나머지 이미지 순회하기 (2번째부터 끝까지)
        for _ in range(1, int(image_count_max)):
            # 다음 버튼 클릭
            self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.BU49A"))
            ).click()
            
            # 이미지가 바뀔 때까지 잠시 대기
            self.wait.until(EC.staleness_of(image_tag))
            
            # 새로운 이미지 요소 가져오기
            image_tag = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.yJgpY._imgWrapperAreaRef > img"))
            )
            
            # 이미지 URL 저장
            current_url = image_tag.get_attribute("src")
            image_urls.append(current_url)
        
        return image_urls

    # 리뷰 가져오기
    def _get_reviews(self, soup: BeautifulSoup):
        review_tags = soup.select("span.PXMot > a")
        base_url = "https://m.place.naver.com"

        reviews = {}
        for review_tag in review_tags:
            [name, count] = review_tag.text.split(" 리뷰 ")
            reviews[f"{name} 리뷰"] = count
            reviews[f"{name} 리뷰 링크"] = f"{base_url}{review_tag.get('href')}"

        return reviews

    def get_home_data(self):
        """네이버 플레이스 메인 페이지 데이터 가져오기"""
        self.driver.get(self.url)
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # 영업 시간 더보기 존재 여부
        has_business_hours_toggle = bool(self.driver.find_elements(By.CSS_SELECTOR, "a.gKP9i.RMgN0"))

        # 영업 시간 더보기가 있을 경우 클릭
        if has_business_hours_toggle:
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.gKP9i.RMgN0"))
            ).click()

        soup = BeautifulSoup(self.driver.page_source, 'lxml')

        try: 
            business_hours = self._get_business_hours(soup, has_business_hours_toggle)
            price_images = self._get_price_images()
            reviews = self._get_reviews(soup)
            map_link = f"https://map.naver.com/p/entry/place/{self.place_id}"

            return {
                "가격표 이미지": price_images,
                "네이버 지도 링크": map_link,
                **business_hours,
                **reviews
            }
        except Exception as e:
            print(f"ID {self.place_id} 메인 크롤링 오류 발생: {e}")
            return {}
