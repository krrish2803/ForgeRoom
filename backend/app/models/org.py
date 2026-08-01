from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, BeforeValidator
from typing_extensions import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationInDB(OrganizationBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    billing_plan: str = "Free"  # "Free", "Premium", "Enterprise"
    billing_status: str = "active"

    class Config:
        populate_by_name = True

class OrganizationResponse(OrganizationBase):
    id: PyObjectId = Field(alias="_id")
    created_by: str
    created_at: datetime
    billing_plan: str
    billing_status: str

    class Config:
        populate_by_name = True
        from_attributes = True

class OrgMemberBase(BaseModel):
    org_id: str
    user_id: str
    role: str = "viewer"  # "owner" | "editor" | "viewer"

class OrgMemberInDB(OrgMemberBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    username: str
    joined_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class OrgMemberResponse(OrgMemberBase):
    id: PyObjectId = Field(alias="_id")
    username: str
    joined_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True

class OrgAgentConfigBase(BaseModel):
    system_prompt: str
    temperature: float = 0.5
    model_name: str = "meta/llama-3.1-70b-instruct"

class OrgAgentConfigInDB(OrgAgentConfigBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)  # maps to org_id

    class Config:
        populate_by_name = True

class OrgAgentConfigResponse(OrgAgentConfigBase):
    org_id: PyObjectId = Field(alias="_id")

    class Config:
        populate_by_name = True
        from_attributes = True

class OrgAuditLogBase(BaseModel):
    org_id: str
    room_id: Optional[str] = None
    user_id: str
    username: str
    action: str
    details: str

class OrgAuditLogInDB(OrgAuditLogBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class OrgAuditLogResponse(OrgAuditLogBase):
    id: PyObjectId = Field(alias="_id")
    timestamp: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
