# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.user import User
from app.schemas.user import UserResp, EmailCheckResp

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserResp)
def get_user(user_id: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.userId == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="not_found")
    return {
        "userId": u.userId,
        "email": u.email,
        "nickname": u.nickname,
        "birthDate": u.birth_date,
        "createdAt": u.created_at,
        "updatedAt": u.updated_at,
    }
