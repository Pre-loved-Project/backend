from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.db import Base

class Posting(Base):
    __tablename__ = "postings"

    id = Column(Integer, primary_key=True, index=True)                # postingId
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    price = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    # ✅ NEW: category
    category = Column(String(50), nullable=False)

    view_count = Column(Integer, nullable=False, default=0)
    like_count = Column(Integer, nullable=False, default=0)
    chat_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    images = relationship("PostingImage", cascade="all, delete-orphan", back_populates="posting", lazy="selectin")

class PostingImage(Base):
    __tablename__ = "posting_images"

    id = Column(Integer, primary_key=True)
    posting_id = Column(Integer, ForeignKey("postings.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String(500), nullable=False)

    posting = relationship("Posting", back_populates="images")
