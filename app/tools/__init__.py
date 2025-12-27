"""LangChain tools for database interaction"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from langchain.tools import BaseTool

from app.tools.user_tools import create_user_tools
from app.tools.conversation_tools import create_conversation_tools
from app.tools.message_tools import create_message_tools
from app.tools.lead_tools import create_lead_tools
from app.tools.plan_tools import create_plan_tools
from app.tools.analytics_tools import create_analytics_tools
from app.tools.handoff_tools import create_handoff_tools
from app.models.user import User
from app.utils.logger import logger


def create_sales_tools(db: AsyncSession) -> List[BaseTool]:
    """
    Create all tools for Sales Agent
    
    Args:
        db: Database session
    
    Returns:
        List of LangChain tools
    """
    tools = []
    
    try:
        logger.info("Creating user tools...")
        tools.extend(create_user_tools(db))
        logger.info(f"User tools created: {len([t for t in tools if 'user' in t.name.lower()])}")
    except Exception as e:
        logger.error(f"Error creating user tools: {e}")
        raise
    
    try:
        logger.info("Creating conversation tools...")
        tools.extend(create_conversation_tools(db))
    except Exception as e:
        logger.error(f"Error creating conversation tools: {e}")
        raise
    
    try:
        logger.info("Creating message tools...")
        tools.extend(create_message_tools(db))
    except Exception as e:
        logger.error(f"Error creating message tools: {e}")
        raise
    
    try:
        logger.info("Creating lead tools...")
        tools.extend(create_lead_tools(db))
    except Exception as e:
        logger.error(f"Error creating lead tools: {e}")
        raise
    
    try:
        logger.info("Creating plan tools...")
        tools.extend(create_plan_tools(db))
    except Exception as e:
        logger.error(f"Error creating plan tools: {e}")
        raise
    
    try:
        logger.info("Creating handoff tools...")
        tools.extend(create_handoff_tools(db))
    except Exception as e:
        logger.error(f"Error creating handoff tools: {e}")
        raise
    
    logger.info(f"Total tools created: {len(tools)}")
    return tools


def create_analyst_tools(db: AsyncSession, user: Optional[User] = None) -> List[BaseTool]:
    """
    Create all tools for Analyst Agent
    
    Args:
        db: Database session
        user: User making the request (for admin check)
    
    Returns:
        List of LangChain tools
    """
    tools = []
    tools.extend(create_analytics_tools(db, user))
    tools.extend(create_conversation_tools(db))
    
    return tools


def create_admin_tools(db: AsyncSession, user: Optional[User] = None) -> List[BaseTool]:
    """
    Create all tools for Admin Agent
    
    Combines analytics tools (with admin access) and conversation tools
    to allow admins to analyze data and access conversation history.
    
    Args:
        db: Database session
        user: User making the request (must be admin)
    
    Returns:
        List of LangChain tools
    """
    tools = []
    
    # Analytics tools (already restricted to admin)
    tools.extend(create_analytics_tools(db, user))
    
    # Conversation tools for accessing history
    tools.extend(create_conversation_tools(db))
    
    # Message tools for viewing messages
    tools.extend(create_message_tools(db))
    
    logger.info(f"Admin tools created: {len(tools)}")
    return tools


__all__ = [
    "create_sales_tools",
    "create_analyst_tools",
    "create_admin_tools",
]
