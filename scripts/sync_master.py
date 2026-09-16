"""지역별 결과 파일을 마스터 4개 파일에 병합(갱신/추가/제거).

AI/S3 호출 없음 — 이미 만들어진 {location}_*.json 파일들을
output/info_new.json, avg_price_per_time.json, price_and_product.json,
product_pricing.json에 합치기만 하는 순수 파일 연산.

병합 규칙:
    1. info_new.json의 address에서 정규식으로 구를 파싱해, 마스터 파일 중
       "이 구 소속"인 place_id 집합을 구한다.
    2. 그 집합에 속하는 마스터 행은 전부 제거한 뒤, 지역 파일의 최신 행을
       그대로 추가한다.
       → 지역 파일에 있으면 최신 내용으로 갱신, 없던 id면 추가, 마스터에만
         있고 지역 파일엔 없으면 자동으로 제거됨 (한 번의 연산으로 3가지 다 처리).
    3. 다른 구 소속 행(주소가 다른 구인 것)은 "이 구 소속 집합"에 안 들어가서
       건드리지 않음.

마스터 파일은 덮어쓰기 전에 <파일명>.bak으로 백업한다.

어느 구를 언제 동기화했는지는 output/_sync_status.json에 기록된다
(사람이 봐도 되고, `--status`로 표로도 볼 수 있음).

사용법:
    python scripts/sync_master.py 관악구 [--output-dir output]
    python scripts/sync_master.py --status [--output-dir output]   # 동기화 이력만 조회
"""
import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

SYNC_STATUS_FILENAME = "_sync_status.json"

DISTRICT_PATTERN = re.compile(r"([가-힣]+구)\b")

# {마스터 파일명(확장자 제외): 병합 키}
FILES = {
    "info_new": "id",
    "avg_price_per_time": "kindergarten_id",
    "price_and_product": "kindergarten_id",
    "product_pricing": "id",
}


def load_json(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def parse_district(address: str):
    if not address:
        return None
    match = DISTRICT_PATTERN.search(address)
    return match.group(1) if match else None


def load_sync_status(output_dir: Path):
    path = output_dir / SYNC_STATUS_FILENAME
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_sync_status(output_dir: Path, status: dict):
    with (output_dir / SYNC_STATUS_FILENAME).open("w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2, sort_keys=True)


def print_status(output_dir: Path):
    status = load_sync_status(output_dir)
    if not status:
        print("동기화 이력이 없습니다.")
        return
    print(f"{'구':<8} {'마지막 동기화':<21} {'총 건수':>6} {'갱신':>5} {'추가':>5} {'제거':>5}")
    for location, info in sorted(status.items()):
        print(
            f"{location:<8} {info['synced_at']:<21} {info['total']:>6} "
            f"{info['updated']:>5} {info['added']:>5} {info['removed']:>5}"
        )


def sync_location(location: str, output_dir: Path):
    district_info_path = output_dir / f"{location}_info_new.json"
    district_info = load_json(district_info_path)
    if not district_info:
        raise SystemExit(f"{district_info_path}가 없거나 비어있습니다. 먼저 main.py로 만들어주세요.")

    for name in FILES:
        district_path = output_dir / f"{location}_{name}.json"
        if not district_path.exists():
            raise SystemExit(f"{district_path}가 없습니다. 4개 파일이 다 있어야 병합할 수 있습니다.")

    master_info = load_json(output_dir / "info_new.json")
    district_ids_in_master = {
        r["id"] for r in master_info if parse_district(r.get("address")) == location
    }
    fresh_ids = {r["id"] for r in district_info}

    removed_ids = district_ids_in_master - fresh_ids
    updated_ids = district_ids_in_master & fresh_ids
    added_ids = fresh_ids - district_ids_in_master

    old_names = {r["id"]: r.get("name") for r in master_info}
    fresh_names = {r["id"]: r.get("name") for r in district_info}

    print(f"[{location}] 갱신 {len(updated_ids)}건 / 추가 {len(added_ids)}건 / 제거 {len(removed_ids)}건")
    if added_ids:
        print("  추가된 곳:")
        for pid in added_ids:
            print(f"    {pid} {fresh_names.get(pid)}")
    if removed_ids:
        print("  제거된 곳:")
        for pid in removed_ids:
            print(f"    {pid} {old_names.get(pid)}")

    for name, key in FILES.items():
        master_path = output_dir / f"{name}.json"
        district_path = output_dir / f"{location}_{name}.json"

        master_data = load_json(master_path)
        district_data = load_json(district_path)

        kept = [row for row in master_data if row.get(key) not in district_ids_in_master]
        merged = kept + district_data

        if master_path.exists():
            shutil.copy2(master_path, master_path.with_suffix(".json.bak"))
        save_json(master_path, merged)
        print(f"  {master_path.name}: {len(master_data)} -> {len(merged)}건 (백업: {master_path.name}.bak)")

    status = load_sync_status(output_dir)
    status[location] = {
        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total": len(fresh_ids),
        "updated": len(updated_ids),
        "added": len(added_ids),
        "removed": len(removed_ids),
        "added_list": [{"id": pid, "name": fresh_names.get(pid)} for pid in sorted(added_ids)],
        "removed_list": [{"id": pid, "name": old_names.get(pid)} for pid in sorted(removed_ids)],
    }
    save_sync_status(output_dir, status)
    print(f"  동기화 이력 기록됨: {output_dir / SYNC_STATUS_FILENAME}")

    return {"updated": updated_ids, "added": added_ids, "removed": removed_ids}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="지역별 결과를 마스터 4개 파일에 병합")
    parser.add_argument("location", nargs="?", help="병합할 지역명 (예: 관악구)")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--status", action="store_true", help="동기화 이력만 표로 조회하고 종료")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    if args.status:
        print_status(output_dir)
    elif args.location:
        sync_location(args.location, output_dir)
    else:
        parser.error("location을 지정하거나 --status를 사용하세요.")
