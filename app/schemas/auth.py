from typing import Union
from datetime import datetime, date
from pydantic import Field, EmailStr, field_validator
from .base import BaseSchema  # ✅ 자동 camelCase 변환용 베이스

class SignupIn(BaseSchema):
    email: EmailStr
    nickname: str = Field(..., min_length=2, max_length=30)
    birth_date: str
    password: str = Field(..., min_length=8)

    @field_validator("birth_date")
    @classmethod
    def _validate_birth_date(cls, v: str) -> str:
        # YYYY-MM-DD 형식 검증
        datetime.strptime(v, "%Y-%m-%d")
        return v


class UserOut(BaseSchema):
    user_id: int
    email: EmailStr
    nickname: str
    birth_date: Union[date, str]
    created_at: datetime
    updated_at: datetime


class LoginIn(BaseSchema):
    email: str
    password: str = Field(..., min_length=8)


class TokenOut(BaseSchema):
    access_token: str
