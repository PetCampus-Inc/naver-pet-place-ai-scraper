FROM python:3.11-slim

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 출력 디렉토리 생성
RUN mkdir -p /app/output

# 필요한 파일들 복사
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 모든 소스 코드 복사
COPY . .

# 환경 변수 설정
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 컨테이너가 시작될 때 실행할 명령어
CMD ["python", "main.py"]