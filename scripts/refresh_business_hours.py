"""기존 JSON 파일의 business_hours 필드만 신규 파서로 재구축.

다른 필드(categories, services, menus, S3 키 등)는 보존.
Claude/S3 재호출 없이 m.place.naver.com 의 detail HTML만 다시 받음.
"""
import json
import re
import sys
import time
from pathlib import Path

import requests

from lib.scrapper.naver_place_parser import NaverPlaceParser


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
}
APOLLO_RE = re.compile(r"window\.__APOLLO_STATE__\s*=\s*({.*?});", re.DOTALL)


def fetch_business_hours(place_id: int):
    r = requests.get(f"https://m.place.naver.com/place/{place_id}/home", headers=HEADERS, timeout=15)
    r.encoding = "utf-8"
    m = APOLLO_RE.search(r.text)
    if not m:
        return None
    state = json.loads(m.group(1))
    parsed = NaverPlaceParser().parse(state)
    return parsed.get("business_hours")


def refresh(path: Path):
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n=== {path.name} ({len(data)}개) ===")
    for i, place in enumerate(data, 1):
        pid = place["id"]
        try:
            new_bh = fetch_business_hours(pid)
            if new_bh is None:
                print(f"  [{i:2d}] {place['name']} → ❌ Apollo 파싱 실패")
                continue
            place["business_hours"] = new_bh
            offdays = new_bh[0].get("offdays", []) if new_bh else []
            is_24h = new_bh[0].get("is_24h") if new_bh else False
            print(f"  [{i:2d}] {place['name']} → ✅ (24h={is_24h}, offdays={offdays})")
        except Exception as e:
            print(f"  [{i:2d}] {place['name']} → ❌ {e}")
        time.sleep(0.3)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"  저장 완료: {path}")


if __name__ == "__main__":
    targets = sys.argv[1:] or ["용인시 처인구.json", "목포시.json"]
    for t in targets:
        p = Path(t)
        if p.exists():
            refresh(p)
        else:
            print(f"건너뜀 (없음): {t}")
