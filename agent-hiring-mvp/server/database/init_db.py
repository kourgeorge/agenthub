"""Database initialization for the Agent Hiring System."""

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import get_engine
from ..models import Base, Agent, User, Hiring, Execution

logger = logging.getLogger(__name__)


def init_database() -> None:
    """Initialize the database with tables and sample data."""
    engine = get_engine()
    
    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create sample data
    logger.info("Creating sample data...")
    create_sample_data(engine)
    
    logger.info("Database initialization completed!")


def create_sample_data(engine) -> None:
    """Create sample data for development."""
    with Session(engine) as session:
        # Check if sample data already exists
        existing_agents = session.query(Agent).count()
        if existing_agents > 0:
            logger.info("Sample data already exists, skipping...")
            return
        
        # Create sample users
        sample_users = [
            User(
                username="admin",
                email="admin@agenthub.com",
                full_name="System Administrator",
                is_active=True,
                is_verified=True,
            ),
            User(
                username="creator1",
                email="creator1@example.com",
                full_name="Agent Creator",
                is_active=True,
                is_verified=True,
            ),
        ]
        
        for user in sample_users:
            session.add(user)
        session.commit()
        
        # Create sample agents
        sample_agents = [
            Agent(
                name="Data Analyzer",
                description="An intelligent agent that analyzes data and provides insights",
                version="1.0.0",
                author="creator1",
                email="creator1@example.com",
                entry_point="main.py:DataAnalyzerAgent",
                requirements=["pandas", "numpy", "matplotlib"],
                tags=["data-analysis", "insights", "visualization"],
                category="data-science",
                pricing_model="per_use",
                price_per_use=0.10,
                status="approved",
                is_public=True,
            ),
            Agent(
                name="Code Reviewer",
                description="Reviews code for best practices, security issues, and improvements",
                version="1.0.0",
                author="creator1",
                email="creator1@example.com",
                entry_point="main.py:CodeReviewerAgent",
                requirements=["ast", "black", "flake8"],
                tags=["code-review", "security", "best-practices"],
                category="development",
                pricing_model="per_use",
                price_per_use=0.25,
                status="approved",
                is_public=True,
            ),
            Agent(
                name="Content Writer",
                description="Creates high-quality content for blogs, articles, and marketing",
                version="1.0.0",
                author="creator1",
                email="creator1@example.com",
                entry_point="main.py:ContentWriterAgent",
                requirements=["openai", "markdown"],
                tags=["content-writing", "marketing", "seo"],
                category="content",
                pricing_model="per_use",
                price_per_use=0.50,
                status="approved",
                is_public=True,
            ),
        ]
        
        for agent in sample_agents:
            session.add(agent)
        session.commit()
        
        logger.info(f"Created {len(sample_users)} users and {len(sample_agents)} agents")


def reset_database() -> None:
    """Reset the database (drop all tables and recreate)."""
    engine = get_engine()
    
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    
    logger.info("Recreating database...")
    init_database()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_database() 