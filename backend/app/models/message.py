from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, BeforeValidator
from typing_extensions import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

class MessageBase(BaseModel):
    content: str
    message_type: str = "user"  # "user" | "agent"
    username: str

class MessageCreate(MessageBase):
    pass

class MessageInDB(MessageBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    room_id: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class MessageResponse(MessageBase):
    id: PyObjectId = Field(alias="_id")
    room_id: str
    user_id: str
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True

# ==========================================
# VERSION SNAPSHOT MESSAGES
# ==========================================
class VersionMessageInDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    version_id: str
    message_id: str
    room_id: str
    content: str
    message_type: str
    username: str
    created_at: datetime

    class Config:
        populate_by_name = True

class VersionMessageResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    version_id: str
    message_id: str
    room_id: str
    content: str
    message_type: str
    username: str
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
