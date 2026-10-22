from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from backend.app.database import get_db
from backend.app.models.protocol import Protocol
from backend.app.models.alert import AlertRule, AlertIncident
from backend.app.schemas.alert import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertIncidentResponse,
)
from backend.app.schemas.common import PaginatedResponse, StatusResponse
from backend.app.security.auth import verify_admin_api_key

router = APIRouter(prefix="/alerts", tags=["Alerts & Risk Monitoring"])


@router.get("/rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    protocol_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AlertRule)
    if protocol_id:
        stmt = stmt.where(AlertRule.protocol_id == protocol_id)
    rules = (await db.execute(stmt)).scalars().all()
    return [AlertRuleResponse.model_validate(r) for r in rules]


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    payload: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    if payload.protocol_id:
        proto = await db.get(Protocol, payload.protocol_id)
        if not proto:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol {payload.protocol_id} not found.")

    rule = AlertRule(**payload.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return AlertRuleResponse.model_validate(rule)


@router.patch("/rules/{id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    id: int,
    payload: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    rule = await db.get(AlertRule, id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert rule {id} not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(rule, k, v)

    await db.commit()
    await db.refresh(rule)
    return AlertRuleResponse.model_validate(rule)


@router.delete("/rules/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    id: int,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    rule = await db.get(AlertRule, id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert rule {id} not found.")
    await db.delete(rule)
    await db.commit()
    return None


@router.get("/incidents", response_model=PaginatedResponse[AlertIncidentResponse])
async def list_alert_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    unacknowledged_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AlertIncident)
    if severity:
        stmt = stmt.where(AlertIncident.severity == severity)
    if unacknowledged_only:
        stmt = stmt.where(AlertIncident.acknowledged.is_(False))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(desc(AlertIncident.triggered_at)).offset((page - 1) * page_size).limit(page_size)
    results = (await db.execute(stmt)).scalars().all()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=[AlertIncidentResponse.model_validate(i) for i in results],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/incidents/{id}/acknowledge", response_model=StatusResponse)
async def acknowledge_incident(
    id: int,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    incident = await db.get(AlertIncident, id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {id} not found.")
    incident.acknowledged = True
    await db.commit()
    return StatusResponse(status="ok", message=f"Incident {id} acknowledged.")
