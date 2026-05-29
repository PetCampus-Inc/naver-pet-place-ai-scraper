import os
import json
from typing import List
from anthropic import Anthropic

from lib.logger import get_logger

log = get_logger(__name__)

api_key = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key)

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 10000


def batch_api(requests: List[dict]):
    return client.messages.batches.create(requests=requests)


def make_batch_option(request_id, system_messages: List[str], user_messages: List[dict]) -> dict:
    system = [{"type": "text", "text": msg} for msg in system_messages]

    user_content = []
    for message in user_messages:
        if message["type"] == "text":
            user_content.append({"type": "text", "text": message["text"]})
        elif message["type"] == "image":
            user_content.append(message)

    return {
        "custom_id": str(request_id),
        "params": {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": user_content}],
        },
    }


def get_batch_status(batch_id: str) -> str:
    response = client.messages.batches.retrieve(batch_id)
    return response.processing_status


def get_batch_result(batch_id: str) -> List[dict]:
    results = []
    for entry in client.messages.batches.results(batch_id):
        if entry.result.type != "succeeded":
            log.warning(f"Batch entry 실패 (custom_id={entry.custom_id}, type={entry.result.type})")
            continue

        text = entry.result.message.content[0].text
        text = text.replace("```json\n", "").replace("```", "").strip()

        try:
            content = json.loads(text)
        except json.JSONDecodeError as e:
            log.error(f"JSON 파싱 실패 (custom_id={entry.custom_id}): {e}")
            continue

        results.append({"id": entry.custom_id, "content": content})

    return results


def cancel_batch(batch_id: str):
    client.messages.batches.cancel(batch_id)
