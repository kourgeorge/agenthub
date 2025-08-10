"""Database package for the Agent Hiring System."""

from .config import get_database_url, get_engine, get_session, get_session_dependency
from .init_db import init_database, safe_init_database, is_database_initialized, get_current_session, reset_database

# FastAPI dependency for database sessions - use the actual dependency function
get_db = get_session_dependency

__all__ = [
    "get_database_url",
    "get_engine", 
    "get_session",
    "get_db",
    "init_database",
    "safe_init_database",
    "is_database_initialized", 
    "get_current_session",
    "reset_database",
] 