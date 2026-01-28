"""API dependencies"""
from typing import AsyncGenerator
from uuid import UUID
from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models import Tenant


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_tenant(request: Request) -> Tenant:
    """
    Dependency to get current tenant from request state.

    The tenant is injected by TenantMiddleware.
    This dependency makes the tenant available to route handlers.
    """
    if not hasattr(request.state, "tenant"):
        raise HTTPException(
            status_code=500,
            detail="Tenant not found in request state. Ensure TenantMiddleware is configured."
        )

    return request.state.tenant


async def get_tenant_id(request: Request) -> UUID:
    """
    Dependency to get current tenant ID from request state.

    This is a convenience dependency for routes that only need the tenant ID.
    """
    if not hasattr(request.state, "tenant_id"):
        raise HTTPException(
            status_code=500,
            detail="Tenant ID not found in request state. Ensure TenantMiddleware is configured."
        )

    return request.state.tenant_id

