"""User-related tools for LangChain agents"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import uuid

from app.models.user import User, WorkType
from app.utils.logger import logger


class GetUserInfoInput(BaseModel):
    """Input schema for get_user_info tool"""
    user_key: str = Field(..., description="User key to search for")
    
    class Config:
        arbitrary_types_allowed = True


class CreateUserInput(BaseModel):
    """Input schema for create_user tool"""
    user_key: str = Field(..., description="Unique user key")
    name: Optional[str] = Field(None, description="User name")
    email: Optional[str] = Field(None, description="User email")
    phone: Optional[str] = Field(None, description="User phone")
    work_type: Optional[str] = Field(None, description="Type of work: freelancer, startup, company, other")


class UpdateUserInfoInput(BaseModel):
    """Input schema for update_user_info tool"""
    user_key: str = Field(..., description="User key")
    name: Optional[str] = Field(None, description="User name")
    email: Optional[str] = Field(None, description="User email")
    phone: Optional[str] = Field(None, description="User phone")


async def get_user_info(user_key: str, db: AsyncSession) -> dict:
    """
    Get user information by user_key
    
    Args:
        user_key: User identification key
        db: Database session
    
    Returns:
        User information as dictionary
    """
    try:
        # Validar entrada
        if not user_key or not isinstance(user_key, str):
            return {
                "success": False,
                "error": "User key is required and must be a string"
            }
        
        if len(user_key) > 255:
            return {
                "success": False,
                "error": "User key exceeds maximum length"
            }
        
        result = await db.execute(
            select(User).where(User.user_key == user_key)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found: {user_key}")
            return {
                "success": False,
                "error": "User not found",
                "user_key": user_key
            }
        
        return {
            "success": True,
            "id": str(user.id),
            "user_key": user.user_key,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "company": user.company,
            "work_type": user.work_type.value if user.work_type else None,
            "created_at": user.created_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting user info: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


async def create_user(
    user_key: str,
    db: AsyncSession,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    work_type: Optional[str] = None,
) -> dict:
    """
    Create a new user
    
    Args:
        user_key: Unique user key
        db: Database session
        name: User name
        email: User email
        phone: User phone
        work_type: Type of work
    
    Returns:
        Created user information
    """
    try:
        # Validar entrada
        if not user_key or not isinstance(user_key, str):
            return {
                "success": False,
                "error": "User key is required and must be a string"
            }
        
        if len(user_key) > 255:
            return {
                "success": False,
                "error": "User key exceeds maximum length"
            }
        
        # Validar email se fornecido
        if email and "@" not in email:
            return {
                "success": False,
                "error": "Invalid email format"
            }
        
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.user_key == user_key)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            logger.info(f"User already exists: {user_key}")
            return {
                "success": True,
                "id": str(existing_user.id),
                "user_key": existing_user.user_key,
                "message": "User already exists"
            }
        
        # Create new user
        work_type_enum = None
        if work_type:
            try:
                work_type_enum = WorkType(work_type.lower())
            except ValueError:
                work_type_enum = WorkType.OTHER
        
        user = User(
            user_key=user_key,
            name=name,
            email=email,
            phone=phone,
            work_type=work_type_enum,
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Created user: {user_key}")
        
        return {
            "success": True,
            "id": str(user.id),
            "user_key": user.user_key,
            "name": user.name,
            "message": "User created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        await db.rollback()
        return {
            "success": False,
            "error": str(e)
        }


async def update_user_info(
    user_key: str,
    db: AsyncSession,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> dict:
    """
    Update user information
    
    Args:
        user_key: User key
        db: Database session
        name: User name (optional)
        email: User email (optional)
        phone: User phone (optional)
    
    Returns:
        Updated user information
    """
    try:
        # Get user
        result = await db.execute(
            select(User).where(User.user_key == user_key)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found for update: {user_key}")
            return {"error": "User not found", "user_key": user_key}
        
        # Update only provided fields
        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        if phone is not None:
            user.phone = phone
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Updated user info: {user_key}")
        
        return {
            "id": str(user.id),
            "user_key": user.user_key,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "message": "User information updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating user info: {e}")
        await db.rollback()
        return {"error": str(e)}


def create_user_tools(db: AsyncSession):
    """Create user-related tools for LangChain agents"""
    
    async def _get_user_info(user_key: str) -> dict:
        return await get_user_info(user_key, db)
    
    async def _create_user(
        user_key: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        work_type: Optional[str] = None,
    ) -> dict:
        return await create_user(user_key, db, name, email, phone, work_type)
    
    async def _update_user_info(
        user_key: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> dict:
        return await update_user_info(user_key, db, name, email, phone)
    
    return [
        StructuredTool.from_function(
            coroutine=_get_user_info,
            name="get_user_info",
            description="Get user information by user_key. Returns user details including name, email, work type.",
            args_schema=GetUserInfoInput,
        ),
        StructuredTool.from_function(
            coroutine=_create_user,
            name="create_user",
            description="Create a new user with provided information. Use when user doesn't exist yet.",
            args_schema=CreateUserInput,
        ),
        StructuredTool.from_function(
            coroutine=_update_user_info,
            name="update_user_info",
            description="Update user information (name, email, phone). Use to save data collected during conversation.",
            args_schema=UpdateUserInfoInput,
        ),
    ]

