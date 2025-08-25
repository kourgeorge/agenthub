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

from .database.init_db import init_database, get_current_session
from .services.token_service import TokenService
from .services.resource_usage_tracker import ResourceUsageTracker
from .models.deployment import AgentDeployment
from .models.hiring import Hiring
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
    diagnostic_router,
    agent_proxy_router,
    resources_router,
    auth_router,
    api_keys_router,
    stats_router,
    earnings_router,
    contact_router,
    webhooks_router,
    admin_router,
    admin_permissions_router,
    metrics_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global task references for monitoring
cleanup_task = None
metrics_task = None
metrics_collection_active = False


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





async def collect_container_metrics():
    """Background task to continuously collect container resource usage metrics."""
    # Wait a bit for the system to fully initialize before starting metrics collection
    await asyncio.sleep(10)
    logger.info("Starting container metrics collection service...")
    
    while True:
        try:
            # Get a fresh database session for this iteration
            db = get_current_session()
            try:
                # Check if the required tables exist before querying
                try:
                    # Simple check if tables exist by doing a basic query
                    db.execute(db.query(AgentDeployment).limit(1).statement)
                    
                    # Get all running deployments
                    running_deployments = db.query(AgentDeployment).join(Hiring).filter(
                        AgentDeployment.status == "running"
                    ).all()
                except Exception as table_error:
                    # Tables might not be ready yet, skip this iteration
                    logger.debug(f"Tables not ready for metrics collection: {table_error}")
                    await asyncio.sleep(30)
                    continue
                
                if running_deployments:
                    logger.info(f"Collecting metrics for {len(running_deployments)} running deployments")
                    
                    # Initialize resource usage tracker
                    tracker = ResourceUsageTracker(db)
                    
                    # Collect metrics for each running deployment
                    for deployment in running_deployments:
                        try:
                            # Check if container still exists and is running
                            if deployment.container_name:
                                # Run the synchronous collect_container_metrics in a thread pool
                                loop = asyncio.get_event_loop()
                                resource_usage = await loop.run_in_executor(
                                    None, 
                                    tracker.collect_container_metrics, 
                                    deployment.deployment_id
                                )
                                
                                if not resource_usage:
                                    logger.debug(f"No metrics collected for deployment {deployment.deployment_id} (container may not be accessible)")
                                    
                            else:
                                # This deployment will be handled by the reconciliation service
                                logger.debug(f"Deployment {deployment.deployment_id} has no container name - will be reconciled")
                                continue
                                
                        except Exception as e:
                            logger.error(f"Error collecting metrics for deployment {deployment.deployment_id}: {e}")
                            continue
                    
                    logger.info(f"Completed metrics collection for {len(running_deployments)} deployments")
                else:
                    logger.debug("No running deployments found for metrics collection")
                    
            except Exception as e:
                logger.error(f"Error in container metrics collection: {e}")
            finally:
                db.close()
                
            # Wait for next collection cycle (30 seconds as configured in ResourceUsageTracker)
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Fatal error in container metrics collection loop: {e}")
            # Wait a bit longer on error before retrying
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global cleanup_task, metrics_task, metrics_collection_active
    
    # Startup
    logger.info("Starting Agent Hiring System...")
    try:
        init_database()
        logger.info("Database initialized successfully")
        
        # Start background cleanup task
        cleanup_task = asyncio.create_task(cleanup_tokens())
        logger.info("Token cleanup task started")
        
        # Start container metrics collection task
        metrics_task = asyncio.create_task(collect_container_metrics())
        metrics_collection_active = True
        logger.info("Container metrics collection task started")
        

        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent Hiring System...")
    try:
        if cleanup_task:
            cleanup_task.cancel()
            await cleanup_task
            logger.info("Token cleanup task stopped")
        
        if metrics_task:
            metrics_task.cancel()
            await metrics_task
            metrics_collection_active = False
            logger.info("Container metrics collection task stopped")
        

        
    except Exception as e:
        logger.error(f"Error stopping background tasks: {e}")


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
app.include_router(diagnostic_router, prefix="/api/v1")
app.include_router(agent_proxy_router, prefix="/api/v1")
app.include_router(resources_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(stats_router, prefix="/api/v1")
app.include_router(earnings_router, prefix="/api/v1")
app.include_router(contact_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(admin_permissions_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")


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
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint to monitor system status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": "connected",
            "token_cleanup": "active" if cleanup_task and not cleanup_task.done() else "inactive",
            "metrics_collection": "active" if metrics_collection_active and metrics_task and not metrics_task.done() else "inactive"
        },
        "metrics_collection": {
            "active": metrics_collection_active,
            "task_status": "running" if metrics_task and not metrics_task.done() else "stopped",
            "last_error": None  # Could be enhanced to track last error
        }
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
    
    # Provide more specific error messages for common exceptions
    if isinstance(exc, ValueError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )
    elif isinstance(exc, KeyError):
        return JSONResponse(
            status_code=400,
            content={"detail": f"Missing required field: {str(exc)}"},
        )
    elif isinstance(exc, AttributeError):
        return JSONResponse(
            status_code=400,
            content={"detail": f"Invalid attribute: {str(exc)}"},
        )
    elif isinstance(exc, TypeError):
        return JSONResponse(
            status_code=400,
            content={"detail": f"Type error: {str(exc)}"},
        )
    else:
        # For other exceptions, provide a generic message but log the actual error
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
        workers=1,  # Use 1 worker if reload is enabled
    )


if __name__ == "__main__":
    main() 