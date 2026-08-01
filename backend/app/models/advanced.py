from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, BeforeValidator
from typing_extensions import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

# ==========================================
# 1. MENTIONS SCHEMAS
# ==========================================
class MentionBase(BaseModel):
    room_id: str
    message_id: Optional[str] = None
    mentioned_user_id: Optional[str] = None
    mentioned_username: str
    mention_type: str = "user"  # "user" | "agent"

class MentionInDB(MentionBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class MentionResponse(MentionBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True

# ==========================================
# 2. MENTION NOTIFICATIONS SCHEMAS
# ==========================================
class MentionNotificationBase(BaseModel):
    user_id: str
    mention_id: str
    is_read: bool = False

class MentionNotificationInDB(MentionNotificationBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class MentionNotificationResponse(MentionNotificationBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True

# ==========================================
# 3. TEMPLATES SCHEMAS
# ==========================================
class TemplateBase(BaseModel):
    name: str
    slug: str
    description: str
    icon: str
    starter_prompt: str
    suggested_agents: List[str] = []

class TemplateInDB(TemplateBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class TemplateResponse(TemplateBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True

# ==========================================
# 4. FEEDBACK SCHEMAS
# ==========================================
class FeedbackBase(BaseModel):
    output_id: str
    room_id: str
    user_id: str
    feedback_type: str  # "thumbs_up" | "thumbs_down" | "emoji"
    emoji: Optional[str] = None
    comment: Optional[str] = None

class FeedbackInDB(FeedbackBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

# ==========================================
# 5. FEEDBACK SUMMARY SCHEMAS
# ==========================================
class FeedbackSummaryBase(BaseModel):
    output_id: str
    thumbs_up_count: int = 0
    thumbs_down_count: int = 0
    emoji_reactions: Dict[str, int] = {}
    quality_score: float = 0.5

class FeedbackSummaryInDB(FeedbackSummaryBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)

    class Config:
        populate_by_name = True

class FeedbackSummaryResponse(FeedbackSummaryBase):
    id: PyObjectId = Field(alias="_id")

    class Config:
        populate_by_name = True
        from_attributes = True
