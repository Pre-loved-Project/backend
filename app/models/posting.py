from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.db import Base

class Posting(Base):
    __tablename__ = "postings"

    # 실제 DB 컬럼명은 "id" (주석에 postingId라고 쓰여 있었지만 코드상은 id임)
    id = Column(Integer, primary_key=True, index=True)

    # FK를 실제 컬럼명에 맞춤: users.userId
    seller_id = Column(Integer, ForeignKey("users.userId", ondelete="CASCADE"), nullable=False)

    title = Column(String(200), nullable=False)
    price = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    category = Column(String(50), nullable=False)

    view_count = Column(Integer, nullable=False, default=0)
    like_count = Column(Integer, nullable=False, default=0)
    chat_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    images = relationship("PostingImage", cascade="all, delete-orphan", back_populates="posting", lazy="selectin")
    # (선택) 판매자 관계
    # seller = relationship("User", backref="postings")
    

class PostingImage(Base):
    __tablename__ = "posting_images"

    id = Column(Integer, primary_key=True)

    # postings의 실제 PK 컬럼명은 "id"
    posting_id = Column(Integer, ForeignKey("postings.id", ondelete="CASCADE"), nullable=False, index=True)

    url = Column(String(500), nullable=False)

    posting = relationship("Posting", back_populates="images")
