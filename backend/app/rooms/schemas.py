from typing import List, Optional
from pydantic import BaseModel
from app.models.room import RoomResponse
from app.models.message import MessageResponse

class RoomJoinRequest(BaseModel):
    room_id: str

class RoomAddMemberRequest(BaseModel):
    user_email: str

class RoomDetailResponse(BaseModel):
    room: RoomResponse
    messages: List[MessageResponse]
    active_members: List[str]  # names of active users
