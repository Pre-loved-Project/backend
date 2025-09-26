# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.db import get_db
from app.models.user import User
from app.schemas.auth import (
    SignupIn,
    UserOut,
    EmailUsedOut,
    UsernameUsedOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/email/used", response_model=EmailUsedOut)
def email_used(
    email: str = Query(..., description="중복 확인할 이메일"),
    db: Session = Depends(get_db),
):
    used = db.query(User.userId).filter(User.email == email).first() is not None
    return {"isEmailUsed": used}


@router.get("/username/used", response_model=UsernameUsedOut)
def username_used(
    userName: str = Query(..., description="중복 확인할 닉네임"),
    db: Session = Depends(get_db),
):
    used = db.query(User.userId).filter(User.nickname == userName).first() is not None
    return {"isUserNameUsed": used}


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    # 이메일 중복 검사
    if db.query(User.userId).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="email_conflict")

    # 닉네임 중복 검사
    if db.query(User.userId).filter(User.nickname == payload.user_name).first():
        raise HTTPException(status_code=400, detail="nickname_conflict")

    # birthDate 문자열 → date 객체로 변환
    try:
        bd_date = datetime.strptime(payload.birth_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_birthDate_format")

    # 사용자 생성
    u = User(
        email=payload.email,
        password_hash=payload.password_hash_input,  # 클라에서 전달한 해시 그대로 저장 (명세 준수)
        nickname=payload.user_name,
        birth_date=bd_date,
    )

    db.add(u)
    db.commit()
    db.refresh(u)

    # 응답 직렬화 (명세 키)
    return {
        "userId": u.userId,
        "email": u.email,
        "nickname": u.nickname,
        "birthDate": u.birth_date.strftime("%Y-%m-%d"),
        "createdAt": u.created_at,
        "updatedAt": u.updated_at,
    }
