# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from datetime import datetime
from jose import JWTError
from jose.exceptions import ExpiredSignatureError
from app.core.db import get_db
from app.models.user import User
from app.schemas.auth import SignupIn, UserOut, LoginIn, TokenOut
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    if db.query(User.userId).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="isEmailUsed")
    if db.query(User.userId).filter(User.nickname == payload.nickname).first():
        raise HTTPException(status_code=400, detail="isNicknameUsed")
    try:
        bd_date = datetime.strptime(payload.birth_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_birthDateFormat")
    u = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname,
        birth_date=bd_date,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return {
        "userId": u.userId,
        "email": u.email,
        "nickname": u.nickname,
        "birthDate": u.birth_date.strftime("%Y-%m-%d"),
        "createdAt": u.created_at,
        "updatedAt": u.updated_at,
    }

@router.post("/login", response_model=TokenOut, status_code=status.HTTP_200_OK)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    access = create_access_token(subject=user.userId)
    refresh = create_refresh_token(subject=user.userId)
    response.set_cookie(
        key="refreshToken",
        value=refresh,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
        path="/",
    )
    return {"accessToken": access}

@router.post("/refresh", response_model=TokenOut, status_code=status.HTTP_200_OK)
def refresh(request: Request):
    token = request.cookies.get("refreshToken")
    if not token:
        raise HTTPException(status_code=401, detail="no_refresh_token")
    try:
        payload = decode_refresh_token(token)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="invalid_token_payload")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="refresh_token_expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid_refresh_token")
    access = create_access_token(subject=sub)
    return {"accessToken": access}

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(request: Request, response: Response):
    token = request.cookies.get("refreshToken")
    if not token:
        raise HTTPException(status_code=401, detail="no_refresh_token")
    try:
        decode_refresh_token(token)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="refresh_token_expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid_refresh_token")
    response.delete_cookie(
        key="refreshToken",
        path="/",
    )
    return {"message": "로그아웃 성공"}
