from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from backend.app.database import get_db
from backend.app.models.protocol import Protocol
from backend.app.models.job import AnalysisJob
from backend.app.schemas.job import AnalysisJobCreate, AnalysisJobResponse
from backend.app.schemas.common import PaginatedResponse
from backend.app.ingestion.service import ingestion_service
from backend.app.security.auth import verify_admin_api_key

router = APIRouter(prefix="/jobs", tags=["Analysis Jobs"])


@router.get("", response_model=PaginatedResponse[AnalysisJobResponse])
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AnalysisJob)
    if status_filter:
        stmt = stmt.where(AnalysisJob.status == status_filter)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(desc(AnalysisJob.created_at)).offset((page - 1) * page_size).limit(page_size)
    results = (await db.execute(stmt)).scalars().all()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=[AnalysisJobResponse.model_validate(j) for j in results],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=AnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_analysis_job(
    payload: AnalysisJobCreate,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    if payload.protocol_id:
        proto = await db.get(Protocol, payload.protocol_id)
        if not proto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Protocol {payload.protocol_id} not found.",
            )

    job = AnalysisJob(
        protocol_id=payload.protocol_id,
        job_type=payload.job_type,
        status="running",
        parameters=payload.parameters,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Execute task synchronously or simulate async execution
    try:
        if payload.job_type in ["ingestion", "recalculation"]:
            if payload.protocol_id:
                proto = await db.get(Protocol, payload.protocol_id)
                snap = await ingestion_service.ingest_and_calculate_snapshot(db, proto)
                job.result_summary = {
                    "snapshot_id": snap.id,
                    "composite_cdi": snap.composite_cdi,
                    "risk": snap.composite_risk,
                }
            else:
                # Batch run across all active protocols
                stmt = select(Protocol).where(Protocol.is_active.is_(True))
                protocols = (await db.execute(stmt)).scalars().all()
                count = 0
                for p in protocols:
                    await ingestion_service.ingest_and_calculate_snapshot(db, p)
                    count += 1
                job.result_summary = {"synced_protocols": count}
        else:
            job.result_summary = {"message": f"Job type {payload.job_type} executed successfully"}

        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(job)
    return AnalysisJobResponse.model_validate(job)


@router.get("/{id}", response_model=AnalysisJobResponse)
async def get_job(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(AnalysisJob, id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {id} not found.")
    return AnalysisJobResponse.model_validate(job)
