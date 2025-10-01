from typing import Union
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime, date

class SignupIn(BaseModel):
    email: EmailStr
    nickname: str = Field(alias="nickname", min_length=2, max_length=30)
    birth_date: str = Field(alias="birthDate")
    password: str = Field(alias="password", min_length=8)

    @field_validator("birth_date")
    @classmethod
    def _validate_birth_date(cls, v: str) -> str:
        datetime.strptime(v, "%Y-%m-%d")
        return v

    model_config = {"populate_by_name": True}

class UserOut(BaseModel):
    user_id: int = Field(alias="userId")
    email: EmailStr
    nickname: str
    birth_date: Union[date, str] = Field(alias="birthDate")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    model_config = {"populate_by_name": True, "from_attributes": True}

class LoginIn(BaseModel):
    email: str = Field(alias="email")
    password: str = Field(alias="password", min_length=8)
    model_config = {"populate_by_name": True}

class TokenOut(BaseModel):
    access_token: str = Field(alias="accessToken")
    model_config = {"populate_by_name": True}
