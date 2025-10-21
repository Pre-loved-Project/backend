from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, func
from app.core.db import Base

class UserConsent(Base):
    __tablename__ = "user_consents"
    id = Column(Integer, primary_key=True)
    # users.userId로 맞춤 (이미 OK)
    user_id = Column(Integer, ForeignKey("users.userId", ondelete="CASCADE"), nullable=False)
    tos = Column(Boolean, nullable=False)
    privacy = Column(Boolean, nullable=False)
    marketing = Column(Boolean, nullable=False, default=False)
    agreed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
