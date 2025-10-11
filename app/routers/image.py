from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
import boto3
from botocore.exceptions import NoCredentialsError
from app.core.config import settings
from uuid import uuid4

router = APIRouter(prefix="/api", tags=["image"])

@router.post("/image")
async def upload_image(image: UploadFile = File(...)):
    try:
        # AWS S3 클라이언트 생성
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name="ap-northeast-2"
        )

        # 파일명 고유화
        file_extension = image.filename.split(".")[-1]
        unique_name = f"uploads/{uuid4().hex}.{file_extension}"

        # S3 업로드
        s3.upload_fileobj(
            image.file,
            settings.AWS_S3_BUCKET_NAME,
            unique_name,
            ExtraArgs={"ContentType": image.content_type}
        )

        image_url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{unique_name}"
        return {"imageUrl": image_url}

    except NoCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AWS credentials not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
