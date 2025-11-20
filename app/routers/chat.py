# app/routers/chat.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List, Literal
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from datetime import timezone

from app.core.db import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.posting import Posting
from app.models.chat import ChatRoom, ChatMessage, ChatRead
from app.schemas.chat import ChatListOut, ChatListItemOut, ChatLastMessageOut

router = APIRouter(tags=["Chat"])


class CreateChatIn(BaseModel):
    postingId: int


class CreateChatOut(BaseModel):
    chatId: int
    postingId: int
    sellerId: int
    buyerId: int
    createdAt: str


@router.post("/api/chat", response_model=CreateChatOut, status_code=status.HTTP_201_CREATED)
def create_chat(
    req: CreateChatIn,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    posting = db.query(Posting).filter(Posting.id == req.postingId).first()
    if not posting:
        raise HTTPException(status_code=404, detail="posting_not_found")
    if posting.seller_id == me.user_id:
        raise HTTPException(status_code=400, detail="cannot_chat_with_self")

    exists = (
        db.query(ChatRoom)
        .filter(ChatRoom.posting_id == posting.id, ChatRoom.buyer_id == me.user_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="chat_already_exists")

    room = ChatRoom(
        posting_id=posting.id,
        seller_id=posting.seller_id,
        buyer_id=me.user_id,
        status=None,
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    return CreateChatOut(
        chatId=room.id,
        postingId=room.posting_id,
        sellerId=room.seller_id,
        buyerId=room.buyer_id,
        createdAt=room.created_at.astimezone(timezone.utc).isoformat(),
    )


@router.get("/api/chat/me", response_model=ChatListOut)
def get_my_chats(
    role: Optional[Literal["buyer", "seller"]] = Query(None),
    status_param: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    q = db.query(ChatRoom).filter(
        or_(
            ChatRoom.buyer_id == me.user_id,
            ChatRoom.seller_id == me.user_id,
        )
    )

    if role == "buyer":
        q = q.filter(ChatRoom.buyer_id == me.user_id)
    elif role == "seller":
        q = q.filter(ChatRoom.seller_id == me.user_id)

    if status_param:
        q = q.filter(ChatRoom.status == status_param)

    rooms: List[ChatRoom] = q.order_by(desc(ChatRoom.created_at)).all()

    items: List[ChatListItemOut] = []

    for room in rooms:
        posting = db.query(Posting).get(room.posting_id)

        if room.buyer_id == me.user_id:
            my_role: Literal["buyer", "seller"] = "buyer"
            other_id = room.seller_id
        else:
            my_role = "seller"
            other_id = room.buyer_id

        other = db.query(User).get(other_id)

        last_msg: ChatMessage | None = (
            db.query(ChatMessage)
            .filter(ChatMessage.chat_id == room.id)
            .order_by(desc(ChatMessage.id))
            .first()
        )

        last_msg_out: Optional[ChatLastMessageOut] = None

        if last_msg:
            read_row: ChatRead | None = (
                db.query(ChatRead)
                .filter(
                    ChatRead.chat_id == room.id,
                    ChatRead.user_id == me.user_id,
                )
                .first()
            )

            last_is_read = False
            if read_row is not None and read_row.last_read_message_id >= last_msg.id:
                last_is_read = True

            last_msg_out = ChatLastMessageOut(
                messageId=last_msg.id,
                isMine=last_msg.sender_id == me.user_id,
                type=last_msg.type,
                content=last_msg.content,
                sendAt=last_msg.created_at,
                isRead=last_is_read,
            )

        status_value = room.status or "ACTIVE"

        item = ChatListItemOut(
            chatId=room.id,
            postingId=room.posting_id,
            postingTitle=posting.title if posting else "",
            role=my_role,
            lastMessage=last_msg_out,
            createdAt=room.created_at,
            status=status_value,
            otherId=other.user_id,
            otherNickname=other.nickname,
            otherImageUrl=other.image_url,
        )
        items.append(item)

    return ChatListOut(chats=items)
