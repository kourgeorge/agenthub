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
            
            # Add agent type and ACP manifest
            if config.agent_type:
                form_data.add_field("agent_type", config.agent_type)
            
            if config.acp_manifest:
                form_data.add_field("acp_manifest", json.dumps(config.acp_manifest))
            
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

    async def approve_agent(self, agent_id: int) -> Dict[str, Any]:
        """Approve an agent (admin only)."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.put(
            f"{self.api_base}/agents/{agent_id}/approve",
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to approve agent: {error_text}")

    async def reject_agent(self, agent_id: int, reason: str) -> Dict[str, Any]:
        """Reject an agent (admin only)."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        data = {"reason": reason}
        async with self.session.put(
            f"{self.api_base}/agents/{agent_id}/reject",
            json=data,
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to reject agent: {error_text}")
    
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
                # Return the full response with agent type and deployment info
                return {
                    "hiring_id": result.get("hiring_id") or result.get("id"),
                    "agent_id": result.get("agent_id"),
                    "agent_name": result.get("agent_name"),
                    "agent_type": result.get("agent_type", "unknown"),
                    "status": result.get("status"),
                    "billing_cycle": result.get("billing_cycle") or billing_cycle or "per_use",
                    "message": result.get("message", "Agent hired successfully"),
                    "deployment_status": result.get("deployment_status")
                }
            else:
                error_text = await response.text()
                raise Exception(f"Failed to hire agent: {error_text}")
    
    async def list_hired_agents(self, user_id: Optional[int] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """List hired agents."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        # Default user_id to 1 for testing purposes
        if user_id is None:
            user_id = 1
        
        # Build query parameters
        params = {}
        if status and status != "all":
            params["status"] = status
        
        async with self.session.get(
            f"{self.api_base}/hiring/user/{user_id}",
            params=params,
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

    async def get_hiring_details(self, hiring_id: int) -> Dict[str, Any]:
        """Get hiring information."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.api_base}/hiring/{hiring_id}",
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get hiring details: {error_text}")
    
    async def cancel_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        """Cancel a hiring."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        data = {}
        if notes:
            data["notes"] = notes
        
        async with self.session.put(
            f"{self.api_base}/hiring/{hiring_id}/cancel",
            json=data,
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to cancel hiring: {error_text}")

    async def suspend_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        """Suspend a hiring."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        data = {}
        if notes:
            data["notes"] = notes
        
        async with self.session.put(
            f"{self.api_base}/hiring/{hiring_id}/suspend",
            json=data,
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to suspend hiring: {error_text}")

    async def activate_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        """Activate a hiring."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        data = {}
        if notes:
            data["notes"] = notes
        
        async with self.session.put(
            f"{self.api_base}/hiring/{hiring_id}/activate",
            json=data,
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to activate hiring: {error_text}")
    
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
    
    async def execute_hired_agent(
        self,
        hiring_id: int,
        input_data: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a hired agent."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        data = {
            "hiring_id": hiring_id,
            "input_data": input_data,
        }
        
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

    async def run_hired_agent(
        self,
        hiring_id: int,
        input_data: Dict[str, Any],
        user_id: Optional[int] = None,
        wait_for_completion: bool = True,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Run a hired agent and optionally wait for completion."""
        # Create and trigger execution
        execution_result = await self.execute_hired_agent(
            hiring_id=hiring_id,
            input_data=input_data,
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
    # DEPLOYMENT MANAGEMENT (ACP Server Agents)
    # =============================================================================
    
    async def create_deployment(self, hiring_id: int) -> Dict[str, Any]:
        """Create a deployment for a hired ACP agent."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.post(
            f"{self.api_base}/deployment/create/{hiring_id}",
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to create deployment: {error_text}")

    # REMOVED: deploy_agent method - deployments must be created through proper hiring workflow
    # Use: create_deployment(hiring_id) after hiring an agent
    
    async def stop_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Stop a deployed ACP server agent."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.post(
            f"{self.api_base}/deployment/stop/{deployment_id}",
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to stop deployment: {error_text}")
    
    async def restart_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Restart a stopped deployment."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.post(
            f"{self.api_base}/deployment/restart/{deployment_id}",
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to restart deployment: {error_text}")
    
    async def get_deployment_status(self, agent_id: int) -> Dict[str, Any]:
        """Get deployment status for an agent."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.api_base}/deployment/status/{agent_id}",
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get deployment status: {error_text}")
    
    async def get_deployment_status_by_id(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status by deployment ID."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.api_base}/deployment/status/{deployment_id}",
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get deployment status: {error_text}")
    
    async def list_deployments(self, agent_id: Optional[int] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """List deployments with optional filtering."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        # Build query parameters
        params = {}
        if agent_id:
            params["agent_id"] = agent_id
        if status and status != "all":
            params["deployment_status"] = status
        
        async with self.session.get(
            f"{self.api_base}/deployment/list",
            params=params,
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to list deployments: {error_text}")
    
    async def get_deployment_logs(self, agent_id: int, tail: int = 50) -> Dict[str, Any]:
        """Get logs for a deployed agent."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.api_base}/deployment/logs/{agent_id}",
            params={"tail": tail},
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get deployment logs: {error_text}")

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


def approve_agent_sync(
    agent_id: int,
    base_url: str = "http://localhost:8002",
) -> Dict[str, Any]:
    """Approve an agent synchronously."""
    async def _approve():
        async with AgentHubClient(base_url) as client:
            return await client.approve_agent(agent_id)
    
    return asyncio.run(_approve())


def reject_agent_sync(
    agent_id: int,
    reason: str,
    base_url: str = "http://localhost:8002",
) -> Dict[str, Any]:
    """Reject an agent synchronously."""
    async def _reject():
        async with AgentHubClient(base_url) as client:
            return await client.reject_agent(agent_id, reason)
    
    return asyncio.run(_reject())


def create_deployment_sync(
    hiring_id: int,
    base_url: str = "http://localhost:8002",
) -> Dict[str, Any]:
    """Create a deployment synchronously."""
    async def _create():
        async with AgentHubClient(base_url) as client:
            return await client.create_deployment(hiring_id)
    
    return asyncio.run(_create())