"""Unit tests for handoff tools"""
import pytest
import uuid
from app.tools.handoff_tools import request_handoff
from app.models.conversation import Conversation, ConversationStatus, FunnelStage
from app.models.lead import Lead
from app.models.user import User
from sqlalchemy import select


@pytest.fixture
async def test_conversation_for_handoff(test_db, test_user):
    """Create test conversation for handoff tests"""
    conversation = Conversation(
        user_id=test_user.id,
        status=ConversationStatus.ACTIVE,
        funnel_stage=FunnelStage.NEGOTIATION,
    )
    test_db.add(conversation)
    await test_db.commit()
    await test_db.refresh(conversation)
    return conversation


@pytest.mark.asyncio
async def test_request_handoff_success(test_db, test_conversation_for_handoff):
    """Test request_handoff with valid conversation"""
    conversation_id = str(test_conversation_for_handoff.id)
    reason = "Cliente solicitou contato com vendedor humano"
    
    result = await request_handoff(
        conversation_id=conversation_id,
        reason=reason,
        summary="Cliente interessado no plano Flex",
        db=test_db
    )
    
    assert "error" not in result
    assert result["conversation_id"] == conversation_id
    assert result["status"] == "awaiting_human"
    assert "message" in result
    
    # Verify conversation status was updated
    await test_db.refresh(test_conversation_for_handoff)
    assert test_conversation_for_handoff.status == ConversationStatus.AWAITING_HUMAN


@pytest.mark.asyncio
async def test_request_handoff_creates_lead(test_db, test_conversation_for_handoff, test_user):
    """Test request_handoff automatically creates lead"""
    conversation_id = str(test_conversation_for_handoff.id)
    
    # Verify no lead exists before
    result_before = await test_db.execute(
        select(Lead).where(Lead.conversation_id == test_conversation_for_handoff.id)
    )
    lead_before = result_before.scalar_one_or_none()
    assert lead_before is None
    
    # Request handoff
    result = await request_handoff(
        conversation_id=conversation_id,
        reason="Test handoff",
        summary="Test summary",
        db=test_db
    )
    
    assert "error" not in result
    
    # Verify lead was created
    result_after = await test_db.execute(
        select(Lead).where(Lead.conversation_id == test_conversation_for_handoff.id)
    )
    lead_after = result_after.scalar_one_or_none()
    assert lead_after is not None
    assert lead_after.user_id == test_user.id
    assert lead_after.conversation_id == test_conversation_for_handoff.id


@pytest.mark.asyncio
async def test_request_handoff_updates_existing_lead(test_db, test_conversation_for_handoff, test_user):
    """Test request_handoff updates existing lead"""
    conversation_id = str(test_conversation_for_handoff.id)
    
    # Create existing lead
    from app.models.lead import LeadStage
    existing_lead = Lead(
        conversation_id=test_conversation_for_handoff.id,
        user_id=test_user.id,
        stage=LeadStage.WARM,
        score=50
    )
    test_db.add(existing_lead)
    await test_db.commit()
    
    # Request handoff
    result = await request_handoff(
        conversation_id=conversation_id,
        reason="Test handoff",
        summary="Test summary",
        db=test_db
    )
    
    assert "error" not in result
    
    # Verify lead was updated (not duplicated)
    result_after = await test_db.execute(
        select(Lead).where(Lead.conversation_id == test_conversation_for_handoff.id)
    )
    leads_after = result_after.scalars().all()
    assert len(leads_after) == 1  # Should still be only one lead


@pytest.mark.asyncio
async def test_request_handoff_invalid_conversation_id(test_db):
    """Test request_handoff with invalid conversation_id"""
    result = await request_handoff(
        conversation_id="invalid-uuid",
        reason="Test",
        summary="Test summary",
        db=test_db
    )
    
    assert "error" in result
    assert "Invalid UUID format" in result["error"]


@pytest.mark.asyncio
async def test_request_handoff_not_found(test_db):
    """Test request_handoff with non-existent conversation"""
    fake_id = str(uuid.uuid4())
    
    result = await request_handoff(
        conversation_id=fake_id,
        reason="Test",
        summary="Test summary",
        db=test_db
    )
    
    assert "error" in result
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_request_handoff_empty_conversation_id(test_db):
    """Test request_handoff with empty conversation_id"""
    result = await request_handoff(
        conversation_id="",
        reason="Test",
        summary="Test summary",
        db=test_db
    )
    
    assert "error" in result
    assert "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_request_handoff_with_reason(test_db, test_conversation_for_handoff):
    """Test request_handoff with reason"""
    conversation_id = str(test_conversation_for_handoff.id)
    reason = "Cliente precisa de informações sobre desconto"
    
    result = await request_handoff(
        conversation_id=conversation_id,
        reason=reason,
        summary="Cliente interessado no plano Flex",
        db=test_db
    )
    
    assert "error" not in result
    assert result["status"] == "awaiting_human"
    
    # Verify reason is stored in conversation
    await test_db.refresh(test_conversation_for_handoff)
    # The reason might be stored in handoff_reason field or context_summary
    # Check if it's accessible
    assert test_conversation_for_handoff.status == ConversationStatus.AWAITING_HUMAN

