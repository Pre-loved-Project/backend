# app/core/security.py
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from jose import jwt, JWTError
from passlib.hash import argon2

# 환경변수로 설정 (운영 시 꼭 바꾸기)
JWT_ACCESS_SECRET = os.getenv("JWT_ACCESS_SECRET", "dev-access-secret")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET", "dev-refresh-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")

# 기본 만료시간 (분)
ACCESS_TOKEN_MIN = int(os.getenv("ACCESS_TOKEN_MIN", "15"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "30"))

# ── Password ───────────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    # Argon2 파라미터는 운영 환경에 맞춰 조정하세요.
    return argon2.using(time_cost=2, memory_cost=102400, parallelism=8).hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return argon2.verify(plain, hashed)

# ── JWT ────────────────────────────────────────────────────────────────────────
def _jwt_now() -> datetime:
    return datetime.now(timezone.utc)

def create_access_token(subject: Union[str, int], minutes: Optional[int] = None) -> str:
    """
    subject: 사용자 식별자 (user_id 등)
    minutes: 만료 분 (미지정 시 기본값)
    """
    now = _jwt_now()
    exp = now + timedelta(minutes=minutes or ACCESS_TOKEN_MIN)
    payload = {"sub": str(subject), "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, JWT_ACCESS_SECRET, algorithm=JWT_ALG)

def create_refresh_token(subject: Union[str, int], days: Optional[int] = None) -> str:
    now = _jwt_now()
    exp = now + timedelta(days=days or REFRESH_TOKEN_DAYS)
    payload = {"sub": str(subject), "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, JWT_REFRESH_SECRET, algorithm=JWT_ALG)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_ACCESS_SECRET, algorithms=[JWT_ALG])

def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, JWT_REFRESH_SECRET, algorithms=[JWT_ALG])
