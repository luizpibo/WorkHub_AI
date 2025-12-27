"""Conversation schemas"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.conversation import ConversationStatus, FunnelStage


class ConversationBase(BaseModel):
    """Base conversation schema"""
    status: ConversationStatus = ConversationStatus.ACTIVE
    funnel_stage: FunnelStage = FunnelStage.AWARENESS
    interested_plan_id: Optional[UUID] = None
    context_summary: Optional[str] = None
    conversation_metadata: Optional[Dict[str, Any]] = None


class ConversationCreate(BaseModel):
    """Schema for creating a conversation"""
    user_id: UUID


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""
    status: Optional[ConversationStatus] = None
    funnel_stage: Optional[FunnelStage] = None
    interested_plan_id: Optional[UUID] = None
    context_summary: Optional[str] = None
    conversation_metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(ConversationBase):
    """Schema for conversation response"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

