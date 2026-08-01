from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, BeforeValidator
from typing_extensions import Annotated

# Helper to validate and convert MongoDB ObjectId to string
PyObjectId = Annotated[str, BeforeValidator(str)]

class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str = None  # user_id
    exp: int = None

class UserInDB(UserBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "hashed_password": "hashed_string_here",
                "created_at": "2026-07-29T14:30:00"
            }
        }

class UserResponse(UserBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
