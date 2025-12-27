"""Unit tests for conversation tools"""
import pytest
import uuid
from datetime import datetime
from app.tools.conversation_tools import (
    get_conversation_history,
    update_conversation_status,
    update_context_summary
)
from app.models.conversation import Conversation, ConversationStatus, FunnelStage
from app.models.message import Message, MessageRole
from app.models.user import User


@pytest.fixture
async def test_conversation(test_db, test_user):
    """Create test conversation"""
    conversation = Conversation(
        user_id=test_user.id,
        status=ConversationStatus.ACTIVE,
        funnel_stage=FunnelStage.AWARENESS,
    )
    test_db.add(conversation)
    await test_db.commit()
    await test_db.refresh(conversation)
    return conversation


@pytest.fixture
async def test_messages(test_db, test_conversation):
    """Create test messages"""
    messages = [
        Message(
            conversation_id=test_conversation.id,
            role=MessageRole.USER,
            content="Olá, quero saber sobre coworking"
        ),
        Message(
            conversation_id=test_conversation.id,
            role=MessageRole.ASSISTANT,
            content="Olá! Que bom que você se interessou pelo WorkHub."
        ),
        Message(
            conversation_id=test_conversation.id,
            role=MessageRole.USER,
            content="Quanto custa o plano Flex?"
        ),
    ]
    
    for msg in messages:
        test_db.add(msg)
    
    await test_db.commit()
    return messages


@pytest.mark.asyncio
async def test_get_conversation_history_success(test_db, test_conversation, test_messages):
    """Test get_conversation_history with existing conversation"""
    conversation_id = str(test_conversation.id)
    result = await get_conversation_history(conversation_id, test_db, limit=10)
    
    assert result["success"] is True
    assert result["conversation_id"] == conversation_id
    assert result["message_count"] == 3
    assert len(result["messages"]) == 3
    assert result["messages"][0]["role"] == "user"
    assert "coworking" in result["messages"][0]["content"].lower()


@pytest.mark.asyncio
async def test_get_conversation_history_not_found(test_db):
    """Test get_conversation_history with non-existent conversation"""
    fake_id = str(uuid.uuid4())
    result = await get_conversation_history(fake_id, test_db)
    
    assert result["success"] is True
    assert result["message_count"] == 0
    assert len(result["messages"]) == 0


@pytest.mark.asyncio
async def test_get_conversation_history_invalid_uuid(test_db):
    """Test get_conversation_history with invalid UUID"""
    result = await get_conversation_history("invalid-uuid", test_db)
    
    assert result["success"] is False
    assert "error" in result
    assert "Invalid UUID format" in result["error"]


@pytest.mark.asyncio
async def test_get_conversation_history_empty_conversation_id(test_db):
    """Test get_conversation_history with empty conversation_id"""
    result = await get_conversation_history("", test_db)
    
    assert result["success"] is False
    assert "error" in result
    assert "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_get_conversation_history_with_limit(test_db, test_conversation, test_messages):
    """Test get_conversation_history with limit"""
    conversation_id = str(test_conversation.id)
    result = await get_conversation_history(conversation_id, test_db, limit=2)
    
    assert result["success"] is True
    assert result["message_count"] == 2
    assert len(result["messages"]) == 2


@pytest.mark.asyncio
async def test_get_conversation_history_default_limit(test_db, test_conversation, test_messages):
    """Test get_conversation_history with None limit (defaults to 10)"""
    conversation_id = str(test_conversation.id)
    result = await get_conversation_history(conversation_id, test_db, limit=None)
    
    assert result["success"] is True
    assert result["message_count"] == 3  # All messages fit in limit of 10


@pytest.mark.asyncio
async def test_update_conversation_status(test_db, test_conversation):
    """Test update_conversation_status"""
    conversation_id = str(test_conversation.id)
    result = await update_conversation_status(
        conversation_id,
        test_db,
        status="converted",
        funnel_stage="closed_won"
    )
    
    assert "error" not in result
    assert result["status"] == "converted"
    assert result["funnel_stage"] == "closed_won"
    assert "message" in result


@pytest.mark.asyncio
async def test_update_conversation_status_only_status(test_db, test_conversation):
    """Test update_conversation_status with only status"""
    conversation_id = str(test_conversation.id)
    result = await update_conversation_status(
        conversation_id,
        test_db,
        status="abandoned"
    )
    
    assert "error" not in result
    assert result["status"] == "abandoned"


@pytest.mark.asyncio
async def test_update_conversation_status_only_funnel_stage(test_db, test_conversation):
    """Test update_conversation_status with only funnel_stage"""
    conversation_id = str(test_conversation.id)
    result = await update_conversation_status(
        conversation_id,
        test_db,
        funnel_stage="interest"
    )
    
    assert "error" not in result
    assert result["funnel_stage"] == "interest"


@pytest.mark.asyncio
async def test_update_conversation_status_invalid_uuid(test_db):
    """Test update_conversation_status with invalid UUID"""
    result = await update_conversation_status("invalid-uuid", test_db, status="active")
    
    assert "error" in result
    assert "Invalid UUID format" in result["error"]


@pytest.mark.asyncio
async def test_update_conversation_status_not_found(test_db):
    """Test update_conversation_status with non-existent conversation"""
    fake_id = str(uuid.uuid4())
    result = await update_conversation_status(fake_id, test_db, status="active")
    
    assert "error" in result
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_update_conversation_status_invalid_status(test_db, test_conversation):
    """Test update_conversation_status with invalid status"""
    conversation_id = str(test_conversation.id)
    result = await update_conversation_status(
        conversation_id,
        test_db,
        status="invalid_status"
    )
    
    assert "error" in result
    assert "Invalid status" in result["error"]


@pytest.mark.asyncio
async def test_update_conversation_status_invalid_funnel_stage(test_db, test_conversation):
    """Test update_conversation_status with invalid funnel_stage"""
    conversation_id = str(test_conversation.id)
    result = await update_conversation_status(
        conversation_id,
        test_db,
        funnel_stage="invalid_stage"
    )
    
    assert "error" in result
    assert "Invalid funnel_stage" in result["error"]


@pytest.mark.asyncio
async def test_update_context_summary(test_db, test_conversation):
    """Test update_context_summary"""
    conversation_id = str(test_conversation.id)
    summary = "Cliente interessado no plano Flex, aguardando resposta sobre desconto."
    result = await update_context_summary(conversation_id, summary, test_db)
    
    assert "error" not in result
    assert result["conversation_id"] == conversation_id
    assert "message" in result
    
    # Verify it was saved
    await test_db.refresh(test_conversation)
    assert test_conversation.context_summary == summary


@pytest.mark.asyncio
async def test_update_context_summary_invalid_uuid(test_db):
    """Test update_context_summary with invalid UUID"""
    result = await update_context_summary("invalid-uuid", "Summary", test_db)
    
    assert "error" in result
    assert "Invalid UUID format" in result["error"]


@pytest.mark.asyncio
async def test_update_context_summary_not_found(test_db):
    """Test update_context_summary with non-existent conversation"""
    fake_id = str(uuid.uuid4())
    result = await update_context_summary(fake_id, "Summary", test_db)
    
    assert "error" in result
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_update_context_summary_empty_conversation_id(test_db):
    """Test update_context_summary with empty conversation_id"""
    result = await update_context_summary("", "Summary", test_db)
    
    assert "error" in result
    assert "required" in result["error"].lower()

