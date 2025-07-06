"""Database configuration for the Agent Hiring System."""

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database settings."""
    
    # Database URL (SQLite for development, PostgreSQL for production)
    database_url: str = "sqlite:///./agent_hiring.db"
    
    # Database connection settings
    echo: bool = False  # SQLAlchemy echo mode
    pool_size: int = 10
    max_overflow: int = 20
    pool_pre_ping: bool = True
    
    class Config:
        env_file = ".env"


# Global settings instance
db_settings = DatabaseSettings()

# Global engine and session factory
_engine: Optional[object] = None
_SessionLocal: Optional[object] = None


def get_database_url() -> str:
    """Get the database URL."""
    return db_settings.database_url


def get_engine():
    """Get the database engine."""
    global _engine
    
    if _engine is None:
        _engine = create_engine(
            db_settings.database_url,
            echo=db_settings.echo,
            pool_size=db_settings.pool_size,
            max_overflow=db_settings.max_overflow,
            pool_pre_ping=db_settings.pool_pre_ping,
        )
    
    return _engine


def get_session() -> Session:
    """Get a database session."""
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return _SessionLocal()


def get_session_dependency() -> Session:
    """Dependency for FastAPI to get database session."""
    db = get_session()
    try:
        yield db
    finally:
        db.close() 