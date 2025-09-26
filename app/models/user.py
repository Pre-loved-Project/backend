from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, func
from app.core.db import Base

class User(Base):
    __tablename__ = "users"

    userId = Column(Integer, primary_key=True, index=True)   # ✅ id → userId
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nickname = Column(String, unique=True, index=True, nullable=False)
    birth_date = Column(Date, nullable=False)
    email_verified = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
