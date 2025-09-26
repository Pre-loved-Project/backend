# app/schemas/auth.py
from typing import Union
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime, date


# ── 요청: 회원가입 ─────────────────────────────────────────────
class SignupIn(BaseModel):
    email: EmailStr
    user_name: str = Field(alias="userName", min_length=2, max_length=30)
    birth_date: str = Field(alias="birthDate")
    password_hash_input: str = Field(alias="passwordHash", min_length=8)

    @field_validator("birth_date")
    @classmethod
    def _validate_birth_date(cls, v: str) -> str:
        # YYYY-MM-DD 형식 검증
        datetime.strptime(v, "%Y-%m-%d")
        return v

    model_config = {"populate_by_name": True}


# ── 응답: 회원가입 성공 ────────────────────────────────────────
class UserOut(BaseModel):
    user_id: int = Field(alias="userId")
    email: EmailStr
    nickname: str
    birth_date: Union[date, str] = Field(alias="birthDate")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


# ── 응답: 이메일 중복 체크 ─────────────────────────────────────
class EmailUsedOut(BaseModel):
    is_email_used: bool = Field(alias="isEmailUsed")

    model_config = {"populate_by_name": True}


# ── 응답: 닉네임 중복 체크 ────────────────────────────────────
class UsernameUsedOut(BaseModel):
    is_user_name_used: bool = Field(alias="isUserNameUsed")

    model_config = {"populate_by_name": True}
