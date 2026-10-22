from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.protocol import Protocol, DataSource
from backend.app.models.snapshot import CDISnapshot
from backend.app.models.alert import AlertRule
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
    compute_risk_indicators,
)
from backend.app.ingestion.synthetic_provider import SyntheticDataProvider

SEED_PROTOCOLS = [
    {
        "slug": "uniswap",
        "name": "Uniswap v3",
        "symbol": "UNI",
        "category": "DEX",
        "chain": "ethereum",
        "contract_address": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "governance_type": "GovernorBravo",
        "color": "#378ADD",
        "description": "Decentralized automated liquidity protocol on Ethereum.",
        "base_structural": 0.62,
        "base_development": 0.58,
    },
    {
        "slug": "aave",
        "name": "Aave v3",
        "symbol": "AAVE",
        "category": "Lending",
        "chain": "ethereum",
        "contract_address": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        "governance_type": "AaveGovernanceV2",
        "color": "#1D9E75",
        "description": "Non-custodial decentralized liquidity protocol for earning interest on deposits.",
        "base_structural": 0.59,
        "base_development": 0.63,
    },
    {
        "slug": "sushi",
        "name": "SushiSwap",
        "symbol": "SUSHI",
        "category": "DEX",
        "chain": "ethereum",
        "contract_address": "0x6B3595068778DD592e39A122f4f5a5cF09C90fE2",
        "governance_type": "Snapshot",
        "color": "#EF9F27",
        "description": "Community-driven decentralized exchange with cross-chain AMM pools.",
        "base_structural": 0.64,
        "base_development": 0.52,
    },
    {
        "slug": "curve",
        "name": "Curve DAO",
        "symbol": "CRV",
        "category": "AMM",
        "chain": "ethereum",
        "contract_address": "0xD533a949740bb3306d119CC777fa900bA034cd52",
        "governance_type": "VotingEscrow",
        "color": "#D85A30",
        "description": "Decentralized exchange liquidity pool designed for extremely efficient stablecoin trading.",
        "base_structural": 0.66,
        "base_development": 0.50,
    },
    {
        "slug": "compound",
        "name": "Compound v3",
        "symbol": "COMP",
        "category": "Lending",
        "chain": "ethereum",
        "contract_address": "0xc00e94Cb662C3520282E6f5717214004A7f26888",
        "governance_type": "GovernorBravo",
        "color": "#7F77DD",
        "description": "Algorithmic, autonomous interest rate protocol for decentralized finance lending.",
        "base_structural": 0.57,
        "base_development": 0.56,
    },
]


async def seed_database(db: AsyncSession) -> None:
    # Check if already seeded
    existing = await db.execute(select(Protocol))
    if existing.scalars().first():
        return

    provider = SyntheticDataProvider()
    now = datetime.now(timezone.utc)

    for p_data in SEED_PROTOCOLS:
        slug = p_data["slug"]
        base_struct = p_data.pop("base_structural")
        base_dev = p_data.pop("base_development")

        protocol = Protocol(**p_data)
        db.add(protocol)
        await db.flush()

        # Add data sources
        rpc_source = DataSource(
            protocol_id=protocol.id,
            source_type="rpc",
            endpoint_url="https://cloudflare-eth.com",
            status="active",
        )
        snapshot_source = DataSource(
            protocol_id=protocol.id,
            source_type="snapshot",
            endpoint_url=f"https://hub.snapshot.org/graphql",
            status="active",
        )
        db.add(rpc_source)
        db.add(snapshot_source)

        # Generate 30 days of historical snapshots
        holdings = await provider.fetch_holder_distribution(slug)
        gov_data = await provider.fetch_governance_distribution(slug)

        gini = compute_gini(holdings)
        hhi_pts, hhi_norm = compute_hhi(holdings)
        raw_ent, norm_ent = compute_shannon_entropy(holdings)
        nakamoto = compute_nakamoto_coefficient(holdings)
        palma = compute_palma_ratio(holdings)

        eco_score = compute_economic_dimension(gini, hhi_norm, norm_ent, nakamoto / len(holdings), palma)
        gov_score = compute_governance_dimension(hhi_norm, norm_ent, gov_data["delegation_centrality"], gov_data["bloc_clustering"])
        struct_score = compute_structural_dimension(base_struct, gov_data["bloc_clustering"], norm_ent)
        dev_score = compute_development_dimension(base_dev, gini, 6)

        cdi_val = 0.25 * eco_score + 0.25 * gov_score + 0.25 * struct_score + 0.25 * dev_score

        for day in range(30, -1, -1):
            ts = now - timedelta(days=day)
            # Add subtle historical drift / variance
            day_drift = (day / 30.0) * 0.02
            current_cdi = max(0.1, min(0.9, cdi_val + day_drift))

            risk = compute_risk_indicators(
                cdi=current_cdi,
                economic=eco_score,
                governance=gov_score,
                structural=struct_score,
                gini=gini,
                hhi_points=hhi_pts,
                delegation_centrality=gov_data["delegation_centrality"],
                bloc_clustering=gov_data["bloc_clustering"],
            )

            snapshot = CDISnapshot(
                protocol_id=protocol.id,
                timestamp=ts,
                block_number=21_000_000 - (day * 7200),
                gini_coefficient=round(gini, 4),
                hhi_points=round(hhi_pts, 1),
                hhi_normalized=round(hhi_norm, 4),
                shannon_entropy=round(raw_ent, 4),
                shannon_entropy_normalized=round(norm_ent, 4),
                nakamoto_coefficient=nakamoto,
                palma_ratio=round(palma, 3),
                delegation_centrality=round(gov_data["delegation_centrality"], 4),
                bloc_clustering=round(gov_data["bloc_clustering"], 4),
                economic_score=round(eco_score, 4),
                governance_score=round(gov_score, 4),
                structural_score=round(struct_score, 4),
                development_score=round(dev_score, 4),
                weight_economic=0.25,
                weight_governance=0.25,
                weight_structural=0.25,
                weight_development=0.25,
                composite_cdi=round(current_cdi, 4),
                centralization_risk=risk["centralization_risk"],
                governance_capture_risk=risk["governance_capture_risk"],
                cartel_formation_risk=risk["cartel_formation_risk"],
                composite_risk=risk["composite_risk"],
                confidence_score=0.90,
                sample_size=len(holdings),
                provenance_type="synthetic",
                metadata_json={"seeded": True},
            )
            db.add(snapshot)

    # Seed standard alert rules
    default_rules = [
        AlertRule(
            name="Critical Centralization Alert",
            metric_name="composite_cdi",
            condition="lt",
            threshold=0.35,
            severity="critical",
        ),
        AlertRule(
            name="High Whale Concentration Warning",
            metric_name="gini_coefficient",
            condition="gt",
            threshold=0.75,
            severity="warning",
        ),
        AlertRule(
            name="Governance Capture Risk Alert",
            metric_name="centralization_risk",
            condition="gt",
            threshold=0.70,
            severity="warning",
        ),
    ]
    for r in default_rules:
        db.add(r)

    await db.commit()
