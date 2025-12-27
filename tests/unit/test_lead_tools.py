"""Unit tests for lead tools"""
import pytest
import uuid
from app.tools.lead_tools import (
    create_lead,
    update_lead,
    get_lead_by_conversation
)
from app.models.lead import Lead, LeadStage
from app.models.conversation import Conversation, ConversationStatus, FunnelStage
from app.models.user import User


@pytest.fixture
async def test_conversation_for_lead(test_db, test_user):
    """Create test conversation for lead tests"""
    conversation = Conversation(
        user_id=test_user.id,
        status=ConversationStatus.ACTIVE,
        funnel_stage=FunnelStage.INTEREST,
    )
    test_db.add(conversation)
    await test_db.commit()
    await test_db.refresh(conversation)
    return conversation


@pytest.mark.asyncio
async def test_create_lead_success(test_db, test_conversation_for_lead, test_user):
    """Test create_lead with valid data"""
    conversation_id = str(test_conversation_for_lead.id)
    user_id = str(test_user.id)
    
    result = await create_lead(
        conversation_id=conversation_id,
        user_id=user_id,
        stage="warm",
        score=75,
        db=test_db,
        preferred_plan_slug="flex"
    )
    
    assert "error" not in result
    assert result["conversation_id"] == conversation_id
    assert result["stage"] == "warm"
    assert result["score"] == 75
    assert "message" in result


@pytest.mark.asyncio
async def test_create_lead_with_none_score(test_db, test_conversation_for_lead, test_user):
    """Test create_lead with None score (defaults to 0)"""
    conversation_id = str(test_conversation_for_lead.id)
    user_id = str(test_user.id)
    
    result = await create_lead(
        conversation_id=conversation_id,
        user_id=user_id,
        stage="cold",
        score=None,
        db=test_db
    )
    
    assert "error" not in result
    assert result["score"] == 0


@pytest.mark.asyncio
async def test_create_lead_invalid_conversation_id(test_db, test_user):
    """Test create_lead with invalid conversation_id"""
    user_id = str(test_user.id)
    
    result = await create_lead(
        conversation_id="invalid-uuid",
        user_id=user_id,
        stage="warm",
        score=50,
        db=test_db
    )
    
    assert "error" in result
    assert "Invalid UUID format" in result["error"]


@pytest.mark.asyncio
async def test_create_lead_invalid_user_id(test_db, test_conversation_for_lead):
    """Test create_lead with invalid user_id"""
    conversation_id = str(test_conversation_for_lead.id)
    
    result = await create_lead(
        conversation_id=conversation_id,
        user_id="invalid-uuid",
        stage="warm",
        score=50,
        db=test_db
    )
    
    assert "error" in result
    assert "Invalid UUID format" in result["error"]


@pytest.mark.asyncio
async def test_create_lead_invalid_stage(test_db, test_conversation_for_lead, test_user):
    """Test create_lead with invalid stage"""
    conversation_id = str(test_conversation_for_lead.id)
    user_id = str(test_user.id)
    
    result = await create_lead(
        conversation_id=conversation_id,
        user_id=user_id,
        stage="invalid_stage",
        score=50,
        db=test_db
    )
    
    assert "error" in result
    assert "Invalid stage" in result["error"]


@pytest.mark.asyncio
async def test_update_lead_success(test_db, test_conversation_for_lead, test_user):
    """Test update_lead with valid data"""
    # First create a lead
    conversation_id = str(test_conversation_for_lead.id)
    user_id = str(test_user.id)
    
    await create_lead(
        conversation_id=conversation_id,
        user_id=user_id,
        stage="warm",
        score=50,
        db=test_db
    )
    
    # Now update it
    result = await update_lead(
        conversation_id=conversation_id,
        db=test_db,
        stage="hot",
        score=85,
        objections=["Preço alto"],
        next_action="Agendar reunião"
    )
    
    assert "error" not in result
    assert result["stage"] == "hot"
    assert result["score"] == 85
    assert "message" in result


@pytest.mark.asyncio
async def test_update_lead_partial(test_db, test_conversation_for_lead, test_user):
    """Test update_lead with partial data"""
    # First create a lead
    conversation_id = str(test_conversation_for_lead.id)
    user_id = str(test_user.id)
    
    await create_lead(
        conversation_id=conversation_id,
        user_id=user_id,
        stage="warm",
        score=50,
        db=test_db
    )
    
    # Update only score
    result = await update_lead(
        conversation_id=conversation_id,
        db=test_db,
        score=75
    )
    
    assert "error" not in result
    assert result["score"] == 75
    assert result["stage"] == "warm"  # Should keep original


@pytest.mark.asyncio
async def test_update_lead_not_found(test_db):
    """Test update_lead with non-existent lead"""
    fake_id = str(uuid.uuid4())
    
    result = await update_lead(
        conversation_id=fake_id,
        db=test_db,
        stage="hot"
    )
    
    assert "error" in result
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_update_lead_invalid_uuid(test_db):
    """Test update_lead with invalid UUID"""
    result = await update_lead(
        conversation_id="invalid-uuid",
        db=test_db,
        stage="hot"
    )
    
    assert "error" in result
    assert "Invalid UUID format" in result["error"]


@pytest.mark.asyncio
async def test_update_lead_invalid_stage(test_db, test_conversation_for_lead, test_user):
    """Test update_lead with invalid stage"""
    # First create a lead
    conversation_id = str(test_conversation_for_lead.id)
    user_id = str(test_user.id)
    
    await create_lead(
        conversation_id=conversation_id,
        user_id=user_id,
        stage="warm",
        score=50,
        db=test_db
    )
    
    # Try to update with invalid stage
    result = await update_lead(
        conversation_id=conversation_id,
        db=test_db,
        stage="invalid_stage"
    )
    
    assert "error" in result
    assert "Invalid stage" in result["error"]


@pytest.mark.asyncio
async def test_get_lead_by_conversation_success(test_db, test_conversation_for_lead, test_user):
    """Test get_lead_by_conversation with existing lead"""
    # First create a lead
    conversation_id = str(test_conversation_for_lead.id)
    user_id = str(test_user.id)
    
    await create_lead(
        conversation_id=conversation_id,
        user_id=user_id,
        stage="qualified",
        score=90,
        db=test_db
    )
    
    # Now get it
    result = await get_lead_by_conversation(conversation_id, test_db)
    
    assert "error" not in result
    assert result["conversation_id"] == conversation_id
    assert result["stage"] == "qualified"
    assert result["score"] == 90


@pytest.mark.asyncio
async def test_get_lead_by_conversation_not_found(test_db):
    """Test get_lead_by_conversation with non-existent lead"""
    fake_id = str(uuid.uuid4())
    result = await get_lead_by_conversation(fake_id, test_db)
    
    assert "error" in result
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_get_lead_by_conversation_invalid_uuid(test_db):
    """Test get_lead_by_conversation with invalid UUID"""
    result = await get_lead_by_conversation("invalid-uuid", test_db)
    
    assert "error" in result
    assert "Invalid UUID format" in result["error"]

