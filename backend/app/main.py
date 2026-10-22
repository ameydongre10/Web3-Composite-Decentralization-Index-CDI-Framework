from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database import init_db, async_session_maker
from backend.app.utils.seed import seed_database
from backend.app.api.v1.router import v1_router
from backend.app.security.rate_limiter import check_rate_limit


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database schema and run initial seed
    await init_db()
    async with async_session_maker() as session:
        await seed_database(session)
    yield
    # Shutdown logic if any


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security Headers & Rate Limit Middleware
@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    # Apply rate limiter for write/sensitive endpoints
    if request.method in ["POST", "PATCH", "DELETE"] and not request.url.path.startswith("/docs"):
        try:
            await check_rate_limit(request)
        except Exception as exc:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Rate limit exceeded."},
                headers={"Retry-After": "60"},
            )

    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Include master v1 router
app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

# Static files / Frontend mount
frontend_dir = Path(__file__).resolve().parent.parent.parent
if frontend_dir.exists():
    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Web3 CDI Platform Backend Active", "docs": "/api/v1/docs"}

    @app.get("/app.js", include_in_schema=False)
    async def serve_js():
        return FileResponse(frontend_dir / "app.js")

    @app.get("/style.css", include_in_schema=False)
    async def serve_css():
        return FileResponse(frontend_dir / "style.css")


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred.", "error_type": type(exc).__name__},
    )
