#app/models/chat.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.core.db import Base

class ChatRoom(Base):
    __tablename__ = "chat_rooms"
    id = Column(Integer, primary_key=True, index=True)
    posting_id = Column(Integer, ForeignKey("postings.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey("users.userId", ondelete="CASCADE"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.userId", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("posting_id", "buyer_id", name="uq_room_posting_buyer"),)
    messages = relationship("ChatMessage", back_populates="room", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.userId", ondelete="CASCADE"), nullable=True, index=True)  # ✅ 변경
    type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    room = relationship("ChatRoom", back_populates="messages")



class ChatRead(Base):
    __tablename__ = "chat_reads"

    id = Column(Integer, primary_key=True)

    # 이 유저가 어느 채팅방에서
    room_id = Column(
        Integer,
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 누구인지
    user_id = Column(
        Integer,
        ForeignKey("users.userId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 그 방에서 읽은 "가장 마지막" 메시지 ID (커서)
    last_read_message_id = Column(
        Integer,
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 마지막으로 업데이트된 시각
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # (room_id, user_id) 당 row 1개만
        UniqueConstraint("room_id", "user_id", name="uq_room_user"),
    )

