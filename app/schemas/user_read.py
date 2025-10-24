from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class UserReadOut(BaseModel):
    userId: int
    email: str
    nickname: str
    birthDate: date
    introduction: Optional[str] = None
    imageUrl: Optional[str] = None
    category: Optional[str] = None
    sellCount: int
    buyCount: int
    createdAt: datetime
    updatedAt: datetime
