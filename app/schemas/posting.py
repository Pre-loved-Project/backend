# app/schemas/posting.py
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import HttpUrl, Field
from .base import BaseSchema  # ✅ camelCase 자동 변환 베이스

# ✅ 먼저 정의: 카테고리 리터럴 (그대로 사용)
Category = Literal[
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
]

class PostingImageOut(BaseSchema):
    url: HttpUrl

class PostingCreateIn(BaseSchema):
    title: str
    price: int
    content: str
    category: Category
    images: List[HttpUrl] = Field(default_factory=list)

class PostingUpdateIn(BaseSchema):
    title: Optional[str] = None
    price: Optional[int] = None
    content: Optional[str] = None
    category: Optional[Category] = None
    images: Optional[List[HttpUrl]] = None

class PostingOut(BaseSchema):
    posting_id: int
    seller_id: int
    title: str
    price: int
    content: str
    category: Category
    view_count: int
    like_count: int
    chat_count: int
    created_at: datetime
    updated_at: datetime
    images: List[HttpUrl]
    is_owner: Optional[bool] = None

class PostingListItem(BaseSchema):
    posting_id: int
    seller_id: int
    title: str
    price: int
    content: Optional[str] = None
    category: Category
    created_at: datetime
    like_count: int
    chat_count: int
    view_count: int
    thumbnail: Optional[HttpUrl] = None

class PageOut(BaseSchema):
    page: int
    size: int
    total: int
    data: List[PostingListItem]
