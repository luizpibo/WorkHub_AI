"""Unit tests for chat service (partial - without LLM)"""
import pytest
from app.services.chat_service import ChatService
from app.models.user import User
from app.models.conversation import Conversation, ConversationStatus, FunnelStage
from sqlalchemy import select


@pytest.fixture
def chat_service(test_db):
    """Create ChatService instance"""
    return ChatService(test_db)


@pytest.mark.asyncio
async def test_get_or_create_user_existing(test_db, test_user, chat_service):
    """Test get_or_create_user with existing user"""
    user = await chat_service.get_or_create_user(
        user_key=test_user.user_key,
        user_name=test_user.name
    )
    
    assert user.id == test_user.id
    assert user.user_key == test_user.user_key
    assert user.name == test_user.name


@pytest.mark.asyncio
async def test_get_or_create_user_new(test_db, chat_service):
    """Test get_or_create_user creates new user"""
    new_user = await chat_service.get_or_create_user(
        user_key="new_user_123",
        user_name="New User"
    )
    
    assert new_user.user_key == "new_user_123"
    assert new_user.name == "New User"
    
    # Verify it was saved
    result = await test_db.execute(
        select(User).where(User.user_key == "new_user_123")
    )
    saved_user = result.scalar_one_or_none()
    assert saved_user is not None
    assert saved_user.name == "New User"


@pytest.mark.asyncio
async def test_get_or_create_user_by_name(test_db, test_user, chat_service):
    """Test get_or_create_user finds user by name when user_key not found"""
    # Create user with different user_key but same name
    existing_user = await chat_service.get_or_create_user(
        user_key="different_key",
        user_name=test_user.name
    )
    
    # Now try to get with original user_key but same name
    found_user = await chat_service.get_or_create_user(
        user_key="another_key",
        user_name=test_user.name
    )
    
    # Should find the existing user by name
    assert found_user.id == existing_user.id
    assert found_user.name == test_user.name


@pytest.mark.asyncio
async def test_get_or_create_user_updates_name(test_db, test_user, chat_service):
    """Test get_or_create_user updates name if provided and different"""
    # Update name
    updated_user = await chat_service.get_or_create_user(
        user_key=test_user.user_key,
        user_name="Updated Name"
    )
    
    assert updated_user.id == test_user.id
    assert updated_user.name == "Updated Name"
    
    # Verify it was saved
    await test_db.refresh(updated_user)
    assert updated_user.name == "Updated Name"


@pytest.mark.asyncio
async def test_get_or_create_conversation_existing(test_db, test_user, chat_service):
    """Test get_or_create_conversation with existing conversation"""
    # Create conversation first
    conversation = Conversation(
        user_id=test_user.id,
        status=ConversationStatus.ACTIVE,
        funnel_stage=FunnelStage.AWARENESS,
    )
    test_db.add(conversation)
    await test_db.commit()
    await test_db.refresh(conversation)
    
    # Get or create should return existing
    found_conversation = await chat_service.get_or_create_conversation(
        user_id=test_user.id
    )
    
    assert found_conversation.id == conversation.id
    assert found_conversation.user_id == test_user.id


@pytest.mark.asyncio
async def test_get_or_create_conversation_new(test_db, test_user, chat_service):
    """Test get_or_create_conversation creates new conversation"""
    # Ensure no conversation exists
    result = await test_db.execute(
        select(Conversation).where(Conversation.user_id == test_user.id)
    )
    existing = result.scalars().all()
    for conv in existing:
        await test_db.delete(conv)
    await test_db.commit()
    
    # Create new conversation
    new_conversation = await chat_service.get_or_create_conversation(
        user_id=test_user.id
    )
    
    assert new_conversation.user_id == test_user.id
    assert new_conversation.status == ConversationStatus.ACTIVE
    assert new_conversation.funnel_stage == FunnelStage.AWARENESS
    
    # Verify it was saved
    result = await test_db.execute(
        select(Conversation).where(Conversation.id == new_conversation.id)
    )
    saved_conversation = result.scalar_one_or_none()
    assert saved_conversation is not None


@pytest.mark.asyncio
async def test_get_or_create_conversation_with_existing_id(test_db, test_user, chat_service):
    """Test get_or_create_conversation with existing conversation_id"""
    # Create conversation first
    conversation = Conversation(
        user_id=test_user.id,
        status=ConversationStatus.ACTIVE,
        funnel_stage=FunnelStage.INTEREST,
    )
    test_db.add(conversation)
    await test_db.commit()
    await test_db.refresh(conversation)
    
    # Get or create with specific ID
    found = await chat_service.get_or_create_conversation(
        user_id=test_user.id,
        conversation_id=conversation.id
    )
    
    assert found.id == conversation.id
    assert found.funnel_stage == FunnelStage.INTEREST  # Should keep original


@pytest.mark.asyncio
async def test_get_or_create_conversation_with_new_id(test_db, test_user, chat_service):
    """Test get_or_create_conversation with new conversation_id"""
    import uuid
    new_id = uuid.uuid4()
    
    conversation = await chat_service.get_or_create_conversation(
        user_id=test_user.id,
        conversation_id=new_id
    )
    
    assert conversation.id == new_id
    assert conversation.user_id == test_user.id

