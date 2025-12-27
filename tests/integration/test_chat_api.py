"""Integration tests for chat API"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_endpoint_new_conversation(client: AsyncClient, test_plans):
    """Test chat endpoint with new conversation"""
    response = await client.post(
        "/api/v1/chat",
        json={
            "message": "Olá, quero saber sobre coworking",
            "user_key": "integration_test_user"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "response" in data
    assert "conversation_id" in data
    assert "user_id" in data
    assert "funnel_stage" in data
    assert data["funnel_stage"] in ["awareness", "interest"]


@pytest.mark.asyncio
async def test_chat_endpoint_existing_conversation(client: AsyncClient, test_plans):
    """Test chat endpoint with existing conversation"""
    # First message
    response1 = await client.post(
        "/api/v1/chat",
        json={
            "message": "Olá",
            "user_key": "test_user_conv"
        }
    )
    
    assert response1.status_code == 200
    conversation_id = response1.json()["conversation_id"]
    
    # Second message in same conversation
    response2 = await client.post(
        "/api/v1/chat",
        json={
            "message": "Quanto custa o plano Flex?",
            "user_key": "test_user_conv",
            "conversation_id": conversation_id
        }
    )
    
    assert response2.status_code == 200
    data = response2.json()
    
    assert data["conversation_id"] == conversation_id
    assert "response" in data


@pytest.mark.asyncio
async def test_get_plans_endpoint(client: AsyncClient, test_plans):
    """Test get plans endpoint"""
    response = await client.get("/api/v1/plans")
    
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_plan_by_slug(client: AsyncClient, test_plans):
    """Test get plan by slug endpoint"""
    response = await client.get("/api/v1/plans/flex")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["slug"] == "flex"
    assert data["name"] == "Flex"


@pytest.mark.asyncio
async def test_create_user_endpoint(client: AsyncClient):
    """Test create user endpoint"""
    response = await client.post(
        "/api/v1/users",
        json={
            "user_key": "api_test_user",
            "name": "API Test User",
            "email": "apitest@example.com",
            "work_type": "freelancer"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["user_key"] == "api_test_user"
    assert data["name"] == "API Test User"


@pytest.mark.asyncio
async def test_get_user_endpoint(client: AsyncClient, test_user):
    """Test get user endpoint"""
    response = await client.get(f"/api/v1/users/{test_user.user_key}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["user_key"] == test_user.user_key
    assert data["name"] == test_user.name

