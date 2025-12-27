"""User schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.user import WorkType


class UserBase(BaseModel):
    """Base user schema"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    work_type: Optional[WorkType] = None


class UserCreate(UserBase):
    """Schema for creating a user"""
    user_key: str = Field(..., description="Unique user key for authentication")


class UserUpdate(UserBase):
    """Schema for updating a user"""
    pass


class UserResponse(UserBase):
    """Schema for user response"""
    id: UUID
    user_key: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

