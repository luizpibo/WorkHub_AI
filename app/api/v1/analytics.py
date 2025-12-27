"""Analytics API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.api.deps import get_db
from app.schemas.analytics import AnalyzeRequest, FunnelMetrics, PlanPerformanceResponse
from app.services.analyst_service import create_analyst_service
from app.tools.analytics_tools import get_funnel_metrics, get_plan_performance
from app.models.user import User
from app.services.auth_service import is_admin_user
from app.utils.logger import logger

router = APIRouter()


@router.post("/analytics/analyze")
async def analyze_conversation(
    request: AnalyzeRequest,
    user_key: str = Query(..., description="User key for admin verification"),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a specific conversation using AI (Admin only)
    
    - **conversation_id**: Conversation ID to analyze
    - **user_key**: User key for admin verification
    
    Returns detailed analysis with insights and recommendations
    """
    try:
        # Get user and verify admin access
        result = await db.execute(select(User).where(User.user_key == user_key))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not is_admin_user(user):
            raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
        
        analyst_service = await create_analyst_service(db, user)
        
        result = await analyst_service.analyze_conversation(
            conversation_id=str(request.conversation_id)
        )
        
        return result
        
    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error in analyze endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/funnel")
async def get_funnel_analytics(
    user_key: str = Query(..., description="User key for admin verification"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get funnel metrics and AI analysis (Admin only)
    
    - **user_key**: User key for admin verification
    - **start_date**: Start date for analysis (optional)
    - **end_date**: End date for analysis (optional)
    
    Returns funnel metrics with conversion rates and AI insights
    """
    try:
        # Get user and verify admin access
        result = await db.execute(select(User).where(User.user_key == user_key))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not is_admin_user(user):
            raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
        
        # Get raw metrics
        metrics = await get_funnel_metrics(db, start_date, end_date, user)
        
        # Get AI analysis
        analyst_service = await create_analyst_service(db, user)
        analysis = await analyst_service.get_funnel_metrics(start_date, end_date)
        
        return {
            "metrics": metrics,
            "ai_analysis": analysis
        }
        
    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error in funnel analytics endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/plans-performance")
async def get_plans_performance(
    user_key: str = Query(..., description="User key for admin verification"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance metrics for each plan (Admin only)
    
    - **user_key**: User key for admin verification
    
    Returns interest counts, conversion counts, and conversion rates per plan
    """
    try:
        # Get user and verify admin access
        result = await db.execute(select(User).where(User.user_key == user_key))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not is_admin_user(user):
            raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
        
        result = await get_plan_performance(db, user)
        return result
        
    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error in plans performance endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

