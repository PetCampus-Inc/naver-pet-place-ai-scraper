from lib.crawler.browser_setup import setup_browser
from lib.crawler.crawler_home import CrawlerHome
from lib.crawler.crawler_information import CrawlerInformation

class NaverPlaceCrawler:
    def __init__(self):
        self.driver, self.wait = setup_browser()

    def get_place_details(self, place_id):
        self.crawler_home = CrawlerHome(self.driver, self.wait, place_id)
        self.crawler_information = CrawlerInformation(self.driver, self.wait, place_id)
    
        try:
            home = self.crawler_home.get_home_data()
            information = self.crawler_information.get_information()

            return {**home, **information}
        
        except Exception as e:
            print(f"ID {place_id} 크롤링 중 오류 발생: {e}")
            return {}
        
    def close(self):
        if self.driver:
            self.driver.quit()
