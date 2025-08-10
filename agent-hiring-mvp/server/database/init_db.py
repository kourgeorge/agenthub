"""Database initialization for the Agent Hiring System."""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from .config import get_database_url
from ..models.base import Base

logger = logging.getLogger(__name__)

def is_database_initialized() -> bool:
    """Check if the database is already initialized by checking if key tables exist."""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # Check if a key table exists (users table is a good indicator)
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='users'
            """))
            return result.fetchone() is not None
    except Exception as e:
        logger.warning(f"Could not check database initialization status: {e}")
        return False


def safe_init_database():
    """Safely initialize the database, handling concurrent calls gracefully."""
    try:
        # Check if database is already initialized
        if is_database_initialized():
            logger.info("Database already initialized, skipping...")
            return None, None
        
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # Test database connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            logger.info("Database connection successful")
        
        # Create all tables - this will handle the case where tables already exist
        try:
            print(f"DEBUG: About to create all tables. Base metadata tables: {list(Base.metadata.tables.keys())}")
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified successfully")
            print(f"DEBUG: Successfully created all tables")
        except OperationalError as e:
            if "already exists" in str(e):
                logger.info("Database tables already exist, continuing...")
                print(f"DEBUG: Tables already exist, continuing...")
            else:
                logger.error(f"Error creating database tables: {e}")
                print(f"DEBUG: Error creating tables: {e}")
                raise
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        logger.info("Database initialization completed successfully")
        return engine, SessionLocal
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def init_database():
    """Initialize the database and create all tables."""
    return safe_init_database()


def get_current_session():
    """Get the current database session."""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        raise


def reset_database() -> None:
    """Reset the database (drop all tables and recreate schema only)."""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        logger.info("Dropping all tables...")
        try:
            Base.metadata.drop_all(bind=engine)
            logger.info("All tables dropped successfully")
        except OperationalError as e:
            if "no such table" in str(e).lower():
                logger.info("No tables to drop, continuing...")
            else:
                logger.error(f"Error dropping tables: {e}")
                raise
        
        logger.info("Recreating database schema...")
        safe_init_database()
        
        logger.info("Database reset completed!")
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        raise


if __name__ == "__main__":
    init_database() 