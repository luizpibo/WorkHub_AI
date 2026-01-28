"""Tenant management API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import bcrypt
import uuid

from app.api.deps import get_db, get_current_tenant, get_tenant_id
from app.models import (
    Tenant, TenantStatus, PromptTemplate, PromptType,
    KnowledgeDocument, DocumentType, Plan, BillingCycle
)
from app.schemas.tenant import (
    TenantCreate, TenantUpdate, TenantResponse, TenantWithApiKey,
    PromptTemplateCreate, PromptTemplateResponse,
    KnowledgeDocumentCreate, KnowledgeDocumentUpdate, KnowledgeDocumentResponse,
    TenantPlanCreate, TenantPlanResponse,
    BulkTenantSetup, BulkTenantSetupResponse
)
from app.services.tenant_prompt_service import tenant_prompt_service
from app.utils.logger import logger

router = APIRouter()


# ========================================
# TENANT CRUD ENDPOINTS
# ========================================

@router.post("/admin/tenants", response_model=TenantWithApiKey, status_code=201)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new tenant (platform admin only).

    Returns the tenant data with the API key (SHOWN ONLY ONCE).

    **Important:** Save the API key immediately - it cannot be retrieved later!
    """
    try:
        # Check if slug already exists
        result = await db.execute(
            select(Tenant).where(Tenant.slug == tenant_data.slug)
        )
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Tenant with slug '{tenant_data.slug}' already exists"
            )

        # Generate API key
        api_key = f"{tenant_data.slug[:2]}_{uuid.uuid4().hex[:32]}"
        api_key_hash = bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        api_key_prefix = api_key[:8]

        # Create tenant
        tenant = Tenant(
            id=uuid.uuid4(),
            slug=tenant_data.slug,
            name=tenant_data.name,
            config=tenant_data.config,
            api_key_hash=api_key_hash,
            api_key_prefix=api_key_prefix,
            status=tenant_data.status,
            expires_at=tenant_data.expires_at
        )

        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)

        logger.info(f"Created tenant: {tenant.slug} (ID: {tenant.id})")

        # Return with full API key
        return TenantWithApiKey(
            **tenant.__dict__,
            api_key=api_key
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tenant: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating tenant: {str(e)}")


@router.get("/admin/tenants", response_model=list[TenantResponse])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    List all tenants (platform admin only).
    """
    try:
        result = await db.execute(
            select(Tenant)
            .offset(skip)
            .limit(limit)
            .order_by(Tenant.created_at.desc())
        )
        tenants = result.scalars().all()

        return [TenantResponse.from_orm(tenant) for tenant in tenants]

    except Exception as e:
        logger.error(f"Error listing tenants: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing tenants: {str(e)}")


@router.get("/admin/tenants/{tenant_slug}", response_model=TenantResponse)
async def get_tenant(
    tenant_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant by slug (platform admin only).
    """
    try:
        result = await db.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant '{tenant_slug}' not found")

        return TenantResponse.from_orm(tenant)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting tenant: {str(e)}")


@router.put("/admin/tenants/{tenant_slug}", response_model=TenantResponse)
async def update_tenant(
    tenant_slug: str,
    tenant_data: TenantUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update tenant (platform admin only).
    """
    try:
        result = await db.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant '{tenant_slug}' not found")

        # Update fields
        if tenant_data.name is not None:
            tenant.name = tenant_data.name
        if tenant_data.config is not None:
            tenant.config = tenant_data.config
        if tenant_data.status is not None:
            tenant.status = tenant_data.status
        if tenant_data.is_active is not None:
            tenant.is_active = tenant_data.is_active
        if tenant_data.expires_at is not None:
            tenant.expires_at = tenant_data.expires_at

        await db.commit()
        await db.refresh(tenant)

        logger.info(f"Updated tenant: {tenant.slug}")

        return TenantResponse.from_orm(tenant)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating tenant: {str(e)}")


@router.delete("/admin/tenants/{tenant_slug}", status_code=200)
async def delete_tenant(
    tenant_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete tenant (set is_active=False) (platform admin only).

    **Warning:** This does NOT delete data - it only deactivates the tenant.
    """
    try:
        result = await db.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant '{tenant_slug}' not found")

        # Soft delete
        tenant.is_active = False
        tenant.status = TenantStatus.CANCELLED

        await db.commit()

        logger.info(f"Soft deleted tenant: {tenant.slug}")

        return {"message": f"Tenant '{tenant_slug}' deactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tenant: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting tenant: {str(e)}")


# ========================================
# PROMPT MANAGEMENT ENDPOINTS
# ========================================

@router.put("/tenants/prompts/{prompt_type}", response_model=PromptTemplateResponse)
async def update_tenant_prompt(
    prompt_type: PromptType,
    prompt_data: PromptTemplateCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Update prompt for current tenant (creates new version).

    This endpoint is called by tenant admins to customize their prompts.
    """
    try:
        # Get tenant from middleware
        tenant_id = await get_tenant_id(request)

        # Get max version
        result = await db.execute(
            select(PromptTemplate.version)
            .where(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.prompt_type == prompt_type
            )
            .order_by(PromptTemplate.version.desc())
        )
        max_version = result.scalar_one_or_none() or 0
        new_version = max_version + 1

        # Deactivate previous versions
        await db.execute(
            select(PromptTemplate)
            .where(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.prompt_type == prompt_type
            )
        )
        # Update is_active for all matching prompts
        prompts_to_deactivate = await db.execute(
            select(PromptTemplate).where(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.prompt_type == prompt_type
            )
        )
        for prompt in prompts_to_deactivate.scalars():
            prompt.is_active = False

        # Create new version
        new_prompt = PromptTemplate(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            prompt_type=prompt_type,
            version=new_version,
            system_prompt=prompt_data.system_prompt,
            knowledge_base=prompt_data.knowledge_base,
            created_by=prompt_data.created_by,
            is_active=True
        )

        db.add(new_prompt)
        await db.commit()
        await db.refresh(new_prompt)

        # Invalidate cache
        tenant_prompt_service.invalidate_cache(tenant_id, prompt_type)

        logger.info(f"Updated prompt for tenant {tenant_id}: {prompt_type.value} v{new_version}")

        return PromptTemplateResponse.from_orm(new_prompt)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating prompt: {str(e)}")


@router.get("/tenants/prompts", response_model=list[PromptTemplateResponse])
async def list_tenant_prompts(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    List all prompts for current tenant.
    """
    try:
        tenant_id = await get_tenant_id(request)

        result = await db.execute(
            select(PromptTemplate)
            .where(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.is_active == True
            )
            .order_by(PromptTemplate.prompt_type, PromptTemplate.version.desc())
        )
        prompts = result.scalars().all()

        return [PromptTemplateResponse.from_orm(prompt) for prompt in prompts]

    except Exception as e:
        logger.error(f"Error listing prompts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing prompts: {str(e)}")


# ========================================
# KNOWLEDGE DOCUMENT ENDPOINTS
# ========================================

@router.post("/tenants/knowledge", response_model=KnowledgeDocumentResponse, status_code=201)
async def create_knowledge_document(
    doc_data: KnowledgeDocumentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create knowledge document for current tenant.
    """
    try:
        tenant_id = await get_tenant_id(request)

        # Check if slug exists
        result = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.tenant_id == tenant_id,
                KnowledgeDocument.slug == doc_data.slug
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Knowledge document with slug '{doc_data.slug}' already exists"
            )

        # Create document
        document = KnowledgeDocument(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            title=doc_data.title,
            slug=doc_data.slug,
            content=doc_data.content,
            document_type=doc_data.document_type,
            is_active=doc_data.is_active
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        logger.info(f"Created knowledge document for tenant {tenant_id}: {doc_data.slug}")

        return KnowledgeDocumentResponse.from_orm(document)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating knowledge document: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating knowledge document: {str(e)}")


@router.get("/tenants/knowledge", response_model=list[KnowledgeDocumentResponse])
async def list_knowledge_documents(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    List all knowledge documents for current tenant.
    """
    try:
        tenant_id = await get_tenant_id(request)

        result = await db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.tenant_id == tenant_id)
            .order_by(KnowledgeDocument.created_at.desc())
        )
        documents = result.scalars().all()

        return [KnowledgeDocumentResponse.from_orm(doc) for doc in documents]

    except Exception as e:
        logger.error(f"Error listing knowledge documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing knowledge documents: {str(e)}")


@router.put("/tenants/knowledge/{document_slug}", response_model=KnowledgeDocumentResponse)
async def update_knowledge_document(
    document_slug: str,
    doc_data: KnowledgeDocumentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Update knowledge document for current tenant.
    """
    try:
        tenant_id = await get_tenant_id(request)

        result = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.tenant_id == tenant_id,
                KnowledgeDocument.slug == document_slug
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail=f"Knowledge document '{document_slug}' not found")

        # Update fields
        if doc_data.title is not None:
            document.title = doc_data.title
        if doc_data.content is not None:
            document.content = doc_data.content
        if doc_data.document_type is not None:
            document.document_type = doc_data.document_type
        if doc_data.is_active is not None:
            document.is_active = doc_data.is_active

        await db.commit()
        await db.refresh(document)

        logger.info(f"Updated knowledge document for tenant {tenant_id}: {document_slug}")

        return KnowledgeDocumentResponse.from_orm(document)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating knowledge document: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating knowledge document: {str(e)}")


# ========================================
# PLAN/PRODUCT ENDPOINTS
# ========================================

@router.post("/tenants/plans", response_model=TenantPlanResponse, status_code=201)
async def create_tenant_plan(
    plan_data: TenantPlanCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create plan/product for current tenant.
    """
    try:
        tenant_id = await get_tenant_id(request)

        # Check if slug exists
        result = await db.execute(
            select(Plan).where(
                Plan.tenant_id == tenant_id,
                Plan.slug == plan_data.slug
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Plan with slug '{plan_data.slug}' already exists"
            )

        # Create plan
        plan = Plan(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=plan_data.name,
            slug=plan_data.slug,
            price=plan_data.price,
            billing_cycle=BillingCycle(plan_data.billing_cycle.lower()),
            features=plan_data.features,
            description=plan_data.description,
            is_active=plan_data.is_active
        )

        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        logger.info(f"Created plan for tenant {tenant_id}: {plan_data.slug}")

        return TenantPlanResponse(
            id=plan.id,
            tenant_id=plan.tenant_id,
            name=plan.name,
            slug=plan.slug,
            price=float(plan.price),
            billing_cycle=plan.billing_cycle.value,
            features=plan.features,
            description=plan.description,
            is_active=plan.is_active,
            created_at=plan.created_at,
            updated_at=plan.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating plan: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating plan: {str(e)}")


@router.get("/tenants/plans", response_model=list[TenantPlanResponse])
async def list_tenant_plans(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    List all plans for current tenant.
    """
    try:
        tenant_id = await get_tenant_id(request)

        result = await db.execute(
            select(Plan)
            .where(Plan.tenant_id == tenant_id)
            .order_by(Plan.created_at.desc())
        )
        plans = result.scalars().all()

        return [
            TenantPlanResponse(
                id=plan.id,
                tenant_id=plan.tenant_id,
                name=plan.name,
                slug=plan.slug,
                price=float(plan.price),
                billing_cycle=plan.billing_cycle.value,
                features=plan.features,
                description=plan.description,
                is_active=plan.is_active,
                created_at=plan.created_at,
                updated_at=plan.updated_at
            )
            for plan in plans
        ]

    except Exception as e:
        logger.error(f"Error listing plans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing plans: {str(e)}")
