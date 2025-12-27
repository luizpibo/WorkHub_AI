"""User API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.models.user import User, WorkType
from app.utils.logger import logger

router = APIRouter()


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user
    
    - **user_key**: Unique user identification key
    - **name**: User's name (optional)
    - **email**: User's email (optional)
    - **phone**: User's phone (optional)
    - **work_type**: Type of work (optional)
    """
    try:
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.user_key == user_data.user_key)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create user
        work_type_enum = None
        if user_data.work_type:
            try:
                work_type_enum = WorkType(user_data.work_type.lower())
            except ValueError:
                work_type_enum = WorkType.OTHER
        
        user = User(
            user_key=user_data.user_key,
            name=user_data.name,
            email=user_data.email,
            phone=user_data.phone,
            work_type=work_type_enum,
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Created user: {user.user_key}")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_key}", response_model=UserResponse)
async def get_user(
    user_key: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user by user_key"""
    try:
        result = await db.execute(
            select(User).where(User.user_key == user_key)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

