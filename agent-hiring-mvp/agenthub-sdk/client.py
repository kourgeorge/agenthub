"""
AgentHub Client - Complete client for agent creation and hiring.
Provides tools for both agent creators and users.
"""

import json
import logging
import zipfile
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio

try:
    import aiohttp
    import aiofiles
except ImportError:
    raise ImportError(
        "aiohttp and aiofiles are required. Install with: pip install aiohttp aiofiles"
    )

from .agent import Agent, AgentConfig

logger = logging.getLogger(__name__)


class AgentHubClient:
    """Complete client for AgentHub platform interactions."""
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v1"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    # =============================================================================
    # AGENT CREATION AND SUBMISSION
    # =============================================================================
    
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
        config = agent.get_config()
        errors = config.validate()
        if errors:
            raise ValueError(f"Agent validation failed: {errors}")
        
        # Create code ZIP file
        zip_path = await self._create_code_zip(code_directory)
        
        try:
            # Prepare form data
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
                f"{self.api_base}/agents/submit",
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
    
    # =============================================================================
    # AGENT DISCOVERY
    # =============================================================================
    
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
            f"{self.api_base}/agents",
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
            f"{self.api_base}/agents/{agent_id}",
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get agent: {error_text}")
    
    # =============================================================================
    # AGENT HIRING
    # =============================================================================
    
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
        
        # Default user_id to 1 for testing purposes
        if user_id is None:
            user_id = 1
        
        data = {
            "agent_id": int(agent_id),
            "user_id": int(user_id),
            "requirements": config or {},
            "budget": 100.0,  # Default budget
            "duration_hours": 24,  # Default duration
        }
        
        async with self.session.post(
            f"{self.api_base}/hiring/",
            json=data,
        ) as response:
            if response.status == 200:
                result = await response.json()
                # Convert to format expected by CLI
                return {
                    "hiring_id": result.get("id"),
                    "status": result.get("status"),
                    "billing_cycle": billing_cycle or "per_use",
                    "message": result.get("message", "Agent hired successfully")
                }
            else:
                error_text = await response.text()
                raise Exception(f"Failed to hire agent: {error_text}")
    
    async def list_hired_agents(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """List hired agents."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        # Default user_id to 1 for testing purposes
        if user_id is None:
            user_id = 1
        
        async with self.session.get(
            f"{self.api_base}/hiring/user/{user_id}",
        ) as response:
            if response.status == 200:
                hired_agents = await response.json()
                # Convert to format expected by CLI
                return {
                    "hired_agents": [
                        {
                            "id": hiring.get("id"),
                            "agent": {
                                "id": hiring.get("agent_id"),
                                "name": f"Agent {hiring.get('agent_id')}",
                                "category": "general"
                            },
                            "status": hiring.get("status"),
                            "hired_at": hiring.get("hired_at"),
                            "billing_cycle": "per_use"
                        }
                        for hiring in (hired_agents if isinstance(hired_agents, list) else [])
                    ]
                }
            else:
                error_text = await response.text()
                raise Exception(f"Failed to list hired agents: {error_text}")
    
    # =============================================================================
    # AGENT EXECUTION
    # =============================================================================
    
    async def execute_agent(
        self,
        agent_id: int,
        input_data: Dict[str, Any],
        hiring_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute an agent."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        data = {
            "agent_id": agent_id,
            "input_data": input_data,
        }
        
        if hiring_id:
            data["hiring_id"] = hiring_id
        if user_id:
            data["user_id"] = user_id
        
        # Step 1: Create execution
        async with self.session.post(
            f"{self.api_base}/execution",
            json=data,
        ) as response:
            if response.status == 200:
                result = await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to create execution: {error_text}")
        
        # Step 2: Trigger execution automatically
        execution_id = result.get("execution_id")
        if not execution_id:
            raise Exception("No execution ID returned")
        
        async with self.session.post(
            f"{self.api_base}/execution/{execution_id}/run",
        ) as response:
            if response.status == 200:
                # Return the execution result for immediate executions
                execution_result = await response.json()
                return {
                    "execution_id": execution_id,
                    "status": "running",
                    "result": execution_result.get("result"),
                    "message": "Execution triggered successfully"
                }
            else:
                error_text = await response.text()
                raise Exception(f"Failed to trigger execution: {error_text}")
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.api_base}/execution/{execution_id}",
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get execution status: {error_text}")
    
    async def run_agent(
        self,
        agent_id: int,
        input_data: Dict[str, Any],
        hiring_id: Optional[int] = None,
        user_id: Optional[int] = None,
        wait_for_completion: bool = True,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Run an agent and optionally wait for completion."""
        # Create and trigger execution
        execution_result = await self.execute_agent(
            agent_id=agent_id,
            input_data=input_data,
            hiring_id=hiring_id,
            user_id=user_id,
        )
        
        execution_id = execution_result.get("execution_id")
        if not execution_id:
            raise Exception("No execution ID returned")
        
        if not wait_for_completion:
            return execution_result
        
        # Wait for completion
        start_time = asyncio.get_event_loop().time()
        while True:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise Exception(f"Execution timeout after {timeout} seconds")
            
            status_result = await self.get_execution_status(execution_id)
            # Check both possible response formats
            status = status_result.get("status")
            if not status:
                # Try nested format
                execution = status_result.get("execution", {})
                status = execution.get("status")
            
            if status in ["completed", "failed"]:
                return status_result
            
            # Wait before checking again
            await asyncio.sleep(1)
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    async def _create_code_zip(self, code_directory: str) -> str:
        """Create a ZIP file from the code directory."""
        code_path = Path(code_directory)
        if not code_path.exists():
            raise ValueError(f"Code directory does not exist: {code_directory}")
        
        # Create temporary ZIP file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in code_path.rglob('*'):
                if file_path.is_file():
                    # Get relative path for ZIP
                    relative_path = file_path.relative_to(code_path)
                    zip_file.write(file_path, relative_path)
        
        return temp_zip.name
    
    async def health_check(self) -> bool:
        """Check if the server is healthy."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except:
            return False


# Synchronous wrapper functions for convenience
def submit_agent_sync(
    agent: Agent,
    code_directory: str,
    base_url: str = "http://localhost:8002",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit an agent synchronously."""
    async def _submit():
        async with AgentHubClient(base_url) as client:
            return await client.submit_agent(agent, code_directory, api_key)
    
    return asyncio.run(_submit())


def list_agents_sync(
    base_url: str = "http://localhost:8002",
    skip: int = 0,
    limit: int = 100,
    query: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """List agents synchronously."""
    async def _list():
        async with AgentHubClient(base_url) as client:
            return await client.list_agents(skip, limit, query, category)
    
    return asyncio.run(_list())


def hire_agent_sync(
    agent_id: int,
    base_url: str = "http://localhost:8002",
    config: Optional[Dict[str, Any]] = None,
    billing_cycle: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Hire an agent synchronously."""
    async def _hire():
        async with AgentHubClient(base_url) as client:
            return await client.hire_agent(agent_id, config, billing_cycle, user_id)
    
    return asyncio.run(_hire())


def run_agent_sync(
    agent_id: int,
    input_data: Dict[str, Any],
    base_url: str = "http://localhost:8002",
    hiring_id: Optional[int] = None,
    user_id: Optional[int] = None,
    wait_for_completion: bool = True,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Run an agent synchronously."""
    async def _run():
        async with AgentHubClient(base_url) as client:
            return await client.run_agent(
                agent_id, input_data, hiring_id, user_id, wait_for_completion, timeout
            )
    
    return asyncio.run(_run()) 