"""
Configuration file for the Agent Hiring System MVP.
Centralizes all configuration constants and settings.
"""

import os
from typing import Optional

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================

# Default server configuration
DEFAULT_SERVER_HOST = "localhost"
DEFAULT_SERVER_PORT = 8002
DEFAULT_SERVER_URL = f"http://{DEFAULT_SERVER_HOST}:{DEFAULT_SERVER_PORT}"

# Environment variable overrides
SERVER_HOST = os.getenv("AGENT_HIRING_HOST", DEFAULT_SERVER_HOST)
SERVER_PORT = int(os.getenv("AGENT_HIRING_PORT", DEFAULT_SERVER_PORT))
SERVER_URL = os.getenv("AGENT_HIRING_URL", DEFAULT_SERVER_URL)

# API configuration
API_VERSION = "v1"
API_BASE_PATH = f"/api/{API_VERSION}"
FULL_API_BASE_URL = f"{SERVER_URL}{API_BASE_PATH}"

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///agent_hiring.db")
DATABASE_ECHO = os.getenv("DATABASE_ECHO", "false").lower() == "true"

# =============================================================================
# AGENT RUNTIME CONFIGURATION
# =============================================================================

# Execution limits
MAX_EXECUTION_TIME = int(os.getenv("MAX_EXECUTION_TIME", 30))  # seconds
MAX_OUTPUT_SIZE = int(os.getenv("MAX_OUTPUT_SIZE", 1024 * 1024))  # 1MB
MAX_CODE_SIZE = int(os.getenv("MAX_CODE_SIZE", 10 * 1024 * 1024))  # 10MB

# Security settings
ALLOWED_FILE_EXTENSIONS = {'.py', '.js', '.sh', '.txt', '.json', '.yaml', '.yml'}
FORBIDDEN_COMMANDS = {
    'rm', 'del', 'format', 'mkfs', 'dd', 'shutdown', 'reboot',
    'sudo', 'su', 'chmod', 'chown', 'mount', 'umount'
}

# =============================================================================
# API ENDPOINTS
# =============================================================================

class Endpoints:
    """API endpoint constants."""
    
    # Health and info
    HEALTH = "/health"
    ROOT = "/"
    DOCS = "/docs"
    REDOC = "/redoc"
    
    # Agents
    AGENTS = f"{API_BASE_PATH}/agents"
    AGENT_SUBMIT = f"{API_BASE_PATH}/agents/submit"
    AGENT_DETAILS = f"{API_BASE_PATH}/agents/{{agent_id}}"
    AGENT_APPROVE = f"{API_BASE_PATH}/agents/{{agent_id}}/approve"
    AGENT_REJECT = f"{API_BASE_PATH}/agents/{{agent_id}}/reject"
    
    # Hiring
    HIRING = f"{API_BASE_PATH}/hiring"
    HIRING_HIRE = f"{API_BASE_PATH}/hiring/hire/{{agent_id}}"
    HIRING_USER = f"{API_BASE_PATH}/hiring/user/{{user_id}}"
    HIRING_STATS = f"{API_BASE_PATH}/hiring/stats/user/{{user_id}}"
    
    # Execution
    EXECUTION = f"{API_BASE_PATH}/execution"
    EXECUTION_DETAILS = f"{API_BASE_PATH}/execution/{{execution_id}}"
    EXECUTION_RUN = f"{API_BASE_PATH}/execution/{{execution_id}}/run"
    EXECUTION_AGENT = f"{API_BASE_PATH}/execution/agent/{{agent_id}}"
    EXECUTION_STATS = f"{API_BASE_PATH}/execution/stats/agent/{{agent_id}}"
    
    # ACP Protocol
    ACP_DISCOVERY = f"{API_BASE_PATH}/acp/discovery"
    ACP_CAPABILITIES = f"{API_BASE_PATH}/acp/capabilities"
    ACP_SESSION = f"{API_BASE_PATH}/acp/session"
    ACP_MESSAGE = f"{API_BASE_PATH}/acp/{{execution_id}}/message"
    ACP_STATUS = f"{API_BASE_PATH}/acp/{{execution_id}}/status"

# =============================================================================
# TEST CONFIGURATION
# =============================================================================

# Test settings
TEST_SERVER_URL = os.getenv("TEST_SERVER_URL", SERVER_URL)
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", 30))  # seconds
TEST_WAIT_TIME = int(os.getenv("TEST_WAIT_TIME", 2))  # seconds

# Test data
TEST_AGENT_NAME = "Test Submission Agent"
TEST_AGENT_AUTHOR = "Integration Test"
TEST_AGENT_EMAIL = "test@integration.example.com"

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Logging levels
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# =============================================================================
# FILE PATHS
# =============================================================================

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(BASE_DIR, "server")
TESTS_DIR = os.path.join(BASE_DIR, "tests")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_server_url(host: Optional[str] = None, port: Optional[int] = None) -> str:
    """Get the server URL with optional host/port override."""
    if host and port:
        return f"http://{host}:{port}"
    elif host:
        return f"http://{host}:{SERVER_PORT}"
    elif port:
        return f"http://{SERVER_HOST}:{port}"
    else:
        return SERVER_URL

def get_api_url(endpoint: str, **kwargs) -> str:
    """Get a full API URL for an endpoint."""
    base = get_server_url()
    endpoint_url = endpoint.format(**kwargs) if kwargs else endpoint
    return f"{base}{endpoint_url}"

def get_test_config() -> dict:
    """Get configuration for tests."""
    return {
        "server_url": TEST_SERVER_URL,
        "api_base": f"{TEST_SERVER_URL}{API_BASE_PATH}",
        "timeout": TEST_TIMEOUT,
        "wait_time": TEST_WAIT_TIME,
        "test_agent": {
            "name": TEST_AGENT_NAME,
            "author": TEST_AGENT_AUTHOR,
            "email": TEST_AGENT_EMAIL,
        }
    }

# =============================================================================
# VALIDATION
# =============================================================================

def validate_config():
    """Validate configuration values."""
    errors = []
    
    if SERVER_PORT < 1 or SERVER_PORT > 65535:
        errors.append(f"Invalid server port: {SERVER_PORT}")
    
    if MAX_EXECUTION_TIME < 1:
        errors.append(f"Invalid max execution time: {MAX_EXECUTION_TIME}")
    
    if MAX_OUTPUT_SIZE < 1024:
        errors.append(f"Invalid max output size: {MAX_OUTPUT_SIZE}")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

# Validate configuration on import
validate_config() 