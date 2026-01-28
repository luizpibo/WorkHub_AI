"""Plan-related tools for LangChain agents"""
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from app.models.plan import Plan
from app.core.knowledge import PLANS_SUMMARY, get_plan_comparison
from app.utils.logger import logger


class GetPlansInput(BaseModel):
    """Input schema for get_available_plans / get_plans (no arguments)"""
    pass


class GetPlanDetailsInput(BaseModel):
    """Input schema for get_plan_details tool"""
    plan_slug: str = Field(..., description="Plan slug: day-pass, flex, or dedicado")


class ComparePlansInput(BaseModel):
    """Input schema for compare_plans tool"""
    plan_slugs: List[str] = Field(..., description="List of plan slugs to compare")


async def get_available_plans(db: AsyncSession) -> dict:
    """
    Get all available plans
    
    Args:
        db: Database session
    
    Returns:
        List of available plans
    """
    try:
        result = await db.execute(
            select(Plan).where(Plan.is_active == True)
        )
        plans = result.scalars().all()
        
        plans_list = [
            {
                "id": str(plan.id),
                "name": plan.name,
                "slug": plan.slug,
                "price": float(plan.price),
                "billing_cycle": plan.billing_cycle.value,
                "description": plan.description,
                "features": plan.features,
            }
            for plan in plans
        ]
        
        # Also return formatted summary
        summary = PLANS_SUMMARY
        
        return {
            "plans": plans_list,
            "count": len(plans_list),
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error getting available plans: {e}")
        return {"error": str(e)}


async def get_plan_details(plan_slug: str, db: AsyncSession) -> dict:
    """
    Get detailed information about a specific plan
    
    Args:
        plan_slug: Plan slug
        db: Database session
    
    Returns:
        Plan details
    """
    try:
        result = await db.execute(
            select(Plan).where(Plan.slug == plan_slug)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            return {"error": f"Plan not found: {plan_slug}"}
        
        return {
            "id": str(plan.id),
            "name": plan.name,
            "slug": plan.slug,
            "price": float(plan.price),
            "billing_cycle": plan.billing_cycle.value,
            "description": plan.description,
            "features": plan.features,
            "is_active": plan.is_active,
        }
    except Exception as e:
        logger.error(f"Error getting plan details: {e}")
        return {"error": str(e)}


async def compare_plans(plan_slugs: List[str], db: AsyncSession) -> dict:
    """
    Compare multiple plans
    
    Args:
        plan_slugs: List of plan slugs to compare
        db: Database session
    
    Returns:
        Comparison data
    """
    try:
        plans_data = []
        
        for slug in plan_slugs:
            result = await db.execute(
                select(Plan).where(Plan.slug == slug)
            )
            plan = result.scalar_one_or_none()
            
            if plan:
                plans_data.append({
                    "name": plan.name,
                    "slug": plan.slug,
                    "price": float(plan.price),
                    "billing_cycle": plan.billing_cycle.value,
                    "features": plan.features,
                })
        
        # Get comparison from knowledge base
        comparison = get_plan_comparison(plan_slugs)
        
        return {
            "plans": plans_data,
            "comparison": comparison,
            "count": len(plans_data)
        }
    except Exception as e:
        logger.error(f"Error comparing plans: {e}")
        return {"error": str(e)}


def create_plan_tools(db: AsyncSession):
    """Create plan-related tools for LangChain agents"""
    
    async def _get_plans() -> dict:
        return await get_available_plans(db)
    
    async def _get_details(plan_slug: str) -> dict:
        return await get_plan_details(plan_slug, db)
    
    async def _compare(plan_slugs: List[str]) -> dict:
        return await compare_plans(plan_slugs, db)
    
    return [
        StructuredTool.from_function(
            coroutine=_get_plans,
            name="get_available_plans",
            description="Get list of all available coworking plans with prices and features. Use at the start of conversation.",
        ),
        StructuredTool.from_function(
            coroutine=_get_details,
            name="get_plan_details",
            description="Get detailed information about a specific plan. Use when customer asks about specific plan.",
            args_schema=GetPlanDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_compare,
            name="compare_plans",
            description="Compare multiple plans side by side. Use when customer is deciding between plans.",
            args_schema=ComparePlansInput,
        ),
    ]

