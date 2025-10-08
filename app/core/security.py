from datetime import datetime, timedelta
from jose import jwt
from passlib.hash import argon2
from app.core.config import settings

def hash_password(plain: str) -> str:
    return argon2.using(time_cost=2, memory_cost=102400, parallelism=8).hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return argon2.verify(plain, hashed)

def create_access_token(sub: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(sub), "iat": datetime.utcnow(), "exp": exp}
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm=settings.JWT_ALG)

def create_refresh_token(sub: str) -> str:
    exp = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(sub), "iat": datetime.utcnow(), "exp": exp}
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm=settings.JWT_ALG)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=[settings.JWT_ALG], options={"verify_aud": False})

def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=[settings.JWT_ALG], options={"verify_aud": False})
