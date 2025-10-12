from fastapi import APIRouter, UploadFile, File
from app.services.upload_to_azure import upload_to_azure

router = APIRouter(prefix="/api", tags=["image"])

@router.post("/image")
def upload_image(image: UploadFile = File(...)):
    image_url = upload_to_azure(image)
    return {"imageUrl" : image_url}