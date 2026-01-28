"""Analyst service for sales analytics"""
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.analyst_agent import AnalystAgent
from app.models.user import User
from app.utils.logger import logger


class AnalystService:
    """Service for managing sales analytics"""
    
    def __init__(self, db: AsyncSession, user: Optional[User] = None):
        self.db = db
        self.user = user
        self.analyst_agent = AnalystAgent(db, user)
    
    async def analyze_conversation(self, conversation_id: str) -> dict:
        """
        Analyze a specific conversation
        
        Args:
            conversation_id: Conversation UUID
        
        Returns:
            Analysis results
        """
        try:
            result = await self.analyst_agent.analyze_conversation(conversation_id)
            return result
        except Exception as e:
            logger.error(f"Error in analyze_conversation: {e}")
            raise
    
    async def get_funnel_metrics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        Get funnel metrics with AI analysis
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Funnel metrics and analysis
        """
        try:
            result = await self.analyst_agent.get_funnel_analysis(start_date, end_date)
            return result
        except Exception as e:
            logger.error(f"Error in get_funnel_metrics: {e}")
            raise



