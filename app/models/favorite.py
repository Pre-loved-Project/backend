from sqlalchemy import Column, Integer, DateTime, ForeignKey
from datetime import datetime
from app.core.db import Base

class Favorite(Base):
    __tablename__ = "favorites"

    # users.userId가 Integer이므로 여기서도 Integer
    user_id = Column(Integer, ForeignKey("users.userId", ondelete="CASCADE"), primary_key=True)

    # postings의 실제 PK는 "id" (Integer)
    posting_id = Column(Integer, ForeignKey("postings.id", ondelete="CASCADE"), primary_key=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
