from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.core.db import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"sqlite_autoincrement": True}  # ✅ 반드시 추가

    user_id = Column("userId", Integer, primary_key=True, index=True, autoincrement=True)  # ✅ 중요

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), unique=True, nullable=False, index=True)
    birth_date = Column(Date, nullable=False)

    introduction = Column(Text, nullable=True)
    image_url = Column(String(1024), nullable=True)
    category = Column(String(50), nullable=True)
    sell_count = Column(Integer, nullable=False, default=0)
    buy_count = Column(Integer, nullable=False, default=0)
    email_verified = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)