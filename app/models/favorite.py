from sqlalchemy import Column, BigInteger, DateTime, PrimaryKeyConstraint
from sqlalchemy.sql import func
from app.core.db import Base

class Favorite(Base):
    __tablename__ = "favorites"
    userId = Column(BigInteger, nullable=False)
    postingId = Column(BigInteger, nullable=False)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (PrimaryKeyConstraint('userId', 'postingId'),)
