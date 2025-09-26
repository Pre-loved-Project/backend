from pydantic import BaseModel

class PostingCreate(BaseModel):
    title: str
    content: str
    price: int

class PostingResp(BaseModel):
    postingId: int
    sellerId: int
    title: str
    content: str
    price: int
    status: str

    class Config:
        from_attributes = True
