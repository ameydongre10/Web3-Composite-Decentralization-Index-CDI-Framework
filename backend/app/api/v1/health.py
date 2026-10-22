from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx

from backend.app.database import get_db
from backend.app.config import settings

router = APIRouter(tags=["Health & System"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    # Check database
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check external RPC
    rpc_status = "untested"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                settings.ETHEREUM_RPC_URL,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            )
            rpc_status = "reachable" if resp.status_code == 200 else f"http_{resp.status_code}"
    except Exception:
        rpc_status = "offline/fallback_active"

    return {
        "status": "ready" if db_status == "connected" else "degraded",
        "database": db_status,
        "ethereum_rpc": rpc_status,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
