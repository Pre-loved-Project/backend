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

# ✅ /api/chat prefix
router = APIRouter(prefix="/api/chat", tags=["Chat"])


class CreateChatIn(BaseModel):
    postingId: int


class CreateChatOut(BaseModel):
    chatId: int
    postingId: int
    sellerId: int
    buyerId: int
    createdAt: str


# ✅ POST /api/chat

@router.post("", response_model=CreateChatOut, status_code=status.HTTP_201_CREATED)
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

    # 🔥 여기서 chatCount +1
    posting.chat_count = (posting.chat_count or 0) + 1

    db.commit()
    db.refresh(room)
    db.refresh(posting)

    return CreateChatOut(
        chatId=room.id,
        postingId=room.posting_id,
        sellerId=room.seller_id,
        buyerId=room.buyer_id,
        createdAt=room.created_at.astimezone(timezone.utc).isoformat(),
    )


# ✅ GET /api/chat/me
@router.get("/me", response_model=ChatListOut)
def get_my_chats(
    role: Optional[Literal["buyer", "seller"]] = Query(None),
    status_param: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # 내가 buyer이거나 seller인 방들
    q = db.query(ChatRoom).filter(
        or_(
            ChatRoom.buyer_id == me.user_id,
            ChatRoom.seller_id == me.user_id,
        )
    )

    # role 필터
    if role == "buyer":
        q = q.filter(ChatRoom.buyer_id == me.user_id)
    elif role == "seller":
        q = q.filter(ChatRoom.seller_id == me.user_id)

    # status 필터
    if status_param:
        q = q.filter(ChatRoom.status == status_param)

    rooms: List[ChatRoom] = q.order_by(desc(ChatRoom.created_at)).all()

    items: List[ChatListItemOut] = []

    for room in rooms:
        posting = db.query(Posting).get(room.posting_id)

        # 내 role / 상대방 계산
        if room.buyer_id == me.user_id:
            my_role: Literal["buyer", "seller"] = "buyer"
            other_id = room.seller_id
        else:
            my_role = "seller"
            other_id = room.buyer_id

        other = db.query(User).get(other_id)

        # ✅ 마지막 메시지: room_id 기준으로 조회
        last_msg: Optional[ChatMessage] = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.room_id == room.id,
                ChatMessage.type.in_(["text", "image"]),
            )
            .order_by(desc(ChatMessage.id))
            .first()
        )

        # 기본값: 메시지가 없을 때
        if last_msg is None:
            last_msg_out = ChatLastMessageOut(
                messageId=0,                 # 실제 메시지 아님 (더미값)
                isMine=False,
                type="text",                 # 그냥 텍스트로 통일
                content="메시지 없음",
                sendAt=room.created_at,      # 방 생성 시간 정도로 넣어도 됨
                isRead=True,
            )
        else:
            read_row: Optional[ChatRead] = (
                db.query(ChatRead)
                .filter(
                    ChatRead.room_id == room.id,
                    ChatRead.user_id == me.user_id,
                    ChatRead.last_read_message_id >= last_msg.id,
                )
                .first()
            )

            last_is_read = read_row is not None

            last_msg_out = ChatLastMessageOut(
                messageId=last_msg.id,
                isMine=(last_msg.sender_id == me.user_id),
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
