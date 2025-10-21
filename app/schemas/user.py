# app/schemas/user.py
from datetime import datetime, date
from typing import Optional
from pydantic import EmailStr, HttpUrl, Field, field_validator
from .base import BaseSchema
from .common import ALLOWED_CATEGORIES

class UserCreateIn(BaseSchema):
    email: EmailStr
    nickname: str
    birth_date: date
    password: str

    @field_validator("nickname")
    @classmethod
    def v_nick(cls, v: str) -> str:
        if not (1 <= len(v) <= 30):
            raise ValueError("nickname must be 1~30 chars")
        return v

class MeUpdateIn(BaseSchema):
    nickname: Optional[str] = None
    introduction: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    category: Optional[str] = None

    @field_validator("nickname")
    @classmethod
    def v_nick(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not (1 <= len(v) <= 30):
            raise ValueError("nickname must be 1~30 chars")
        return v

    @field_validator("category")
    @classmethod
    def v_cat(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ALLOWED_CATEGORIES:
            raise ValueError("invalid category")
        return v

class UserOut(BaseSchema):
    user_id: int
    email: EmailStr
    nickname: str
    birth_date: date
    introduction: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    category: Optional[str] = None
    sell_count: int
    buy_count: int
    created_at: datetime
    updated_at: datetime
