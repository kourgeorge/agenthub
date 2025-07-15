"""Database initialization for the Agent Hiring System."""

import logging
from .config import get_engine
from ..models import Base

logger = logging.getLogger(__name__)


def init_database() -> None:
    """Initialize the database with tables/schema only."""
    engine = get_engine()
    
    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialization completed!")
    
    # Run migrations
    try:
        from .migrate_add_container_logs import migrate_add_container_logs
        migrate_add_container_logs()
    except Exception as e:
        logger.warning(f"Migration failed (this is normal for new databases): {e}")


def reset_database() -> None:
    """Reset the database (drop all tables and recreate schema only)."""
    engine = get_engine()
    
    logger.info("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    logger.info("Recreating database schema...")
    init_database()
    
    logger.info("Database reset completed!")


if __name__ == "__main__":
    init_database() 