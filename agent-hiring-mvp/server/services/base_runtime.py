"""Base runtime classes and enums for agent execution."""

import json
from enum import Enum
from typing import Optional, Dict, Any


class RuntimeStatus(str, Enum):
    """Runtime status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    SECURITY_VIOLATION = "security_violation"


class RuntimeResult:
    """Result of a runtime operation."""
    
    def __init__(self, 
                 status: RuntimeStatus,
                 output: Optional[Any] = None,
                 error: Optional[str] = None,
                 execution_time: Optional[float] = None,
                 exit_code: Optional[int] = None,
                 container_logs: Optional[str] = None):
        self.status = status
        self.output = output
        self.error = error
        self.execution_time = execution_time
        self.exit_code = exit_code
        self.container_logs = container_logs
    
    def __repr__(self) -> str:
        return f"RuntimeResult(status={self.status}, output={self.output}, error={self.error})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value if isinstance(self.status, RuntimeStatus) else str(self.status),
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "exit_code": self.exit_code,
            "container_logs": self.container_logs
        }
