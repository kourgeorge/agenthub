"""
Resource Manager - Orchestrates external resources and execution tracking.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from .resources.base import BaseResource, KeyManager, UsageTracker
from .resources.llm import OpenAIResource, AnthropicResource, LiteLLMResource
from .resources.vector_db import PineconeResource, ChromaResource
from .resources.web_search import SerperResource, SerpapiResource, DuckDuckGoResource


class ResourceManager:
    """Manages all external resources for agent executions"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.key_manager = KeyManager(db_session)
        self.usage_tracker = UsageTracker(db_session)
        self.resources: Dict[str, BaseResource] = {}
        self.execution_id: Optional[int] = None
        self.user_id: Optional[int] = None
        
        # Resource configurations
        self.resource_configs = {
            'openai': {
                'rates': {
                    'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
                    'gpt-4': {'input': 0.03, 'output': 0.06},
                    'text-embedding-ada-002': {'input': 0.0001}
                },
                'rate_limits': {'requests_per_minute': 60}
            },
            'anthropic': {
                'rates': {
                    'claude-3-sonnet': {'input': 0.015, 'output': 0.075},
                    'claude-3-haiku': {'input': 0.00025, 'output': 0.00125}
                },
                'rate_limits': {'requests_per_minute': 50}
            },
            'litellm': {
                'rates': {
                    # Dynamic rates based on actual model costs from LiteLLM
                    'default': {'input': 0.0015, 'output': 0.002}
                },
                'rate_limits': {'requests_per_minute': 100}
            },
            'pinecone': {
                'rates': {'upsert': 0.0001, 'query': 0.0, 'delete': 0.0},
                'rate_limits': {'requests_per_minute': 100}
            },
            'serper': {
                'rates': {'search': 0.001},
                'rate_limits': {'requests_per_minute': 100}
            },
            'serpapi': {
                'rates': {'search': 0.005},
                'rate_limits': {'requests_per_minute': 50}
            }
        }
    
    async def start_execution(self, execution_id: str, user_id: int) -> None:
        """Start tracking a new execution"""
        import logging
        logger = logging.getLogger(__name__)
        self.execution_id = execution_id
        self.user_id = user_id
        self.resources = {}  # Reset resources for new execution
        
        # Note: Execution record is already created by ExecutionService
        # We don't need to create it again here

        # Verify the execution exists in the database
        try:
            from ..models.execution import Execution
            execution = self.db.query(Execution).filter(
                Execution.execution_id == execution_id
            ).first()

        except Exception as e:
            logger.error(f"RESOURCE MANAGER: Error checking execution record: {e}")
    
    async def end_execution(self, execution_id: str, status: str = "completed") -> Dict[str, Any]:
        """End execution and return usage summary"""
        import logging
        logger = logging.getLogger(__name__)
        
        # We only track resources and provide usage summaries

        # Get usage summary
        logger.info(f"📊 RESOURCE MANAGER: Getting usage summary: {execution_id}")
        summary = await self.usage_tracker.get_execution_usage_summary(execution_id)
        
        # Reset state
        self.execution_id = None
        self.user_id = None
        self.resources = {}
        
        return summary
    
    async def get_llm(self, provider: str, model: str = None) -> BaseResource:
        """Get LLM resource"""
        # If no active execution, create a temporary one for direct API calls
        if self.user_id is None:
            self.user_id = 0  # Use default user for direct API calls
            self.execution_id = "temp_direct_api"
            # Create execution record for tracking (only for direct API calls)
            await self._create_execution_record(self.execution_id, self.user_id)
            
        resource_key = f"llm:{provider}"
        
        if resource_key not in self.resources:
            config = self.resource_configs.get(provider, {})
            
            if provider == "openai":
                resource = OpenAIResource(provider, config, self.key_manager, self.usage_tracker)
            elif provider == "anthropic":
                resource = AnthropicResource(provider, config, self.key_manager, self.usage_tracker)
            elif provider == "litellm":
                resource = LiteLLMResource(provider, config, self.key_manager, self.usage_tracker)
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
            
            await resource.initialize(self.user_id)
            self.resources[resource_key] = resource
        
        return self.resources[resource_key]
    
    async def get_vector_db(self, provider: str) -> BaseResource:
        """Get vector database resource"""
        # If no active execution, create a temporary one for direct API calls
        if self.user_id is None:
            self.user_id = 0  # Use default user for direct API calls
            self.execution_id = "temp_direct_api"
            # Create execution record for tracking
            await self._create_execution_record(self.execution_id, self.user_id)
            
        resource_key = f"vector_db:{provider}"
        
        if resource_key not in self.resources:
            config = self.resource_configs.get(provider, {})
            
            if provider == "pinecone":
                resource = PineconeResource(provider, config, self.key_manager, self.usage_tracker)
            elif provider == "chroma":
                resource = ChromaResource(provider, config, self.key_manager, self.usage_tracker)
            else:
                raise ValueError(f"Unsupported vector DB provider: {provider}")
            
            await resource.initialize(self.user_id)
            self.resources[resource_key] = resource
        
        return self.resources[resource_key]
    
    async def get_web_search(self, provider: str) -> BaseResource:
        """Get web search resource"""
        # If no active execution, create a temporary one for direct API calls
        if self.user_id is None:
            self.user_id = 0  # Use default user for direct API calls
            self.execution_id = "temp_direct_api"
            # Create execution record for tracking
            await self._create_execution_record(self.execution_id, self.user_id)
            
        resource_key = f"web_search:{provider}"
        
        if resource_key not in self.resources:
            config = self.resource_configs.get(provider, {})
            
            if provider == "serper":
                resource = SerperResource(provider, config, self.key_manager, self.usage_tracker)
            elif provider == "serpapi":
                resource = SerpapiResource(provider, config, self.key_manager, self.usage_tracker)
            elif provider == "duckduckgo":
                resource = DuckDuckGoResource(provider, config, self.key_manager, self.usage_tracker)
            else:
                raise ValueError(f"Unsupported web search provider: {provider}")
            
            await resource.initialize(self.user_id)
            self.resources[resource_key] = resource
        
        return self.resources[resource_key]
    
    async def execute_llm_completion(self, 
                                   provider: str,
                                   model: str,
                                   messages: List[Dict[str, str]],
                                   **kwargs) -> Dict[str, Any]:
        """Execute LLM completion with tracking"""
        # If no active execution, create a temporary one for direct API calls
        if self.execution_id is None:
            self.execution_id = "temp_direct_api"
            self.user_id = 0
            
        llm = await self.get_llm(provider, model)
        return await llm.execute(
            execution_id=self.execution_id,
            operation_type="completion",
            model=model,
            messages=messages,
            **kwargs
        )
    
    async def execute_llm_embedding(self,
                                  provider: str,
                                  model: str,
                                  input_text: str) -> Dict[str, Any]:
        """Execute LLM embedding with tracking"""
        # If no active execution, create a temporary one for direct API calls
        if self.execution_id is None:
            self.execution_id = "temp_direct_api"
            self.user_id = 0
            
        llm = await self.get_llm(provider, model)
        return await llm.execute(
            execution_id=self.execution_id,
            operation_type="embedding",
            model=model,
            input=input_text
        )
    
    async def execute_vector_search(self,
                                  provider: str,
                                  query_vector: List[float],
                                  **kwargs) -> Dict[str, Any]:
        """Execute vector database search with tracking"""
        # If no active execution, create a temporary one for direct API calls
        if self.execution_id is None:
            self.execution_id = "temp_direct_api"
            self.user_id = 0
            
        vector_db = await self.get_vector_db(provider)
        return await vector_db.execute(
            execution_id=self.execution_id,
            operation_type="query",
            query_vector=query_vector,
            **kwargs
        )
    
    async def execute_web_search(self,
                               provider: str,
                               query: str,
                               **kwargs) -> Dict[str, Any]:
        """Execute web search with tracking"""
        # If no active execution, create a temporary one for direct API calls
        if self.execution_id is None:
            self.execution_id = "temp_direct_api"
            self.user_id = 0
            
        web_search = await self.get_web_search(provider)
        return await web_search.execute(
            execution_id=self.execution_id,
            operation_type="search",
            query=query,
            **kwargs
        )
    
    async def _create_execution_record(self, execution_id: int, user_id: int) -> None:
        """Create execution record in database"""
        try:
            from ..models.execution import Execution, ExecutionStatus
            from ..models.agent import Agent
            
            # Check if execution already exists
            existing_execution = self.db.query(Execution).filter(
                Execution.execution_id == str(execution_id)
            ).first()
            
            if existing_execution:
                return
            
            # Get a default agent for temporary executions
            agent = self.db.query(Agent).first()
            if not agent:
                return
            
            # Create execution record
            execution = Execution(
                agent_id=agent.id,
                hiring_id=None,  # No hiring for direct API calls
                user_id=user_id,
                status=ExecutionStatus.RUNNING.value,
                execution_id=str(execution_id),
                input_data={"source": "direct_api_call"}
            )
            
            self.db.add(execution)
            self.db.commit()
            
        except Exception as e:
            # Rollback on error to prevent session issues
            self.db.rollback()

    def get_proxy(self, execution_id: str = None) -> 'AgentResourceProxy':
        """Get an AgentResourceProxy for this resource manager"""
        if execution_id:
            # Set execution ID if provided
            self.execution_id = execution_id
        return AgentResourceProxy(self)


class AgentResourceProxy:
    """Proxy class that agents use to access external resources"""
    
    def __init__(self, resource_manager: ResourceManager):
        self.rm = resource_manager
    
    async def llm_complete(self, 
                          provider: str = "openai",
                          model: str = "gpt-3.5-turbo",
                          messages: Optional[List[Dict[str, str]]] = None,
                          **kwargs) -> str:
        """Complete text using LLM"""
        if messages is None:
            messages = []
        
        response = await self.rm.execute_llm_completion(
            provider=provider,
            model=model,
            messages=messages,
            **kwargs
        )
        
        return response.get("content", "")
    
    async def llm_embed(self,
                       text: str,
                       provider: str = "openai",
                       model: str = "text-embedding-ada-002") -> List[float]:
        """Generate embeddings using LLM"""
        response = await self.rm.execute_llm_embedding(
            provider=provider,
            model=model,
            input_text=text
        )
        
        return response.get("embeddings", [])
    
    async def vector_search(self,
                           query_vector: List[float],
                           provider: str = "pinecone",
                           **kwargs) -> List[Dict[str, Any]]:
        """Search vector database"""
        response = await self.rm.execute_vector_search(
            provider=provider,
            query_vector=query_vector,
            **kwargs
        )
        
        return response.get("matches", [])
    
    async def web_search(self,
                        query: str,
                        provider: str = "serper",
                        **kwargs) -> List[Dict[str, Any]]:
        """Search the web"""
        response = await self.rm.execute_web_search(
            provider=provider,
            query=query,
            **kwargs
        )
        
        return response.get("results", []) 