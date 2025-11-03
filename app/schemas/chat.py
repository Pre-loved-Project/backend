from pydantic import BaseModel, Field
from typing import Literal

class JoinRoomIn(BaseModel):
    event: Literal["join_room"]
    userId: int

class SendTextIn(BaseModel):
    event: Literal["send_message"]
    type: Literal["text"]
    content: str = Field(min_length=1)

class SendImageIn(BaseModel):
    event: Literal["send_message"]
    type: Literal["image"]
    content: str = Field(min_length=1)

class ReadMessageIn(BaseModel):
    event: Literal["read_message"]
    messageId: int

class LeaveRoomIn(BaseModel):
    event: Literal["leave_room"]

class ReceiveMessageOut(BaseModel):
    event: Literal["receive_message"] = "receive_message"
    messageId: int
    senderId: int
    type: Literal["text", "image"]
    content: str
    createdAt: str

class SystemMessageOut(BaseModel):
    event: Literal["system_message"] = "system_message"
    type: str
    message: str

class ErrorOut(BaseModel):
    event: Literal["error"] = "error"
    code: int
    message: str
