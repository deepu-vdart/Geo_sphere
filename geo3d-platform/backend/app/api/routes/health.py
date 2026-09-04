from datetime import datetime, timezone
from fastapi import APIRouter
from sqlalchemy import text
import app.database as db_mod
from app.config import get_settings
from app.schemas.schemas import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint — verifies API and database connectivity."""
    db_status = "unavailable"
    try:
        async with db_mod.AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)[:80]}"

    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/version", tags=["System"])
async def get_version():
    """Return application version information."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }



@router.get("/version", tags=["System"])
async def get_version():
    """Return application version information."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
