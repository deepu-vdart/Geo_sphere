import os
import logging
import sqlalchemy
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

db_url = settings.DATABASE_URL
engine_kwargs = {"echo": settings.DEBUG}
if "sqlite" not in db_url:
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW

engine = create_async_engine(db_url, **engine_kwargs)


def _setup_sqlite_shims(eng):
    """Register SpatiaLite dummy functions on SQLite connections so GeoAlchemy2 works seamlessly."""
    @event.listens_for(eng.sync_engine, "connect")
    def receive_connect(dbapi_connection, connection_record):
        spatial_shims = [
            ("RecoverGeometryColumn", 5),
            ("InitSpatialMetaData", 0),
            ("AddGeometryColumn", 5),
            ("DiscardGeometryColumn", 2),
            ("CreateSpatialIndex", 2),
            ("DisableSpatialIndex", 2),
            ("CheckSpatialIndex", 2),
            ("ST_AsText", 1),
            ("ST_GeomFromText", 2),
            ("AsEWKB", 1),
            ("AsEWKT", 1),
            ("AsBinary", 1),
            ("AsGeoJSON", 1),
            ("GeomFromEWKB", 1),
            ("GeomFromEWKT", 1),
            ("ST_AsEWKB", 1),
            ("ST_AsEWKT", 1),
        ]
        for fn_name, arity in spatial_shims:
            try:
                dbapi_connection.create_function(fn_name, arity, lambda *args: args[0] if args else None)
            except Exception:
                pass


if "sqlite" in db_url:
    _setup_sqlite_shims(engine)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency: yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables (development use; with SQLite fallback if Postgres is unreachable)."""
    global engine, AsyncSessionLocal

    try:
        async with engine.begin() as conn:
            if "sqlite" not in settings.DATABASE_URL:
                try:
                    await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                    await conn.execute(sqlalchemy.text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
                    logger.info("PostGIS extensions enabled.")
                except Exception as e:
                    logger.warning(f"Could not enable PostGIS extensions (non-fatal): {e}")

            from app.models import project, dataset, processing_job, asset  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables verified.")

    except Exception as e:
        logger.warning(f"Primary database connection failed ({e}). Falling back to local SQLite engine.")
        sqlite_path = os.path.join(settings.DATA_DIR, "geo3d.db")
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        fallback_url = f"sqlite+aiosqlite:///{sqlite_path}"
        engine = create_async_engine(fallback_url, echo=settings.DEBUG)
        _setup_sqlite_shims(engine)
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with engine.begin() as conn:
            from app.models import project, dataset, processing_job, asset  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"Fallback SQLite database initialized at {sqlite_path}.")
