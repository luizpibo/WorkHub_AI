"""Plan schemas"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.models.plan import BillingCycle


class PlanBase(BaseModel):
    """Base plan schema"""
    name: str
    slug: str
    price: Decimal
    billing_cycle: BillingCycle
    features: List[str]
    description: Optional[str] = None
    is_active: bool = True


class PlanCreate(PlanBase):
    """Schema for creating a plan"""
    pass


class PlanUpdate(BaseModel):
    """Schema for updating a plan"""
    name: Optional[str] = None
    price: Optional[Decimal] = None
    features: Optional[List[str]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PlanResponse(PlanBase):
    """Schema for plan response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlanComparison(BaseModel):
    """Schema for comparing plans"""
    plans: List[PlanResponse]
    comparison: dict

