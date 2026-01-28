"""Tenant management schemas"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.models import TenantStatus, PromptType, DocumentType


# ========================================
# TENANT SCHEMAS
# ========================================

class TenantCreate(BaseModel):
    """Schema for creating a new tenant"""
    slug: str = Field(..., description="URL-safe identifier (e.g., 'workhub', 'techspace')", min_length=3, max_length=50)
    name: str = Field(..., description="Display name (e.g., 'WorkHub Coworking')")
    config: Optional[Dict[str, Any]] = Field(default={}, description="Tenant configuration (JSONB)")
    status: Optional[TenantStatus] = Field(default=TenantStatus.ACTIVE, description="Tenant status")
    expires_at: Optional[datetime] = Field(None, description="Expiration date for trial tenants")

    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format"""
        import re
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v

    class Config:
        use_enum_values = True


class TenantUpdate(BaseModel):
    """Schema for updating tenant"""
    name: Optional[str] = Field(None, description="Display name")
    config: Optional[Dict[str, Any]] = Field(None, description="Tenant configuration")
    status: Optional[TenantStatus] = Field(None, description="Tenant status")
    is_active: Optional[bool] = Field(None, description="Active flag")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")

    class Config:
        use_enum_values = True


class TenantResponse(BaseModel):
    """Schema for tenant response"""
    id: UUID
    slug: str
    name: str
    config: Dict[str, Any]
    api_key_prefix: Optional[str]
    status: TenantStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True
        use_enum_values = True


class TenantWithApiKey(TenantResponse):
    """Schema for tenant response with API key (only shown once)"""
    api_key: str = Field(..., description="Full API key (SAVE THIS - shown only once!)")


# ========================================
# PROMPT SCHEMAS
# ========================================

class PromptTemplateCreate(BaseModel):
    """Schema for creating/updating prompt template"""
    prompt_type: PromptType = Field(..., description="Type of prompt (sales_agent, admin_agent, analyst_agent)")
    system_prompt: str = Field(..., description="System prompt content", min_length=10)
    knowledge_base: Optional[str] = Field(None, description="Knowledge base content (optional)")
    created_by: Optional[str] = Field(None, description="Creator identifier")

    class Config:
        use_enum_values = True


class PromptTemplateResponse(BaseModel):
    """Schema for prompt template response"""
    id: UUID
    tenant_id: UUID
    prompt_type: PromptType
    version: int
    is_active: bool
    system_prompt: str
    knowledge_base: Optional[str]
    created_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


# ========================================
# KNOWLEDGE DOCUMENT SCHEMAS
# ========================================

class KnowledgeDocumentCreate(BaseModel):
    """Schema for creating knowledge document"""
    title: str = Field(..., description="Document title")
    slug: str = Field(..., description="URL-safe identifier (e.g., 'product-knowledge')")
    content: str = Field(..., description="Document content (markdown/text)", min_length=10)
    document_type: DocumentType = Field(..., description="Document type (product, faq, objections, scripts)")
    is_active: Optional[bool] = Field(default=True, description="Active flag")

    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format"""
        import re
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v

    class Config:
        use_enum_values = True


class KnowledgeDocumentUpdate(BaseModel):
    """Schema for updating knowledge document"""
    title: Optional[str] = Field(None, description="Document title")
    content: Optional[str] = Field(None, description="Document content")
    document_type: Optional[DocumentType] = Field(None, description="Document type")
    is_active: Optional[bool] = Field(None, description="Active flag")

    class Config:
        use_enum_values = True


class KnowledgeDocumentResponse(BaseModel):
    """Schema for knowledge document response"""
    id: UUID
    tenant_id: UUID
    title: str
    slug: str
    content: str
    document_type: DocumentType
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


# ========================================
# PLAN/PRODUCT SCHEMAS (tenant-specific)
# ========================================

class TenantPlanCreate(BaseModel):
    """Schema for creating tenant plan/product"""
    name: str = Field(..., description="Plan name")
    slug: str = Field(..., description="URL-safe identifier")
    price: float = Field(..., description="Price", ge=0)
    billing_cycle: str = Field(..., description="Billing cycle (daily, monthly, yearly)")
    features: List[str] = Field(default=[], description="List of features")
    description: Optional[str] = Field(None, description="Plan description")
    is_active: Optional[bool] = Field(default=True, description="Active flag")

    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format"""
        import re
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v


class TenantPlanResponse(BaseModel):
    """Schema for tenant plan response"""
    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    price: float
    billing_cycle: str
    features: List[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========================================
# BULK OPERATION SCHEMAS
# ========================================

class BulkTenantSetup(BaseModel):
    """Schema for bulk tenant setup (onboarding)"""
    tenant: TenantCreate
    plans: Optional[List[TenantPlanCreate]] = Field(default=[], description="Initial plans")
    prompts: Optional[Dict[str, str]] = Field(default={}, description="Prompts by type (sales_agent, admin_agent, etc.)")
    knowledge_documents: Optional[List[KnowledgeDocumentCreate]] = Field(default=[], description="Initial knowledge documents")


class BulkTenantSetupResponse(BaseModel):
    """Schema for bulk setup response"""
    tenant: TenantWithApiKey
    plans: List[TenantPlanResponse]
    prompts: List[PromptTemplateResponse]
    knowledge_documents: List[KnowledgeDocumentResponse]
    message: str = Field(..., description="Success message")
