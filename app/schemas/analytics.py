"""Analytics schemas"""
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import UUID


class AnalyzeRequest(BaseModel):
    """Schema for analysis request"""
    conversation_id: UUID = Field(..., description="Conversation ID to analyze")


class AnalyzeResponse(BaseModel):
    """Schema for analysis response"""
    conversation_id: UUID
    insights: str
    metrics: Dict[str, Any]
    recommendations: List[str]
    priority: str


class FunnelMetrics(BaseModel):
    """Schema for funnel metrics"""
    stages: Dict[str, int]
    conversion_rates: Dict[str, float]
    total_leads: int
    period: Dict[str, datetime]


class PlanPerformance(BaseModel):
    """Schema for plan performance"""
    plan_name: str
    plan_slug: str
    interest_count: int
    conversion_count: int
    conversion_rate: float


class PlanPerformanceResponse(BaseModel):
    """Schema for plan performance response"""
    plans: List[PlanPerformance]
    total_conversations: int
    period: Optional[Dict[str, datetime]] = None

