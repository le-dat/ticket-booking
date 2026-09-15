# REASON: Provide Async Engine and Async Session Factory for SQLAlchemy 2.0
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from src.core.config import settings

# REASON: Create AsyncEngine with optimized connection pooling for microservices
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,           # REASON: Set to True to print all SQL statements to terminal during debug
    future=True,          # REASON: Enable SQLAlchemy 2.0 standards
    pool_pre_ping=True,   # REASON: Automatically verify connection liveness before checkout
    pool_size=10,         # REASON: Base number of connections maintained in the pool
    max_overflow=20,      # REASON: Maximum overflow connections allowed during load spikes
)

# REASON: Session factory responsible for generating isolated AsyncSessions per request
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # REASON: Prevent SQLAlchemy from refreshing objects post-commit unexpectedly
    autocommit=False,
    autoflush=False,
)


# REASON: Base class for all ORM models in the project
class Base(DeclarativeBase):
    pass


# REASON: FastAPI Dependency providing DB Session per request and ensuring cleanup
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            # REASON: Automatically rollback transaction on unhandled exception
            await session.rollback()
            raise
        finally:
            # REASON: Safely close session and return connection to pool
            await session.close()
