from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Float, Integer, BigInteger, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base


class CDISnapshot(Base):
    __tablename__ = "cdi_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    protocol_id: Mapped[int] = mapped_column(Integer, ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    block_number: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)

    # Core concentration and entropy metrics
    gini_coefficient: Mapped[float] = mapped_column(Float, nullable=False)  # [0, 1]
    hhi_points: Mapped[float] = mapped_column(Float, nullable=False)        # 0 to 10,000
    hhi_normalized: Mapped[float] = mapped_column(Float, nullable=False)    # [0, 1] concentration
    shannon_entropy: Mapped[float] = mapped_column(Float, nullable=False)   # Raw entropy
    shannon_entropy_normalized: Mapped[float] = mapped_column(Float, nullable=False)  # [0, 1] decentralization
    nakamoto_coefficient: Mapped[int] = mapped_column(Integer, default=1)
    palma_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    delegation_centrality: Mapped[float] = mapped_column(Float, default=0.3)
    bloc_clustering: Mapped[float] = mapped_column(Float, default=0.3)

    # Dimensional Scores (All normalized in [0, 1] where 1.0 = highly decentralized)
    economic_score: Mapped[float] = mapped_column(Float, nullable=False)
    governance_score: Mapped[float] = mapped_column(Float, nullable=False)
    structural_score: Mapped[float] = mapped_column(Float, nullable=False)
    development_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Dimension Weights (sum to 1.0)
    weight_economic: Mapped[float] = mapped_column(Float, default=0.25)
    weight_governance: Mapped[float] = mapped_column(Float, default=0.25)
    weight_structural: Mapped[float] = mapped_column(Float, default=0.25)
    weight_development: Mapped[float] = mapped_column(Float, default=0.25)

    # Composite Index
    composite_cdi: Mapped[float] = mapped_column(Float, index=True, nullable=False)

    # Risk Probabilities [0.0, 1.0]
    centralization_risk: Mapped[float] = mapped_column(Float, default=0.3)
    governance_capture_risk: Mapped[float] = mapped_column(Float, default=0.3)
    cartel_formation_risk: Mapped[float] = mapped_column(Float, default=0.3)
    composite_risk: Mapped[float] = mapped_column(Float, default=0.3)

    # Data Quality & Provenance
    confidence_score: Mapped[float] = mapped_column(Float, default=0.95)
    sample_size: Mapped[int] = mapped_column(Integer, default=100)
    provenance_type: Mapped[str] = mapped_column(String(64), default="rpc_verified")  # rpc_verified, snapshot_graphql, synthetic
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    protocol: Mapped["Protocol"] = relationship("Protocol", back_populates="snapshots")
