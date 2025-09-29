#app/routers/auth.py
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
    LoginIn,
    LoginOut,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── 이메일 중복 확인 ─────────────────────────────────────────────
@router.get("/email/used", response_model=EmailUsedOut)
def email_used(
    email: str = Query(..., description="중복 확인할 이메일"),
    db: Session = Depends(get_db),
):
    used = db.query(User.userId).filter(User.email == email).first() is not None
    return {"isEmailUsed": used}


# ── 닉네임 중복 확인 ─────────────────────────────────────────────
@router.get("/username/used", response_model=UsernameUsedOut)
def username_used(
    userName: str = Query(..., description="중복 확인할 닉네임"),
    db: Session = Depends(get_db),
):
    used = db.query(User.userId).filter(User.nickname == userName).first() is not None
    return {"isUserNameUsed": used}


# ── 회원가입 ─────────────────────────────────────────────────────
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
        password_hash=payload.password_hash_input,  # 클라에서 해싱한 값 그대로 저장
        nickname=payload.user_name,
        birth_date=bd_date,
    )

    db.add(u)
    db.commit()
    db.refresh(u)

    # 응답 직렬화
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
    - username 은 이메일을 아이디로 사용
    - passwordHash 는 클라에서 해싱해 보낸 문자열 (서버 비교만 수행)
    """
    user = db.query(User).filter(User.email == payload.username).first()
    if not user or user.password_hash != payload.password_hash_input:
        raise HTTPException(status_code=401, detail="invalid_credentials")

    access = create_access_token(subject=user.userId)
    refresh = create_refresh_token(subject=user.userId)

    return {"accessToken": access, "refreshToken": refresh}
