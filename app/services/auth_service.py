"""Authentication and authorization service for admin access"""
from typing import Optional
from app.models.user import User
from app.core.config import settings
from app.utils.logger import logger


def is_admin_user(user: Optional[User]) -> bool:
    """
    Check if a user is an admin based on name
    
    Args:
        user: User object to check
    
    Returns:
        True if user is admin, False otherwise
    """
    if not user or not user.name:
        return False
    
    # Get admin keywords from config (default: ["admin", "ADMIN", "administrador"])
    admin_keywords = getattr(settings, 'ADMIN_KEYWORDS', ["admin", "ADMIN", "administrador"])
    
    user_name_lower = user.name.lower()
    
    # Check if any admin keyword is in the user's name
    for keyword in admin_keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in user_name_lower:
            logger.info(f"✅ Admin detected! User {user.user_key} (name: '{user.name}') contains keyword: '{keyword}'")
            return True
    
    logger.debug(f"❌ Not admin: User {user.user_key} (name: '{user.name}') - No admin keywords found in: {admin_keywords}")
    return False


def check_admin_access(user: Optional[User]) -> bool:
    """
    Validate admin access for a user
    
    Args:
        user: User object to validate
    
    Returns:
        True if user has admin access, False otherwise
    """
    return is_admin_user(user)


def require_admin(user: Optional[User]) -> None:
    """
    Raise exception if user is not admin
    
    Args:
        user: User object to check
    
    Raises:
        PermissionError: If user is not admin
    """
    if not is_admin_user(user):
        user_name = user.name if user and user.name else "Unknown"
        raise PermissionError(f"Access denied. Admin privileges required. User: {user_name}")

