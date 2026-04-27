from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    password: str


class UserInDB(UserBase):
    id: UUID = Field(default_factory=uuid4)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserResponse(UserBase):
    id: UUID
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str | None = None
    role: str | None = None
    exp: int | None = None
