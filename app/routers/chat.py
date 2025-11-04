# app/routers/chat.py (상단 import는 기존 그대로 + 몇 개 추가)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Set, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.db import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.posting import Posting
from app.models.chat import ChatRoom, ChatMessage, ChatRead

router = APIRouter()

class CreateChatIn(BaseModel):
    postingId: int

class CreateChatOut(BaseModel):
    chatId: int
    createdAt: str

@router.post("/api/chat", response_model=CreateChatOut)
def create_chat(req: CreateChatIn, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    posting = db.query(Posting).filter(Posting.id == req.postingId).first()
    if not posting:
        raise HTTPException(status_code=404, detail="posting_not_found")
    if posting.seller_id == me.user_id:
        raise HTTPException(status_code=400, detail="cannot_chat_with_self")

    seller_id = posting.seller_id
    buyer_id = me.user_id

    exists = (
        db.query(ChatRoom)
        .filter(ChatRoom.posting_id == posting.id, ChatRoom.buyer_id == buyer_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="chat_already_exists")

    room = ChatRoom(
        posting_id=posting.id,
        seller_id=seller_id,
        buyer_id=buyer_id,
        status=None,
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    return CreateChatOut(chatId=room.id, createdAt=room.created_at.astimezone().isoformat())
