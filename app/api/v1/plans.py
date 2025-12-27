"""Plan API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.deps import get_db
from app.schemas.plan import PlanResponse
from app.models.plan import Plan
from app.utils.logger import logger

router = APIRouter()


@router.get("/plans", response_model=List[PlanResponse])
async def get_plans(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all available plans
    
    Returns list of all active coworking plans with details
    """
    try:
        result = await db.execute(
            select(Plan).where(Plan.is_active == True)
        )
        plans = result.scalars().all()
        
        return plans
        
    except Exception as e:
        logger.error(f"Error getting plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans/{slug}", response_model=PlanResponse)
async def get_plan(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get plan details by slug
    
    - **slug**: Plan slug (day-pass, flex, or dedicado)
    """
    try:
        result = await db.execute(
            select(Plan).where(Plan.slug == slug)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        return plan
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

