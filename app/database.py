from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from functools import lru_cache

_engine = None
_async_session = None


def _get_engine():
    global _engine
    if _engine is None:
        from app.config import get_settings
        settings = get_settings()
        db_url = settings.DATABASE_URL
        # Ensure async driver prefix for SQLAlchemy async engine
        if db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        _engine = create_async_engine(db_url, echo=False)
    return _engine


def _get_session_maker():
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session


class Base(DeclarativeBase):
    pass


@property
def engine():
    """Lazy engine accessor — backwards-compatible import target."""
    return _get_engine()


async def get_db() -> AsyncSession:
    async with _get_session_maker()() as session:
        yield session
