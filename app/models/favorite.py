from sqlalchemy import Column, Integer, BigInteger, DateTime, ForeignKey
from datetime import datetime
from app.core.db import Base

class Favorite(Base):
    __tablename__ = "favorites"

    # User PK 타입에 맞추세요 (예시: users.userId가 BigInt라면 BigInteger 유지)
    user_id = Column(BigInteger, ForeignKey("users.userId", ondelete="CASCADE"), primary_key=True)

    # 🔗 postings.posting_id가 Integer 이므로 여기서도 Integer
    posting_id = Column(Integer, ForeignKey("postings.posting_id", ondelete="CASCADE"), primary_key=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
