from azure.storage.blob import BlobServiceClient, ContentSettings
from fastapi import UploadFile, HTTPException
import uuid
import os
from dotenv import load_dotenv


#환경 변수 불러오기
load_dotenv()

AZURE_CONNECTION_STRING = os.getenv("AZURE_STOARGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "uploads")

print(AZURE_CONNECTION_STRING)
print(CONTAINER_NAME)

#Blob service client load
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

def upload_to_azure(image: UploadFile) -> str:
    """
    이미지를 Azure Blob Storage에 저장하고 저장된 이미지에 접근할 수 있는 url을 반환합니다.
    """
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일을 선택해주세요.")

    try:
        #파일 확장자 및 이름 설정
        extension = image.filename.split(".")[-1]
        blob_name = f"profile_{uuid.uuid4()}.{extension}"

        #Blob 업로드
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(
            image.file,
            overwrite=True,
            content_settings=ContentSettings(content_type=image.content_type)
        )

        image_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}"
        return image_url
    except Exception as e:
        return HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")