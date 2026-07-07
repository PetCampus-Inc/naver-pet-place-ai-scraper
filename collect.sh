#!/bin/sh

set -eu

cd "$(dirname "$0")"

location="${1:-}"
limit="${2:-5}"

if [ -z "$location" ]; then
    printf '수집할 지역의 구 이름을 입력하세요 (예: 강남구, 서초구): '
    read -r location
fi

if [ -z "$location" ]; then
    echo '지역명은 빈 값일 수 없습니다.'
    exit 1
fi

case "$limit" in
    ''|*[!0-9]*|0)
        echo '수집 건수는 1 이상의 숫자여야 합니다.'
        exit 1
        ;;
esac

if [ ! -x "venv/bin/python" ]; then
    echo 'Python 가상환경을 찾을 수 없습니다. 먼저 설치 안내를 확인하세요.'
    exit 1
fi

echo "'$location' 지역에서 최대 ${limit}개 업체를 수집합니다."
echo 'S3 업로드와 AI API 호출은 수행하지 않습니다.'

venv/bin/python main.py \
    --collection-only \
    --location "$location" \
    --limit "$limit" \
    --output-dir output

echo "수집 완료: output/${location}.json"
