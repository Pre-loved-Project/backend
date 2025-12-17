# app/routers/chat_rest.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.db import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.posting import Posting
from app.models.chat import ChatRoom, ChatMessage, ChatRead
from app.routers import chat_ws

router = APIRouter(prefix="/api/chat", tags=["Chat REST"])

# 🔹 채팅방 생성 요청/응답 모델 추가
class CreateChatIn(BaseModel):
    postingId: int

class CreateChatOut(BaseModel):
    chatId: int
    postingId: int
    sellerId: int
    buyerId: int
    createdAt: str


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
    lastReadMessageId: Optional[int] = None

class UpdateDealStatusIn(BaseModel):
    status: str


class DealStatusOut(BaseModel):
    chatId: int
    postingId: int
    sellerId: int
    buyerId: int
    dealStatus: str
    postStatus: str
    changedBy: int
    changedAt: str


# 🔥 새 채팅방 생성 + 판매자에게만 chat_created 브로드캐스트
# app/routers/chat_rest.py

@router.post("", response_model=CreateChatOut)
def create_chat(
    body: CreateChatIn,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    posting = db.query(Posting).filter(Posting.id == body.postingId).first()
    if not posting:
        raise HTTPException(status_code=404, detail="posting_not_found")

    if posting.seller_id == me.user_id:
        raise HTTPException(status_code=400, detail="cannot_chat_with_self")

    room = ChatRoom(
        posting_id=posting.id,
        seller_id=posting.seller_id,
        buyer_id=me.user_id,
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



@router.get("/{chat_id}", response_model=MessagesOut)
def list_messages(
    chat_id: int = Path(...),
    cursor: Optional[int] = Query(None),
    size: Optional[int] = Query(20),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
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

    messages: List[MessageItem] = []
    for m in rows:
        if m.type.upper() == "SYSTEM":
            is_mine = False
            read = True  # 시스템 메시지는 항상 읽은 걸로
        else:
            is_mine = (m.sender_id == me.user_id)
            # ChatRead에 메시지가 있으면 읽은거임
            read = (
                db.query(ChatRead)
                .filter(
                    ChatRead.room_id == m.room_id,
                    ChatRead.user_id != m.sender_id,
                    ChatRead.last_read_message_id >= m.id,
                )
                .count() > 0
            )

        messages.append(
            MessageItem(
                messageId=m.id,
                isMine=is_mine,
                type=m.type,
                content=m.content,
                sendAt=m.created_at.astimezone(timezone.utc).isoformat(),
                isRead=read,
            )
        )

    next_cursor = rows[-1].id if rows else None

    # 👇 이 채팅방에서 "상대방이 읽은, 내가 보낸 마지막 메시지 ID"
    # 상대방 ID 계산
    other_user_id = room.seller_id if me.user_id == room.buyer_id else room.buyer_id

    last_read_row = (
        db.query(ChatRead.last_read_message_id)
        .join(ChatMessage, ChatRead.last_read_message_id == ChatMessage.id)
        .filter(
            ChatMessage.room_id == chat_id,        # 이 방에서
            ChatRead.user_id == other_user_id,     # 상대방이 읽은 메시지들 중
            ChatMessage.sender_id == me.user_id,   # 그 중에서 "내가 보낸" 메시지
        )
        .order_by(ChatRead.last_read_message_id.desc())      # 가장 큰 id = 마지막으로 읽은 메시지
        .first()
    )
    last_read_id = last_read_row[0] if last_read_row else None

    return MessagesOut(
        messages=messages,
        hasNext=has_next,
        nextCursor=next_cursor,
        lastReadMessageId=last_read_id,
    )




@router.patch("/{chat_id}/deal", response_model=DealStatusOut)
async def update_deal_status(
    chat_id: int = Path(..., description="대상 채팅방 ID"),
    body: UpdateDealStatusIn = ...,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # 이하 내용은 네가 올린 그대로 (거래 상태 변경 + system 메시지 + broadcast_deal_update)
    room = db.query(ChatRoom).filter(ChatRoom.id == chat_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="chat_not_found")

    if me.user_id not in (room.buyer_id, room.seller_id):
        raise HTTPException(status_code=403, detail="forbidden")

    allowed = {"ACTIVE", "RESERVED", "COMPLETED"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail="invalid_status")

    prev_status = room.status or "ACTIVE"
    new_status = body.status

    if prev_status == "COMPLETED" and new_status != "COMPLETED":
        raise HTTPException(status_code=400, detail="completed_cannot_change")

    if prev_status == new_status:
        raise HTTPException(status_code=400, detail="same_status")

    posting = db.query(Posting).filter(Posting.id == room.posting_id).first()
    if not posting:
        raise HTTPException(status_code=404, detail="posting_not_found")

    if prev_status == "ACTIVE" and new_status == "RESERVED":
        if posting.status == "SELLING":
            posting.status = "RESERVED"
    elif prev_status == "RESERVED" and new_status == "ACTIVE":
        if posting.status == "RESERVED":
            posting.status = "SELLING"
    elif prev_status == "RESERVED" and new_status == "COMPLETED":
        if posting.status == "RESERVED":
            posting.status = "SOLD"

        seller = db.query(User).filter(User.user_id == room.seller_id).first()
        buyer = db.query(User).filter(User.user_id == room.buyer_id).first()
        if seller is not None:
            seller.sell_count = (seller.sell_count or 0) + 1
        if buyer is not None:
            buyer.buy_count = (buyer.buy_count or 0) + 1

    room.status = new_status
    changed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    db.commit()
    db.refresh(room)
    db.refresh(posting)

    nick = me.nickname or "사용자"

    if prev_status == "RESERVED" and new_status == "ACTIVE":
        msg_text = f"{nick}님이 예약을 취소했습니다"
    elif new_status == "RESERVED":
        msg_text = f"{nick}님이 예약을 요청했습니다"
    elif new_status == "COMPLETED":
        msg_text = f"{nick}님이 거래를 완료했습니다"
    else:
        msg_text = f"{nick}님이 거래 상태를 변경했습니다"

    system_msg = ChatMessage(
        room_id=room.id,
        sender_id=me.user_id,
        type="system",
        content=msg_text,
    )
    db.add(system_msg)
    db.commit()
    db.refresh(system_msg)

    await chat_ws.broadcast_deal_update(
        chat_id=room.id,
        deal_status=new_status,
        post_status=posting.status,
        system_message=msg_text,
    )

    return DealStatusOut(
        chatId=room.id,
        postingId=room.posting_id,
        sellerId=room.seller_id,
        buyerId=room.buyer_id,
        dealStatus=new_status,
        postStatus=posting.status,
        changedBy=me.user_id,
        changedAt=changed_at,
    )
