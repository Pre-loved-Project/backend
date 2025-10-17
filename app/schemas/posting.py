from typing import List, Literal, Optional
from pydantic import BaseModel, HttpUrl, Field
from pydantic import ConfigDict

# ✅ 먼저 정의: 카테고리 리터럴
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

class PostingImageOut(BaseModel):
    url: HttpUrl
    model_config = ConfigDict(from_attributes=True)

class PostingCreateIn(BaseModel):
    title: str
    price: int
    content: str
    category: Category
    images: List[HttpUrl] = Field(default_factory=list)

class PostingUpdateIn(BaseModel):
    title: Optional[str] = None
    price: Optional[int] = None
    content: Optional[str] = None
    category: Optional[Category] = None
    images: Optional[List[HttpUrl]] = None

class PostingOut(BaseModel):
    postingId: int
    sellerId: int
    title: str
    price: int
    content: str
    category: Category
    viewCount: int
    likeCount: int
    chatCount: int
    createdAt: str
    updatedAt: str
    images: List[HttpUrl]
    isOwner: Optional[bool] = None  # Py3.9는 Optional 사용

class PostingListItem(BaseModel):
    postingId: int
    sellerId: int
    title: str
    price: int
    content: Optional[str] = None
    category: Category
    createdAt: str
    likeCount: int
    chatCount: int
    viewCount: int
    thumbnail: Optional[HttpUrl] = None

class PageOut(BaseModel):
    page: int
    size: int
    total: int
    data: List[PostingListItem]
