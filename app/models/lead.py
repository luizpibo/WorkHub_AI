"""Lead model"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, Integer, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class LeadStage(str, enum.Enum):
    """Lead stage enumeration"""
    COLD = "cold"
    WARM = "warm"
    HOT = "hot"
    QUALIFIED = "qualified"
    CONVERTED = "converted"


class Lead(Base):
    """Lead model representing qualified sales opportunities"""
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)  # Nullable for migration
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    stage = Column(SQLEnum(LeadStage), default=LeadStage.COLD, nullable=False)
    score = Column(Integer, default=0, nullable=False)
    objections = Column(JSONB, nullable=True, default=list)
    preferred_plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=True)
    next_action = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="leads")
    conversation = relationship("Conversation", back_populates="leads")
    user = relationship("User", back_populates="leads")
    preferred_plan = relationship("Plan", back_populates="leads")

    # Indexes
    __table_args__ = (
        Index('idx_lead_tenant_stage', 'tenant_id', 'stage'),
        Index('idx_lead_tenant_user', 'tenant_id', 'user_id'),
    )

    def __repr__(self):
        return f"<Lead {self.stage.value} - Score: {self.score}>"

