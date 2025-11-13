from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.user import User

from typing import Optional

from app.core.security import (
    create_access_token,
    decode_refresh_token,
)


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

def get_current_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    access = request.cookies.get("accessToken")
    refresh = request.cookies.get("refreshToken")
    # ------------------------------
    # 1) accessToken 검증
    # ------------------------------

    if access:
        try:
            payload = jwt.decode(
                access, settings.JWT_ACCESS_SECRET, algorithms=[settings.JWT_ALG]
            )
            sub = payload.get("sub")
            if not sub:
                raise JWTError("missing sub")
            
            # ✅ user_id 기준으로 사용자 조회
            pk_col = _user_pk_col()
            user = db.query(User).filter(pk_col == int(sub)).first()
            if user:
                return user
        except ExpiredSignatureError:
            pass #refresh 검증 로직으로 전환
        except JWTError:
            pass #refresh 검증 로직으로 전환

    # ------------------------------
    # 2) refreshToken 검증
    # ------------------------------
    if not refresh:
        raise HTTPException(status_code=401, detail="not_authenticated")
    
    try:
        payload = decode_refresh_token(refresh)
        sub = payload.get("sub")
        if not sub:
            raise JWTError("missing_sub")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="refresh_expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid_refresh_token")

    # ------------------------------
    # 3) refresh 통과 → accessToken 재발급
    # ------------------------------
    new_access = create_access_token(sub=sub)

    response.set_cookie(
        key="accessToken",
        value=new_access,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=15 * 60,
        path="/",
    )

    # ------------------------------
    # 4) user 조회 후 반환
    # ------------------------------
    pk_col = _user_pk_col()
    user = db.query(User).filter(pk_col == int(sub)).first()

    if not user:
        raise HTTPException(status_code=401, detail="invalid_token")

    return user

def get_current_user_optional(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """토큰이 없거나, 유효하지 않으면 None을 반환 (401 내지 않음)."""
    try:
        return get_current_user(request, response, db)
    except HTTPException:
        return None