# app/routers/chat_list_ws.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import Dict, Set, Optional, Iterable

from app.core.db import get_db
from app.models.chat import ChatRoom, ChatMessage, ChatRead
from app.models.posting import Posting
from app.models.user import User
from app.utils.auth_ws import decode_user_id


router = APIRouter()

# 유저별 연결 관리 (채팅방이 아니라 user_id 기준)
chat_list_connections: Dict[int, Set[WebSocket]] = {}


async def send_event(ws: WebSocket, event: str, payload: dict):
    data = {"event": event, "payload": payload}
    await ws.send_json(jsonable_encoder(data))


async def send_error(ws: WebSocket, code: int, message: str):
    await send_event(ws, "error", {"code": code, "message": message})


async def broadcast_to_user(user_id: int, event: str, payload: dict):
    conns = chat_list_connections.get(user_id)
    if not conns:
        return

    dead: list[WebSocket] = []
    for ws in list(conns):
        try:
            await send_event(ws, event, payload)
        except Exception:
            dead.append(ws)

    for d in dead:
        conns.discard(d)
    if conns and len(conns) == 0:
        chat_list_connections.pop(user_id, None)


def _get_role(chat: ChatRoom, me_id: int) -> str:
    if chat.buyer_id == me_id:
        return "buyer"
    if chat.seller_id == me_id:
        return "seller"
    return "buyer"  # fallback


def _build_status(chat: ChatRoom) -> str:
    # DB에 뭐라고 저장하는지에 따라 매핑 필요 (예: "ACTIVE"/"RESERVED"/"COMPLETED")
    if chat.status == "RESERVED":
        return "RESERVED"
    if chat.status == "COMPLETED":
        return "COMPLETED"
    return "ACTIVE"


def _build_other(chat: ChatRoom, me_id: int, db: Session) -> dict:
    other_id = chat.seller_id if chat.buyer_id == me_id else chat.buyer_id
    other = db.query(User).filter(User.user_id == other_id).first()
    return {
        "otherId": other_id,
        "otherNickname": other.nickname if other else "",
        "otherImageUrl": getattr(other, "image_url", None) if other else None,
    }


def _build_last_message(chat: ChatRoom, me_id: int, db: Session) -> Optional[dict]:
    last_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.room_id == chat.id)
        .order_by(desc(ChatMessage.created_at))
        .first()
    )
    if not last_msg:
        return None

    # 내가 읽었는지 여부 (ChatRead 기준)
    is_read = (
        db.query(ChatRead)
        .filter(
            ChatRead.message_id == last_msg.id,
            ChatRead.user_id == me_id,
        )
        .first()
        is not None
    )

    return {
        "messageId": last_msg.id,
        "isMine": last_msg.sender_id == me_id,
        "type": "image" if last_msg.type == "image" else "text",
        "content": last_msg.content or "",
        "sendAt": last_msg.created_at.astimezone().isoformat(),
        "isRead": is_read,
    }


def _build_chat_created_payload(chat: ChatRoom, me_id: int, db: Session) -> Optional[dict]:
    posting = db.query(Posting).filter(Posting.id == chat.posting_id).first()
    if not posting:
        return None

    other = _build_other(chat, me_id, db)
    last_message = _build_last_message(chat, me_id, db)

    payload: dict = {
        "chatId": chat.id,
        "postingId": posting.id,
        "postingTitle": posting.title,
        "role": _get_role(chat, me_id),
        "status": _build_status(chat),
        "otherId": other["otherId"],
        "otherNickname": other["otherNickname"],
        "otherImageUrl": other["otherImageUrl"],
    }
    if last_message:
        payload["lastMessage"] = last_message
    return payload


# ---------- 외부에서 호출하는 브로드캐스트 함수들 ----------

async def broadcast_chat_created(chat: ChatRoom, db: Session):
    """새 채팅방 생성 시 buyer/seller 둘 다에게 chat_created 이벤트"""
    users = [chat.buyer_id, chat.seller_id]
    for uid in users:
        payload = _build_chat_created_payload(chat, uid, db)
        if payload:
            await broadcast_to_user(uid, "chat_created", payload)


async def broadcast_chat_list_update(chat: ChatRoom, last_msg: ChatMessage, db: Session):
    """해당 채팅방의 lastMessage 변경 시 buyer/seller 둘에게 chat_list_update 이벤트"""
    users = [chat.buyer_id, chat.seller_id]

    for uid in users:
        last_message = _build_last_message(chat, uid, db)
        if not last_message:
            continue
        payload = {
            "chatId": chat.id,
            "lastMessage": last_message,
        }
        await broadcast_to_user(uid, "chat_list_update", payload)


# ---------- WebSocket 엔드포인트 ----------

@router.websocket("/ws/chat-list")
async def websocket_chat_list(websocket: WebSocket, db: Session = Depends(get_db)):
    # 1) 토큰 검증
    token = websocket.query_params.get("token")
    user_id = decode_user_id(token)

    if not user_id:
        await websocket.accept()
        await send_error(websocket, 4001, "INVALID_OR_EXPIRED_TOKEN")
        await websocket.close(code=4001)
        return

    # 2) 접속 수락 + 연결 등록
    await websocket.accept()
    chat_list_connections.setdefault(user_id, set()).add(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if event == "join_chat_list":
                # 필요하면 여기서 최초 채팅 목록 쏴주기
                # (이미 /api/chat/me 사용 중이면 생략해도 됨)
                await send_event(
                    websocket,
                    "system_message",
                    {"type": "join_chat_list", "message": "ok"},
                )

                # ✨ 옵션: 여기서 DB 조회로 전체 목록 보내고 싶으면:
                # rooms = (
                #     db.query(ChatRoom)
                #     .filter(
                #         or_(ChatRoom.buyer_id == user_id, ChatRoom.seller_id == user_id)
                #     )
                #     .all()
                # )
                # for room in rooms:
                #     payload = _build_chat_created_payload(room, user_id, db)
                #     if payload:
                #         await send_event(websocket, "chat_created", payload)

            elif event == "leave_chat_list":
                await send_event(
                    websocket,
                    "system_message",
                    {"type": "leave_chat_list", "message": "bye"},
                )
                await websocket.close(code=1000)  # 정상 종료
                break

            else:
                await send_error(websocket, 4000, f"UNKNOWN_EVENT: {event}")

    except WebSocketDisconnect:
        pass
    finally:
        conns = chat_list_connections.get(user_id)
        if conns and websocket in conns:
            conns.discard(websocket)
            if len(conns) == 0:
                chat_list_connections.pop(user_id, None)
