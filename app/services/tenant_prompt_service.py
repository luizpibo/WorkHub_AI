"""Tenant-aware prompt service for multi-tenant support"""
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import time

from app.models import Tenant, PromptTemplate, PromptType, KnowledgeDocument, DocumentType
from app.utils.logger import logger


class TenantPromptService:
    """
    Service for managing tenant-specific prompts with caching.

    Features:
    - Database-backed prompts (TenantPrompt table)
    - TTL-based caching (10 minutes for prompts, 30 minutes for knowledge)
    - Fallback to file-based templates for new tenants
    - Versioning support
    """

    def __init__(self):
        self.prompts_dir = Path("prompts")
        self.knowledge_dir = self.prompts_dir / "knowledge"

        # Caches with TTL
        self.prompt_cache: Dict[str, tuple[str, float]] = {}  # cache_key -> (content, timestamp)
        self.knowledge_cache: Dict[str, tuple[str, float]] = {}

        # Cache TTLs (in seconds)
        self.prompt_ttl = 600  # 10 minutes
        self.knowledge_ttl = 1800  # 30 minutes

    def _get_cache_key(self, tenant_id: UUID, key_type: str, identifier: str) -> str:
        """Generate cache key"""
        return f"{tenant_id}:{key_type}:{identifier}"

    def _is_cache_valid(self, timestamp: float, ttl: int) -> bool:
        """Check if cached value is still valid"""
        return (time.time() - timestamp) < ttl

    async def get_prompt(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        prompt_type: PromptType
    ) -> str:
        """
        Get prompt template for tenant (with caching).

        Order of precedence:
        1. Cache (if valid)
        2. Database (active version)
        3. File fallback (default template)

        Args:
            db: Database session
            tenant_id: Tenant UUID
            prompt_type: Type of prompt (SALES_AGENT, ADMIN_AGENT, etc.)

        Returns:
            Prompt template content
        """
        cache_key = self._get_cache_key(tenant_id, "prompt", prompt_type.value)

        # Check cache
        if cache_key in self.prompt_cache:
            cached_content, timestamp = self.prompt_cache[cache_key]
            if self._is_cache_valid(timestamp, self.prompt_ttl):
                logger.debug(f"Prompt cache hit: {cache_key}")
                return cached_content
            else:
                logger.debug(f"Prompt cache expired: {cache_key}")

        # Try database
        result = await db.execute(
            select(PromptTemplate)
            .where(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.prompt_type == prompt_type,
                PromptTemplate.is_active == True
            )
            .order_by(PromptTemplate.version.desc())
        )
        prompt_template = result.scalar_one_or_none()

        if prompt_template:
            logger.info(f"Loaded prompt from DB: tenant={tenant_id}, type={prompt_type.value}, version={prompt_template.version}")
            content = prompt_template.system_prompt
        else:
            # Fallback to file
            logger.info(f"No DB prompt found, using file fallback: tenant={tenant_id}, type={prompt_type.value}")
            content = self._load_default_template(prompt_type)

        # Cache and return
        self.prompt_cache[cache_key] = (content, time.time())
        return content

    async def get_knowledge_base(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        document_slug: str = "product-knowledge"
    ) -> str:
        """
        Get knowledge base content for tenant (with caching).

        Args:
            db: Database session
            tenant_id: Tenant UUID
            document_slug: Knowledge document slug (default: "product-knowledge")

        Returns:
            Knowledge base content (or empty string if not found)
        """
        cache_key = self._get_cache_key(tenant_id, "knowledge", document_slug)

        # Check cache
        if cache_key in self.knowledge_cache:
            cached_content, timestamp = self.knowledge_cache[cache_key]
            if self._is_cache_valid(timestamp, self.knowledge_ttl):
                logger.debug(f"Knowledge cache hit: {cache_key}")
                return cached_content

        # Try database
        result = await db.execute(
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.tenant_id == tenant_id,
                KnowledgeDocument.slug == document_slug,
                KnowledgeDocument.is_active == True
            )
        )
        knowledge_doc = result.scalar_one_or_none()

        if knowledge_doc:
            logger.info(f"Loaded knowledge from DB: tenant={tenant_id}, slug={document_slug}")
            content = knowledge_doc.content
        else:
            # Try file fallback (for backward compatibility)
            logger.info(f"No DB knowledge found, trying file fallback: tenant={tenant_id}")
            try:
                content = self._load_knowledge_file("workhub_product.txt")
            except FileNotFoundError:
                logger.warning(f"No knowledge found for tenant {tenant_id}")
                content = ""

        # Cache and return
        self.knowledge_cache[cache_key] = (content, time.time())
        return content

    def _load_default_template(self, prompt_type: PromptType) -> str:
        """
        Load default prompt template from file.

        Args:
            prompt_type: Type of prompt

        Returns:
            Template content
        """
        # Map prompt types to filenames
        filename_map = {
            PromptType.SALES_AGENT: "sales_agent.txt",
            PromptType.ADMIN_AGENT: "admin_agent.txt",
            PromptType.ANALYST_AGENT: "analyst_agent.txt",
        }

        filename = filename_map.get(prompt_type)
        if not filename:
            raise ValueError(f"Unknown prompt type: {prompt_type}")

        template_path = self.prompts_dir / filename

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Loaded default template: {filename}")
            return content
        except FileNotFoundError:
            logger.error(f"Default template not found: {filename}")
            raise

    def _load_knowledge_file(self, filename: str) -> str:
        """Load knowledge from file (fallback)"""
        knowledge_path = self.knowledge_dir / filename

        with open(knowledge_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Loaded knowledge file: {filename}")
        return content

    def inject_variables(self, template: str, **kwargs: Any) -> str:
        """
        Inject variables into template.

        Args:
            template: Template string with {variable} placeholders
            **kwargs: Variables to inject

        Returns:
            Template with variables replaced
        """
        try:
            # Replace None values with default
            safe_kwargs = {}
            for key, value in kwargs.items():
                if value is None:
                    safe_kwargs[key] = "Não informado"
                elif isinstance(value, list):
                    safe_kwargs[key] = "\n".join(f"- {item}" for item in value)
                else:
                    safe_kwargs[key] = str(value)

            result = template.format(**safe_kwargs)
            logger.debug("Injected variables into template")
            return result
        except KeyError as e:
            logger.error(f"Missing variable in template: {e}")
            raise
        except Exception as e:
            logger.error(f"Error injecting variables: {e}")
            raise

    async def get_sales_prompt(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_name: str = None,
        work_type: str = None,
        conversation_summary: str = None,
        funnel_stage: str = "awareness",
        available_plans: str = None,
        conversation_id: str = None,
    ) -> str:
        """
        Get complete sales agent prompt with injected variables.

        Args:
            db: Database session
            tenant_id: Tenant UUID
            user_name: User's name
            work_type: Type of work
            conversation_summary: Conversation summary
            funnel_stage: Current funnel stage
            available_plans: Formatted list of available plans
            conversation_id: Conversation ID

        Returns:
            Complete prompt ready for LLM
        """
        # Load prompt template
        template = await self.get_prompt(db, tenant_id, PromptType.SALES_AGENT)

        # Load knowledge base
        product_knowledge = await self.get_knowledge_base(db, tenant_id)

        # Get tenant config for business-specific variables
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            logger.warning(f"Tenant {tenant_id} not found for prompt injection")

        # Inject variables
        return self.inject_variables(
            template,
            product_knowledge=product_knowledge,
            tenant_name=tenant.name if tenant else "Empresa",
            business_domain=tenant.config.get("business_type", "coworking") if tenant else "coworking",
            user_name=user_name or "Cliente",
            work_type=work_type or "Não informado",
            conversation_summary=conversation_summary or "Primeira interação",
            funnel_stage=funnel_stage,
            available_plans=available_plans or "Carregando planos...",
            conversation_id=conversation_id or "N/A",
        )

    async def get_admin_prompt(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        conversation_id: str = None,
    ) -> str:
        """
        Get admin agent prompt with injected variables.

        Args:
            db: Database session
            tenant_id: Tenant UUID
            conversation_id: Conversation ID

        Returns:
            Complete admin prompt ready for LLM
        """
        template = await self.get_prompt(db, tenant_id, PromptType.ADMIN_AGENT)

        return self.inject_variables(
            template,
            conversation_id=conversation_id or "N/A",
        )

    async def get_analyst_prompt(
        self,
        db: AsyncSession,
        tenant_id: UUID,
    ) -> str:
        """
        Get analyst agent prompt.

        Args:
            db: Database session
            tenant_id: Tenant UUID

        Returns:
            Analyst prompt ready for LLM
        """
        return await self.get_prompt(db, tenant_id, PromptType.ANALYST_AGENT)

    def invalidate_cache(self, tenant_id: UUID, prompt_type: Optional[PromptType] = None):
        """
        Invalidate cache for tenant.

        Args:
            tenant_id: Tenant UUID
            prompt_type: Specific prompt type to invalidate (or None for all)
        """
        if prompt_type:
            # Invalidate specific prompt type
            cache_key = self._get_cache_key(tenant_id, "prompt", prompt_type.value)
            self.prompt_cache.pop(cache_key, None)
            logger.info(f"Invalidated prompt cache: {cache_key}")
        else:
            # Invalidate all for tenant
            keys_to_remove = [
                k for k in self.prompt_cache
                if k.startswith(f"{tenant_id}:")
            ]
            for key in keys_to_remove:
                self.prompt_cache.pop(key, None)
            logger.info(f"Invalidated all prompt cache for tenant {tenant_id}")

        # Also invalidate knowledge cache
        knowledge_keys = [
            k for k in self.knowledge_cache
            if k.startswith(f"{tenant_id}:")
        ]
        for key in knowledge_keys:
            self.knowledge_cache.pop(key, None)


# Singleton instance
tenant_prompt_service = TenantPromptService()
