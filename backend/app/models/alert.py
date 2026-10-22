from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Float, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    protocol_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("protocols.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)  # composite_cdi, gini_coefficient, hhi_points, centralization_risk
    condition: Mapped[str] = mapped_column(String(16), nullable=False)    # lt, gt, lte, gte
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="warning")   # info, watch, warning, critical
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    protocol: Mapped[Optional["Protocol"]] = relationship("Protocol", back_populates="alerts")
    incidents: Mapped[list["AlertIncident"]] = relationship(
        "AlertIncident", back_populates="rule", cascade="all, delete-orphan"
    )


class AlertIncident(Base):
    __tablename__ = "alert_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    protocol_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("protocols.id", ondelete="CASCADE"), nullable=True, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="warning")
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    rule: Mapped["AlertRule"] = relationship("AlertRule", back_populates="incidents")
