from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base


class Protocol(Base):
    __tablename__ = "protocols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="DEX", index=True)
    chain: Mapped[str] = mapped_column(String(64), default="ethereum", index=True)
    contract_address: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    governance_type: Mapped[str] = mapped_column(String(64), default="Snapshot")
    color: Mapped[str] = mapped_column(String(32), default="#378ADD")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    data_sources: Mapped[List["DataSource"]] = relationship(
        "DataSource", back_populates="protocol", cascade="all, delete-orphan", lazy="selectin"
    )
    snapshots: Mapped[List["CDISnapshot"]] = relationship(
        "CDISnapshot", back_populates="protocol", cascade="all, delete-orphan", lazy="selectin"
    )
    alerts: Mapped[List["AlertRule"]] = relationship(
        "AlertRule", back_populates="protocol", cascade="all, delete-orphan"
    )


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    protocol_id: Mapped[int] = mapped_column(Integer, ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="rpc")  # rpc, snapshot, coingecko, synthetic
    endpoint_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active, degraded, offline
    sync_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    protocol: Mapped["Protocol"] = relationship("Protocol", back_populates="data_sources")
