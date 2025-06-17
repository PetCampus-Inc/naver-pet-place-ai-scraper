import os

from openai import OpenAI
from lib.ai.prompt import get_prompt
from utils.file import encode_base64_image, read_text_file


api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def query_gpt(model="gpt-4.1", image_paths=None, text_path=None, json_path=None):
    """GPT-4.1에 프롬프트, 이미지, 텍스트 파일 전송"""
    messages = []

    system_prompt = get_prompt()
    messages.append({ "role": "system", "content": system_prompt })
    
    user_content = []

    # 이미지 파일 추가
    if image_paths:
        for image_path in image_paths:
            file_extension, base64_image = encode_base64_image(image_path)
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{file_extension};base64,{base64_image}"
                }
            })

    # JSON 파일 추가
    if json_path:
        json_content = read_text_file(json_path)
        user_content.append({
            "type": "text",
            "metadata": { "name": "content.json" },
            "text": json_content
        })

    # 텍스트 파일 내용 추가
    if text_path:
        text_content = read_text_file(text_path)
        user_content.append({
            "type": "text", 
            "metadata": { "name": "service.txt" },
            "text": text_content
        })

    messages.append({ "role": "user", "content": user_content })

    # API 호출
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=4000,
        temperature=0,
        response_format={ "type": "json_object" }
    )

    return response.choices[0].message.content
