from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.db import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserOut,
    UserUpdateIn,
    UserDeleteOut,
)

router = APIRouter(prefix="/users", tags=["users"])


# ── 유저 정보 조회 ─────────────────────────────────────────────
@router.get("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ── 유저 정보 수정 ─────────────────────────────────────────────
@router.put("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
def update_me(
    payload: UserUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 닉네임 변경
    if payload.nickname is not None:
        current_user.nickname = payload.nickname

    # 생년월일 변경
    if payload.birth_date is not None:
        current_user.birth_date = payload.birth_date

    # 비밀번호 변경 (프론트 해시 → 서버 Argon2)
    if payload.password_hash_input is not None:
        from app.core.security import hash_password
        current_user.password_hash = hash_password(payload.password_hash_input)

    current_user.updated_at = datetime.utcnow()
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user


# ── 유저 정보 삭제 ─────────────────────────────────────────────
@router.delete("/me", response_model=UserDeleteOut, status_code=status.HTTP_200_OK)
def delete_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.userId

    # 유저 삭제
    db.delete(current_user)
    db.commit()

    return {"userId": user_id}
