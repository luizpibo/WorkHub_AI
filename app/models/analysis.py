"""Analysis Report model"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class AnalysisType(str, enum.Enum):
    """Analysis type enumeration"""
    FUNNEL = "funnel"
    SENTIMENT = "sentiment"
    OBJECTIONS = "objections"
    RECOMMENDATIONS = "recommendations"


class AnalysisReport(Base):
    """Analysis Report model for storing conversation analysis"""
    __tablename__ = "analysis_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)  # Nullable for migration
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    analysis_type = Column(SQLEnum(AnalysisType), nullable=False)
    result = Column(JSONB, nullable=False, default=dict)
    insights = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="analysis_reports")
    conversation = relationship("Conversation", back_populates="analysis_reports")

    # Indexes
    __table_args__ = (
        Index('idx_analysis_tenant_type', 'tenant_id', 'analysis_type'),
    )

    def __repr__(self):
        return f"<AnalysisReport {self.analysis_type.value} - {self.created_at}>"

