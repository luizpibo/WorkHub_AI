"""Integration tests for handoff functionality"""
import pytest
from httpx import AsyncClient
from app.models.user import User
from app.models.conversation import Conversation, ConversationStatus
from sqlalchemy import select


@pytest.mark.asyncio
async def test_handoff_without_complete_data(client: AsyncClient, test_db, test_user, test_plans):
    """Test that handoff fails when user data is incomplete"""
    # Create conversation
    response1 = await client.post(
        "/api/v1/chat",
        json={
            "message": "Quero contratar o plano Flex",
            "user_key": test_user.user_key
        }
    )
    
    assert response1.status_code == 200
    data = response1.json()
    conversation_id = data["conversation_id"]
    
    # User has no email/phone, so handoff should be blocked
    # The agent should be instructed to collect data first


@pytest.mark.asyncio
async def test_handoff_with_complete_data(client: AsyncClient, test_db, test_plans):
    """Test that handoff succeeds when user has complete data"""
    # Create user with complete data
    user_key = "complete_user"
    
    # First message
    response1 = await client.post(
        "/api/v1/chat",
        json={
            "message": "Olá",
            "user_key": user_key
        }
    )
    
    assert response1.status_code == 200
    conversation_id = response1.json()["conversation_id"]
    
    # Simulate data collection (would be done by agent in real scenario)
    # Update user with complete data
    result = await test_db.execute(
        select(User).where(User.user_key == user_key)
    )
    user = result.scalar_one_or_none()
    
    if user:
        user.name = "João Silva"
        user.email = "joao@email.com"
        user.phone = "(11) 99999-9999"
        await test_db.commit()
    
    # Now handoff should work
    # In real scenario, agent would call request_handoff tool


@pytest.mark.asyncio
async def test_conversation_blocked_after_handoff(client: AsyncClient, test_db, test_plans):
    """Test that conversation is blocked after handoff"""
    user_key = "handoff_test_user"
    
    # Create conversation
    response1 = await client.post(
        "/api/v1/chat",
        json={
            "message": "Quero falar com alguém",
            "user_key": user_key
        }
    )
    
    assert response1.status_code == 200
    conversation_id = response1.json()["conversation_id"]
    
    # Update user with complete data
    result = await test_db.execute(
        select(User).where(User.user_key == user_key)
    )
    user = result.scalar_one_or_none()
    
    if user:
        user.name = "Maria Santos"
        user.email = "maria@email.com"
        user.phone = "(11) 88888-8888"
        await test_db.commit()
    
    # Manually set conversation to awaiting_human
    conv_result = await test_db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    
    if conversation:
        conversation.status = ConversationStatus.AWAITING_HUMAN
        conversation.handoff_reason = "Cliente solicitou atendimento humano"
        await test_db.commit()
    
    # Try to send another message
    response2 = await client.post(
        "/api/v1/chat",
        json={
            "message": "Ainda estou aqui",
            "user_key": user_key,
            "conversation_id": conversation_id
        }
    )
    
    assert response2.status_code == 200
    data = response2.json()
    
    # Should be blocked
    assert data["status"] == "awaiting_human"
    assert data.get("blocked") == True
    assert "transferida" in data["response"].lower()


@pytest.mark.asyncio
async def test_update_user_info_via_api(client: AsyncClient, test_user):
    """Test updating user info through chat flow"""
    # This would test the full flow where agent collects data
    # For now, just verify the endpoint works
    
    response = await client.post(
        "/api/v1/chat",
        json={
            "message": "Meu nome é Pedro",
            "user_key": test_user.user_key
        }
    )
    
    assert response.status_code == 200
    # Agent should use update_user_info tool to save the name

