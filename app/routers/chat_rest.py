from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import timezone
from app.core.db import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.posting import Posting
from app.models.chat import ChatRoom, ChatMessage, ChatRead

router = APIRouter(prefix="/api/chat", tags=["Chat REST"])

class CreateChatIn(BaseModel):
    postingId: int

class CreateChatOut(BaseModel):
    chatId: int
    createdAt: str

@router.post("", response_model=CreateChatOut)
def create_chat(req: CreateChatIn, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    posting = db.query(Posting).filter(Posting.id == req.postingId).first()
    if not posting:
        raise HTTPException(status_code=404, detail="posting_not_found")
    if posting.seller_id == me.user_id:
        raise HTTPException(status_code=400, detail="cannot_chat_with_self")
    exists = db.query(ChatRoom).filter(ChatRoom.posting_id == posting.id, ChatRoom.buyer_id == me.user_id).first()
    if exists:
        raise HTTPException(status_code=409, detail="chat_already_exists")
    room = ChatRoom(posting_id=posting.id, seller_id=posting.seller_id, buyer_id=me.user_id)
    db.add(room)
    db.commit()
    db.refresh(room)
    return {"chatId": room.id, "createdAt": room.created_at.astimezone(timezone.utc).isoformat()}

class ChatItem(BaseModel):
    chatId: int
    postingId: int
    postingTitle: str
    role: str
    lastMessage: Optional[str]
    status: Optional[str]
    otherId: int
    otherNick: str
    otherImage: Optional[str]
    createdAt: str

@router.get("/me", response_model=List[ChatItem])
def list_my_chats(role: Optional[str] = None, status: Optional[str] = None,
                  db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    q = db.query(ChatRoom).filter((ChatRoom.buyer_id == me.user_id) | (ChatRoom.seller_id == me.user_id))
    if role in ("buyer", "seller"):
        q = q.filter(ChatRoom.buyer_id == me.user_id) if role == "buyer" else q.filter(ChatRoom.seller_id == me.user_id)
    if status in ("RESERVED", "SOLD"):
        q = q.filter(ChatRoom.status == status)
    rooms = q.all()
    res = []
    from app.models.posting import Posting
    from app.models.user import User as U
    for r in rooms:
        last = db.query(ChatMessage).filter(ChatMessage.room_id == r.id).order_by(ChatMessage.id.desc()).first()
        posting = db.query(Posting).filter(Posting.id == r.posting_id).first()
        if me.user_id == r.buyer_id:
            other_id = r.seller_id
            role_ = "buyer"
        else:
            other_id = r.buyer_id
            role_ = "seller"
        other = db.query(U).filter(U.user_id == other_id).first()
        res.append(ChatItem(
            chatId=r.id,
            postingId=r.posting_id,
            postingTitle=posting.title if posting else "",
            role=role_,
            lastMessage=last.content if last else None,
            status=r.status,
            otherId=other_id,
            otherNick=other.nickname if other else "",
            otherImage=other.image_url if other else None,
            createdAt=r.created_at.astimezone(timezone.utc).isoformat(),
        ))
    return res

class MessageItem(BaseModel):
    messageId: int
    isMine: bool
    type: str
    content: str
    sendAt: str
    isRead: bool

class MessagesOut(BaseModel):
    messages: List[MessageItem]
    hasNext: bool
    nextCursor: Optional[int]

@router.get("/{chat_id}", response_model=MessagesOut)
def list_messages(chat_id: int = Path(...), cursor: Optional[int] = Query(None), size: Optional[int] = Query(20),
                  db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    room = db.query(ChatRoom).filter(ChatRoom.id == chat_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="chat_not_found")
    if me.user_id not in (room.buyer_id, room.seller_id):
        raise HTTPException(status_code=403, detail="forbidden")
    q = db.query(ChatMessage).filter(ChatMessage.room_id == chat_id)
    if cursor:
        q = q.filter(ChatMessage.id < cursor)
    rows = q.order_by(ChatMessage.id.desc()).limit(size + 1).all()
    has_next = len(rows) > size
    rows = rows[:size]
    messages = []
    for m in rows:
        is_mine = (m.sender_id == me.user_id)
        read = db.query(ChatRead).filter(ChatRead.message_id == m.id).count() > 0
        messages.append(MessageItem(
            messageId=m.id,
            isMine=is_mine,
            type=m.type,
            content=m.content,
            sendAt=m.created_at.astimezone(timezone.utc).isoformat(),
            isRead=read,
        ))
    next_cursor = rows[-1].id if rows else None
    return MessagesOut(messages=messages, hasNext=has_next, nextCursor=next_cursor)
