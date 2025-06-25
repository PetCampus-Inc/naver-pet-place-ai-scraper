import os
import json
from typing import List
from openai import OpenAI


api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def batch_api(jsonl_path: str):
    batch_input_file = client.files.create(
        file=open(jsonl_path, "rb"),
        purpose="batch",
    )

    batch_input_file_id = batch_input_file.id
    response = client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={"description": "data analysis job"},
    )

    return response

def make_batch_option(request_id: str, system_messages: List[str], user_messages: List[dict]) -> dict:
    _system_messages = [{"role": "system", "content": message} for message in system_messages]
    
    # user_messages 구조 수정
    user_content = []
    for message in user_messages:
        if message["type"] == "text":
            user_content.append({
                "type": "text", 
                "text": message["text"]
            })
        elif message["type"] == "image_url":
            user_content.append({
                "type": "image_url",
                "image_url": message["image_url"]
            })
    
    _user_messages = [{"role": "user", "content": user_content}]
    messages = _system_messages + _user_messages

    return {
        "custom_id": str(request_id),
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "gpt-4.1",
            "max_tokens": 10000,
            "messages": messages,
            "response_format": { "type": "json_object" }
        }
    }

def get_batch_result(batch_id: str) -> List[dict]:
    response = client.batches.retrieve(batch_id)
    file_response = client.files.content(response.output_file_id)

    content = file_response.content.decode('utf-8')
    lines = content.strip().split('\n')

    results = []
    for line in lines:
        if line.strip():
            data = json.loads(line)
            content = data['response']['body']['choices'][0]['message']['content']
            content = content.replace('```json\n', '').replace('```', '')
            content = json.loads(content)
            
            results.append({
                "id": data['custom_id'],
                "content": content
            })

    return results

def get_batch_status(batch_id: str) -> str:
    response = client.batches.retrieve(batch_id)
    return response.status

def cancel_batch(batch_id: str):
    client.batches.cancel(batch_id)