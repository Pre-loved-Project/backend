from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class MyPostingItemOut(BaseModel):
    postingId: int
    sellerId: int
    title: str
    price: int
    content: str
    category: str
    createdAt: datetime
    likeCount: int
    chatCount: int
    viewCount: int
    thumbnail: Optional[str] = None


class MyPostingsOut(BaseModel):
    page: int
    size: int
    total: int
    data: List[MyPostingItemOut]
