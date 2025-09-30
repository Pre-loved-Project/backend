from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.db import get_db
from app.models.user import User
from app.schemas.auth import (
    SignupIn,
    UserOut,
    LoginIn,
    LoginOut,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── 회원가입 ─────────────────────────────────────────────────────
@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    # 중복 검사: 이메일
    if db.query(User.userId).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="isEmailUsed")

    # 중복 검사: 닉네임(userName)
    if db.query(User.userId).filter(User.nickname == payload.user_name).first():
        raise HTTPException(status_code=400, detail="isNicknameUsed")

    # birthDate 문자열 → date 객체 변환
    try:
        bd_date = datetime.strptime(payload.birth_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_birthDateFormat")

    # 프론트 해시 → 서버 Argon2 재해싱 저장
    u = User(
        email=payload.email,
        password_hash=hash_password(payload.password_hash_input),
        nickname=payload.user_name,
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


# ── 로그인 ───────────────────────────────────────────────────────
@router.post("/login", response_model=LoginOut, status_code=status.HTTP_200_OK)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """
    명세: username + passwordHash
    - username: 이메일
    - passwordHash: 프론트에서 해싱한 문자열
    - DB에는 Argon2 해시가 저장되어 있으므로 verify_password 사용
    """
    user = db.query(User).filter(User.email == payload.username).first()

    if not user or not verify_password(payload.password_hash_input, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")

    access = create_access_token(subject=user.userId)
    refresh = create_refresh_token(subject=user.userId)

    return {"accessToken": access, "refreshToken": refresh}
