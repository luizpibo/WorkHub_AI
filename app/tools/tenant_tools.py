"""
Tenant-aware tools wrapper for multi-tenant support.

This module wraps existing tools with tenant_id injection to ensure data isolation.
All database queries are automatically scoped to the tenant.
"""
from typing import Optional, Callable, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sql_update
from langchain.tools import StructuredTool
from pydantic import BaseModel

from app.models import User, Conversation, Message, Lead, Plan
from app.utils.logger import logger

# Import original tool schemas
from app.tools.user_tools import (
    GetUserInfoInput, CreateUserInput, UpdateUserInfoInput
)
from app.tools.conversation_tools import (
    GetConversationHistoryInput, UpdateConversationStatusInput, UpdateContextSummaryInput
)
from app.tools.lead_tools import (
    CreateLeadInput, UpdateLeadInput
)
from app.tools.plan_tools import (
    GetPlansInput, GetPlanDetailsInput
)
from app.tools.handoff_tools import (
    RequestHandoffInput
)


class TenantToolRegistry:
    """
    Registry for creating tenant-scoped tools.

    This class creates LangChain tools that automatically filter all database
    queries by tenant_id to ensure complete data isolation between tenants.
    """

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        """
        Initialize tenant tool registry.

        Args:
            db: Database session
            tenant_id: Tenant UUID for data isolation
        """
        self.db = db
        self.tenant_id = tenant_id

    def _create_tenant_tool(
        self,
        func: Callable,
        name: str,
        description: str,
        schema: BaseModel
    ) -> StructuredTool:
        """
        Wrap a tool function with tenant context injection.

        Args:
            func: Original tool function
            name: Tool name
            description: Tool description
            schema: Pydantic schema for tool arguments

        Returns:
            StructuredTool with tenant_id injected
        """
        async def wrapped_func(**kwargs):
            """Wrapper that injects tenant_id and db"""
            return await func(
                db=self.db,
                tenant_id=self.tenant_id,
                **kwargs
            )

        return StructuredTool.from_function(
            coroutine=wrapped_func,
            name=name,
            description=description,
            args_schema=schema
        )

    # ========================================
    # USER TOOLS (tenant-scoped)
    # ========================================

    async def _get_user_info_tenant(self, user_key: str, db: AsyncSession, tenant_id: UUID) -> dict:
        """Get user info (tenant-scoped)"""
        try:
            if not user_key or not isinstance(user_key, str):
                return {"success": False, "error": "User key is required"}

            result = await db.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.user_key == user_key
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                return {
                    "success": False,
                    "error": "User not found",
                    "user_key": user_key
                }

            return {
                "success": True,
                "id": str(user.id),
                "user_key": user.user_key,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "company": user.company,
                "work_type": user.work_type.value if user.work_type else None,
                "created_at": user.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"[Tenant: {tenant_id}] Error getting user info: {e}")
            return {"success": False, "error": str(e)}

    async def _update_user_info_tenant(
        self,
        user_key: str,
        db: AsyncSession,
        tenant_id: UUID,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> dict:
        """Update user info (tenant-scoped)"""
        try:
            result = await db.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.user_key == user_key
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                return {"success": False, "error": "User not found"}

            # Update fields
            if name is not None:
                user.name = name
            if email is not None:
                user.email = email
            if phone is not None:
                user.phone = phone

            await db.commit()
            await db.refresh(user)

            return {
                "success": True,
                "message": "User updated successfully",
                "user_key": user.user_key,
                "name": user.name,
                "email": user.email,
                "phone": user.phone
            }
        except Exception as e:
            logger.error(f"[Tenant: {tenant_id}] Error updating user: {e}")
            await db.rollback()
            return {"success": False, "error": str(e)}

    # ========================================
    # CONVERSATION TOOLS (tenant-scoped)
    # ========================================

    async def _get_conversation_history_tenant(
        self,
        conversation_id: str,
        db: AsyncSession,
        tenant_id: UUID,
        limit: Optional[int] = 10
    ) -> dict:
        """Get conversation history (tenant-scoped)"""
        try:
            import uuid as uuid_mod

            conv_uuid = uuid_mod.UUID(conversation_id)
            limit = limit or 10
            limit = min(max(1, limit), 100)

            result = await db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conv_uuid,
                    Message.tenant_id == tenant_id
                )
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            messages = list(reversed(result.scalars().all()))

            return {
                "success": True,
                "conversation_id": conversation_id,
                "message_count": len(messages),
                "messages": [
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in messages
                ]
            }
        except Exception as e:
            logger.error(f"[Tenant: {tenant_id}] Error getting conversation history: {e}")
            return {"success": False, "error": str(e)}

    async def _update_conversation_status_tenant(
        self,
        conversation_id: str,
        db: AsyncSession,
        tenant_id: UUID,
        status: Optional[str] = None,
        funnel_stage: Optional[str] = None
    ) -> dict:
        """Update conversation status (tenant-scoped)"""
        try:
            import uuid as uuid_mod
            from app.models import ConversationStatus, FunnelStage

            conv_uuid = uuid_mod.UUID(conversation_id)

            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == conv_uuid,
                    Conversation.tenant_id == tenant_id
                )
            )
            conversation = result.scalar_one_or_none()

            if not conversation:
                return {"success": False, "error": "Conversation not found"}

            # Update fields
            if status:
                try:
                    conversation.status = ConversationStatus(status.lower())
                except ValueError:
                    return {"success": False, "error": f"Invalid status: {status}"}

            if funnel_stage:
                try:
                    conversation.funnel_stage = FunnelStage(funnel_stage.lower())
                except ValueError:
                    return {"success": False, "error": f"Invalid funnel stage: {funnel_stage}"}

            await db.commit()
            await db.refresh(conversation)

            return {
                "success": True,
                "message": "Conversation updated",
                "conversation_id": str(conversation.id),
                "status": conversation.status.value,
                "funnel_stage": conversation.funnel_stage.value
            }
        except Exception as e:
            logger.error(f"[Tenant: {tenant_id}] Error updating conversation: {e}")
            await db.rollback()
            return {"success": False, "error": str(e)}

    # ========================================
    # PLAN TOOLS (tenant-scoped)
    # ========================================

    async def _get_plans_tenant(self, db: AsyncSession, tenant_id: UUID) -> dict:
        """Get all active plans (tenant-scoped)"""
        try:
            result = await db.execute(
                select(Plan).where(
                    Plan.tenant_id == tenant_id,
                    Plan.is_active == True
                )
            )
            plans = result.scalars().all()

            return {
                "success": True,
                "count": len(plans),
                "plans": [
                    {
                        "id": str(plan.id),
                        "name": plan.name,
                        "slug": plan.slug,
                        "price": float(plan.price),
                        "billing_cycle": plan.billing_cycle.value,
                        "features": plan.features,
                        "description": plan.description
                    }
                    for plan in plans
                ]
            }
        except Exception as e:
            logger.error(f"[Tenant: {tenant_id}] Error getting plans: {e}")
            return {"success": False, "error": str(e)}

    # ========================================
    # LEAD TOOLS (tenant-scoped)
    # ========================================

    async def _create_lead_tenant(
        self,
        conversation_id: str,
        user_id: str,
        db: AsyncSession,
        tenant_id: UUID,
        stage: str = "cold",
        score: int = 0,
        preferred_plan_id: Optional[str] = None
    ) -> dict:
        """Create or update lead (tenant-scoped)"""
        try:
            import uuid as uuid_mod
            from app.models import LeadStage

            conv_uuid = uuid_mod.UUID(conversation_id)
            user_uuid = uuid_mod.UUID(user_id)

            # Check if lead exists
            result = await db.execute(
                select(Lead).where(
                    Lead.conversation_id == conv_uuid,
                    Lead.tenant_id == tenant_id
                )
            )
            lead = result.scalar_one_or_none()

            if lead:
                # Update existing
                lead.stage = LeadStage(stage.lower())
                lead.score = score
                if preferred_plan_id:
                    lead.preferred_plan_id = uuid_mod.UUID(preferred_plan_id)
            else:
                # Create new
                lead = Lead(
                    tenant_id=tenant_id,
                    conversation_id=conv_uuid,
                    user_id=user_uuid,
                    stage=LeadStage(stage.lower()),
                    score=score,
                    preferred_plan_id=uuid_mod.UUID(preferred_plan_id) if preferred_plan_id else None
                )
                db.add(lead)

            await db.commit()
            await db.refresh(lead)

            return {
                "success": True,
                "message": "Lead created/updated",
                "lead_id": str(lead.id),
                "stage": lead.stage.value,
                "score": lead.score
            }
        except Exception as e:
            logger.error(f"[Tenant: {tenant_id}] Error creating lead: {e}")
            await db.rollback()
            return {"success": False, "error": str(e)}

    # ========================================
    # HANDOFF TOOLS (tenant-scoped)
    # ========================================

    async def _request_handoff_tenant(
        self,
        conversation_id: str,
        reason: str,
        db: AsyncSession,
        tenant_id: UUID
    ) -> dict:
        """Request handoff to human (tenant-scoped)"""
        try:
            import uuid as uuid_mod
            from datetime import datetime
            from app.models import ConversationStatus

            conv_uuid = uuid_mod.UUID(conversation_id)

            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == conv_uuid,
                    Conversation.tenant_id == tenant_id
                )
            )
            conversation = result.scalar_one_or_none()

            if not conversation:
                return {"success": False, "error": "Conversation not found"}

            # Update conversation for handoff
            conversation.status = ConversationStatus.AWAITING_HUMAN
            conversation.handoff_reason = reason
            conversation.handoff_requested_at = datetime.utcnow()

            await db.commit()

            return {
                "success": True,
                "message": "Handoff requested successfully",
                "conversation_id": str(conversation.id),
                "status": "awaiting_human",
                "reason": reason
            }
        except Exception as e:
            logger.error(f"[Tenant: {tenant_id}] Error requesting handoff: {e}")
            await db.rollback()
            return {"success": False, "error": str(e)}

    # ========================================
    # TOOL REGISTRATION
    # ========================================

    async def get_all_tools(self) -> list:
        """
        Get all tenant-scoped tools.

        Returns:
            List of StructuredTool instances with tenant context
        """
        tools = []

        # User tools
        tools.append(self._create_tenant_tool(
            self._get_user_info_tenant,
            "get_user_info",
            "Get user information by user_key",
            GetUserInfoInput
        ))

        tools.append(self._create_tenant_tool(
            self._update_user_info_tenant,
            "update_user_info",
            "Update user information (name, email, phone)",
            UpdateUserInfoInput
        ))

        # Conversation tools
        tools.append(self._create_tenant_tool(
            self._get_conversation_history_tenant,
            "get_conversation_history",
            "Get conversation message history",
            GetConversationHistoryInput
        ))

        tools.append(self._create_tenant_tool(
            self._update_conversation_status_tenant,
            "update_conversation_status",
            "Update conversation status and funnel stage",
            UpdateConversationStatusInput
        ))

        # Plan tools
        tools.append(self._create_tenant_tool(
            self._get_plans_tenant,
            "get_plans",
            "Get all active plans/products",
            GetPlansInput
        ))

        # Lead tools
        tools.append(self._create_tenant_tool(
            self._create_lead_tenant,
            "create_lead",
            "Create or update lead information",
            CreateLeadInput
        ))

        # Handoff tools
        tools.append(self._create_tenant_tool(
            self._request_handoff_tenant,
            "request_handoff",
            "Request transfer to human agent",
            RequestHandoffInput
        ))

        logger.info(f"[Tenant: {self.tenant_id}] Created {len(tools)} tenant-scoped tools")
        return tools
