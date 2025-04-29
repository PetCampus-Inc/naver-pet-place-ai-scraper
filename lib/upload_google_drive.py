import requests
import io

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from httplib2 import Http
from oauth2client import file, client, tools
from logger import get_logger

log = get_logger()

class UploadGoogleDrive:
    def __init__(self):
        self.credential_file = 'token.json'
        self.folder_id = '1o72Csal-45lJIABVg5374Ha88jF1LH9o'
        pass

    # 이미지 타입 추출
    def _get_image_mimetype(self, file_name: str) -> str:
        if file_name.endswith('.png'):
            return 'image/png'
        if file_name.endswith('.jpeg') or file_name.endswith('.jpg'):
            return 'image/jpeg'
        if file_name.endswith('.webp'):
            return 'image/webp'
        return 'image/png'
    
    # 구글 드라이브 API 인증
    def _google_api_auth(self):
        SCOPES = 'https://www.googleapis.com/auth/drive.file'
        store = file.Storage('storage.json')    # 토큰 저장 파일
        creds = store.get()

        # 토큰이 만료되었을 경우 새로 발급
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(self.credential_file, SCOPES)
            creds = tools.run_flow(flow, store)

        return build('drive', 'v3', http=creds.authorize(Http()))

    # 이미지 업로드
    def upload_image(self, file_name: str, image_url: str) -> str | None:
        try:
            drive = self._google_api_auth()

            # URL에서 데이터 스트리밍
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            
            # 데이터를 메모리 버퍼에 로드
            file_data = io.BytesIO(response.content)
            
            # 이미지 타입 추출 및 이름
            image_mimetype = self._get_image_mimetype(image_url)
            image_name = f"{file_name}.{image_mimetype.split('/')[-1]}"

            # 파일 업로드를 위한 MediaIoBaseUpload 객체 생성
            media = MediaIoBaseUpload(file_data, mimetype=image_mimetype, resumable=True)

            # 파일 업로드 요청 바디 생성
            request_body = {
                'name': image_name, 
                'parents': [self.folder_id]
            }

            # 파일 업로드 요청
            res = drive.files().create(
                body=request_body,
                media_body=media,
                fields='id,webViewLink'
            ).execute()

            if res: return res.get('webViewLink')
            return None
        except Exception as e:
            log.error(f"이미지 업로드 중 오류 발생: {e}")
            return None