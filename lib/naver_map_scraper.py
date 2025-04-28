import requests

class NaverMapScraper:
    def __init__(self, location, keywords):
        self.location = location
        self.keywords = keywords
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'https://m.map.naver.com/'
        }

    def _fetch_data_for_keyword(self, keyword):
        """지역+키워드에 대한 검색 결과 가져오기"""
        url = f"https://m.map.naver.com/search2/searchMore.naver?query={self.location}+{keyword}&sm=clk&style=v5&page=1&displayCount=500&type=SITE_1"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()["result"]["site"]["list"]
        except (requests.RequestException, KeyError, ValueError) as e:
            print(f"데이터 가져오기 실패 ({keyword}): {e}")
            return []

    def _filter_data(self, datas):
        """결과 필터링 및 중복 제거"""
        filtered_data = []
        seen_ids = set()
        
        for item in datas:
            item_id = item['id']
            
            if item_id not in seen_ids and self.location in item['address']:
                filtered_data.append(item)
                seen_ids.add(item_id)
                
        return filtered_data
    
    def _parse_data(self, data):
        """데이터 가공"""
        return {
            'id': data['id'],
            '업체명': data['name'],
            '등록업종': ', '.join(data['category']),
            '전화번호': data['tel'],
            '주소(도로명)': data['roadAddress'],
            'x': data['x'],
            'y': data['y']
        }
    
    def fetch_place_list(self):
        """네이버 지도 검색 및 가공 된 데이터 가져오기"""
        raw_results = []
        
        for keyword in self.keywords:
            data_list = self._fetch_data_for_keyword(keyword)
            raw_results.extend(data_list)
        
        filtered_results = self._filter_data(raw_results)
        parsed_results = [self._parse_data(item) for item in filtered_results]
        
        return parsed_results
