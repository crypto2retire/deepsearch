from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Basic health check - always returns ok if app is running."""
    return {"status": "ok", "service": "deepsearch"}


@router.get("/health/ready")
async def health_ready():
    """
    Readiness check - verifies DB connectivity if DATABASE_URL is set.
    Railway's /health probe should use this endpoint.
    """
    from app.config import get_settings
    from app.database import _get_engine

    s = get_settings()

    if s.DATABASE_URL:
        try:
            engine = _get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "ok", "service": "deepsearch", "db": "connected"}
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "error", "service": "deepsearch", "db": "unreachable", "detail": str(e)},
            )
    else:
        # No DB configured (e.g. local dev without DB)
        return {"status": "ok", "service": "deepsearch", "db": "not_configured"}
