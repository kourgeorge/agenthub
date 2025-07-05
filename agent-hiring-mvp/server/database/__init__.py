"""Database package for the Agent Hiring System."""

from .config import get_database_url, get_engine, get_session, get_session_dependency
from .init_db import init_database

# FastAPI dependency for database sessions
def get_db():
    """Get database session dependency for FastAPI."""
    return get_session_dependency()

__all__ = [
    "get_database_url",
    "get_engine", 
    "get_session",
    "get_db",
    "init_database",
] 