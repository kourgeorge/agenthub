"""Main FastAPI application for the Agent Hiring System."""

import logging
import argparse
import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# StaticFiles removed - no static files needed for API-only server
from fastapi.responses import JSONResponse
# SessionMiddleware removed - not needed for server-side only API

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from the project root (agent-hiring-mvp directory)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logging.info(f"Loaded environment variables from {env_path}")
    else:
        logging.warning(f".env file not found at {env_path}")
except ImportError:
    logging.warning("python-dotenv not installed, environment variables may not be loaded from .env file")

from .database.init_db import init_database
from .services.token_service import TokenService
# Import models to ensure they're registered with SQLAlchemy Base metadata
from .models import *
from .api import (
    agents_router, 
    hiring_router, 
    execution_router, 
    acp_router, 
    users_router, 
    billing_router,
    deployment_router,
    agent_proxy_router,
    resources_router,
    auth_router,
    api_keys_router,
    stats_router,
    earnings_router,
    contact_router,
    webhooks_router,
    admin_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def cleanup_tokens():
    """Background task to clean up expired tokens and blacklist."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            TokenService.cleanup_expired_tokens()
            TokenService.cleanup_blacklist()
            logger.info("Token cleanup completed")
        except Exception as e:
            logger.error(f"Error during token cleanup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Agent Hiring System...")
    try:
        init_database()
        logger.info("Database initialized successfully")
        
        # Start background cleanup task
        cleanup_task = asyncio.create_task(cleanup_tokens())
        logger.info("Token cleanup task started")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent Hiring System...")
    try:
        cleanup_task.cancel()
        await cleanup_task
        logger.info("Token cleanup task stopped")
    except Exception as e:
        logger.error(f"Error stopping cleanup task: {e}")


# Create FastAPI app
app = FastAPI(
    title="Agent Hiring System",
    description="A platform for hiring and managing AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

# Session middleware removed - not needed for server-side only API

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with API prefix
app.include_router(agents_router, prefix="/api/v1")
app.include_router(hiring_router, prefix="/api/v1")
app.include_router(execution_router, prefix="/api/v1")
app.include_router(acp_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(deployment_router, prefix="/api/v1")
app.include_router(agent_proxy_router, prefix="/api/v1")
app.include_router(resources_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(stats_router, prefix="/api/v1")
app.include_router(earnings_router, prefix="/api/v1")
app.include_router(contact_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agent Hiring System API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "agents": "/api/v1/agents",
            "users": "/api/v1/users",
            "hiring": "/api/v1/hiring",
            "execution": "/api/v1/execution",
            "acp": "/api/v1/acp",
            "billing": "/api/v1/billing",
            "deployment": "/api/v1/deployment",
            "agent_proxy": "/api/v1/agent-proxy",
            "resources": "/api/v1/resources",
            "api_keys": "/api/v1/api-keys",
            "earnings": "/api/v1/earnings",
            "contact": "/api/v1/contact",
            "webhooks": "/api/v1/webhooks",
            "admin": "/api/v1/admin"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "agent-hiring-system",
        "version": "0.1.0",
    }


@app.post("/refresh")
async def refresh_database():
    """Refresh database connection and reinitialize data."""
    try:
        logger.info("Refreshing database connection...")
        init_database()
        logger.info("Database refreshed successfully")
        return {
            "status": "success",
            "message": "Database refreshed successfully",
            "service": "agent-hiring-system",
        }
    except Exception as e:
        logger.error(f"Failed to refresh database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh database: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Agent Hiring System")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable development mode"
    )
    
    args = parser.parse_args()
    
    if args.dev:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Development mode enabled")
    
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if args.dev else "info",
        workers=1 if args.reload else 4,  # Use 1 worker if reload is enabled
    )


if __name__ == "__main__":
    main() 