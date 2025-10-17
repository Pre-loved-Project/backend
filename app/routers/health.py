# app/routers/health.py
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])

@router.get("/health")
async def health():
    return {"status": "ok"}
