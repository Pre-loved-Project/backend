from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.db import Base

class Posting(Base):
    __tablename__ = "postings"
    postingId = Column(BigInteger, primary_key=True, autoincrement=True)
    sellerId = Column(BigInteger, nullable=False, index=True)
    title = Column(String(120), nullable=False)
    content = Column(Text, nullable=False)
    price = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False, default="ON_SALE")
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    viewCount = Column(Integer, nullable=False, default=0)
    likeCount = Column(Integer, nullable=False, default=0)
    chatCount = Column(Integer, nullable=False, default=0)
