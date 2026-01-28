"""Tenant models for multi-tenant support"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Enum as SQLEnum, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class TenantStatus(str, enum.Enum):
    """Tenant status enumeration"""
    ACTIVE = "active"
    TRIAL = "trial"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class PromptType(str, enum.Enum):
    """Prompt type enumeration"""
    SALES_AGENT = "sales_agent"
    ADMIN_AGENT = "admin_agent"
    ANALYST_AGENT = "analyst_agent"


class DocumentType(str, enum.Enum):
    """Knowledge document type enumeration"""
    PRODUCT = "product"
    FAQ = "faq"
    OBJECTIONS = "objections"
    SCRIPTS = "scripts"


class Tenant(Base):
    """Tenant model representing a client/customer of the platform"""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True, nullable=False, index=True)  # URL-safe identifier (e.g., "workhub", "techspace")
    name = Column(String, nullable=False)  # Display name (e.g., "WorkHub Coworking")

    # Configuration (JSONB for flexibility)
    config = Column(JSONB, nullable=False, default=dict)  # Tenant-specific settings
    # Expected config structure:
    # {
    #   "business_type": "coworking|saas|retail|...",
    #   "currency": "BRL|USD|EUR",
    #   "features": {
    #     "enable_handoff": true,
    #     "enable_analytics": true,
    #     "max_users": 1000
    #   },
    #   "funnel_config": {
    #     "stages": [
    #       {"key": "awareness", "name": "Conscientização"},
    #       {"key": "interest", "name": "Interesse"},
    #       ...
    #     ]
    #   },
    #   "llm": {
    #     "provider": "openai",
    #     "model": "gpt-4o-mini",
    #     "temperature": 0.7
    #   }
    # }

    # Authentication
    api_key_hash = Column(String, nullable=True)  # bcrypt hash of API key
    api_key_prefix = Column(String, nullable=True)  # First 8 chars for identification (e.g., "wh_abc12")

    # Status
    status = Column(SQLEnum(TenantStatus), default=TenantStatus.ACTIVE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # For trial tenants

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="tenant", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="tenant")
    messages = relationship("Message", back_populates="tenant")
    leads = relationship("Lead", back_populates="tenant")
    analysis_reports = relationship("AnalysisReport", back_populates="tenant")
    prompt_templates = relationship("PromptTemplate", back_populates="tenant", cascade="all, delete-orphan")
    knowledge_documents = relationship("KnowledgeDocument", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant {self.slug} - {self.name} ({self.status.value})>"


class PromptTemplate(Base):
    """Prompt template model for tenant-specific prompts with versioning"""
    __tablename__ = "prompt_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    prompt_type = Column(SQLEnum(PromptType), nullable=False)
    version = Column(Integer, default=1, nullable=False)  # Versioning support
    is_active = Column(Boolean, default=True, nullable=False)  # Only one active version per (tenant_id, prompt_type)

    # Prompt content
    system_prompt = Column(Text, nullable=False)
    knowledge_base = Column(Text, nullable=True)  # Product/domain knowledge (optional)

    # Metadata
    created_by = Column(String, nullable=True)  # Admin who created it (optional)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="prompt_templates")

    # Constraints
    __table_args__ = (
        UniqueConstraint('tenant_id', 'prompt_type', 'version', name='uq_tenant_prompt_version'),
        Index('idx_tenant_prompt_type_active', 'tenant_id', 'prompt_type', 'is_active'),
    )

    def __repr__(self):
        return f"<PromptTemplate {self.prompt_type.value} v{self.version} (tenant={self.tenant_id})>"


class KnowledgeDocument(Base):
    """Knowledge document model for tenant-specific knowledge base"""
    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String, nullable=False)
    slug = Column(String, nullable=False, index=True)  # URL-safe identifier (e.g., "product-knowledge")
    content = Column(Text, nullable=False)  # Markdown/text content
    document_type = Column(SQLEnum(DocumentType), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="knowledge_documents")

    # Constraints
    __table_args__ = (
        UniqueConstraint('tenant_id', 'slug', name='uq_tenant_knowledge_slug'),
        Index('idx_tenant_document_type', 'tenant_id', 'document_type'),
    )

    def __repr__(self):
        return f"<KnowledgeDocument {self.title} ({self.document_type.value}, tenant={self.tenant_id})>"
