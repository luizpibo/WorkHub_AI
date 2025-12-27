"""Chat schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from app.models.conversation import FunnelStage


class ChatRequest(BaseModel):
    """Schema for chat request"""
    message: str = Field(..., description="User message")
    user_key: str = Field(..., description="User identification key")
    conversation_id: Optional[UUID] = Field(None, description="Existing conversation ID")
    user_name: Optional[str] = Field(None, description="User name for linking chats")


class ChatResponse(BaseModel):
    """Schema for chat response"""
    response: str = Field(..., description="Agent response")
    conversation_id: UUID = Field(..., description="Conversation ID")
    funnel_stage: FunnelStage = Field(..., description="Current funnel stage")
    user_id: UUID = Field(..., description="User ID")
    status: Optional[str] = Field(None, description="Conversation status")
    blocked: Optional[bool] = Field(None, description="Whether conversation is blocked")
    handoff_reason: Optional[str] = Field(None, description="Reason for handoff")


class MessageCreate(BaseModel):
    """Schema for creating a message"""
    conversation_id: UUID
    role: str
    content: str
    tool_calls: Optional[dict] = None
    metadata: Optional[dict] = None

