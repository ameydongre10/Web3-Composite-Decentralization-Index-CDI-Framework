from datetime import datetime, timezone
from typing import Optional, Dict
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.protocol import Protocol, DataSource
from backend.app.models.snapshot import CDISnapshot
from backend.app.models.alert import AlertRule, AlertIncident
from backend.app.engine import (
    compute_gini,
    compute_hhi,
    compute_shannon_entropy,
    compute_nakamoto_coefficient,
    compute_palma_ratio,
    compute_economic_dimension,
    compute_governance_dimension,
    compute_structural_dimension,
    compute_development_dimension,
    normalize_custom_weights,
    compute_risk_indicators,
)
from backend.app.ingestion.rpc_provider import EthereumRPCProvider
from backend.app.ingestion.snapshot_provider import SnapshotGraphQLProvider
from backend.app.ingestion.synthetic_provider import SyntheticDataProvider


class IngestionService:
    def __init__(self):
        self.rpc_provider = EthereumRPCProvider()
        self.snapshot_provider = SnapshotGraphQLProvider()
        self.synthetic_provider = SyntheticDataProvider()

    async def ingest_and_calculate_snapshot(
        self,
        db: AsyncSession,
        protocol: Protocol,
        custom_weights: Optional[Dict[str, float]] = None,
        provenance_preference: str = "auto",
    ) -> CDISnapshot:
        # Determine holdings and governance data
        holdings = []
        governance_data = {"votes": [], "delegation_centrality": 0.35, "bloc_clustering": 0.35}
        block_number = None
        provenance = "synthetic"

        # Attempt to probe data sources if configured
        if provenance_preference != "synthetic" and protocol.data_sources:
            for ds in protocol.data_sources:
                if ds.source_type == "rpc" and ds.status != "offline":
                    try:
                        telemetry = await self.rpc_provider.fetch_telemetry(ds.endpoint_url)
                        block_number = telemetry.get("current_block")
                        ds.last_sync_at = datetime.now(timezone.utc)
                        ds.status = "active"
                    except Exception as e:
                        ds.error_count += 1
                        ds.last_error_message = str(e)
                elif ds.source_type == "snapshot":
                    try:
                        gov = await self.snapshot_provider.fetch_governance_distribution(protocol.slug)
                        if gov.get("votes"):
                            governance_data = gov
                            provenance = "snapshot_graphql"
                            ds.last_sync_at = datetime.now(timezone.utc)
                    except Exception as e:
                        ds.error_count += 1
                        ds.last_error_message = str(e)

        # Fallback to realistic synthetic distribution if empty
        if not holdings:
            holdings = await self.synthetic_provider.fetch_holder_distribution(protocol.slug)
            provenance = "synthetic"

        if not governance_data.get("votes"):
            governance_data = await self.synthetic_provider.fetch_governance_distribution(protocol.slug)

        # 1. Compute Base Metrics
        gini = compute_gini(holdings)
        hhi_points, hhi_norm = compute_hhi(holdings)
        raw_entropy, norm_entropy = compute_shannon_entropy(holdings)
        nakamoto = compute_nakamoto_coefficient(holdings, threshold_ratio=0.50)
        palma = compute_palma_ratio(holdings)

        # Governance metrics
        gov_votes = governance_data.get("votes", holdings)
        _, gov_hhi_norm = compute_hhi(gov_votes)
        _, gov_entropy_norm = compute_shannon_entropy(gov_votes)
        delegation_cent = float(governance_data.get("delegation_centrality", 0.35))
        bloc_cluster = float(governance_data.get("bloc_clustering", 0.35))

        # 2. Compute 4 Dimension Scores (All in [0, 1] where 1.0 = decentralized)
        economic_score = compute_economic_dimension(
            gini=gini,
            hhi_normalized=hhi_norm,
            entropy_normalized=norm_entropy,
            nakamoto_ratio=nakamoto / len(holdings),
            palma_ratio=palma,
        )
        governance_score = compute_governance_dimension(
            hhi_normalized=gov_hhi_norm,
            entropy_normalized=gov_entropy_norm,
            delegation_centrality=delegation_cent,
            bloc_clustering=bloc_cluster,
        )
        structural_score = compute_structural_dimension(
            structural_base=0.62,
            bloc_clustering=bloc_cluster,
            entropy_normalized=norm_entropy,
        )
        development_score = compute_development_dimension(
            development_base=0.58,
            gini=gini,
            bus_factor=6,
        )

        # 3. Apply Weights
        weights = normalize_custom_weights(custom_weights or {
            "economic": 0.25,
            "governance": 0.25,
            "structural": 0.25,
            "development": 0.25,
        })

        composite_cdi = float(
            weights["economic"] * economic_score +
            weights["governance"] * governance_score +
            weights["structural"] * structural_score +
            weights["development"] * development_score
        )

        # 4. Compute Probabilistic Risk Indicators
        risk = compute_risk_indicators(
            cdi=composite_cdi,
            economic=economic_score,
            governance=governance_score,
            structural=structural_score,
            gini=gini,
            hhi_points=hhi_points,
            delegation_centrality=delegation_cent,
            bloc_clustering=bloc_cluster,
        )

        # 5. Build and Persist Snapshot
        snapshot = CDISnapshot(
            protocol_id=protocol.id,
            timestamp=datetime.now(timezone.utc),
            block_number=block_number,
            gini_coefficient=round(gini, 4),
            hhi_points=round(hhi_points, 1),
            hhi_normalized=round(hhi_norm, 4),
            shannon_entropy=round(raw_entropy, 4),
            shannon_entropy_normalized=round(norm_entropy, 4),
            nakamoto_coefficient=nakamoto,
            palma_ratio=round(palma, 3),
            delegation_centrality=round(delegation_cent, 4),
            bloc_clustering=round(bloc_cluster, 4),
            economic_score=round(economic_score, 4),
            governance_score=round(governance_score, 4),
            structural_score=round(structural_score, 4),
            development_score=round(development_score, 4),
            weight_economic=weights["economic"],
            weight_governance=weights["governance"],
            weight_structural=weights["structural"],
            weight_development=weights["development"],
            composite_cdi=round(composite_cdi, 4),
            centralization_risk=risk["centralization_risk"],
            governance_capture_risk=risk["governance_capture_risk"],
            cartel_formation_risk=risk["cartel_formation_risk"],
            composite_risk=risk["composite_risk"],
            confidence_score=0.95 if provenance == "rpc_verified" else 0.85,
            sample_size=len(holdings),
            provenance_type=provenance,
            metadata_json={"top_10_share": round(np.sum(sorted(holdings)[-10:]) / sum(holdings), 4)},
        )

        db.add(snapshot)
        await db.flush()

        # 6. Evaluate Active Alert Rules for this protocol
        await self._evaluate_alerts(db, protocol.id, snapshot)

        return snapshot

    async def _evaluate_alerts(self, db: AsyncSession, protocol_id: int, snapshot: CDISnapshot):
        stmt = select(AlertRule).where(
            AlertRule.is_active.is_(True),
            (AlertRule.protocol_id.is_(None)) | (AlertRule.protocol_id == protocol_id),
        )
        rules = (await db.execute(stmt)).scalars().all()

        for rule in rules:
            val = getattr(snapshot, rule.metric_name, None)
            if val is None:
                continue

            triggered = False
            if rule.condition == "lt" and val < rule.threshold:
                triggered = True
            elif rule.condition == "gt" and val > rule.threshold:
                triggered = True
            elif rule.condition == "lte" and val <= rule.threshold:
                triggered = True
            elif rule.condition == "gte" and val >= rule.threshold:
                triggered = True

            if triggered:
                msg = f"Alert '{rule.name}' triggered: {rule.metric_name} is {val:.4f} ({rule.condition} {rule.threshold})"
                incident = AlertIncident(
                    rule_id=rule.id,
                    protocol_id=protocol_id,
                    metric_value=float(val),
                    message=msg,
                    severity=rule.severity,
                    triggered_at=datetime.now(timezone.utc),
                )
                db.add(incident)


ingestion_service = IngestionService()
