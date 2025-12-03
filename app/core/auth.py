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
    """
    Authorization 헤더가 없으면 None 반환.
    Authorization 헤더가 있지만 invalid/expired 하면 401 발생.
    유효하면 User 객체 반환.
    """

    # 1) 헤더 자체가 없으면 완전 anonymous
    if creds is None:
        return None

    # 2) Bearer 스킴 검증
    if (creds.scheme or "").lower() != "bearer":
        # Bearer인데 토큰이 invalid인 것은 아니므로 None 반환
        return None

    token = creds.credentials

    # 3) 토큰이 있는데 invalid → 이때는 401 내줘야 함
    try:
        payload = jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=[settings.JWT_ALG])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="INVALID_TOKEN")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="TOKEN_EXPIRED")
    except JWTError:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")

    # 4) DB 조회
    user = db.query(User).filter(User.user_id == int(sub)).first()

    if not user:
        raise HTTPException(status_code=401, detail="USER_NOT_FOUND")

    return user


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
