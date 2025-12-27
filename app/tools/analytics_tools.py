"""Analytics-related tools for LangChain agents"""
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from app.models.conversation import Conversation, FunnelStage, ConversationStatus
from app.models.lead import Lead
from app.models.plan import Plan
from app.models.user import User
from app.services.auth_service import is_admin_user
from app.utils.logger import logger
from sqlalchemy.orm import aliased


class GetFunnelMetricsInput(BaseModel):
    """Input schema for get_funnel_metrics tool"""
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")


class GetConversationsByStageInput(BaseModel):
    """Input schema for get_conversations_by_stage tool"""
    stage: str = Field(..., description="Funnel stage to filter by")


class GetRecentLeadsInput(BaseModel):
    """Input schema for get_recent_leads tool"""
    limit: Optional[int] = Field(10, description="Number of recent leads to return (default: 10, max: 50)")


async def get_funnel_metrics(
    db: AsyncSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: Optional[User] = None,
) -> dict:
    """
    Get funnel metrics for a date range
    
    Args:
        db: Database session
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        user: User making the request (for admin check)
    
    Returns:
        Funnel metrics
    """
    # Check admin access
    if not is_admin_user(user):
        return {"error": "Access denied. Admin privileges required."}
    
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.utcnow() - timedelta(days=30)
        
        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.utcnow()
        
        # Get conversations in date range
        result = await db.execute(
            select(Conversation.funnel_stage, func.count(Conversation.id))
            .where(
                and_(
                    Conversation.created_at >= start,
                    Conversation.created_at <= end
                )
            )
            .group_by(Conversation.funnel_stage)
        )
        
        stages = dict(result.all())
        
        # Calculate conversion rates
        total = sum(stages.values())
        conversion_rates = {}
        
        stage_order = [
            FunnelStage.AWARENESS,
            FunnelStage.INTEREST,
            FunnelStage.CONSIDERATION,
            FunnelStage.NEGOTIATION,
            FunnelStage.CLOSED_WON,
        ]
        
        for i, stage in enumerate(stage_order[:-1]):
            current_count = stages.get(stage, 0)
            next_count = stages.get(stage_order[i + 1], 0)
            
            if current_count > 0:
                rate = (next_count / current_count) * 100
                conversion_rates[f"{stage.value}_to_{stage_order[i + 1].value}"] = round(rate, 2)
        
        return {
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "stages": {stage.value: count for stage, count in stages.items()},
            "conversion_rates": conversion_rates,
            "total_leads": total
        }
    except Exception as e:
        logger.error(f"Error getting funnel metrics: {e}")
        return {"error": str(e)}


async def get_conversations_by_stage(stage: str, db: AsyncSession, user: Optional[User] = None) -> dict:
    """
    Get conversations filtered by funnel stage
    
    Args:
        stage: Funnel stage
        db: Database session
        user: User making the request (for admin check)
    
    Returns:
        List of conversations
    """
    # Check admin access
    if not is_admin_user(user):
        return {"error": "Access denied. Admin privileges required."}
    
    try:
        try:
            stage_enum = FunnelStage(stage.lower())
        except ValueError:
            return {"error": f"Invalid stage: {stage}"}
        
        result = await db.execute(
            select(Conversation)
            .where(Conversation.funnel_stage == stage_enum)
            .limit(50)
        )
        conversations = result.scalars().all()
        
        return {
            "stage": stage,
            "count": len(conversations),
            "conversations": [
                {
                    "id": str(conv.id),
                    "user_id": str(conv.user_id),
                    "status": conv.status.value,
                    "context_summary": conv.context_summary,
                    "created_at": conv.created_at.isoformat(),
                }
                for conv in conversations
            ]
        }
    except Exception as e:
        logger.error(f"Error getting conversations by stage: {e}")
        return {"error": str(e)}


async def get_common_objections(db: AsyncSession, user: Optional[User] = None) -> dict:
    """
    Get most common objections from leads
    
    Args:
        db: Database session
        user: User making the request (for admin check)
    
    Returns:
        List of common objections
    """
    # Check admin access
    if not is_admin_user(user):
        return {"error": "Access denied. Admin privileges required."}
    
    try:
        result = await db.execute(
            select(Lead).where(Lead.objections.isnot(None))
        )
        leads = result.scalars().all()
        
        # Count objections
        objection_counts = {}
        for lead in leads:
            if lead.objections:
                for objection in lead.objections:
                    objection_counts[objection] = objection_counts.get(objection, 0) + 1
        
        # Sort by frequency
        sorted_objections = sorted(
            objection_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "total_leads_with_objections": len(leads),
            "objections": [
                {"objection": obj, "count": count}
                for obj, count in sorted_objections[:10]
            ]
        }
    except Exception as e:
        logger.error(f"Error getting common objections: {e}")
        return {"error": str(e)}


async def get_recent_leads(
    db: AsyncSession,
    limit: Optional[int] = 10,
    user: Optional[User] = None,
) -> dict:
    """
    Get most recently created leads with their details
    
    Args:
        db: Database session
        limit: Number of leads to return (default: 10, max: 50)
        user: User making the request (for admin check)
    
    Returns:
        List of recent leads with stage, description, creation date, and contact info
    """
    # Check admin access
    if not is_admin_user(user):
        return {"error": "Access denied. Admin privileges required."}
    
    try:
        # Validate and limit
        if limit is None:
            limit = 10
        limit = min(max(1, limit), 50)  # Between 1 and 50
        
        # Get recent leads from leads table
        leads_result = await db.execute(
            select(Lead)
            .order_by(Lead.created_at.desc())
            .limit(limit * 2)  # Get more to account for filtering
        )
        explicit_leads = leads_result.scalars().all()
        
        # Get conversations with AWAITING_HUMAN status that don't have a lead
        # Use LEFT JOIN to find conversations without leads
        LeadAlias = aliased(Lead)
        conversations_result = await db.execute(
            select(Conversation)
            .outerjoin(LeadAlias, Conversation.id == LeadAlias.conversation_id)
            .where(
                and_(
                    Conversation.status == ConversationStatus.AWAITING_HUMAN,
                    LeadAlias.id.is_(None)  # No lead exists
                )
            )
            .order_by(Conversation.created_at.desc())
            .limit(limit * 2)
        )
        qualified_conversations = conversations_result.scalars().all()
        
        logger.info(
            f"📊 get_recent_leads: Found {len(explicit_leads)} explicit leads and "
            f"{len(qualified_conversations)} qualified conversations without leads (limit={limit})"
        )
        
        # Combine leads and conversations into unified list
        combined_items = []
        
        # Add explicit leads
        for lead in explicit_leads:
            user_result = await db.execute(
                select(User).where(User.id == lead.user_id)
            )
            lead_user = user_result.scalar_one_or_none()
            
            description = lead.next_action if lead.next_action else "Sem descrição disponível"
            
            contact_info = {}
            if lead_user:
                if lead_user.email:
                    contact_info["email"] = lead_user.email
                if lead_user.phone:
                    contact_info["phone"] = lead_user.phone
                contact_info["name"] = lead_user.name or "Sem nome"
            
            combined_items.append({
                "type": "lead",
                "id": str(lead.id),
                "conversation_id": str(lead.conversation_id),
                "stage": lead.stage.value,
                "score": lead.score,
                "description": description,
                "created_at": lead.created_at.isoformat(),
                "contact": contact_info,
                "objections": lead.objections if lead.objections else [],
            })
        
        # Add qualified conversations without leads
        for conv in qualified_conversations:
            user_result = await db.execute(
                select(User).where(User.id == conv.user_id)
            )
            conv_user = user_result.scalar_one_or_none()
            
            # Determine stage based on funnel stage
            if conv.funnel_stage == FunnelStage.NEGOTIATION:
                stage = "hot"
                score = 80
            elif conv.funnel_stage == FunnelStage.CONSIDERATION:
                stage = "warm"
                score = 60
            else:
                stage = "warm"
                score = 50
            
            description = conv.context_summary or conv.handoff_reason or "Conversa qualificada aguardando atendimento"
            
            contact_info = {}
            if conv_user:
                if conv_user.email:
                    contact_info["email"] = conv_user.email
                if conv_user.phone:
                    contact_info["phone"] = conv_user.phone
                contact_info["name"] = conv_user.name or "Sem nome"
            
            combined_items.append({
                "type": "qualified_conversation",
                "id": str(conv.id),
                "conversation_id": str(conv.id),
                "stage": stage,
                "score": score,
                "description": description,
                "created_at": conv.created_at.isoformat(),
                "contact": contact_info,
                "objections": [],
                "handoff_reason": conv.handoff_reason,
            })
        
        # Sort by creation date (most recent first) and limit
        combined_items.sort(key=lambda x: x["created_at"], reverse=True)
        recent_leads = combined_items[:limit]
        
        logger.info(
            f"✅ get_recent_leads: Returning {len(recent_leads)} items "
            f"({sum(1 for x in recent_leads if x['type'] == 'lead')} leads, "
            f"{sum(1 for x in recent_leads if x['type'] == 'qualified_conversation')} qualified conversations)"
        )
        
        return {
            "total": len(recent_leads),
            "leads": recent_leads
        }
    except Exception as e:
        logger.error(f"Error getting recent leads: {e}")
        return {"error": str(e)}


async def get_plan_performance(db: AsyncSession, user: Optional[User] = None) -> dict:
    """
    Get performance metrics for each plan
    
    Args:
        db: Database session
        user: User making the request (for admin check)
    
    Returns:
        Plan performance data
    """
    # Check admin access
    if not is_admin_user(user):
        return {"error": "Access denied. Admin privileges required."}
    
    try:
        # Get all plans
        plans_result = await db.execute(select(Plan).where(Plan.is_active == True))
        plans = plans_result.scalars().all()
        
        performance = []
        
        for plan in plans:
            # Count conversations interested in this plan
            interest_result = await db.execute(
                select(func.count(Conversation.id))
                .where(Conversation.interested_plan_id == plan.id)
            )
            interest_count = interest_result.scalar()
            
            # Count converted conversations
            conversion_result = await db.execute(
                select(func.count(Conversation.id))
                .where(
                    and_(
                        Conversation.interested_plan_id == plan.id,
                        Conversation.status == ConversationStatus.CONVERTED
                    )
                )
            )
            conversion_count = conversion_result.scalar()
            
            conversion_rate = (conversion_count / interest_count * 100) if interest_count > 0 else 0
            
            performance.append({
                "plan_name": plan.name,
                "plan_slug": plan.slug,
                "interest_count": interest_count,
                "conversion_count": conversion_count,
                "conversion_rate": round(conversion_rate, 2)
            })
        
        return {
            "plans": performance,
            "total_plans": len(performance)
        }
    except Exception as e:
        logger.error(f"Error getting plan performance: {e}")
        return {"error": str(e)}


def create_analytics_tools(db: AsyncSession, user: Optional[User] = None):
    """Create analytics-related tools for LangChain agents"""
    
    async def _get_metrics(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        return await get_funnel_metrics(db, start_date, end_date, user)
    
    async def _get_by_stage(stage: str) -> dict:
        return await get_conversations_by_stage(stage, db, user)
    
    async def _get_objections() -> dict:
        return await get_common_objections(db, user)
    
    async def _get_performance() -> dict:
        return await get_plan_performance(db, user)
    
    async def _get_recent_leads(limit: Optional[int] = 10) -> dict:
        return await get_recent_leads(db, limit, user)
    
    return [
        StructuredTool.from_function(
            coroutine=_get_metrics,
            name="get_funnel_metrics",
            description="Get funnel metrics including stage counts and conversion rates for a date range.",
            args_schema=GetFunnelMetricsInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_by_stage,
            name="get_conversations_by_stage",
            description="Get conversations filtered by funnel stage. Use to analyze specific stage.",
            args_schema=GetConversationsByStageInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_objections,
            name="get_common_objections",
            description="Get most common objections from leads. Use to identify patterns.",
        ),
        StructuredTool.from_function(
            coroutine=_get_performance,
            name="get_plan_performance",
            description="Get performance metrics for each plan (interest and conversion). Use to identify best-selling plans.",
        ),
        StructuredTool.from_function(
            coroutine=_get_recent_leads,
            name="get_recent_leads",
            description="Get most recently created leads with their stage, description, creation date, and contact information. Use to see latest leads and follow up.",
            args_schema=GetRecentLeadsInput,
        ),
    ]

