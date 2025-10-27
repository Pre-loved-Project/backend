from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.user import User

from typing import Optional

print("### IMPORT auth.py OK")

bearer = HTTPBearer(auto_error=False)


def _user_pk_col():
    """✅ User 모델의 PK 컬럼 자동 탐색 (user_id → userId → id 순서)"""
    if hasattr(User, "user_id"):
        return User.user_id
    elif hasattr(User, "userId"):
        return User.userId
    elif hasattr(User, "id"):
        return User.id
    else:
        raise AttributeError("User 모델에 PK 컬럼(user_id, userId, id)이 없습니다.")

def get_current_user_optional(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """토큰이 없거나, 유효하지 않으면 None을 반환 (401 내지 않음)."""
    if not creds or (creds.scheme or "").lower() != "bearer":
        return None

    token = creds.credentials
    try:
        payload = jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=[settings.JWT_ALG])
        sub = payload.get("sub")
        if not sub:
            return None
    except (ExpiredSignatureError, JWTError):
        return None

    pk_col = _user_pk_col()
    return db.query(User).filter(pk_col == int(sub)).first()

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """JWT 토큰 인증 후 현재 사용자 객체 반환"""
    if not creds or (creds.scheme or "").lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = creds.credentials
    try:
        # ✅ ACCESS 토큰 검증
        payload = jwt.decode(
            token, settings.JWT_ACCESS_SECRET, algorithms=[settings.JWT_ALG]
        )
        sub = payload.get("sub")
        if not sub:
            raise JWTError("missing sub")
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ✅ user_id 기준으로 사용자 조회
    pk_col = _user_pk_col()
    user = db.query(User).filter(pk_col == int(sub)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
