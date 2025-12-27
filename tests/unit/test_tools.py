"""Unit tests for tools"""
import pytest
from app.tools.user_tools import get_user_info, create_user, update_user_info
from app.tools.plan_tools import get_available_plans, get_plan_details


@pytest.mark.asyncio
async def test_get_user_info(test_db, test_user):
    """Test get_user_info tool"""
    result = await get_user_info(test_user.user_key, test_db)
    
    assert "error" not in result
    assert result["user_key"] == test_user.user_key
    assert result["name"] == test_user.name


@pytest.mark.asyncio
async def test_get_user_info_not_found(test_db):
    """Test get_user_info with non-existent user"""
    result = await get_user_info("nonexistent", test_db)
    
    assert "error" in result


@pytest.mark.asyncio
async def test_create_user(test_db):
    """Test create_user tool"""
    result = await create_user(
        user_key="new_user",
        db=test_db,
        name="New User",
        email="new@example.com",
    )
    
    assert "error" not in result
    assert result["user_key"] == "new_user"
    assert "message" in result


@pytest.mark.asyncio
async def test_update_user_info(test_db, test_user):
    """Test update_user_info tool"""
    result = await update_user_info(
        user_key=test_user.user_key,
        db=test_db,
        name="Nome Atualizado",
        email="novo@email.com",
        phone="(11) 99999-9999",
    )
    
    assert "error" not in result
    assert result["name"] == "Nome Atualizado"
    assert result["email"] == "novo@email.com"
    assert result["phone"] == "(11) 99999-9999"
    assert "message" in result


@pytest.mark.asyncio
async def test_update_user_info_partial(test_db, test_user):
    """Test update_user_info with partial data"""
    result = await update_user_info(
        user_key=test_user.user_key,
        db=test_db,
        email="only_email@example.com",
    )
    
    assert "error" not in result
    assert result["email"] == "only_email@example.com"
    assert result["name"] == test_user.name  # Should keep original


@pytest.mark.asyncio
async def test_get_available_plans(test_db, test_plans):
    """Test get_available_plans tool"""
    result = await get_available_plans(test_db)
    
    assert "error" not in result
    assert result["count"] == 2
    assert len(result["plans"]) == 2


@pytest.mark.asyncio
async def test_get_plan_details(test_db, test_plans):
    """Test get_plan_details tool"""
    result = await get_plan_details("flex", test_db)
    
    assert "error" not in result
    assert result["slug"] == "flex"
    assert result["name"] == "Flex"

