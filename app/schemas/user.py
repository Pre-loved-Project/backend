from datetime import datetime, date
from typing import Optional, ClassVar
from pydantic import BaseModel, EmailStr, HttpUrl, field_validator, ConfigDict

def to_camel(s: str) -> str:
    parts = s.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])

ALLOWED_CATEGORIES = {
    "전자제품/가전제품",
    "식료품",
    "의류/패션",
    "스포츠/레저",
    "뷰티",
    "게임",
    "도서/음반/문구",
    "티켓/쿠폰",
    "리빙/가구/생활",
    "반려동물/취미",
    ""
}

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        str_strip_whitespace=True
    )

class UserCreateIn(CamelModel):
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

class MeUpdateIn(CamelModel):
    nickname: Optional[str] = None
    introduction: Optional[str] = None
    image_url: Optional[str] = None
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

class UserOut(CamelModel):
    user_id: int
    email: EmailStr
    nickname: str
    birth_date: date
    introduction: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    sell_count: int
    buy_count: int
    created_at: datetime
    updated_at: datetime
