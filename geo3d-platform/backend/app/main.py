"""
Geo3D Platform — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import get_settings
from app.database import init_db
from app.api.routes import health, projects, datasets, jobs, analysis, aoi, terrain, ai, providers, classification, temporal, gl3d

# ─── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")

    # Ensure data directories exist
    for d in [settings.DATA_DIR, settings.RAW_DIR, settings.PROCESSED_DIR,
              settings.TERRAIN_DIR, settings.TILES_DIR]:
        os.makedirs(d, exist_ok=True)

    # Initialize database tables
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("Continuing without database — some endpoints will fail.")

    yield

    logger.info("Shutting down Geo3D Platform.")


# ─── Application Factory ─────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Geo3D Interactive 3D Digital Twin Platform API. "
        "Provides endpoints for projects, datasets, processing jobs, "
        "3D assets, analysis, and AI features."
    ),
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── Routes ──────────────────────────────────────────────────────────────────

app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(projects.router, prefix=settings.API_PREFIX)
app.include_router(datasets.router, prefix=settings.API_PREFIX)
app.include_router(jobs.router, prefix=settings.API_PREFIX)
app.include_router(analysis.router, prefix=settings.API_PREFIX)
app.include_router(aoi.router, prefix=settings.API_PREFIX)
app.include_router(terrain.router, prefix=settings.API_PREFIX)
app.include_router(ai.router, prefix=settings.API_PREFIX)
app.include_router(providers.router, prefix=settings.API_PREFIX)
app.include_router(classification.router, prefix=settings.API_PREFIX)
app.include_router(temporal.router, prefix=settings.API_PREFIX)
app.include_router(gl3d.router, prefix=settings.API_PREFIX)


# ─── Root ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_PREFIX}/docs",
        "health": f"{settings.API_PREFIX}/health",
    }

