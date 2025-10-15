# app/services/upload_to_azure.py
from typing import Optional
from azure.storage.blob import BlobServiceClient, ContentSettings
from app.core.config import settings

# .env 값은 Settings가 이미 로드함
CONN = settings.AZURE_STORAGE_CONNECTION_STRING
CONTAINER = settings.AZURE_CONTAINER_NAME

# 방어적으로 체크
if not CONN:
    raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is missing")
if not CONTAINER:
    raise RuntimeError("AZURE_CONTAINER_NAME is missing (Blob 컨테이너 이름을 넣어야 함)")

# 클라이언트 준비
blob_service_client = BlobServiceClient.from_connection_string(CONN)

# (선택) 컨테이너 자동 생성
try:
    blob_service_client.create_container(CONTAINER)
except Exception:
    pass  # 이미 있으면 스킵

def upload_to_azure(data: bytes, blob_name: str, content_type: Optional[str] = None) -> str:
    """바이트 데이터를 주어진 blob 이름으로 업로드하고 URL을 반환."""
    blob_client = blob_service_client.get_blob_client(container=CONTAINER, blob=blob_name)
    content_settings = ContentSettings(content_type=content_type) if content_type else None
    blob_client.upload_blob(data, overwrite=True, content_settings=content_settings)
    return blob_client.url
