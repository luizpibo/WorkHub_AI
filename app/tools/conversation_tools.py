"""Conversation-related tools for LangChain agents"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import uuid

from app.models.conversation import Conversation, ConversationStatus, FunnelStage
from app.models.message import Message, MessageRole
from app.utils.logger import logger


class GetConversationHistoryInput(BaseModel):
    """Input schema for get_conversation_history tool"""
    conversation_id: str = Field(..., description="Conversation ID")
    limit: Optional[int] = Field(None, description="Number of messages to retrieve")


class UpdateConversationStatusInput(BaseModel):
    """Input schema for update_conversation_status tool"""
    conversation_id: str = Field(..., description="Conversation ID")
    status: Optional[str] = Field(None, description="New status: active, converted, lost, abandoned")
    funnel_stage: Optional[str] = Field(None, description="New funnel stage: awareness, interest, consideration, negotiation, closed_won, closed_lost")


class UpdateContextSummaryInput(BaseModel):
    """Input schema for update_context_summary tool"""
    conversation_id: str = Field(..., description="Conversation ID")
    summary: str = Field(..., description="Updated context summary")


async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession,
    limit: Optional[int] = None
) -> dict:
    """
    Get conversation message history
    
    Args:
        conversation_id: Conversation UUID
        db: Database session
        limit: Number of messages to retrieve (defaults to 10 if None)
    
    Returns:
        List of messages
    """
    try:
        # Validar entrada
        if not conversation_id or conversation_id.strip() == "":
            return {
                "success": False,
                "error": "Conversation ID is required"
            }
        
        # Verificar se não é um placeholder inválido
        if conversation_id.lower() in ["default_conversation_id", "conversation_id", "none", "null"]:
            logger.warning(f"Invalid conversation_id provided: {conversation_id}")
            return {
                "success": False,
                "error": f"Invalid conversation ID: {conversation_id}. Please provide a valid UUID."
            }
        
        # Validar formato UUID
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except ValueError as ve:
            logger.error(f"Invalid UUID format for conversation_id: {conversation_id} - {ve}")
            return {
                "success": False,
                "error": f"Invalid UUID format: {conversation_id}"
            }
        
        # Tratar None como 10
        if limit is None:
            limit = 10
        
        # Validar limite
        if limit < 1 or limit > 100:
            limit = min(max(1, limit), 100)  # Forçar entre 1 e 100
        
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv_uuid)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        messages = result.scalars().all()
        
        # Reverse to get chronological order
        messages = list(reversed(messages))
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "message_count": len(messages),
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content[:500],  # Limitar tamanho do conteúdo
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ]
        }
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


async def update_conversation_status(
    conversation_id: str,
    db: AsyncSession,
    status: Optional[str] = None,
    funnel_stage: Optional[str] = None,
) -> dict:
    """
    Update conversation status and/or funnel stage
    
    Args:
        conversation_id: Conversation UUID
        db: Database session
        status: New conversation status
        funnel_stage: New funnel stage
    
    Returns:
        Updated conversation info
    """
    try:
        # Validar que conversation_id é um UUID válido
        if not conversation_id or conversation_id.strip() == "":
            return {"error": "Conversation ID is required"}
        
        if conversation_id.lower() in ["default_conversation_id", "conversation_id", "none", "null"]:
            logger.warning(f"Invalid conversation_id provided: {conversation_id}")
            return {"error": f"Invalid conversation ID: {conversation_id}. Please provide a valid UUID."}
        
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except ValueError as ve:
            logger.error(f"Invalid UUID format for conversation_id: {conversation_id} - {ve}")
            return {"error": f"Invalid UUID format: {conversation_id}"}
        
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv_uuid)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return {"error": "Conversation not found"}
        
        if status:
            try:
                conversation.status = ConversationStatus(status.lower())
            except ValueError:
                return {"error": f"Invalid status: {status}"}
        
        if funnel_stage:
            try:
                conversation.funnel_stage = FunnelStage(funnel_stage.lower())
            except ValueError:
                return {"error": f"Invalid funnel_stage: {funnel_stage}"}
        
        await db.commit()
        await db.refresh(conversation)
        
        logger.info(f"Updated conversation {conversation_id}: status={conversation.status.value}, stage={conversation.funnel_stage.value}")
        
        return {
            "conversation_id": conversation_id,
            "status": conversation.status.value,
            "funnel_stage": conversation.funnel_stage.value,
            "message": "Conversation updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        await db.rollback()
        return {"error": str(e)}


async def update_context_summary(
    conversation_id: str,
    summary: str,
    db: AsyncSession,
) -> dict:
    """
    Update conversation context summary
    
    Args:
        conversation_id: Conversation UUID
        summary: New context summary
        db: Database session
    
    Returns:
        Success message
    """
    try:
        # Validar que conversation_id é um UUID válido
        if not conversation_id or conversation_id.strip() == "":
            return {"error": "Conversation ID is required"}
        
        # Verificar se não é um placeholder inválido
        if conversation_id.lower() in ["default_conversation_id", "conversation_id", "none", "null"]:
            logger.warning(f"Invalid conversation_id provided: {conversation_id}")
            return {"error": f"Invalid conversation ID: {conversation_id}. Please provide a valid UUID."}
        
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except ValueError as ve:
            logger.error(f"Invalid UUID format for conversation_id: {conversation_id} - {ve}")
            return {"error": f"Invalid UUID format: {conversation_id}. Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"}
        
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv_uuid)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return {"error": f"Conversation not found: {conversation_id}"}
        
        conversation.context_summary = summary
        await db.commit()
        
        logger.info(f"Updated context summary for conversation {conversation_id}")
        
        return {
            "conversation_id": conversation_id,
            "message": "Context summary updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating context summary: {e}")
        await db.rollback()
        return {"error": str(e)}


def create_conversation_tools(db: AsyncSession):
    """Create conversation-related tools for LangChain agents"""
    
    async def _get_history(conversation_id: str, limit: Optional[int] = None) -> dict:
        return await get_conversation_history(conversation_id, db, limit)
    
    async def _update_status(
        conversation_id: str,
        status: Optional[str] = None,
        funnel_stage: Optional[str] = None,
    ) -> dict:
        return await update_conversation_status(conversation_id, db, status, funnel_stage)
    
    async def _update_summary(conversation_id: str, summary: str) -> dict:
        return await update_context_summary(conversation_id, summary, db)
    
    return [
        StructuredTool.from_function(
            coroutine=_get_history,
            name="get_conversation_history",
            description="Get message history for a conversation. Use to understand context of previous interactions.",
            args_schema=GetConversationHistoryInput,
        ),
        StructuredTool.from_function(
            coroutine=_update_status,
            name="update_conversation_status",
            description="Update conversation status and funnel stage. Use when lead progresses through sales funnel.",
            args_schema=UpdateConversationStatusInput,
        ),
        StructuredTool.from_function(
            coroutine=_update_summary,
            name="update_context_summary",
            description="Update conversation context summary. Use to save important information about the conversation.",
            args_schema=UpdateContextSummaryInput,
        ),
    ]

