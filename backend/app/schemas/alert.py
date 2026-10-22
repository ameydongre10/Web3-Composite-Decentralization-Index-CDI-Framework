from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AlertRuleBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    metric_name: str = Field("composite_cdi", description="composite_cdi, gini_coefficient, hhi_points, centralization_risk, drift")
    condition: str = Field("lt", description="lt, gt, lte, gte")
    threshold: float
    severity: str = Field("warning", description="info, watch, warning, critical")
    is_active: bool = True


class AlertRuleCreate(AlertRuleBase):
    protocol_id: Optional[int] = None


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    metric_name: Optional[str] = None
    condition: Optional[str] = None
    threshold: Optional[float] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None


class AlertRuleResponse(AlertRuleBase):
    id: int
    protocol_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertIncidentResponse(BaseModel):
    id: int
    rule_id: int
    protocol_id: Optional[int] = None
    metric_value: float
    message: str
    severity: str
    acknowledged: bool
    triggered_at: datetime

    model_config = ConfigDict(from_attributes=True)
