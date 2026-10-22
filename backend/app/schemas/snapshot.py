from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, ConfigDict


class CDISnapshotBase(BaseModel):
    block_number: Optional[int] = None
    gini_coefficient: float = Field(..., ge=0.0, le=1.0)
    hhi_points: float = Field(..., ge=0.0, le=10000.0)
    hhi_normalized: float = Field(..., ge=0.0, le=1.0)
    shannon_entropy: float = Field(..., ge=0.0)
    shannon_entropy_normalized: float = Field(..., ge=0.0, le=1.0)
    nakamoto_coefficient: int = Field(1, ge=1)
    palma_ratio: float = Field(1.0, ge=0.0)
    delegation_centrality: float = Field(0.3, ge=0.0, le=1.0)
    bloc_clustering: float = Field(0.3, ge=0.0, le=1.0)

    economic_score: float = Field(..., ge=0.0, le=1.0)
    governance_score: float = Field(..., ge=0.0, le=1.0)
    structural_score: float = Field(..., ge=0.0, le=1.0)
    development_score: float = Field(..., ge=0.0, le=1.0)

    weight_economic: float = Field(0.25, ge=0.0, le=1.0)
    weight_governance: float = Field(0.25, ge=0.0, le=1.0)
    weight_structural: float = Field(0.25, ge=0.0, le=1.0)
    weight_development: float = Field(0.25, ge=0.0, le=1.0)

    composite_cdi: float = Field(..., ge=0.0, le=1.0)

    centralization_risk: float = Field(0.3, ge=0.0, le=1.0)
    governance_capture_risk: float = Field(0.3, ge=0.0, le=1.0)
    cartel_formation_risk: float = Field(0.3, ge=0.0, le=1.0)
    composite_risk: float = Field(0.3, ge=0.0, le=1.0)

    confidence_score: float = Field(0.95, ge=0.0, le=1.0)
    sample_size: int = Field(100, ge=1)
    provenance_type: str = "rpc_verified"
    metadata_json: Optional[Dict] = None


class CDISnapshotCreate(CDISnapshotBase):
    protocol_id: int


class CDISnapshotResponse(CDISnapshotBase):
    id: int
    protocol_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class CalculateCDIRequest(BaseModel):
    protocol_id: int
    holdings: Optional[List[float]] = Field(None, description="Raw token/wallet balance distribution")
    voter_weights: Optional[List[float]] = Field(None, description="DAO proposal voting power distribution")
    delegation_centrality: Optional[float] = Field(0.35, ge=0.0, le=1.0)
    bloc_clustering: Optional[float] = Field(0.30, ge=0.0, le=1.0)
    structural_base: Optional[float] = Field(0.60, ge=0.0, le=1.0)
    development_base: Optional[float] = Field(0.55, ge=0.0, le=1.0)
    custom_weights: Optional[Dict[str, float]] = None


class SensitivityAnalysisRequest(BaseModel):
    protocol_id: int
    scenarios: Dict[str, Dict[str, float]] = Field(
        ...,
        description="Named weight scenarios mapping to dimension weights",
        json_schema_extra={
            "example": {
                "equal_weights": {"economic": 0.25, "governance": 0.25, "structural": 0.25, "development": 0.25},
                "governance_heavy": {"economic": 0.10, "governance": 0.60, "structural": 0.15, "development": 0.15},
                "economic_heavy": {"economic": 0.60, "governance": 0.15, "structural": 0.15, "development": 0.10},
            }
        }
    )


class SensitivityAnalysisResponse(BaseModel):
    protocol_id: int
    baseline_cdi: float
    scenario_results: Dict[str, float]
    variance: float
