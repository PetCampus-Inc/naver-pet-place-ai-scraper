import os
import base64


# 이미지 파일을 base64로 인코딩
def encode_base64_image(image_path):
    """이미지 파일을 base64로 인코딩"""
    with open(image_path, "rb") as image_file:
        file_extension = os.path.splitext(image_path)[1][1:]
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        return file_extension, base64_image

# 텍스트 파일 내용 읽기
def read_text_file(text_path):
    """텍스트 파일 내용 읽기"""
    with open(text_path, "r", encoding="utf-8") as text_file:
        return text_file.read()