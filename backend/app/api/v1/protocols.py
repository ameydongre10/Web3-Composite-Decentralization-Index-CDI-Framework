from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from backend.app.database import get_db
from backend.app.models.protocol import Protocol
from backend.app.schemas.protocol import (
    ProtocolCreate,
    ProtocolUpdate,
    ProtocolResponse,
    ProtocolDetailResponse,
)
from backend.app.schemas.common import PaginatedResponse
from backend.app.security.auth import verify_admin_api_key

router = APIRouter(prefix="/protocols", tags=["Protocols"])


@router.get("", response_model=PaginatedResponse[ProtocolResponse])
async def list_protocols(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    chain: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|name|symbol)$"),
    sort_desc: bool = True,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Protocol)

    if category:
        stmt = stmt.where(Protocol.category == category)
    if chain:
        stmt = stmt.where(Protocol.chain == chain)
    if is_active is not None:
        stmt = stmt.where(Protocol.is_active == is_active)
    if search:
        search_filter = f"%{search}%"
        stmt = stmt.where(
            or_(
                Protocol.name.ilike(search_filter),
                Protocol.symbol.ilike(search_filter),
                Protocol.slug.ilike(search_filter),
            )
        )

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Sorting
    order_col = getattr(Protocol, sort_by)
    stmt = stmt.order_by(order_col.desc() if sort_desc else order_col.asc())

    # Pagination
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    results = (await db.execute(stmt)).scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=[ProtocolResponse.model_validate(p) for p in results],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=ProtocolResponse, status_code=status.HTTP_201_CREATED)
async def create_protocol(
    payload: ProtocolCreate,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    # Check if slug exists
    existing = await db.execute(select(Protocol).where(Protocol.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Protocol with slug '{payload.slug}' already exists.",
        )

    protocol = Protocol(**payload.model_dump())
    db.add(protocol)
    await db.commit()
    await db.refresh(protocol)
    return ProtocolResponse.model_validate(protocol)


@router.get("/{id_or_slug}", response_model=ProtocolDetailResponse)
async def get_protocol(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
):
    if id_or_slug.isdigit():
        stmt = select(Protocol).where(Protocol.id == int(id_or_slug))
    else:
        stmt = select(Protocol).where(Protocol.slug == id_or_slug)

    protocol = (await db.execute(stmt)).scalar_one_or_none()
    if not protocol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Protocol '{id_or_slug}' not found.",
        )
    return ProtocolDetailResponse.model_validate(protocol)


@router.patch("/{id_or_slug}", response_model=ProtocolResponse)
async def update_protocol(
    id_or_slug: str,
    payload: ProtocolUpdate,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    if id_or_slug.isdigit():
        stmt = select(Protocol).where(Protocol.id == int(id_or_slug))
    else:
        stmt = select(Protocol).where(Protocol.slug == id_or_slug)

    protocol = (await db.execute(stmt)).scalar_one_or_none()
    if not protocol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Protocol '{id_or_slug}' not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(protocol, field, val)

    await db.commit()
    await db.refresh(protocol)
    return ProtocolResponse.model_validate(protocol)


@router.delete("/{id_or_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_protocol(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_api_key),
):
    if id_or_slug.isdigit():
        stmt = select(Protocol).where(Protocol.id == int(id_or_slug))
    else:
        stmt = select(Protocol).where(Protocol.slug == id_or_slug)

    protocol = (await db.execute(stmt)).scalar_one_or_none()
    if not protocol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Protocol '{id_or_slug}' not found.",
        )

    await db.delete(protocol)
    await db.commit()
    return None
