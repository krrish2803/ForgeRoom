from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, BeforeValidator
from typing_extensions import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

# 1. Agent Library Schema
class AgentLibraryBase(BaseModel):
    slug: str = Field(..., alias="_id")  # Slug like "legal-analyst" serves as ID
    name: str
    description: str
    icon: str
    system_prompt: str
    suggested_model: str = "meta/llama-3.1-70b-instruct"
    temperature: float = 0.5

    class Config:
        populate_by_name = True

class AgentLibraryResponse(AgentLibraryBase):
    pass

# 2. Org Agent (Custom Agent / Override) Schema
class OrgAgentBase(BaseModel):
    org_id: str
    agent_id: str  # Custom ID or original Library slug
    name: str
    description: str
    icon: str
    system_prompt: str
    model_name: str = "meta/llama-3.1-70b-instruct"
    temperature: float = 0.5

class OrgAgentInDB(OrgAgentBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    version: int = 1
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class OrgAgentResponse(OrgAgentBase):
    id: PyObjectId = Field(alias="_id")
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True

# 3. Agent Prompt Version History Schema
class OrgAgentVersionInDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    org_id: str
    agent_id: str
    version: int
    system_prompt: str
    model_name: str
    temperature: float
    updated_by: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class OrgAgentVersionResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    org_id: str
    agent_id: str
    version: int
    system_prompt: str
    model_name: str
    temperature: float
    updated_by: str
    updated_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True

# 4. Multi-Agent Chain Pipeline Schema
class OrgAgentChainBase(BaseModel):
    org_id: str
    name: str
    description: str
    agents: List[str]  # Ordered sequence of agent IDs

class OrgAgentChainInDB(OrgAgentChainBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class OrgAgentChainResponse(OrgAgentChainBase):
    id: PyObjectId = Field(alias="_id")
    created_by: str
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
