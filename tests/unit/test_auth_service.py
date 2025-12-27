"""Unit tests for auth service"""
import pytest
from app.models.user import User
from app.services.auth_service import is_admin_user, check_admin_access, require_admin


@pytest.mark.asyncio
async def test_is_admin_user_with_admin_keyword():
    """Test is_admin_user with admin keyword in name"""
    user = User(user_key="admin_user", name="Admin User")
    assert is_admin_user(user) is True


@pytest.mark.asyncio
async def test_is_admin_user_without_admin_keyword():
    """Test is_admin_user without admin keyword in name"""
    user = User(user_key="regular_user", name="Regular User")
    assert is_admin_user(user) is False


@pytest.mark.asyncio
async def test_is_admin_user_case_insensitive():
    """Test is_admin_user is case insensitive"""
    # Test with lowercase
    user1 = User(user_key="user1", name="admin user")
    assert is_admin_user(user1) is True
    
    # Test with uppercase
    user2 = User(user_key="user2", name="ADMIN USER")
    assert is_admin_user(user2) is True
    
    # Test with mixed case
    user3 = User(user_key="user3", name="AdMiN User")
    assert is_admin_user(user3) is True


@pytest.mark.asyncio
async def test_is_admin_user_with_administrador():
    """Test is_admin_user with 'administrador' keyword"""
    user = User(user_key="user1", name="Administrador João")
    assert is_admin_user(user) is True


@pytest.mark.asyncio
async def test_is_admin_user_none_user():
    """Test is_admin_user with None user"""
    assert is_admin_user(None) is False


@pytest.mark.asyncio
async def test_is_admin_user_no_name():
    """Test is_admin_user with user without name"""
    user = User(user_key="user1", name=None)
    assert is_admin_user(user) is False


@pytest.mark.asyncio
async def test_is_admin_user_partial_match():
    """Test is_admin_user with partial keyword match"""
    user = User(user_key="user1", name="Administrative Assistant")
    assert is_admin_user(user) is True  # Contains "admin" in "Administrative"


@pytest.mark.asyncio
async def test_check_admin_access_with_admin():
    """Test check_admin_access with admin user"""
    user = User(user_key="admin_user", name="Admin User")
    assert check_admin_access(user) is True


@pytest.mark.asyncio
async def test_check_admin_access_without_admin():
    """Test check_admin_access with regular user"""
    user = User(user_key="regular_user", name="Regular User")
    assert check_admin_access(user) is False


@pytest.mark.asyncio
async def test_require_admin_raises_permission_error():
    """Test require_admin raises PermissionError when not admin"""
    user = User(user_key="regular_user", name="Regular User")
    
    with pytest.raises(PermissionError) as exc_info:
        require_admin(user)
    
    assert "Access denied" in str(exc_info.value)
    assert "Admin privileges required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_require_admin_allows_admin():
    """Test require_admin allows admin user (no exception)"""
    user = User(user_key="admin_user", name="Admin User")
    
    # Should not raise exception
    require_admin(user)


@pytest.mark.asyncio
async def test_require_admin_with_none_user():
    """Test require_admin with None user raises PermissionError"""
    with pytest.raises(PermissionError):
        require_admin(None)

