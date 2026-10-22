from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class DataSourceBase(BaseModel):
    source_type: str = Field(..., description="Type of data source: rpc, snapshot, coingecko, synthetic")
    endpoint_url: str = Field(..., description="Endpoint URL")
    sync_interval_seconds: int = Field(60, ge=5, le=86400)


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    endpoint_url: Optional[str] = None
    status: Optional[str] = None
    sync_interval_seconds: Optional[int] = Field(None, ge=5, le=86400)


class DataSourceResponse(DataSourceBase):
    id: int
    protocol_id: int
    status: str
    error_count: int
    last_sync_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProtocolBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    symbol: str = Field(..., min_length=1, max_length=32)
    category: str = Field("DEX", max_length=64)
    chain: str = Field("ethereum", max_length=64)
    contract_address: Optional[str] = Field(None, max_length=128)
    governance_type: str = Field("Snapshot", max_length=64)
    color: str = Field("#378ADD", max_length=32)
    description: Optional[str] = None
    is_active: bool = True


class ProtocolCreate(ProtocolBase):
    slug: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$")


class ProtocolUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    symbol: Optional[str] = Field(None, min_length=1, max_length=32)
    category: Optional[str] = None
    chain: Optional[str] = None
    contract_address: Optional[str] = None
    governance_type: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProtocolResponse(ProtocolBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProtocolDetailResponse(ProtocolResponse):
    data_sources: List[DataSourceResponse] = []

    model_config = ConfigDict(from_attributes=True)
