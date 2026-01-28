"""Chat API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.deps import get_db, get_tenant_id
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.utils.logger import logger

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message to the sales agent

    - **message**: User message
    - **user_key**: User identification key
    - **conversation_id**: Optional existing conversation ID

    Returns the agent's response along with conversation metadata

    Note: Multi-tenant mode is controlled by MULTI_TENANT_ENABLED setting.
    When enabled, requires X-Tenant-ID and X-API-Key headers.
    """
    try:
        # Choose service based on multi-tenant mode
        if settings.MULTI_TENANT_ENABLED:
            # Multi-tenant mode: use ChatService with tenant_id from middleware
            tenant_id = await get_tenant_id(http_request)
            logger.info(f"Using ChatService (multi-tenant mode) for tenant: {tenant_id}")
            chat_service = ChatService(db, tenant_id=tenant_id)
        else:
            # Single-tenant mode: use ChatService without tenant_id (backward compatibility)
            logger.info("Using ChatService (single-tenant mode)")
            chat_service = ChatService(db, tenant_id=None)

        result = await chat_service.process_message(
            message=chat_request.message,
            user_key=chat_request.user_key,
            conversation_id=str(chat_request.conversation_id) if chat_request.conversation_id else None,
            user_name=chat_request.user_name
        )

        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        import traceback
        error_detail = str(e)
        if settings.APP_ENV == "development":
            error_detail += f"\n\nTraceback:\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

