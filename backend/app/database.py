from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# SQLite pool_size/max_overflow args are not supported — only pass them for postgres
_url = settings.DATABASE_URL
_is_sqlite = "sqlite" in _url

if _is_sqlite:
    engine = create_async_engine(_url, echo=False)
else:
    engine = create_async_engine(_url, echo=False, pool_size=10, max_overflow=20)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup (used in local dev without Postgres)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
