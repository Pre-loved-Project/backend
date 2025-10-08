from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.db import Base

class Posting(Base):
    __tablename__ = "postings"

    # 🔑 SQLite에서는 INTEGER PRIMARY KEY 여야 자동 증가됨
    posting_id = Column(Integer, primary_key=True, autoincrement=True)

    # User PK 이름에 맞추세요: users.userId 또는 users.id
    seller_id = Column(BigInteger, ForeignKey("users.userId", ondelete="RESTRICT"), nullable=False, index=True)

    title = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    view_count = Column(Integer, nullable=False, default=0)
    like_count = Column(Integer, nullable=False, default=0)
    chat_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    images = relationship("PostingImage", cascade="all, delete-orphan", lazy="joined")


class PostingImage(Base):
    __tablename__ = "posting_images"

    # 🔑 여기 PK도 Integer로
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 🔗 FK 타입도 postings.posting_id와 동일하게 Integer
    posting_id = Column(Integer, ForeignKey("postings.posting_id", ondelete="CASCADE"), index=True, nullable=False)

    url = Column(Text, nullable=False)
    ord = Column(Integer, nullable=False, default=0)
