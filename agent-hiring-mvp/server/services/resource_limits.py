"""
Resource limits configuration for agent deployments.
Defines default memory and CPU limits that can be overridden by agent config.
"""

import os
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import re

@dataclass
class ResourceLimits:
    """Resource limits for Docker containers."""
    memory_limit: str  # e.g., "512m", "1g"
    memory_swap: str   # e.g., "1g", "2g"
    cpu_limit: str     # e.g., "1.0", "0.5"
    pids_limit: int    # Maximum number of processes
    ulimits: Optional[Dict[str, int]] = None  # Additional ulimits

class ResourceLimitsConfig:
    """Configuration for resource limits with environment variable support."""
    
    # Default resource limits (can be overridden by environment variables)
    DEFAULT_MEMORY_LIMIT = os.getenv("AGENTHUB_DEFAULT_MEMORY_LIMIT", "512m")
    DEFAULT_MEMORY_SWAP = os.getenv("AGENTHUB_DEFAULT_MEMORY_SWAP", "1g")
    DEFAULT_CPU_LIMIT = os.getenv("AGENTHUB_DEFAULT_CPU_LIMIT", "1.0")
    DEFAULT_PIDS_LIMIT = int(os.getenv("AGENTHUB_DEFAULT_PIDS_LIMIT", "100"))
    
    # Maximum resource limits (safety caps)
    MAX_MEMORY_LIMIT = os.getenv("AGENTHUB_MAX_MEMORY_LIMIT", "4g")
    MAX_MEMORY_SWAP = os.getenv("AGENTHUB_MAX_MEMORY_SWAP", "8g")
    MAX_CPU_LIMIT = float(os.getenv("AGENTHUB_MAX_CPU_LIMIT", "4.0"))
    MAX_PIDS_LIMIT = int(os.getenv("AGENTHUB_MAX_PIDS_LIMIT", "500"))
    
    # Agent type specific defaults
    AGENT_TYPE_DEFAULTS = {
        "function": {
            "memory_limit": "256m",
            "memory_swap": "512m",
            "cpu_limit": "0.5",
            "pids_limit": 50
        },
        "acp_server": {
            "memory_limit": "1g",
            "memory_swap": "2g",
            "cpu_limit": "1.0",
            "pids_limit": 100
        },
        "persistent": {
            "memory_limit": "512m",
            "memory_swap": "1g",
            "cpu_limit": "0.75",
            "pids_limit": 75
        }
    }
    
    @classmethod
    def get_default_limits(cls, agent_type: str = "function") -> ResourceLimits:
        """Get default resource limits for an agent type."""
        type_defaults = cls.AGENT_TYPE_DEFAULTS.get(agent_type, cls.AGENT_TYPE_DEFAULTS["function"])
        
        return ResourceLimits(
            memory_limit=type_defaults["memory_limit"],
            memory_swap=type_defaults["memory_swap"],
            cpu_limit=type_defaults["cpu_limit"],
            pids_limit=type_defaults["pids_limit"]
        )
    
    @classmethod
    def parse_memory_string(cls, memory_str: str) -> int:
        """Parse memory string (e.g., '512m', '1g') to bytes."""
        if not memory_str:
            return 0
        
        # Remove spaces and convert to lowercase
        memory_str = memory_str.strip().lower()
        
        # Extract number and unit
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([kmg])?b?$', memory_str)
        if not match:
            raise ValueError(f"Invalid memory format: {memory_str}")
        
        number = float(match.group(1))
        unit = match.group(2) or 'b'
        
        # Convert to bytes
        multipliers = {'b': 1, 'k': 1024, 'm': 1024**2, 'g': 1024**3}
        return int(number * multipliers[unit])
    
    @classmethod
    def format_memory_bytes(cls, bytes_value: int) -> str:
        """Format bytes to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.0f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.0f}TB"
    
    @classmethod
    def validate_memory_limit(cls, memory_limit: str) -> bool:
        """Validate memory limit format."""
        try:
            cls.parse_memory_string(memory_limit)
            return True
        except ValueError:
            return False
    
    @classmethod
    def validate_cpu_limit(cls, cpu_limit: str) -> bool:
        """Validate CPU limit format."""
        try:
            cpu_val = float(cpu_limit)
            return 0.1 <= cpu_val <= cls.MAX_CPU_LIMIT
        except ValueError:
            return False
    
    @classmethod
    def get_agent_resource_limits(cls, agent_config: Dict[str, Any], agent_type: str = "function") -> ResourceLimits:
        """
        Get resource limits for an agent, combining defaults with agent-specific overrides.
        
        Args:
            agent_config: Agent configuration dictionary
            agent_type: Type of agent (function, acp_server, persistent)
            
        Returns:
            ResourceLimits object with validated limits
        """
        # Start with type-specific defaults
        limits = cls.get_default_limits(agent_type)
        
        # Override with agent-specific config if present
        if "deployment" in agent_config and "resources" in agent_config["deployment"]:
            resources = agent_config["deployment"]["resources"]
            
            # Memory limit override
            if "memory_limit" in resources:
                memory_limit = str(resources["memory_limit"])
                if cls.validate_memory_limit(memory_limit):
                    limits.memory_limit = memory_limit
            
            # Memory swap override
            if "memory_swap" in resources:
                memory_swap = str(resources["memory_swap"])
                if cls.validate_memory_limit(memory_swap):
                    limits.memory_swap = memory_swap
            
            # CPU limit override
            if "cpu_limit" in resources:
                cpu_limit = str(resources["cpu_limit"])
                if cls.validate_cpu_limit(cpu_limit):
                    limits.cpu_limit = cpu_limit
            
            # PIDs limit override
            if "pids_limit" in resources:
                pids_limit = int(resources["pids_limit"])
                if 1 <= pids_limit <= cls.MAX_PIDS_LIMIT:
                    limits.pids_limit = pids_limit
        
        # Apply safety caps
        limits.memory_limit = cls._apply_memory_cap(limits.memory_limit, cls.MAX_MEMORY_LIMIT)
        limits.memory_swap = cls._apply_memory_cap(limits.memory_swap, cls.MAX_MEMORY_SWAP)
        limits.cpu_limit = cls._apply_cpu_cap(limits.cpu_limit, cls.MAX_CPU_LIMIT)
        limits.pids_limit = min(limits.pids_limit, cls.MAX_PIDS_LIMIT)
        
        return limits
    
    @classmethod
    def _apply_memory_cap(cls, memory_limit: str, max_limit: str) -> str:
        """Apply memory cap to ensure limits don't exceed maximums."""
        try:
            limit_bytes = cls.parse_memory_string(memory_limit)
            max_bytes = cls.parse_memory_string(max_limit)
            
            if limit_bytes > max_bytes:
                return max_limit
            
            return memory_limit
        except ValueError:
            return max_limit
    
    @classmethod
    def _apply_cpu_cap(cls, cpu_limit: str, max_limit: float) -> str:
        """Apply CPU cap to ensure limits don't exceed maximums."""
        try:
            limit_float = float(cpu_limit)
            if limit_float > max_limit:
                return str(max_limit)
            
            return cpu_limit
        except ValueError:
            return str(max_limit)
    
    @classmethod
    def to_docker_config(cls, limits: ResourceLimits) -> Dict[str, Any]:
        """
        Convert ResourceLimits to Docker container configuration.
        
        Args:
            limits: ResourceLimits object
            
        Returns:
            Dictionary with Docker resource constraints
        """
        docker_config = {
            "mem_limit": limits.memory_limit,
            "memswap_limit": limits.memory_swap,
            "cpu_quota": int(float(limits.cpu_limit) * 100000),  # Convert to microseconds
            "cpu_period": 100000,  # 100ms period
            "pids_limit": limits.pids_limit
        }
        
        # Add ulimits if specified
        if limits.ulimits:
            docker_config["ulimits"] = limits.ulimits
        
        return docker_config
    
    @classmethod
    def get_resource_summary(cls) -> Dict[str, Any]:
        """Get summary of current resource limit configuration."""
        return {
            "defaults": {
                "memory_limit": cls.DEFAULT_MEMORY_LIMIT,
                "memory_swap": cls.DEFAULT_MEMORY_SWAP,
                "cpu_limit": cls.DEFAULT_CPU_LIMIT,
                "pids_limit": cls.DEFAULT_PIDS_LIMIT
            },
            "maximums": {
                "memory_limit": cls.MAX_MEMORY_LIMIT,
                "memory_swap": cls.MAX_MEMORY_SWAP,
                "cpu_limit": cls.MAX_CPU_LIMIT,
                "pids_limit": cls.MAX_PIDS_LIMIT
            },
            "agent_type_defaults": cls.AGENT_TYPE_DEFAULTS,
            "environment_variables": {
                "AGENTHUB_DEFAULT_MEMORY_LIMIT": cls.DEFAULT_MEMORY_LIMIT,
                "AGENTHUB_DEFAULT_MEMORY_SWAP": cls.DEFAULT_MEMORY_SWAP,
                "AGENTHUB_DEFAULT_CPU_LIMIT": cls.DEFAULT_CPU_LIMIT,
                "AGENTHUB_DEFAULT_PIDS_LIMIT": cls.DEFAULT_PIDS_LIMIT,
                "AGENTHUB_MAX_MEMORY_LIMIT": cls.MAX_MEMORY_LIMIT,
                "AGENTHUB_MAX_MEMORY_SWAP": cls.MAX_MEMORY_SWAP,
                "AGENTHUB_MAX_CPU_LIMIT": cls.MAX_CPU_LIMIT,
                "AGENTHUB_MAX_PIDS_LIMIT": cls.MAX_PIDS_LIMIT
            }
        }

# Convenience functions for easy access
def get_agent_resource_limits(agent_config: Dict[str, Any], agent_type: str = "function") -> ResourceLimits:
    """Get resource limits for an agent."""
    return ResourceLimitsConfig.get_agent_resource_limits(agent_config, agent_type)

def get_default_limits(agent_type: str = "function") -> ResourceLimits:
    """Get default resource limits for an agent type."""
    return ResourceLimitsConfig.get_default_limits(agent_type)

def to_docker_config(limits: ResourceLimits) -> Dict[str, Any]:
    """Convert ResourceLimits to Docker configuration."""
    return ResourceLimitsConfig.to_docker_config(limits)

def get_resource_summary() -> Dict[str, Any]:
    """Get summary of resource limit configuration."""
    return ResourceLimitsConfig.get_resource_summary()
