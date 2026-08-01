from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, BeforeValidator
from typing_extensions import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

# ==========================================
# 1. ROOM SCHEMAS
# ==========================================
class RoomBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    is_public: bool = True
    contract_text: Optional[str] = None
    org_id: Optional[str] = None
    active_agent_id: Optional[str] = None
    active_chain_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

class RoomCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    created_by_id: str
    org_id: Optional[str] = None

class RoomInDB(RoomBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class RoomResponse(RoomBase):
    id: PyObjectId = Field(alias="_id")
    created_by: str
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True

# ==========================================
# 2. PARTICIPANT SCHEMAS
# ==========================================
class ParticipantBase(BaseModel):
    room_id: str
    user_id: str
    username: str
    avatar_initial: Optional[str] = None
    is_online: bool = True

class ParticipantInDB(ParticipantBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class ParticipantResponse(ParticipantBase):
    id: PyObjectId = Field(alias="_id")
    joined_at: datetime
    last_seen: datetime

    class Config:
        populate_by_name = True
        from_attributes = True

# ==========================================
# 3. CANVAS / AGENT OUTPUT CARD SCHEMAS
# ==========================================
class AgentOutputBase(BaseModel):
    room_id: str
    message_id: Optional[str] = None
    title: str = "Analysis"
    content: str
    status: str = "draft"  # "draft" | "finalized"
    edited_by: Optional[str] = None
    edited_at: Optional[datetime] = None

class AgentOutputInDB(AgentOutputBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class AgentOutputResponse(AgentOutputBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True

# ==========================================
# 4. SESSION VERSION SCHEMAS
# ==========================================
class SessionVersionBase(BaseModel):
    room_id: str
    version_number: int
    label: str
    parent_version_id: Optional[str] = None
    created_by: str

class SessionVersionInDB(SessionVersionBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class SessionVersionResponse(SessionVersionBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
