"""Security utilities for API authentication"""
from fastapi import Header, HTTPException, status
from typing import Optional
from app.core.config import settings


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias=settings.API_KEY_HEADER)
) -> str:
    """
    Verify API key from header (optional for MVP)
    Can be extended to validate against database
    """
    # For MVP, we're not enforcing API keys
    # This is a placeholder for future implementation
    return x_api_key or "anonymous"

