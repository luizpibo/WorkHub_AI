"""Lead-related tools for LangChain agents"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import uuid

from app.models.lead import Lead, LeadStage
from app.models.plan import Plan
from app.utils.logger import logger


class CreateLeadInput(BaseModel):
    """Input schema for create_lead tool"""
    conversation_id: str = Field(..., description="Conversation ID")
    user_id: str = Field(..., description="User ID")
    stage: str = Field(..., description="Lead stage: cold, warm, hot, qualified, converted")
    score: Optional[int] = Field(None, description="Lead score (0-100)")
    preferred_plan_slug: Optional[str] = Field(None, description="Preferred plan slug")


class UpdateLeadInput(BaseModel):
    """Input schema for update_lead tool"""
    conversation_id: str = Field(..., description="Conversation ID")
    stage: Optional[str] = Field(None, description="New lead stage")
    score: Optional[int] = Field(None, description="New lead score")
    objections: Optional[List[str]] = Field(None, description="List of objections")
    next_action: Optional[str] = Field(None, description="Next action to take")


async def create_lead(
    conversation_id: str,
    user_id: str,
    stage: str,
    score: Optional[int],
    db: AsyncSession,
    preferred_plan_slug: Optional[str] = None,
) -> dict:
    """
    Create or update a lead
    
    Args:
        conversation_id: Conversation UUID
        user_id: User UUID
        stage: Lead stage
        score: Lead score (0-100), defaults to 0 if None
        db: Database session
        preferred_plan_slug: Preferred plan slug
    
    Returns:
        Lead information
    """
    try:
        # Validar entrada
        if not conversation_id or not user_id:
            return {
                "success": False,
                "error": "Conversation ID and User ID are required"
            }
        
        # Tratar score None como 0
        if score is None:
            score = 0
        
        # Validar score
        if not isinstance(score, int) or score < 0 or score > 100:
            return {
                "success": False,
                "error": "Score must be an integer between 0 and 100"
            }
        
        # Validar UUIDs
        try:
            conv_uuid = uuid.UUID(conversation_id)
            user_uuid = uuid.UUID(user_id)
        except (ValueError, AttributeError) as e:
            return {
                "success": False,
                "error": f"Invalid UUID format: {str(e)}"
            }
        
        # Check if lead already exists
        result = await db.execute(
            select(Lead).where(Lead.conversation_id == conv_uuid)
        )
        lead = result.scalar_one_or_none()
        
        # Get plan ID if slug provided
        plan_id = None
        if preferred_plan_slug:
            plan_result = await db.execute(
                select(Plan).where(Plan.slug == preferred_plan_slug)
            )
            plan = plan_result.scalar_one_or_none()
            if plan:
                plan_id = plan.id
        
        # Validar stage
        try:
            stage_enum = LeadStage(stage.lower())
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid stage: {stage}. Must be: cold, warm, hot, qualified, converted"
            }
        
        if lead:
            # Update existing lead
            lead.stage = stage_enum
            lead.score = score
            if plan_id:
                lead.preferred_plan_id = plan_id
            message = "Lead updated successfully"
        else:
            # Create new lead
            lead = Lead(
                conversation_id=conv_uuid,
                user_id=user_uuid,
                stage=stage_enum,
                score=score,
                preferred_plan_id=plan_id,
            )
            db.add(lead)
            message = "Lead created successfully"
        
        await db.commit()
        await db.refresh(lead)
        
        logger.info(f"{message}: {conversation_id}, stage={stage}, score={score}")
        
        return {
            "lead_id": str(lead.id),
            "conversation_id": conversation_id,
            "stage": lead.stage.value,
            "score": lead.score,
            "message": message
        }
    except Exception as e:
        logger.error(f"Error creating/updating lead: {e}")
        await db.rollback()
        return {"error": str(e)}


async def update_lead_objections(
    conversation_id: str,
    db: AsyncSession,
    objections: Optional[List[str]] = None,
    next_action: Optional[str] = None,
) -> dict:
    """
    Update lead objections and next action
    
    Args:
        conversation_id: Conversation UUID
        db: Database session
        objections: List of objections
        next_action: Next action to take
    
    Returns:
        Success message
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
        
        result = await db.execute(
            select(Lead).where(Lead.conversation_id == conv_uuid)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            return {"error": "Lead not found"}
        
        if objections is not None:
            lead.objections = objections
        
        if next_action is not None:
            lead.next_action = next_action
        
        await db.commit()
        
        logger.info(f"Updated lead objections for conversation {conversation_id}")
        
        return {
            "conversation_id": conversation_id,
            "message": "Lead objections updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating lead objections: {e}")
        await db.rollback()
        return {"error": str(e)}


def create_lead_tools(db: AsyncSession):
    """Create lead-related tools for LangChain agents"""
    
    async def _create_lead(
        conversation_id: str,
        user_id: str,
        stage: str,
        score: int = 0,
        preferred_plan_slug: Optional[str] = None,
    ) -> dict:
        return await create_lead(conversation_id, user_id, stage, score, db, preferred_plan_slug)
    
    async def _update_objections(
        conversation_id: str,
        objections: Optional[List[str]] = None,
        next_action: Optional[str] = None,
    ) -> dict:
        return await update_lead_objections(conversation_id, db, objections, next_action)
    
    return [
        StructuredTool.from_function(
            coroutine=_create_lead,
            name="create_lead",
            description="Create or update a lead with stage and score. Use to qualify leads and track preferred plans.",
            args_schema=CreateLeadInput,
        ),
        StructuredTool.from_function(
            coroutine=_update_objections,
            name="update_lead_objections",
            description="Update lead objections and next action. Use to track sales obstacles and follow-up actions.",
            args_schema=UpdateLeadInput,
        ),
    ]

