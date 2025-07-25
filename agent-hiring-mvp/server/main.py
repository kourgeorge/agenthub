"""Main FastAPI application for the Agent Hiring System."""

import logging
import argparse
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# StaticFiles removed - no static files needed for API-only server
from fastapi.responses import JSONResponse
# SessionMiddleware removed - not needed for server-side only API

from .database.init_db import init_database
from .api import agents_router, hiring_router, execution_router, acp_router, users_router, billing_router

from .api.deployment import router as deployment_router
from .api.agent_proxy import router as agent_proxy_router
from .api.resources import router as resources_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Agent Hiring System...")
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent Hiring System...")


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
    )


if __name__ == "__main__":
    main() 