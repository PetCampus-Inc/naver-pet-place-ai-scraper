import os
import requests
import boto3
import aiohttp
import asyncio

from typing import List, Dict, Optional, Union
from concurrent.futures import ThreadPoolExecutor
from lib.logger import get_logger

log = get_logger(__name__)

class S3ImageUploader:
    def __init__(self):
        access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        bucket_name = os.getenv("AWS_BUCKET_NAME")
        
        self.s3 = boto3.client("s3", aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)
        self.bucket = bucket_name
        
        MB = 1024 * 1024
        self.chunk = 100 * MB

    def _upload_content_to_s3(self, content: Union[bytes, any], key: str):
        """S3 multipart 업로드"""
        try:
            mpu = self.s3.create_multipart_upload(Bucket=self.bucket, Key=key)
            mpu_id = mpu["UploadId"]
            
            parts = []
            part_number = 1
            
            # content가 bytes인 경우와 iterator인 경우 처리
            if isinstance(content, bytes):
                for i in range(0, len(content), self.chunk):
                    chunk = content[i:i+self.chunk]
                    part = self.s3.upload_part(
                        Body=chunk, 
                        Bucket=self.bucket, 
                        Key=key, 
                        UploadId=mpu_id, 
                        PartNumber=part_number
                    )
                    parts.append({'PartNumber': part_number, 'ETag': part['ETag']})
                    part_number += 1
            else:
                # iterator (requests stream)
                for chunk in content:
                    if chunk:
                        part = self.s3.upload_part(
                            Body=chunk, 
                            Bucket=self.bucket, 
                            Key=key, 
                            UploadId=mpu_id, 
                            PartNumber=part_number
                        )
                        parts.append({'PartNumber': part_number, 'ETag': part['ETag']})
                        part_number += 1

            return self.s3.complete_multipart_upload(
                Bucket=self.bucket, 
                Key=key, 
                UploadId=mpu_id, 
                MultipartUpload={'Parts': parts}
            )
            
        except Exception as e:
            log.error(f"S3 업로드 실패 {key}: {e}")
            return None

    async def upload_image(self, url: str, key: str):
        """단일 이미지 업로드"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
                    if r.status != 200:
                        raise Exception("유효하지 않은 URL입니다.")
                    
                    content = await r.read()
                    
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, self._upload_content_to_s3, content, key)
        except Exception as e:
            log.error(f"이미지 업로드 실패 {url}: {e}")
            return None

    async def upload_multiple_images(self, image_data: List[Dict[str, str]], max_concurrent: int = 5) -> List[Optional[Dict]]:
        """다중 이미지 업로드 (동시성 제한)"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def upload_with_limit(item):
            async with semaphore:
                return await self.upload_image(item["url"], item["key"])
        
        tasks = [upload_with_limit(item) for item in image_data]
        return await asyncio.gather(*tasks)