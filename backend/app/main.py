"""
TABLZ — FastAPI application factory with lifespan events.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.errors import AppException
from app.core.rate_limit import close_redis
from app.routers.auth import router as auth_router
from app.routers.menu import router as menu_router
from app.routers.tables import router as tables_router
from app.routers.orders import router as orders_router
from app.routers.analytics import router as analytics_router
from app.routers.websocket import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: DB engine is created lazily by SQLAlchemy on first use
    print(f"[TABLZ] Starting in {settings.ENVIRONMENT} mode")
    yield
    # Shutdown: close Redis
    await close_redis()
    print("[TABLZ] Shutdown complete")


app = FastAPI(
    title="TABLZ API",
    description="AI-Powered Restaurant Management Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# ─── CORS ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        settings.BASE_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global exception handler for AppException ───
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.error_message,
                "suggestion": exc.suggestion,
                "http_status": exc.status_code,
                "request_id": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
        headers=exc.headers,
    )


# ─── Routers ───
app.include_router(auth_router)
app.include_router(menu_router)
app.include_router(tables_router)
app.include_router(orders_router)
app.include_router(analytics_router)
app.include_router(ws_router)


# ─── Health check ───
@app.get("/health")
async def health():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}
