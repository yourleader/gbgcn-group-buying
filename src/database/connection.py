"""
Database connection configuration for Group Buying system
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from typing import AsyncGenerator, Generator
import asyncio

from src.core.config import settings
from src.database.models import Base

# Sync engine for migrations and setup
sync_engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG
)

# Async engine for FastAPI
async_database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(
    async_database_url,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG
)

# Session makers
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    expire_on_commit=False
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=sync_engine
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for FastAPI dependency injection"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def get_sync_db() -> Generator[Session, None, None]:
    """Get sync database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

async def init_db() -> None:
    """Initialize database tables"""
    async with async_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

async def close_db() -> None:
    """Close database connections"""
    await async_engine.dispose() 