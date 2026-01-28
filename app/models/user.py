"""User model"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class WorkType(str, enum.Enum):
    """Work type enumeration"""
    FREELANCER = "freelancer"
    STARTUP = "startup"
    COMPANY = "company"
    OTHER = "other"


class User(Base):
    """User model representing potential customers"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)  # Nullable for migration
    user_key = Column(String, nullable=False, index=True)  # No longer globally unique
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    work_type = Column(SQLEnum(WorkType), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="user", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_key', name='uq_tenant_user_key'),
        Index('idx_user_tenant_key', 'tenant_id', 'user_key'),
    )

    def __repr__(self):
        return f"<User {self.user_key} - {self.name}>"

