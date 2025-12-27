"""Unit tests for message tools"""
import pytest
import uuid
from app.tools.message_tools import save_message
from app.models.message import Message, MessageRole
from app.models.conversation import Conversation, ConversationStatus, FunnelStage
from app.models.user import User


@pytest.fixture
async def test_conversation_for_message(test_db, test_user):
    """Create test conversation for message tests"""
    conversation = Conversation(
        user_id=test_user.id,
        status=ConversationStatus.ACTIVE,
        funnel_stage=FunnelStage.AWARENESS,
    )
    test_db.add(conversation)
    await test_db.commit()
    await test_db.refresh(conversation)
    return conversation


@pytest.mark.asyncio
async def test_save_message_success(test_db, test_conversation_for_message):
    """Test save_message with valid data"""
    conversation_id = str(test_conversation_for_message.id)
    
    result = await save_message(
        conversation_id=conversation_id,
        role="user",
        content="Olá, quero saber sobre coworking",
        db=test_db
    )
    
    assert "error" not in result
    assert result["conversation_id"] == conversation_id
    assert result["role"] == "user"
    assert result["content"] == "Olá, quero saber sobre coworking"
    assert "message" in result


@pytest.mark.asyncio
async def test_save_message_assistant_role(test_db, test_conversation_for_message):
    """Test save_message with assistant role"""
    conversation_id = str(test_conversation_for_message.id)
    
    result = await save_message(
        conversation_id=conversation_id,
        role="assistant",
        content="Olá! Que bom que você se interessou pelo WorkHub.",
        db=test_db
    )
    
    assert "error" not in result
    assert result["role"] == "assistant"


@pytest.mark.asyncio
async def test_save_message_invalid_conversation_id(test_db):
    """Test save_message with invalid conversation_id"""
    result = await save_message(
        conversation_id="invalid-uuid",
        role="user",
        content="Test message",
        db=test_db
    )
    
    assert "error" in result
    assert "Invalid UUID format" in result["error"]


@pytest.mark.asyncio
async def test_save_message_empty_conversation_id(test_db):
    """Test save_message with empty conversation_id"""
    result = await save_message(
        conversation_id="",
        role="user",
        content="Test message",
        db=test_db
    )
    
    assert "error" in result
    assert "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_save_message_invalid_role(test_db, test_conversation_for_message):
    """Test save_message with invalid role"""
    conversation_id = str(test_conversation_for_message.id)
    
    result = await save_message(
        conversation_id=conversation_id,
        role="invalid_role",
        content="Test message",
        db=test_db
    )
    
    assert "error" in result
    assert "Invalid role" in result["error"]


@pytest.mark.asyncio
async def test_save_message_empty_content(test_db, test_conversation_for_message):
    """Test save_message with empty content"""
    conversation_id = str(test_conversation_for_message.id)
    
    result = await save_message(
        conversation_id=conversation_id,
        role="user",
        content="",
        db=test_db
    )
    
    assert "error" in result
    assert "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_save_message_not_found_conversation(test_db):
    """Test save_message with non-existent conversation"""
    fake_id = str(uuid.uuid4())
    
    result = await save_message(
        conversation_id=fake_id,
        role="user",
        content="Test message",
        db=test_db
    )
    
    assert "error" in result
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_save_message_multiple_messages(test_db, test_conversation_for_message):
    """Test saving multiple messages"""
    conversation_id = str(test_conversation_for_message.id)
    
    # Save first message
    result1 = await save_message(
        conversation_id=conversation_id,
        role="user",
        content="First message",
        db=test_db
    )
    assert "error" not in result1
    
    # Save second message
    result2 = await save_message(
        conversation_id=conversation_id,
        role="assistant",
        content="Second message",
        db=test_db
    )
    assert "error" not in result2
    
    # Verify both messages were saved
    from sqlalchemy import select
    result = await test_db.execute(
        select(Message).where(Message.conversation_id == test_conversation_for_message.id)
    )
    messages = result.scalars().all()
    assert len(messages) == 2

