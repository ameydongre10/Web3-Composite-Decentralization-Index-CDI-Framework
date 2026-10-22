from fastapi import APIRouter
from backend.app.api.v1.protocols import router as protocols_router
from backend.app.api.v1.data_sources import router as data_sources_router
from backend.app.api.v1.snapshots import router as snapshots_router
from backend.app.api.v1.jobs import router as jobs_router
from backend.app.api.v1.alerts import router as alerts_router
from backend.app.api.v1.metrics import router as metrics_router
from backend.app.api.v1.health import router as health_router

v1_router = APIRouter()

v1_router.include_router(health_router)
v1_router.include_router(protocols_router)
v1_router.include_router(data_sources_router)
v1_router.include_router(snapshots_router)
v1_router.include_router(jobs_router)
v1_router.include_router(alerts_router)
v1_router.include_router(metrics_router)
