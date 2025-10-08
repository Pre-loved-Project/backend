# app/schemas/posting.py
from typing import List, Optional, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, conint, field_validator

def to_camel(s: str) -> str:
    parts = s.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])

class CamelModel(BaseModel):
    # pydantic v2
    model_config = dict(populate_by_name=True, alias_generator=to_camel, from_attributes=True)

class PostingCreateIn(CamelModel):
    title: str = Field(min_length=1, max_length=100)
    price: conint(ge=0)
    content: str = Field(min_length=1, max_length=5000)
    images: List[HttpUrl] = Field(min_length=1, max_length=10)

class PostingUpdateIn(CamelModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    price: Optional[conint(ge=0)] = None
    content: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    images: Optional[List[HttpUrl]] = Field(default=None, min_length=1, max_length=10)

class PostingOut(CamelModel):
    posting_id: int
    seller_id: int
    title: str
    price: int
    content: str
    view_count: int
    like_count: int
    chat_count: int
    created_at: datetime
    updated_at: datetime
    images: List[HttpUrl]

    # ✅ ORM의 PostingImage 객체 리스트를 검증 '이전'에 URL 문자열 리스트로 변환
    @field_validator("images", mode="before")
    @classmethod
    def _coerce_images(cls, v):
        if not v:
            return []
        return [getattr(i, "url", i) for i in v]

class PostingListItemOut(CamelModel):
    posting_id: int
    title: str
    price: int
    seller_id: int
    created_at: datetime
    like_count: int
    chat_count: int
    view_count: int
    thumbnail: Optional[HttpUrl] = None
    content: Optional[str] = None

T = TypeVar("T")

class PageOut(CamelModel, Generic[T]):
    page: int
    size: int
    total: int
    data: List[T]

class FavoriteToggleIn(CamelModel):
    favorite: bool

class FavoriteToggleOut(CamelModel):
    message: str
    posting_id: int
    user_id: int
    favorite: bool
    updated_at: datetime

