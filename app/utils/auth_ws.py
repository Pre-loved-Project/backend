# app/utils/auth_ws.py

from typing import Optional

from jose import jwt, JWTError
from app.core.config import settings


def decode_user_id(token: Optional[str]) -> Optional[int]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except JWTError:
        return None
