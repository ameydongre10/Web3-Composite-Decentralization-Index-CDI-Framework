from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from backend.app.database import get_db
from backend.app.models.protocol import Protocol
from backend.app.models.snapshot import CDISnapshot
from backend.app.schemas.snapshot import (
    CDISnapshotResponse,
    CalculateCDIRequest,
    SensitivityAnalysisRequest,
    SensitivityAnalysisResponse,
)
from backend.app.schemas.common import PaginatedResponse
from backend.app.engine import (
    compute_temporal_drift,
    normalize_custom_weights,
)
from backend.app.ingestion.service import ingestion_service
from backend.app.security.auth import verify_admin_api_key

router = APIRouter(tags=["Snapshots & Analytics"])


@router.get("/snapshots", response_model=PaginatedResponse[CDISnapshotResponse])
async def list_snapshots(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    protocol_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CDISnapshot)
    if protocol_id:
        stmt = stmt.where(CDISnapshot.protocol_id == protocol_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(desc(CDISnapshot.timestamp)).offset((page - 1) * page_size).limit(page_size)
    results = (await db.execute(stmt)).scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=[CDISnapshotResponse.model_validate(s) for s in results],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/snapshots/{id}", response_model=CDISnapshotResponse)
async def get_snapshot(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    snapshot = await db.get(CDISnapshot, id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Snapshot {id} not found.")
    return CDISnapshotResponse.model_validate(snapshot)


@router.post("/snapshots/calculate", response_model=CDISnapshotResponse, status_code=status.HTTP_201_CREATED)
async def calculate_and_save_snapshot(
    payload: CalculateCDIRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    proto = await db.get(Protocol, payload.protocol_id)
    if not proto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol {payload.protocol_id} not found.")

    snapshot = await ingestion_service.ingest_and_calculate_snapshot(
        db=db,
        protocol=proto,
        custom_weights=payload.custom_weights,
    )
    await db.commit()
    await db.refresh(snapshot)
    return CDISnapshotResponse.model_validate(snapshot)


@router.post("/snapshots/sensitivity", response_model=SensitivityAnalysisResponse)
async def sensitivity_analysis(
    payload: SensitivityAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    # Retrieve latest snapshot
    stmt = select(CDISnapshot).where(CDISnapshot.protocol_id == payload.protocol_id).order_by(desc(CDISnapshot.timestamp)).limit(1)
    snapshot = (await db.execute(stmt)).scalar_one_or_none()
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No snapshots found for protocol {payload.protocol_id}. Run calculate first.",
        )

    results = {}
    for scenario_name, weights in payload.scenarios.items():
        w = normalize_custom_weights(weights)
        cdi = float(
            w["economic"] * snapshot.economic_score +
            w["governance"] * snapshot.governance_score +
            w["structural"] * snapshot.structural_score +
            w["development"] * snapshot.development_score
        )
        results[scenario_name] = round(cdi, 4)

    scores = list(results.values())
    variance = float(np_var(scores)) if scores else 0.0

    return SensitivityAnalysisResponse(
        protocol_id=payload.protocol_id,
        baseline_cdi=snapshot.composite_cdi,
        scenario_results=results,
        variance=round(variance, 6),
    )


def np_var(vals: List[float]) -> float:
    if len(vals) < 2:
        return 0.0
    mean_v = sum(vals) / len(vals)
    return sum((x - mean_v) ** 2 for x in vals) / len(vals)


@router.get("/protocols/{protocol_id}/temporal-drift")
async def get_protocol_temporal_drift(
    protocol_id: int,
    lookback: int = Query(60, ge=10, le=180),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CDISnapshot.composite_cdi)
        .where(CDISnapshot.protocol_id == protocol_id)
        .order_by(CDISnapshot.timestamp.asc())
        .limit(lookback)
    )
    series = [float(v) for v in (await db.execute(stmt)).scalars().all()]
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No historical snapshots found for protocol {protocol_id}.",
        )

    drift_stats = compute_temporal_drift(series)
    return {
        "protocol_id": protocol_id,
        "observations_count": len(series),
        "history": series,
        **drift_stats,
    }


@router.delete("/snapshots/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_snapshot(
    id: int,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    snapshot = await db.get(CDISnapshot, id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Snapshot {id} not found.")
    await db.delete(snapshot)
    await db.commit()
    return None
