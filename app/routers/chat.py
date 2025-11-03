from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from jose import jwt, JWTError
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import Dict, Set
from app.core.config import settings
from app.core.db import get_db
from app.models.chat import ChatRoom, ChatMessage, ChatRead
from typing import Optional, Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Set, List
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.chat import ChatRoom, ChatMessage, ChatRead

router = APIRouter()

class RoomHub:
    def __init__(self):
        self.rooms: Dict[int, Set[WebSocket]] = {}

    def join(self, chat_id: int, ws: WebSocket):
        self.rooms.setdefault(chat_id, set()).add(ws)

    def leave(self, chat_id: int, ws: WebSocket):
        room = self.rooms.get(chat_id)
        if room and ws in room:
            room.remove(ws)
            if not room:
                self.rooms.pop(chat_id, None)

    async def broadcast(self, chat_id: int, message: dict):
        room = self.rooms.get(chat_id, set())
        dead = []
        for ws in room:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.leave(chat_id, ws)

hub = RoomHub()

def decode_user_id(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        sub = payload.get("sub")
        if sub is None:
            return None
        return int(sub)
    except JWTError:
        return None
    except Exception:
        return None

async def close_with_error(ws: WebSocket, code: int, message: str):
    await ws.send_json({"event": "error", "code": code, "message": message})
    await ws.close(code=code)

def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()

@router.websocket("/ws/chat/{chat_id}")
async def websocket_chat(ws: WebSocket, chat_id: int, db: Session = Depends(get_db)):
    token = ws.query_params.get("token")
    user_id = decode_user_id(token) if token else None
    if not user_id:
        await close_with_error(ws, 4001, "invalid_or_expired_token")
        return
    room = db.query(ChatRoom).filter(ChatRoom.id == chat_id).first()
    if not room:
        await close_with_error(ws, 4004, "room_not_found")
        return
    await ws.accept()
    hub.join(chat_id, ws)
    await ws.send_json({"event": "system_message", "type": "welcome", "message": "joined"})

    try:
        while True:
            data = await ws.receive_json()
            ev = data.get("event")

            if ev == "join_room":
                await ws.send_json({"event": "system_message", "type": "join", "message": "ok"})

            elif ev == "send_message":
                mtype = data.get("type")
                content = data.get("content")
                if mtype not in ("text", "image") or not content:
                    await ws.send_json({"event": "error", "code": 4003, "message": "invalid_payload"})
                    continue
                msg = ChatMessage(room_id=chat_id, sender_id=user_id, type=mtype, content=content)
                db.add(msg)
                db.commit()
                db.refresh(msg)
                payload = {
                    "event": "receive_message",
                    "messageId": msg.id,
                    "senderId": user_id,
                    "type": mtype,
                    "content": content,
                    "createdAt": iso(msg.created_at),
                }
                await hub.broadcast(chat_id, payload)

            elif ev == "read_message":
                mid = data.get("messageId")
                if not isinstance(mid, int):
                    await ws.send_json({"event": "error", "code": 4003, "message": "invalid_message_id"})
                    continue
                exists = db.query(ChatRead).filter(ChatRead.message_id == mid, ChatRead.user_id == user_id).first()
                if not exists:
                    db.add(ChatRead(message_id=mid, user_id=user_id))
                    db.commit()
                await ws.send_json({"event": "system_message", "type": "read", "message": str(mid)})

            elif ev == "leave_room":
                await ws.close(code=1000)
                break

            else:
                await ws.send_json({"event": "error", "code": 4003, "message": "unknown_event"})

    except WebSocketDisconnect:
        pass
    finally:
        hub.leave(chat_id, ws)


class CreateRoomOut(BaseModel):
    chatId: int

class RoomItem(BaseModel):
    chatId: int
    lastMessageId: Optional[int] = None
    messageCount: int

@router.post("/api/chat/rooms", response_model=CreateRoomOut)
def create_chat_room(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = ChatRoom()
    db.add(room)
    db.commit()
    db.refresh(room)
    return CreateRoomOut(chatId=room.id)

@router.get("/api/chat/rooms", response_model=List[RoomItem])
def list_chat_rooms(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rooms = db.query(ChatRoom).all()
    res = []
    for r in rooms:
        last_id = db.query(ChatMessage.id).filter(ChatMessage.room_id == r.id).order_by(ChatMessage.id.desc()).first()
        cnt = db.query(ChatMessage).filter(ChatMessage.room_id == r.id).count()
        res.append(RoomItem(chatId=r.id, lastMessageId=last_id[0] if last_id else None, messageCount=cnt))
    return res