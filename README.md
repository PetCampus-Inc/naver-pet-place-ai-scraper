![web-scraper-pipeline](https://github.com/user-attachments/assets/84c6f0a8-2fd4-4a12-8844-be1d0fd02009)

## 로컬 JSON 수집

S3 업로드와 AI API 호출 없이 네이버 업체 데이터를 JSON으로 저장합니다.

```bash
./collect.sh 강남구
```

지역명을 생략하면 실행 후 입력할 수 있습니다.

```bash
./collect.sh
```

기본적으로 최대 5개 업체를 수집하며, 두 번째 인자로 건수를 바꿀 수 있습니다.

```bash
./collect.sh 서초구 10
```

결과는 `output/{지역명}.json`에 저장됩니다.

### 사전 준비

Python 3.12 기준입니다.

```bash
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt
```
