"""Database initialization for the Agent Hiring System."""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from .config import get_database_url
from ..models.base import Base

logger = logging.getLogger(__name__)

def is_database_initialized() -> bool:
    """Check if the database is already initialized by checking if key tables and permissions exist."""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # Check if key tables exist
        with engine.connect() as connection:
            # Check if users table exists
            result = connection.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='users'
            """))
            if not result.fetchone():
                return False
            
            # Check if permissions table exists and has data
            result = connection.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='permissions'
            """))
            if not result.fetchone():
                return False
            
            # Check if permissions have been seeded
            result = connection.execute(text("""
                SELECT COUNT(*) FROM permissions
            """))
            permission_count = result.fetchone()[0]
            return permission_count > 0
            
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
        
        # Seed default permissions and roles ONLY if they don't exist
        try:
            from .seed_permissions import PermissionSeeder
            session = SessionLocal()
            
            # Check if system is already fully initialized
            if PermissionSeeder.is_system_initialized(session):
                logger.info("System already fully initialized, skipping seeding")
            else:
                logger.info("System not fully initialized, running initial seeding...")
                try:
                    PermissionSeeder.seed_all(session)
                    logger.info("Default permissions and roles seeded successfully")
                except Exception as seeding_error:
                    logger.warning(f"Permission seeding failed: {seeding_error}")
                    # Check if another process might have succeeded
                    if PermissionSeeder.is_system_initialized(session):
                        logger.info("System appears to be initialized by another process")
                    else:
                        logger.error("Permission system initialization failed completely")
            
            session.close()
        except Exception as e:
            logger.warning(f"Could not check or seed permissions: {e}")
            # Don't fail the entire initialization if permission seeding fails
            # The system can still function with manual permission setup
        
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