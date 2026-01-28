"""Conversation model"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class ConversationStatus(str, enum.Enum):
    """Conversation status enumeration"""
    ACTIVE = "active"
    AWAITING_HUMAN = "awaiting_human"  # Aguardando transferência para humano
    CONVERTED = "converted"
    LOST = "lost"
    ABANDONED = "abandoned"


class FunnelStage(str, enum.Enum):
    """Funnel stage enumeration"""
    AWARENESS = "awareness"
    INTEREST = "interest"
    CONSIDERATION = "consideration"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class Conversation(Base):
    """Conversation model representing chat sessions"""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)  # Nullable for migration
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE, nullable=False)
    funnel_stage = Column(SQLEnum(FunnelStage), default=FunnelStage.AWARENESS, nullable=False)
    interested_plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=True)
    context_summary = Column(Text, nullable=True)
    handoff_reason = Column(Text, nullable=True)  # Motivo da transferência
    handoff_requested_at = Column(DateTime, nullable=True)  # Quando foi solicitada
    conversation_metadata = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    interested_plan = relationship("Plan", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="conversation", cascade="all, delete-orphan")
    analysis_reports = relationship("AnalysisReport", back_populates="conversation", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_conversation_tenant_user', 'tenant_id', 'user_id'),
        Index('idx_conversation_tenant_status', 'tenant_id', 'status'),
        Index('idx_conversation_tenant_funnel', 'tenant_id', 'funnel_stage'),
    )

    def __repr__(self):
        return f"<Conversation {self.id} - {self.status.value} - {self.funnel_stage.value}>"

