"""Client for submitting agents to the hiring platform."""

import json
import logging
import zipfile
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

import aiohttp
import aiofiles

from .agent import Agent, AgentConfig

logger = logging.getLogger(__name__)


class AgentHiringClient:
    """Client for interacting with the Agent Hiring System."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def submit_agent(
        self,
        agent: Agent,
        code_directory: str,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit an agent to the hiring platform."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        # Validate agent configuration
        validation_errors = agent.validate_config()
        if validation_errors:
            raise ValueError(f"Agent validation failed: {validation_errors}")
        
        # Create code ZIP file
        zip_path = await self._create_code_zip(code_directory)
        
        try:
            # Prepare form data
            config = agent.get_config()
            form_data = aiohttp.FormData()
            
            # Add agent metadata
            form_data.add_field("name", config.name)
            form_data.add_field("description", config.description)
            form_data.add_field("version", config.version)
            form_data.add_field("author", config.author)
            form_data.add_field("email", config.email)
            form_data.add_field("entry_point", config.entry_point)
            
            if config.requirements:
                form_data.add_field("requirements", json.dumps(config.requirements))
            
            if config.config_schema:
                form_data.add_field("config_schema", json.dumps(config.config_schema))
            
            if config.tags:
                form_data.add_field("tags", json.dumps(config.tags))
            
            if config.category:
                form_data.add_field("category", config.category)
            
            if config.pricing_model:
                form_data.add_field("pricing_model", config.pricing_model)
            
            if config.price_per_use is not None:
                form_data.add_field("price_per_use", str(config.price_per_use))
            
            if config.monthly_price is not None:
                form_data.add_field("monthly_price", str(config.monthly_price))
            
            # Add code file
            async with aiofiles.open(zip_path, "rb") as f:
                code_content = await f.read()
                form_data.add_field(
                    "code_file",
                    code_content,
                    filename="agent_code.zip",
                    content_type="application/zip"
                )
            
            # Submit agent
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            async with self.session.post(
                f"{self.base_url}/api/agents/submit",
                data=form_data,
                headers=headers,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Agent submitted successfully: {result}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to submit agent: {error_text}")
                    raise Exception(f"Submission failed: {error_text}")
        
        finally:
            # Clean up ZIP file
            if os.path.exists(zip_path):
                os.unlink(zip_path)
    
    async def list_agents(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List available agents."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        params = {"skip": skip, "limit": limit}
        if query:
            params["query"] = query
        if category:
            params["category"] = category
        
        async with self.session.get(
            f"{self.base_url}/api/agents",
            params=params,
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to list agents: {error_text}")
    
    async def get_agent(self, agent_id: int) -> Dict[str, Any]:
        """Get agent details."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.base_url}/api/agents/{agent_id}",
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get agent: {error_text}")
    
    async def hire_agent(
        self,
        agent_id: int,
        config: Optional[Dict[str, Any]] = None,
        billing_cycle: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Hire an agent."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        data = {
            "agent_id": agent_id,
            "config": config or {},
            "billing_cycle": billing_cycle or "per_use",
        }
        
        if user_id:
            data["user_id"] = user_id
        
        async with self.session.post(
            f"{self.base_url}/api/hiring/hire/{agent_id}",
            json=data,
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to hire agent: {error_text}")
    
    async def _create_code_zip(self, code_directory: str) -> str:
        """Create a ZIP file from the code directory."""
        code_path = Path(code_directory)
        if not code_path.exists():
            raise ValueError(f"Code directory does not exist: {code_directory}")
        
        # Create temporary ZIP file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp_zip.close()
        
        try:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in code_path.rglob('*'):
                    if file_path.is_file():
                        # Skip common files that shouldn't be included
                        if any(skip in str(file_path) for skip in [
                            '__pycache__', '.git', '.env', '.DS_Store', '.pyc'
                        ]):
                            continue
                        
                        # Add file to ZIP with relative path
                        arcname = file_path.relative_to(code_path)
                        zipf.write(file_path, arcname)
            
            return temp_zip.name
        
        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_zip.name):
                os.unlink(temp_zip.name)
            raise e


# Convenience functions for synchronous usage
def submit_agent_sync(
    agent: Agent,
    code_directory: str,
    base_url: str = "http://localhost:8000",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous wrapper for submitting an agent."""
    import asyncio
    
    async def _submit():
        async with AgentHiringClient(base_url) as client:
            return await client.submit_agent(agent, code_directory, api_key)
    
    return asyncio.run(_submit())


def list_agents_sync(
    base_url: str = "http://localhost:8000",
    skip: int = 0,
    limit: int = 100,
    query: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous wrapper for listing agents."""
    import asyncio
    
    async def _list():
        async with AgentHiringClient(base_url) as client:
            return await client.list_agents(skip, limit, query, category)
    
    return asyncio.run(_list()) 