# app/routers/chat_rest.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import asyncio

from app.core.db import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.posting import Posting
from app.models.chat import ChatRoom, ChatMessage, ChatRead
from app.routers import chat_ws

router = APIRouter(prefix="/api/chat", tags=["Chat REST"])


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
        if m.type == "SYSTEM":
            is_mine = False
            read = True   # 시스템 메세지는 그냥 항상 읽은 걸로 취급
        else:
            is_mine = (m.sender_id == me.user_id)
            read = db.query(ChatRead).filter(ChatRead.message_id == m.id).count() > 0

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
    return MessagesOut(messages=messages, hasNext=has_next, nextCursor=next_cursor)

@router.patch("/{chat_id}/deal", response_model=DealStatusOut)
async def update_deal_status(
    chat_id: int = Path(..., description="대상 채팅방 ID"),
    body: UpdateDealStatusIn = ...,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # 1) 채팅방 조회
    room = db.query(ChatRoom).filter(ChatRoom.id == chat_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="chat_not_found")

    # 2) 권한 체크
    if me.user_id not in (room.buyer_id, room.seller_id):
        raise HTTPException(status_code=403, detail="forbidden")

    # 3) 허용 status만
    allowed = {"ACTIVE", "RESERVED", "COMPLETED"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail="invalid_status")

    prev_status = room.status or "ACTIVE"
    new_status = body.status

    if prev_status == "COMPLETED" and new_status != "COMPLETED":
        raise HTTPException(status_code=400, detail="completed_cannot_change")

    if prev_status == new_status:
        raise HTTPException(status_code=400, detail="same_status")

    # 4) 게시글 조회
    posting = db.query(Posting).filter(Posting.id == room.posting_id).first()
    if not posting:
        raise HTTPException(status_code=404, detail="posting_not_found")

    # 5) posting.status 연동
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

    # 6) 채팅방 상태 변경
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

    # ✅ 시스템 메시지를 ChatMessage 로 저장
    system_msg = ChatMessage(
        room_id=room.id,
        sender_id=me.user_id,        # 시스템이라서 보낸 사람 없음
        type="system",
        content=msg_text,
    )
    db.add(system_msg)
    db.commit()
    db.refresh(system_msg)

    # ✅ 기존처럼 브로드캐스트 (필요하면 messageId도 같이 넘겨도 됨)
    await chat_ws.broadcast_deal_update(
        chat_id=room.id,
        deal_status=new_status,
        post_status=posting.status,
        system_message=msg_text,
        # 필요하면 system_message_id=system_msg.id 이런 식으로 확장
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