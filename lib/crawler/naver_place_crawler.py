from lib.crawler.browser_setup import BrowserManager
from lib.crawler.crawler_home import CrawlerHome
from lib.crawler.crawler_information import CrawlerInformation
from logger import get_logger

log = get_logger()

class NaverPlaceCrawler:
    def __init__(self):
        """
        네이버 플레이스 크롤러 초기화
        """
        self.browser_manager = BrowserManager()
        self.driver = None
        self.wait = None
        
    def __enter__(self):
        """
        컨텍스트 매니저 진입 메서드
        """
        self.driver, self.wait = self.browser_manager.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        컨텍스트 매니저 종료 메서드
        """
        if hasattr(self, 'browser_manager'):
            self.browser_manager.__exit__(exc_type, exc_val, exc_tb)
            self.driver = None
            self.wait = None
    
    def get_place_details(self, place_id):
        """
        지정된 장소 ID에 대한 상세 정보를 크롤링합니다.
        
        Args:
            place_id (str): 네이버 플레이스 ID
            
        Returns:
            dict: 크롤링된 장소 정보를 담은 딕셔너리
        """
        if not self.driver or not self.wait:
            raise RuntimeError("브라우저가 초기화되지 않았습니다. 컨텍스트 매니저로 사용하세요.")
            
        self.crawler_home = CrawlerHome(self.driver, self.wait, place_id)
        self.crawler_information = CrawlerInformation(self.driver, self.wait, place_id)
    
        try:
            home = self.crawler_home.get_home_data()
            information = self.crawler_information.get_information()
            return {**home, **information}
        
        except Exception as e:
            log.error(f"ID {place_id} 크롤링 중 오류 발생: {e}")
            return {}
        
    def close(self):
        """
        브라우저 자원을 해제합니다.
        """
        self.__exit__(None, None, None)