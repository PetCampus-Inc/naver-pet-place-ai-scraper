import io
import os
import requests
import concurrent.futures

from PIL import Image
from contextlib import closing
from typing import Optional, List, Tuple, Iterator

from lib.logger import get_logger


logger = get_logger()

class ImageOptimizer:
    """
    이미지 크기를 조정하고, 품질을 최적화하여 저장합니다.

    Args:
        max_dimension: 최대 치수
        quality: 품질
        optimize: 최적화 여부
        lossless: 무손실 여부
        image_name: 이미지 이름
        output_dir: 이미지가 저장 될 디렉토리
    """
    def __init__(
            self, 
            max_dimension: int = 1024, 
            quality: int = 95, 
            optimize: bool = True, 
            lossless: bool = False, 
            image_name: str = "image",
            output_dir: str = "images"
        ):
        self.max_dimension = max_dimension
        self.quality = quality
        self.optimize = optimize
        self.lossless = lossless
        self.output_dir = output_dir
        self.image_name = image_name
        
    def _generate_image_paths(
        self,
        image_urls: List[str],
        extension: str = "webp"
    ) -> List[Tuple[str, str]]:
        """
        이미지 URL 목록에 대해 순차적으로 번호가 매겨진 출력 경로를 생성합니다.
        
        Args:
            image_urls: 이미지 URL 목록
            extension: 파일 확장자 (점 없이)
            
        Returns:
            (이미지 URL, 출력 경로) 튜플의 리스트
        """
        return [
            (url, os.path.join(self.output_dir, f"{self.image_name}_{i}.{extension}"))
            for i, url in enumerate(image_urls, start=1)
        ]

    def _download_image(self, image_url: str) -> Optional[bytes]:
        """이미지 URL에서 바이너리 데이터를 다운로드합니다."""
        try:
            with closing(requests.get(image_url, stream=True, timeout=10)) as response:
                response.raise_for_status()
                return response.content
        except requests.RequestException as e:
            logger.error(f"이미지 다운로드 실패: {image_url}, 오류: {str(e)}")
            return None

    def _resize_image(self, img: Image.Image) -> Image.Image:
        """이미지 크기를 최대 치수에 맞게 조정합니다."""
        width, height = img.size
        
        # 원본 이미지가 이미 충분히 작으면 크기 조정 안 함
        if max(width, height) <= self.max_dimension:
            return img
            
        # 종횡비를 유지하며 가장 긴 변을 max_dimension에 맞춤
        ratio = self.max_dimension / max(width, height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _save_image(self, img: Image.Image, output_path: str) -> bool:
        """최적화된 이미지를 저장합니다."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            img.save(
                output_path,
                format="WEBP",
                quality=self.quality,
                optimize=self.optimize,
                lossless=self.lossless,
                method=6
            )
            return True
        except Exception as e:
            logger.error(f"이미지 저장 실패 ({output_path}): {str(e)}")
            return False

    def save_optimized_image(self, image_url: str, output_path: str) -> Optional[str]:
        """
        이미지의 크기와 품질을 최적화 후 저장합니다.
        
        Args:
            image_url: 이미지 URL
            output_path: 출력 이미지 경로

        Returns:
            최적화된 이미지 경로 또는 오류 시 None
        """
        # image_data = self._download_image(image_url)
        # if not image_data:
        #     return None

        try:
            image_byte = requests.get(image_url).content
            with Image.open(io.BytesIO(image_byte)) as img:
                # 이미지 리사이징
                processed_img = self._resize_image(img)
                
                # 최적화된 이미지 저장
                if self._save_image(processed_img, output_path):
                    return output_path
                return None
        except Exception as e:
            logger.error(f"이미지 처리 중 오류 발생: {str(e)}")
            return None