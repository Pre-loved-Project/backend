# app/schemas/user.py
from typing import Union
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date


class EmailCheckResp(BaseModel):
    is_email_used: bool = Field(alias="isEmailUsed")
    model_config = {"populate_by_name": True}


class UserResp(BaseModel):
    user_id: int = Field(alias="userId")
    email: EmailStr
    nickname: str
    birth_date: Union[date, str] = Field(alias="birthDate")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }
