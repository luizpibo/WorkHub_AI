"""Tenant middleware for multi-tenant support"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt
from typing import Optional

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import Tenant, TenantStatus
from app.utils.logger import logger


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate tenant context from requests.

    Supports two modes:
    1. Multi-tenant mode (MULTI_TENANT_ENABLED=True):
       - Requires X-Tenant-ID and X-API-Key headers
       - Validates tenant exists and is active
       - Verifies API key

    2. Single-tenant mode (MULTI_TENANT_ENABLED=False):
       - Uses default tenant (workhub)
       - No authentication required (backward compatibility)
    """

    # Paths that don't require tenant authentication
    EXCLUDED_PATHS = [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/static",
    ]

    async def dispatch(self, request: Request, call_next):
        """Process request and inject tenant context"""

        # Skip tenant validation for excluded paths
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)

        # Skip tenant validation for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        try:
            if settings.MULTI_TENANT_ENABLED:
                # Multi-tenant mode: validate headers and authenticate
                tenant = await self._validate_tenant_headers(request)
            else:
                # Single-tenant mode: use default tenant
                tenant = await self._get_default_tenant()

            if not tenant:
                return JSONResponse(
                    status_code=404 if settings.MULTI_TENANT_ENABLED else 500,
                    content={
                        "error": "Tenant not found" if settings.MULTI_TENANT_ENABLED
                                else "Default tenant not configured"
                    }
                )

            # Inject tenant into request state
            request.state.tenant_id = tenant.id
            request.state.tenant_slug = tenant.slug
            request.state.tenant = tenant

            # Process request
            response = await call_next(request)

            # Add tenant header to response (for debugging)
            response.headers["X-Tenant-Slug"] = tenant.slug

            return response

        except TenantAuthenticationError as e:
            logger.warning(f"Tenant authentication failed: {e}")
            return JSONResponse(
                status_code=e.status_code,
                content={"error": e.message}
            )
        except Exception as e:
            logger.error(f"Unexpected error in TenantMiddleware: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )

    async def _validate_tenant_headers(self, request: Request) -> Optional[Tenant]:
        """Validate tenant ID and API key from headers"""

        # Extract headers
        tenant_slug = request.headers.get(settings.TENANT_ID_HEADER)
        api_key = request.headers.get(settings.API_KEY_HEADER)

        # Validate headers present
        if not tenant_slug:
            raise TenantAuthenticationError(
                f"Missing {settings.TENANT_ID_HEADER} header",
                status_code=400
            )

        if not api_key:
            raise TenantAuthenticationError(
                f"Missing {settings.API_KEY_HEADER} header",
                status_code=400
            )

        # Load tenant from database
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Tenant).where(Tenant.slug == tenant_slug)
            )
            tenant = result.scalar_one_or_none()

        if not tenant:
            raise TenantAuthenticationError(
                f"Tenant '{tenant_slug}' not found",
                status_code=404
            )

        # Check tenant status
        if tenant.status != TenantStatus.ACTIVE:
            raise TenantAuthenticationError(
                f"Tenant '{tenant_slug}' is not active (status: {tenant.status.value})",
                status_code=403
            )

        if not tenant.is_active:
            raise TenantAuthenticationError(
                f"Tenant '{tenant_slug}' is deactivated",
                status_code=403
            )

        # Verify API key
        if not tenant.api_key_hash:
            raise TenantAuthenticationError(
                f"Tenant '{tenant_slug}' has no API key configured",
                status_code=403
            )

        # Compare API key hash
        api_key_valid = bcrypt.checkpw(
            api_key.encode('utf-8'),
            tenant.api_key_hash.encode('utf-8')
        )

        if not api_key_valid:
            raise TenantAuthenticationError(
                "Invalid API key",
                status_code=401
            )

        return tenant

    async def _get_default_tenant(self) -> Optional[Tenant]:
        """Get default tenant for single-tenant mode"""

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Tenant).where(Tenant.slug == settings.DEFAULT_TENANT_SLUG)
            )
            tenant = result.scalar_one_or_none()

        return tenant


class TenantAuthenticationError(Exception):
    """Exception raised when tenant authentication fails"""

    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
