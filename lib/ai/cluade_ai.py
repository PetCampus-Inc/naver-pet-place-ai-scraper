import os

from anthropic import Anthropic
from lib.ai.prompt import get_prompt
from utils.file import read_text_file, encode_base64_image


api_key = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key)

def query_claude(model="claude-sonnet-4-20250514", image_paths=None, text_path=None, json_data=None):
    messages = []

    system_prompt = get_prompt()

    if image_paths:
        for image_path in image_paths:
            file_extension, base64_image = encode_base64_image(image_path)
            messages.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": f"image/{file_extension}",
                    "data": base64_image
                }
            })

    # JSON 파일 추가
    if json_data:
        messages.append({
            "type": "text",
            "text": f"content.json:\n{json_data}"
        })

    # 텍스트 파일 내용 추가
    if text_path:
        text_content = read_text_file(text_path)
        messages.append({
            "type": "text", 
            "text": f"service.txt:\n{text_content}"
        })

    response = client.messages.create(
        model=model,
        max_tokens=5000,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": messages}],
    )

    return response.content[0].text