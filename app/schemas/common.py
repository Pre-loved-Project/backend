# app/schemas/common.py
from typing import Generic, List, Optional, TypeVar
from pydantic import Field
from .base import BaseSchema

T = TypeVar("T")

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
    "",
}

class PageMeta(BaseSchema):
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)
    total: int = Field(0, ge=0)

class Page(BaseSchema, Generic[T]):
    items: List[T]
    meta: PageMeta

class IdOut(BaseSchema):
    id: int = Field(..., ge=1)
