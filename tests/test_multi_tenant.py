"""
Multi-tenant tests

Tests for tenant isolation, authentication, and multi-tenant functionality.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import bcrypt
import uuid

from app.main import app
from app.models import Tenant, TenantStatus, User, Conversation, Plan, BillingCycle
from app.core.database import AsyncSessionLocal


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
async def db_session():
    """Create async database session for tests"""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def test_tenant_a(db_session: AsyncSession):
    """Create test tenant A"""
    api_key = f"ta_{uuid.uuid4().hex[:32]}"
    api_key_hash = bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    tenant = Tenant(
        id=uuid.uuid4(),
        slug="tenant-a",
        name="Tenant A",
        config={"business_type": "coworking"},
        api_key_hash=api_key_hash,
        api_key_prefix=api_key[:8],
        status=TenantStatus.ACTIVE
    )

    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    return {"tenant": tenant, "api_key": api_key}


@pytest.fixture
async def test_tenant_b(db_session: AsyncSession):
    """Create test tenant B"""
    api_key = f"tb_{uuid.uuid4().hex[:32]}"
    api_key_hash = bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    tenant = Tenant(
        id=uuid.uuid4(),
        slug="tenant-b",
        name="Tenant B",
        config={"business_type": "saas"},
        api_key_hash=api_key_hash,
        api_key_prefix=api_key[:8],
        status=TenantStatus.ACTIVE
    )

    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    return {"tenant": tenant, "api_key": api_key}


@pytest.fixture
async def test_user_tenant_a(db_session: AsyncSession, test_tenant_a):
    """Create test user for tenant A"""
    user = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant_a["tenant"].id,
        user_key="user_a_1",
        name="User A1"
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def test_user_tenant_b(db_session: AsyncSession, test_tenant_b):
    """Create test user for tenant B"""
    user = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant_b["tenant"].id,
        user_key="user_b_1",
        name="User B1"
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


# ========================================
# AUTHENTICATION TESTS
# ========================================

@pytest.mark.asyncio
async def test_tenant_authentication_valid(test_tenant_a):
    """Test successful tenant authentication"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            headers={
                "X-Tenant-ID": test_tenant_a["tenant"].slug,
                "X-API-Key": test_tenant_a["api_key"]
            },
            json={
                "message": "Hello",
                "user_key": "test_user",
                "user_name": "Test User"
            }
        )

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_authentication_missing_headers():
    """Test authentication fails without headers"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json={
                "message": "Hello",
                "user_key": "test_user"
            }
        )

        assert response.status_code == 400
        assert "X-Tenant-ID" in response.json()["error"]


@pytest.mark.asyncio
async def test_tenant_authentication_invalid_api_key(test_tenant_a):
    """Test authentication fails with invalid API key"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            headers={
                "X-Tenant-ID": test_tenant_a["tenant"].slug,
                "X-API-Key": "invalid_key_123"
            },
            json={
                "message": "Hello",
                "user_key": "test_user"
            }
        )

        assert response.status_code == 401
        assert "Invalid API key" in response.json()["error"]


@pytest.mark.asyncio
async def test_tenant_authentication_nonexistent_tenant():
    """Test authentication fails with non-existent tenant"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            headers={
                "X-Tenant-ID": "nonexistent",
                "X-API-Key": "some_key"
            },
            json={
                "message": "Hello",
                "user_key": "test_user"
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"]


# ========================================
# DATA ISOLATION TESTS
# ========================================

@pytest.mark.asyncio
async def test_user_isolation_same_key_different_tenants(
    db_session: AsyncSession,
    test_tenant_a,
    test_tenant_b
):
    """Test that users with same user_key are isolated by tenant"""
    # Create users with same user_key in different tenants
    user_a = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant_a["tenant"].id,
        user_key="same_key",
        name="User in Tenant A"
    )

    user_b = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant_b["tenant"].id,
        user_key="same_key",
        name="User in Tenant B"
    )

    db_session.add(user_a)
    db_session.add(user_b)
    await db_session.commit()

    # Verify both exist
    result_a = await db_session.execute(
        select(User).where(
            User.tenant_id == test_tenant_a["tenant"].id,
            User.user_key == "same_key"
        )
    )
    assert result_a.scalar_one_or_none() is not None

    result_b = await db_session.execute(
        select(User).where(
            User.tenant_id == test_tenant_b["tenant"].id,
            User.user_key == "same_key"
        )
    )
    assert result_b.scalar_one_or_none() is not None

    # Verify they are different users
    assert user_a.id != user_b.id
    assert user_a.name != user_b.name


@pytest.mark.asyncio
async def test_conversation_isolation(
    db_session: AsyncSession,
    test_user_tenant_a,
    test_user_tenant_b,
    test_tenant_a,
    test_tenant_b
):
    """Test that conversations are isolated by tenant"""
    # Create conversations for both tenants
    conv_a = Conversation(
        id=uuid.uuid4(),
        tenant_id=test_tenant_a["tenant"].id,
        user_id=test_user_tenant_a.id
    )

    conv_b = Conversation(
        id=uuid.uuid4(),
        tenant_id=test_tenant_b["tenant"].id,
        user_id=test_user_tenant_b.id
    )

    db_session.add(conv_a)
    db_session.add(conv_b)
    await db_session.commit()

    # Query conversations for tenant A
    result_a = await db_session.execute(
        select(Conversation).where(
            Conversation.tenant_id == test_tenant_a["tenant"].id
        )
    )
    conversations_a = result_a.scalars().all()

    # Should only see tenant A's conversations
    assert len(conversations_a) == 1
    assert conversations_a[0].id == conv_a.id

    # Query conversations for tenant B
    result_b = await db_session.execute(
        select(Conversation).where(
            Conversation.tenant_id == test_tenant_b["tenant"].id
        )
    )
    conversations_b = result_b.scalars().all()

    # Should only see tenant B's conversations
    assert len(conversations_b) == 1
    assert conversations_b[0].id == conv_b.id


@pytest.mark.asyncio
async def test_plan_isolation_same_slug(
    db_session: AsyncSession,
    test_tenant_a,
    test_tenant_b
):
    """Test that plans with same slug are isolated by tenant"""
    # Create plans with same slug in different tenants
    plan_a = Plan(
        id=uuid.uuid4(),
        tenant_id=test_tenant_a["tenant"].id,
        name="Basic Plan - Tenant A",
        slug="basic",
        price=100.00,
        billing_cycle=BillingCycle.MONTHLY,
        features=["Feature A1", "Feature A2"]
    )

    plan_b = Plan(
        id=uuid.uuid4(),
        tenant_id=test_tenant_b["tenant"].id,
        name="Basic Plan - Tenant B",
        slug="basic",
        price=200.00,
        billing_cycle=BillingCycle.MONTHLY,
        features=["Feature B1", "Feature B2"]
    )

    db_session.add(plan_a)
    db_session.add(plan_b)
    await db_session.commit()

    # Verify both exist with same slug but different data
    result_a = await db_session.execute(
        select(Plan).where(
            Plan.tenant_id == test_tenant_a["tenant"].id,
            Plan.slug == "basic"
        )
    )
    retrieved_plan_a = result_a.scalar_one_or_none()
    assert retrieved_plan_a is not None
    assert float(retrieved_plan_a.price) == 100.00

    result_b = await db_session.execute(
        select(Plan).where(
            Plan.tenant_id == test_tenant_b["tenant"].id,
            Plan.slug == "basic"
        )
    )
    retrieved_plan_b = result_b.scalar_one_or_none()
    assert retrieved_plan_b is not None
    assert float(retrieved_plan_b.price) == 200.00


# ========================================
# CROSS-TENANT ACCESS TESTS
# ========================================

@pytest.mark.asyncio
async def test_cross_tenant_chat_blocked(
    test_tenant_a,
    test_tenant_b,
    test_user_tenant_a
):
    """Test that tenant B cannot access tenant A's data"""
    # Create conversation in tenant A
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create conversation as tenant A
        response_a = await client.post(
            "/api/v1/chat",
            headers={
                "X-Tenant-ID": test_tenant_a["tenant"].slug,
                "X-API-Key": test_tenant_a["api_key"]
            },
            json={
                "message": "Hello from Tenant A",
                "user_key": test_user_tenant_a.user_key,
                "user_name": test_user_tenant_a.name
            }
        )

        assert response_a.status_code == 200
        conversation_id = response_a.json()["conversation_id"]

        # Try to access conversation as tenant B (should fail or see nothing)
        response_b = await client.post(
            "/api/v1/chat",
            headers={
                "X-Tenant-ID": test_tenant_b["tenant"].slug,
                "X-API-Key": test_tenant_b["api_key"]
            },
            json={
                "message": "Trying to access Tenant A's conversation",
                "user_key": test_user_tenant_a.user_key,
                "conversation_id": conversation_id
            }
        )

        # Should either create new conversation or return error
        # Definitely should NOT access tenant A's conversation
        if response_b.status_code == 200:
            assert response_b.json()["conversation_id"] != conversation_id


# ========================================
# TENANT MANAGEMENT TESTS
# ========================================

@pytest.mark.asyncio
async def test_create_tenant_via_api():
    """Test creating tenant via API"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/admin/tenants",
            json={
                "slug": "test-tenant",
                "name": "Test Tenant",
                "status": "active",
                "config": {"business_type": "test"}
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["slug"] == "test-tenant"
        assert data["name"] == "Test Tenant"
        assert "api_key" in data  # API key returned only once
        assert data["api_key"].startswith("te_")


@pytest.mark.asyncio
async def test_create_duplicate_tenant_fails():
    """Test that creating tenant with duplicate slug fails"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create first tenant
        await client.post(
            "/api/v1/admin/tenants",
            json={
                "slug": "duplicate-test",
                "name": "Duplicate Test"
            }
        )

        # Try to create duplicate
        response = await client.post(
            "/api/v1/admin/tenants",
            json={
                "slug": "duplicate-test",
                "name": "Duplicate Test 2"
            }
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


# ========================================
# HELPER FUNCTIONS FOR TEST SETUP
# ========================================

def create_tenant_headers(tenant_slug: str, api_key: str) -> dict:
    """Helper to create tenant authentication headers"""
    return {
        "X-Tenant-ID": tenant_slug,
        "X-API-Key": api_key
    }


# ========================================
# NOTES FOR UPDATING EXISTING TESTS
# ========================================

"""
To update existing tests for multi-tenant:

1. Add tenant fixtures:
   - Create test tenant(s)
   - Get API keys

2. Add headers to all API requests:
   headers=create_tenant_headers(tenant.slug, api_key)

3. Update database queries to filter by tenant_id:
   select(Model).where(
       Model.tenant_id == tenant_id,
       Model.field == value
   )

4. Test tenant isolation:
   - Create data in tenant A
   - Try to access from tenant B
   - Verify access denied

5. Test with MULTI_TENANT_ENABLED=False:
   - Should use default tenant
   - Should not require headers
"""
