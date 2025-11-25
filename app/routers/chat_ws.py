# app/routers/chat_ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import Dict, Set, Optional
from jose import jwt, JWTError
from app.core.db import get_db
from app.core.config import settings
from app.models.chat import ChatRoom, ChatMessage, ChatRead
from app.schemas.chat import (
    JoinRoomIn,
    SendTextIn,
    SendImageIn,
    ReadMessageIn,
    LeaveRoomIn,
    ReceiveMessageOut,
    SystemMessageOut,
    ErrorOut,
)

router = APIRouter()

# 방별 연결 관리
connections: Dict[int, Set[WebSocket]] = {}


def decode_user_id(token: Optional[str]) -> Optional[int]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except JWTError:
        return None


async def broadcast(chat_id: int, data: dict, exclude: Optional[WebSocket] = None):
    conns = connections.get(chat_id)
    if not conns:
        return
    dead = []
    for ws in list(conns):
        if exclude is not None and ws is exclude:
            continue  # 보낸 본인에게는 전송 안 함
        try:
            # ✅ datetime, Pydantic 등 전부 JSON 가능하게 변환
            encoded = jsonable_encoder(data)
            await ws.send_json(encoded)
        except Exception as e:
            print("send_json ERROR:", repr(e))
            print("ERROR TYPE:", type(e))
            print("ERROR DETAIL:", str(e))
            print("send_json 중 오류 발생")
            dead.append(ws)
    for d in dead:
        conns.discard(d)



@router.websocket("/ws/chat/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: int, db: Session = Depends(get_db)):
    # 1) 토큰 검증 (쿼리 파라미터)
    token = websocket.query_params.get("token")
    user_id = decode_user_id(token)
    if not user_id:
        await websocket.close(code=4001)  # invalid/expired token
        return

    # 2) 방 존재/권한 확인
    room = db.query(ChatRoom).filter(ChatRoom.id == chat_id).first()
    if not room:
        await websocket.close(code=4004)  # room not found
        return
    if user_id not in (room.seller_id, room.buyer_id):
        await websocket.close(code=4003)  # forbidden
        return

    # 3) 접속 수락 및 등록
    await websocket.accept()
    connections.setdefault(chat_id, set()).add(websocket)
    await websocket.send_json(SystemMessageOut(type="welcome", message="joined").dict())

    try:
        while True:
            data = await websocket.receive_json()
            ev = data.get("event")

            if ev == "join_room":
                _ = JoinRoomIn(**data)  # 스키마 검증만
                await websocket.send_json(SystemMessageOut(type="join", message="ok").dict())

            elif ev == "send_message":
                # 텍스트/이미지 분기 검증
                try:
                    parsed = SendTextIn(**data) if data.get("type") == "text" else SendImageIn(**data)
                except Exception:
                    await websocket.send_json(ErrorOut(code=4003, message="invalid_payload").dict())
                    continue

                # DB 저장
                msg = ChatMessage(room_id=chat_id, sender_id=user_id, type=parsed.type, content=parsed.content)
                db.add(msg)
                db.commit()
                db.refresh(msg)

                # 브로드캐스트 (보낸 본인 제외)
                out = ReceiveMessageOut(
                    messageId=msg.id,
                    senderId=user_id,
                    type=msg.type,
                    content=msg.content,
                    createdAt=msg.created_at.astimezone().isoformat(),  # ← str
                )
                await broadcast(chat_id, out.dict(), exclude=websocket)

            elif ev == "read_message":
                parsed = ReadMessageIn(**data)
                exists = (
                    db.query(ChatRead)
                    .filter(ChatRead.message_id == parsed.messageId, ChatRead.user_id == user_id)
                    .first()
                )
                if not exists:
                    db.add(ChatRead(message_id=parsed.messageId, user_id=user_id))
                    db.commit()
                # 읽음 브로드캐스트 (보낸 본인 제외)
                await broadcast(chat_id, SystemMessageOut(type="read", message=str(parsed.messageId)).dict(), exclude=websocket)

            elif ev == "leave_room":
                _ = LeaveRoomIn(**data)
                await websocket.close(code=1000)  # normal close
                break

            else:
                await websocket.send_json(ErrorOut(code=4003, message="unknown_event").dict())

    except WebSocketDisconnect:
        pass
    finally:
        conns = connections.get(chat_id)
        if conns and websocket in conns:
            conns.discard(websocket)

# ---------- 거래 상태 변경 브로드캐스트 ----------
# REST API(update_deal_status)에서 호출함
async def broadcast_deal_update(chat_id: int, deal_status: str, post_status: str, system_message: str):
    data = {
        "type": "DEAL_UPDATE",
        "chatId": chat_id,
        "dealStatus": deal_status,
        "postStatus": post_status,
        "systemMessage": {
            "messageId": system_msg.id,
            "content": system_msg.content,
            "sendAt": system_msg.created_at.isoformat()
        }
    }

    await broadcast(chat_id, data)
