"""Plan model"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class BillingCycle(str, enum.Enum):
    """Billing cycle enumeration"""
    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Plan(Base):
    """Plan model representing coworking plans"""
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    billing_cycle = Column(SQLEnum(BillingCycle), nullable=False)
    features = Column(JSONB, nullable=False, default=list)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    conversations = relationship("Conversation", back_populates="interested_plan")
    leads = relationship("Lead", back_populates="preferred_plan")

    def __repr__(self):
        return f"<Plan {self.name} - R${self.price}/{self.billing_cycle.value}>"

