from fastapi import APIRouter, File, UploadFile, HTTPException
from app.services.ai import predict_image
from app.core.auth import get_current_user

router = APIRouter(prefix="/api", tags=["ai"])

@router.post("/predict")
async def predict(file: UploadFile = File(...)):
    content = await file.read()
    try:
        result = predict_image(content)
    except Exception:
        raise HTTPException(status_code=400, detail="INVALID_IMAGE")
    return result
