from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.app.database import get_db
from backend.app.models.protocol import Protocol
from backend.app.models.snapshot import CDISnapshot

router = APIRouter(prefix="/metrics", tags=["Metrics Overview"])


@router.get("/overview")
async def get_overview_metrics(db: AsyncSession = Depends(get_db)):
    """
    Computes real-time aggregated dashboard averages across the latest snapshots for all active protocols.
    """
    protocols = (await db.execute(select(Protocol).where(Protocol.is_active.is_(True)))).scalars().all()
    if not protocols:
        return {
            "avg_cdi": 0.0,
            "avg_gini": 0.0,
            "avg_entropy": 0.0,
            "avg_hhi": 0.0,
            "interpretation": "No data",
            "protocol_count": 0,
            "dimensions": {
                "economic": 0.0,
                "governance": 0.0,
                "structural": 0.0,
                "development": 0.0,
            },
            "rankings": [],
        }

    latest_snapshots = []
    rankings = []
    for proto in protocols:
        stmt = (
            select(CDISnapshot)
            .where(CDISnapshot.protocol_id == proto.id)
            .order_by(desc(CDISnapshot.timestamp))
            .limit(1)
        )
        snap = (await db.execute(stmt)).scalar_one_or_none()
        if snap:
            latest_snapshots.append(snap)
            rankings.append({
                "id": proto.id,
                "slug": proto.slug,
                "name": proto.name,
                "symbol": proto.symbol,
                "category": proto.category,
                "color": proto.color,
                "cdi": snap.composite_cdi,
                "gini": snap.gini_coefficient,
                "hhi": snap.hhi_points,
                "entropy": snap.shannon_entropy,
                "risk": snap.composite_risk,
                "economic": snap.economic_score,
                "governance": snap.governance_score,
                "structural": snap.structural_score,
                "development": snap.development_score,
            })

    if not latest_snapshots:
        return {
            "avg_cdi": 0.0,
            "avg_gini": 0.0,
            "avg_entropy": 0.0,
            "avg_hhi": 0.0,
            "interpretation": "No snapshots recorded",
            "protocol_count": len(protocols),
            "dimensions": {
                "economic": 0.0,
                "governance": 0.0,
                "structural": 0.0,
                "development": 0.0,
            },
            "rankings": [],
        }

    n = len(latest_snapshots)
    avg_cdi = sum(s.composite_cdi for s in latest_snapshots) / n
    avg_gini = sum(s.gini_coefficient for s in latest_snapshots) / n
    avg_entropy = sum(s.shannon_entropy for s in latest_snapshots) / n
    avg_hhi = sum(s.hhi_points for s in latest_snapshots) / n

    avg_eco = sum(s.economic_score for s in latest_snapshots) / n
    avg_gov = sum(s.governance_score for s in latest_snapshots) / n
    avg_struct = sum(s.structural_score for s in latest_snapshots) / n
    avg_dev = sum(s.development_score for s in latest_snapshots) / n

    if avg_cdi < 0.35:
        interp = "Highly Centralized"
    elif avg_cdi < 0.60:
        interp = "Moderately Decentralized"
    else:
        interp = "Highly Decentralized"

    rankings.sort(key=lambda x: x["cdi"], reverse=True)

    return {
        "avg_cdi": round(avg_cdi, 4),
        "avg_gini": round(avg_gini, 4),
        "avg_entropy": round(avg_entropy, 2),
        "avg_hhi": round(avg_hhi, 1),
        "interpretation": interp,
        "protocol_count": n,
        "dimensions": {
            "economic": round(avg_eco, 4),
            "governance": round(avg_gov, 4),
            "structural": round(avg_struct, 4),
            "development": round(avg_dev, 4),
        },
        "rankings": rankings,
    }
