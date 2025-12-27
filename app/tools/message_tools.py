"""Message-related tools for LangChain agents"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import uuid

from app.models.message import Message, MessageRole
from app.utils.logger import logger


class SaveMessageInput(BaseModel):
    """Input schema for save_message tool"""
    conversation_id: str = Field(..., description="Conversation ID")
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


async def save_message(
    conversation_id: str,
    role: str,
    content: str,
    db: AsyncSession,
    tool_calls: Optional[dict] = None,
) -> dict:
    """
    Save a message to the database
    
    Args:
        conversation_id: Conversation UUID
        role: Message role (user, assistant, system)
        content: Message content
        db: Database session
        tool_calls: Optional tool calls metadata
    
    Returns:
        Saved message info
    """
    try:
        # Validar entrada
        if not content or not isinstance(content, str):
            return {
                "success": False,
                "error": "Content is required and must be a string"
            }
        
        if len(content) > 10000:
            return {
                "success": False,
                "error": "Content exceeds maximum length of 10000 characters"
            }
        
        if not conversation_id:
            return {
                "success": False,
                "error": "Conversation ID is required"
            }
        
        # Validar UUID
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except (ValueError, AttributeError):
            return {
                "success": False,
                "error": f"Invalid conversation ID format: {conversation_id}"
            }
        
        # Validar role
        try:
            role_enum = MessageRole(role.lower())
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid role: {role}. Must be user, assistant, or system"
            }
        
        # Criar e salvar mensagem
        message = Message(
            conversation_id=conv_uuid,
            role=role_enum,
            content=content,
            tool_calls=tool_calls,
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        
        logger.info(f"Saved message: {role} in conversation {conversation_id}")
        
        return {
            "success": True,
            "message_id": str(message.id),
            "conversation_id": conversation_id,
            "role": role,
            "content_preview": content[:100],  # Limitar tamanho do retorno
            "message": "Message saved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error saving message: {e}", exc_info=True)
        await db.rollback()
        return {
            "success": False,
            "error": str(e)
        }


def create_message_tools(db: AsyncSession):
    """Create message-related tools for LangChain agents"""
    
    async def _save_message(
        conversation_id: str,
        role: str,
        content: str,
    ) -> dict:
        return await save_message(conversation_id, role, content, db)
    
    return [
        StructuredTool.from_function(
            coroutine=_save_message,
            name="save_message",
            description="Save a message to the conversation. Use to persist important messages.",
            args_schema=SaveMessageInput,
        ),
    ]

