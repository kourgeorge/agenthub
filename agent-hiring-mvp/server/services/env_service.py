"""Simple environment service for managing external API keys for agents."""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class EnvironmentService:
    """Service for managing external API keys with agent-specific overrides."""
    
    def __init__(self, platform_env_path: Optional[str] = None):
        """
        Initialize the environment service.
        
        Args:
            platform_env_path: Path to the platform API keys file.
                              If None, will look for api_keys.txt in the server directory.
        """
        if platform_env_path:
            self.platform_env_path = Path(platform_env_path)
        else:
            # Default to api_keys.txt in server directory
            self.platform_env_path = Path(__file__).parent.parent / "api_keys.txt"
        
        logger.info(f"Environment service initialized with platform .env: {self.platform_env_path}")
    
    def get_merged_environment_vars(self, agent_env_path: Optional[str] = None) -> Dict[str, str]:
        """
        Get merged environment variables from platform and agent .env files.
        
        Args:
            agent_env_path: Path to agent-specific .env file (optional)
            
        Returns:
            Dictionary of environment variables with agent-specific overrides
        """
        # Start with platform environment variables
        env_vars = self._load_platform_env()
        
        # Override with agent-specific environment variables if provided
        if agent_env_path and os.path.exists(agent_env_path):
            agent_env_vars = self._load_env_file(agent_env_path)
            env_vars.update(agent_env_vars)
            logger.info(f"Merged environment variables from agent .env: {agent_env_path}")
        
        return env_vars
    
    def _load_platform_env(self) -> Dict[str, str]:
        """Load environment variables from the platform api_keys.txt file."""
        if not self.platform_env_path.exists():
            logger.warning(f"Platform api_keys.txt file not found: {self.platform_env_path}")
            return {}
        
        try:
            env_vars = self._load_env_file(str(self.platform_env_path))
            logger.info(f"Loaded {len(env_vars)} environment variables from platform api_keys.txt")
            return env_vars
        except Exception as e:
            logger.error(f"Failed to load platform .env file: {e}")
            return {}
    
    def _load_env_file(self, env_path: str) -> Dict[str, str]:
        """
        Load environment variables from a .env file.
        
        Args:
            env_path: Path to the .env file
            
        Returns:
            Dictionary of environment variables
        """
        try:
            result = {}
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            result[key.strip()] = value.strip()
            return result
        except Exception as e:
            logger.error(f"Failed to load .env file {env_path}: {e}")
            return {}
    
    def create_merged_env_file(self, agent_env_path: Optional[str] = None, 
                              output_path: Optional[str] = None) -> str:
        """
        Create a merged .env file for Docker container deployment.
        
        Args:
            agent_env_path: Path to agent-specific .env file (optional)
            output_path: Path where to save the merged .env file (optional)
            
        Returns:
            Path to the created merged .env file
        """
        env_vars = self.get_merged_environment_vars(agent_env_path)
        
        if output_path is None:
            # Create a temporary file
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            output_path = str(temp_dir / f"merged_env_{os.getpid()}.env")
        
        # Write merged environment variables to file
        with open(output_path, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        logger.info(f"Created merged .env file for Docker: {output_path} with {len(env_vars)} variables")
        return output_path 