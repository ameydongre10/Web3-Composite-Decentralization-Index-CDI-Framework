from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field, ConfigDict


class AnalysisJobCreate(BaseModel):
    protocol_id: Optional[int] = None
    job_type: str = Field(..., description="ingestion, recalculation, drift_analysis, stress_test")
    parameters: Optional[Dict] = None


class AnalysisJobResponse(BaseModel):
    id: str
    protocol_id: Optional[int] = None
    job_type: str
    status: str
    parameters: Optional[Dict] = None
    result_summary: Optional[Dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
