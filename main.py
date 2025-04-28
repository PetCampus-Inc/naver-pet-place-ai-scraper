import pandas as pd
import asyncio
from lib.naver_map_scraper import NaverMapScraper
from lib.crawler.naver_place_crawler import NaverPlaceCrawler

class Main:
    def __init__(self):
        self.location = "강남구"
        self.keywords = ["강아지 유치원", "반려견 유치원", "강아지 호텔", "반려견 호텔", "애견 유치원", "애견 호텔"]
        
        self.scraper = NaverMapScraper(self.location, self.keywords)
        self.crawler = NaverPlaceCrawler()

    async def run(self):
        location_data_list = self.scraper.fetch_place_list()

        try:
            count = 0
            result = []
            for item in location_data_list:
                crawler_data = self.crawler.get_place_details(item['id'])
                result.append({**item, **crawler_data})

                count += 1
                print(item['업체명'], "크롤링 완료", count, "/", len(location_data_list))

            df = pd.DataFrame(result)
            df.to_excel('dog_kindergarten.xlsx', index=False)

            print("엑셀 파일이 생성되었습니다.")
        except Exception as e:
            print(f"에러 발생: {e}")
        finally:
            self.crawler.close()


if __name__ == "__main__":
    main = Main()
    asyncio.run(main.run())