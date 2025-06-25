import os
import json
import time
from typing import List

from utils.image_optimizer import ImageOptimizer
from utils.file import read_text_file, encode_base64_image
from lib.ai import get_service_prompt, get_batch_status, make_batch_option, batch_api, get_batch_result, cancel_batch
from lib.logger import get_logger


log = get_logger(__name__)

def request_batch_api(place_datas: List[dict]):
    batch_options = _create_batch_options(place_datas)
    file_name = f"batchinput.jsonl"
    _create_jsonl(batch_options, file_name)
    
    response = batch_api(file_name)
    batch_results = get_batch_api_response(response.id)

    os.remove(file_name)

    return batch_results

def request_batch_api_2(place_datas: List[dict], batch_count: int = 1):
    results = []
    
    # 전체 데이터를 batch_count 개의 배치로 나누기
    total_items = len(place_datas)
    items_per_batch = total_items // batch_count
    
    for i in range(batch_count):
        start_idx = i * items_per_batch
        # 마지막 배치는 남은 모든 데이터 포함
        end_idx = (i + 1) * items_per_batch if i < batch_count - 1 else total_items
        
        place_slice = place_datas[start_idx:end_idx]
        log.info(f"배치 {i + 1}/{batch_count} 처리 중... ({len(place_slice)}개 아이템)")
        
        # 배치 간 대기 시간
        if i > 0:
            log.info("이전 배치 토큰 해제 대기 중...")
            time.sleep(30)
        
        try:
            batch_options = _create_batch_options(place_slice)
            file_name = f"batchinput_{i}.jsonl"
            _create_jsonl(batch_options, file_name)
            
            response = batch_api(file_name)
            batch_results = get_batch_api_response(response.id)
            results.extend(batch_results)
            
            log.info(f"Batch API 요청 완료: {response.id}")
            
        except Exception as e:
            if "token_limit_exceeded" in str(e):
                log.warning(f"토큰 한계 초과, 60초 대기 후 재시도...")
                time.sleep(60)
                continue
            else:
                raise e
    
    return results

def get_batch_api_response(batch_id: str) -> List[dict]:
    batch_api_status_loop(batch_id)
    
    response = get_batch_result(batch_id)

    results = []
    for res in response:
        results.append({
            "id": int(res['id']),
            "categories": res['content']['categories'],
            "services": res['content']['services'],
            "menus": res['content']['menus']
        })

    return results

def batch_api_status_loop(batch_id: str):
    while True:
        status = get_batch_status(batch_id)
        log.info(f"Batch API 상태: {status}")

        if status == 'completed': break
        elif status == 'failed': raise Exception(f"Batch API 실패: {batch_id}")
        time.sleep(10)

def _create_batch_options(place_datas: List[dict]) -> List[dict]:
    service_text = read_text_file('data/service.txt')
    system_messages = [get_service_prompt(), service_text]

    batch_options = []
    for data in place_datas:
        contents = [{
            "type": "text",
            "metadata": { "name": "content.json" },
            "text": json.dumps(_parse_content(data), ensure_ascii=False, indent=4)
        }]

        output_path = f"temp/{data['id']}"
        image_paths = _save_optimized_images(image_urls=data['menu_image_urls'], output_path=output_path)

        for image_path in image_paths:
            file_extension, base64_image = encode_base64_image(image_path)
            contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{file_extension};base64,{base64_image}"
                }
            })

        batch_option = make_batch_option(
            request_id=data['id'],
            system_messages=system_messages,
            user_messages=contents,
        )

        batch_options.append(batch_option)
    
    return batch_options

def _parse_content(content: dict) -> dict:
    """LLM 요청에 필요한 데이터만 추출"""

    return {
        "name": content['name'],
        "business_hours": content['business_hours'],
        "menus": content['menus'],
        "description": content['description'],
        "keywords": content['keywords'],
        "conveniences": content['conveniences'],
        "parking": content['parking'],
        "valet_parking": content['valet_parking'],
        "page_content": content['page_content']
    }

def _create_jsonl(batch_options: List[dict], file_name: str):
    with open(file_name, 'w', encoding='utf-8') as f:
        for batch_option in batch_options:
            f.write(json.dumps(batch_option, ensure_ascii=False) + '\n')

def _save_optimized_images(image_urls: List[str], output_path: str) -> List[str]:
    image_optimizer = ImageOptimizer()

    paths = []
    for i,url in enumerate(image_urls):
        file_path = f"{output_path}/{i}.webp"
        image_optimizer.save_optimized_image(url, file_path)
        paths.append(file_path)

    return paths