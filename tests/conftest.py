"""Pytest configuration and fixtures"""
import pytest
import asyncio
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient

from app.core.database import Base
from app.main import app
from app.api.deps import get_db
from app.models import User, Plan, Conversation, Message, Lead, AnalysisReport

# Test database URL
# Use db service host if available (Docker), otherwise localhost
DB_HOST = os.getenv("DB_HOST", "db" if os.path.exists("/.dockerenv") else "localhost")
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", 
    f"postgresql+asyncpg://workhub:workhub123@{DB_HOST}:5432/workhub_test_db"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    # Create async engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create test user"""
    user = User(
        user_key="test_user_123",
        name="Test User",
        email="test@example.com",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_plans(test_db: AsyncSession):
    """Create test plans"""
    from decimal import Decimal
    from app.models.plan import BillingCycle
    
    plans = [
        Plan(
            name="Day Pass",
            slug="day-pass",
            price=Decimal("49.00"),
            billing_cycle=BillingCycle.DAILY,
            features=["Acesso 1 dia", "Wi-Fi", "Café"],
            is_active=True,
        ),
        Plan(
            name="Flex",
            slug="flex",
            price=Decimal("497.00"),
            billing_cycle=BillingCycle.MONTHLY,
            features=["10 dias/mês", "Wi-Fi", "Café", "Eventos"],
            is_active=True,
        ),
    ]
    
    for plan in plans:
        test_db.add(plan)
    
    await test_db.commit()
    
    return plans

