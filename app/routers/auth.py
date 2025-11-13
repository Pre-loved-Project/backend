from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from jose import JWTError
from jose.exceptions import ExpiredSignatureError
from datetime import date

from app.core.db import get_db
from app.models.user import User
from app.schemas.auth import SignupIn, UserOut, LoginIn, TokenOut
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    decode_access_token,  # accessToken 검증 함수 추가
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    # 이메일/닉네임 중복 체크는 그대로

    # ✅ birth_date가 str로 오든 date로 오든 모두 안전하게 처리
    bdate = payload.birth_date
    if isinstance(bdate, str):
        try:
            bdate = date.fromisoformat(bdate)   # "YYYY-MM-DD"만 허용
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid_birthDateFormat")

    u = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname,
        birth_date=bdate,     # ← date 객체로 넣기
    )
    db.add(u)
    db.commit()
    db.refresh(u)

    return {
        "userId": u.user_id,
        "email": u.email,
        "nickname": u.nickname,
        "birthDate": u.birth_date.strftime("%Y-%m-%d") if u.birth_date else None,
        "createdAt": u.created_at,
        "updatedAt": u.updated_at,
    }


@router.post("/login", response_model=TokenOut, status_code=status.HTTP_200_OK)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")

    uid = str(user.user_id)

    access = create_access_token(sub=uid)
    refresh = create_refresh_token(sub=uid)
    
    response.set_cookie(
        key="accessToken",
        value=access,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=15 * 60,
        path="/",
    )

    response.set_cookie(
        key="refreshToken",
        value=refresh,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=30 * 24 * 60 * 60,
        path="/",
    )

    return {"accessToken": access}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="accessToken", httponly=True, secure=True, samesite="none", path="/")
    response.delete_cookie(key="refreshToken", httponly=True, secure=True, samesite="none", path="/")
    return {"message": "로그아웃 성공"}
