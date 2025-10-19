from fastapi import APIRouter, UploadFile, File
from app.services.upload_to_azure import upload_to_azure

router = APIRouter(prefix="/api", tags=["image"])

@router.post("/image")
async def upload_image(image: UploadFile = File(...)):
    if not image.filename:
        return {"error": "File name is missing."}, 400

    blob_name = image.filename

    contents = await image.read()

    image_url = upload_to_azure(data=contents, blob_name=blob_name, content_type=image.content_type)

    return {"imageUrl" : image_url}