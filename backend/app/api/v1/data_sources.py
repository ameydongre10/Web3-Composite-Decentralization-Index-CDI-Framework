from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.database import get_db
from backend.app.models.protocol import Protocol, DataSource
from backend.app.schemas.protocol import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
)
from backend.app.security.auth import verify_admin_api_key

router = APIRouter(tags=["Data Sources"])


@router.get("/protocols/{protocol_id}/data-sources", response_model=List[DataSourceResponse])
async def list_protocol_data_sources(
    protocol_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(DataSource).where(DataSource.protocol_id == protocol_id)
    results = (await db.execute(stmt)).scalars().all()
    return [DataSourceResponse.model_validate(ds) for ds in results]


@router.post("/protocols/{protocol_id}/data-sources", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    protocol_id: int,
    payload: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    # Verify protocol exists
    proto = await db.get(Protocol, protocol_id)
    if not proto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Protocol {protocol_id} not found.",
        )

    ds = DataSource(protocol_id=protocol_id, **payload.model_dump())
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return DataSourceResponse.model_validate(ds)


@router.patch("/data-sources/{id}", response_model=DataSourceResponse)
async def update_data_source(
    id: int,
    payload: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    ds = await db.get(DataSource, id)
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {id} not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(ds, field, val)

    await db.commit()
    await db.refresh(ds)
    return DataSourceResponse.model_validate(ds)


@router.delete("/data-sources/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(
    id: int,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    ds = await db.get(DataSource, id)
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {id} not found.",
        )

    await db.delete(ds)
    await db.commit()
    return None
