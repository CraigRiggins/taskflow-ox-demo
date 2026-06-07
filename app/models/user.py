from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


class UserCreate(BaseModel):
    email:    str = Field(..., max_length=255)
    name:     str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)
    role:     str = Field("user", pattern="^(user|admin|viewer)$")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        # basic email check — duplicated in user_service.py
        if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email address")
        return v.lower().strip()


class UserUpdate(BaseModel):
    name:     Optional[str] = Field(None, min_length=1, max_length=100)
    email:    Optional[str] = Field(None, max_length=255)
    role:     Optional[str] = Field(None, pattern="^(user|admin|viewer)$")


class UserResponse(BaseModel):
    id:         int
    email:      str
    name:       str
    role:       str
    created_at: str


class LoginRequest(BaseModel):
    email:    str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      int
    role:         str
