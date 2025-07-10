"""Main FastAPI application for the Agent Hiring System with SSL support."""

import logging
import argparse
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database.init_db import init_database
from .api import agents_router, hiring_router, execution_router, acp_router, users_router
from .api.deployment import router as deployment_router
from .api.agent_proxy import router as agent_proxy_router

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
    logger.info("Starting Agent Hiring System with SSL...")
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
app.include_router(deployment_router, prefix="/api/v1")
app.include_router(agent_proxy_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agent Hiring System API (SSL Enabled)",
        "version": "0.1.0",
        "ssl": True,
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "agents": "/api/v1/agents",
            "users": "/api/v1/users",
            "hiring": "/api/v1/hiring",
            "execution": "/api/v1/execution",
            "acp": "/api/v1/acp",
            "deployment": "/api/v1/deployment",
            "agent_proxy": "/api/v1/agent-proxy"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "agent-hiring-system",
        "version": "0.1.0",
        "ssl": True,
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
    """Main entry point with SSL support."""
    parser = argparse.ArgumentParser(description="Agent Hiring System with SSL")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8443,  # Default HTTPS port
        help="Port to bind to (default: 8443 for HTTPS)"
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
    parser.add_argument(
        "--ssl-certfile",
        default="ssl_certs/cert.pem",
        help="Path to SSL certificate file (.crt or .pem)"
    )
    parser.add_argument(
        "--ssl-keyfile", 
        default="ssl_certs/key.pem",
        help="Path to SSL private key file (.key or .pem)"
    )
    parser.add_argument(
        "--ssl-ca-certs",
        help="Path to CA certificates file (optional)"
    )
    parser.add_argument(
        "--generate-certs",
        action="store_true",
        help="Generate self-signed certificates for testing"
    )
    
    args = parser.parse_args()
    
    if args.dev:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Development mode enabled")
    
    # Generate self-signed certificates if requested
    if args.generate_certs:
        generate_self_signed_certs(args.ssl_certfile, args.ssl_keyfile)
    
    # Check if SSL files exist
    if not os.path.exists(args.ssl_certfile) or not os.path.exists(args.ssl_keyfile):
        logger.error(f"SSL certificate files not found!")
        logger.error(f"Certificate: {args.ssl_certfile}")
        logger.error(f"Private key: {args.ssl_keyfile}")
        logger.error("Use --generate-certs to create self-signed certificates for testing")
        return
    
    import uvicorn
    
    # SSL configuration
    ssl_config = {
        "ssl_certfile": args.ssl_certfile,
        "ssl_keyfile": args.ssl_keyfile,
    }
    
    if args.ssl_ca_certs:
        ssl_config["ssl_ca_certs"] = args.ssl_ca_certs
    
    logger.info(f"Starting server with SSL on {args.host}:{args.port}")
    logger.info(f"Certificate: {args.ssl_certfile}")
    logger.info(f"Private key: {args.ssl_keyfile}")
    
    uvicorn.run(
        "server.main_ssl:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if args.dev else "info",
        **ssl_config
    )


def generate_self_signed_certs(cert_file: str, key_file: str):
    """Generate self-signed certificates for testing."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from datetime import datetime, timedelta
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(cert_file), exist_ok=True)
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AgentHub"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress("127.0.0.1"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write certificate
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Write private key
        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        logger.info(f"Generated self-signed certificates:")
        logger.info(f"  Certificate: {cert_file}")
        logger.info(f"  Private key: {key_file}")
        logger.info("⚠️  These are self-signed certificates for testing only!")
        
    except ImportError:
        logger.error("cryptography library not found. Install with: pip install cryptography")
        logger.error("Or use OpenSSL to generate certificates manually:")
        logger.error("  openssl req -x509 -newkey rsa:4096 -keyout ssl_certs/key.pem -out ssl_certs/cert.pem -days 365 -nodes")
    except Exception as e:
        logger.error(f"Failed to generate certificates: {e}")


if __name__ == "__main__":
    main() 