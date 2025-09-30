# app/schemas/users.py
from typing import Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, date
from pydantic import field_validator


# ── 응답: 유저 정보 ─────────────────────────────────────────────
class UserOut(BaseModel):
    user_id: int = Field(alias="userId")
    email: str
    nickname: str
    birth_date: Union[date, str] = Field(alias="birthDate")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


# ── 요청: 유저 수정 ─────────────────────────────────────────────
class UserUpdateIn(BaseModel):
    nickname: Optional[str] = None
    birth_date: Optional[str] = Field(alias="birthDate", default=None)
    password_hash_input: Optional[str] = Field(alias="passwordHash", default=None, min_length=8)

    @field_validator("birth_date")
    @classmethod
    def _validate_birth_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        datetime.strptime(v, "%Y-%m-%d")  # 형식 체크
        return v

    model_config = {"populate_by_name": True}


# ── 응답: 유저 삭제 ─────────────────────────────────────────────
class UserDeleteOut(BaseModel):
    user_id: int = Field(alias="userId")

    model_config = {"populate_by_name": True}
