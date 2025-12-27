"""Chat API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import create_chat_service
from app.utils.logger import logger

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message to the sales agent
    
    - **message**: User message
    - **user_key**: User identification key
    - **conversation_id**: Optional existing conversation ID
    
    Returns the agent's response along with conversation metadata
    """
    try:
        chat_service = await create_chat_service(db)
        
        result = await chat_service.process_message(
            message=request.message,
            user_key=request.user_key,
            conversation_id=str(request.conversation_id) if request.conversation_id else None,
            user_name=request.user_name
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        import traceback
        error_detail = str(e)
        if settings.APP_ENV == "development":
            error_detail += f"\n\nTraceback:\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

