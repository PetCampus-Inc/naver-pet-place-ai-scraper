import os
import requests
import boto3

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

    def upload_image(self, url: str, key: str):
        try:
            with requests.get(url, stream=True) as r:
                if not r.ok: raise Exception("유효하지 않은 URL입니다.")

                mpu = self.s3.create_multipart_upload(Bucket=self.bucket, Key=key)
                mpu_id = mpu["UploadId"]
                
                parts = []
                for i, chunk in enumerate(r.iter_content(chunk_size=self.chunk), start=1):
                    part = self.s3.upload_part(
                            Body=chunk, 
                            Bucket=self.bucket, 
                            Key=key, 
                            UploadId=mpu_id, 
                            PartNumber=i
                        )
                    part_dict = {'PartNumber': i, 'ETag': part['ETag']}
                    parts.append(part_dict)

                result = self.s3.complete_multipart_upload(
                            Bucket=self.bucket, 
                            Key=key, 
                            UploadId=mpu_id, 
                            MultipartUpload={'Parts': parts}
                        )
                
                return result

        except Exception as e:
            log.error(f"S3 이미지 업로드 실패: {e}")
            return None
