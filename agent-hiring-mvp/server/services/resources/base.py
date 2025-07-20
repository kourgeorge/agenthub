"""
Base resource class for external resource management.
All external resources (LLM, Vector DB, Web Search) inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import asyncio
import time
import json
from datetime import datetime


@dataclass
class ResourceUsage:
    """Records a single resource usage"""
    execution_id: int
    resource_type: str
    provider: str
    model: Optional[str]
    operation_type: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost: float = 0.0
    request_metadata: Optional[Dict[str, Any]] = None
    response_metadata: Optional[Dict[str, Any]] = None
    duration_ms: int = 0


class BaseResource(ABC):
    """Base class for all external resources"""
    
    def __init__(self, 
                 provider: str,
                 config: Dict[str, Any],
                 key_manager: 'KeyManager',
                 usage_tracker: 'UsageTracker'):
        self.provider = provider
        self.config = config
        self.key_manager = key_manager
        self.usage_tracker = usage_tracker
        self.rate_limiter = RateLimiter(provider, config.get('rate_limits', {}))
        self.client = None
    
    @abstractmethod
    async def initialize(self, user_id: int) -> None:
        """Initialize the resource (get API keys, setup clients, etc.)"""
        pass
    
    @abstractmethod
    async def execute(self, 
                     execution_id: int,
                     operation_type: str,
                     **kwargs) -> Dict[str, Any]:
        """Execute the resource operation"""
        pass
    
    @abstractmethod
    def calculate_cost(self, 
                      operation_type: str,
                      **kwargs) -> float:
        """Calculate cost for the operation"""
        pass
    
    @abstractmethod
    def extract_usage_metrics(self, 
                            response: Dict[str, Any],
                            request_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage metrics from response"""
        pass
    
    async def _record_usage(self, 
                           execution_id: int,
                           operation_type: str,
                           cost: float,
                           request_metadata: Dict[str, Any],
                           response_metadata: Dict[str, Any],
                           **metrics) -> None:
        """Record resource usage"""
        usage = ResourceUsage(
            execution_id=execution_id,
            resource_type=self.get_resource_type(),
            provider=self.provider,
            model=request_metadata.get('model'),
            operation_type=operation_type,
            cost=cost,
            request_metadata=request_metadata,
            response_metadata=response_metadata,
            **metrics
        )
        
        await self.usage_tracker.record_usage(usage)
    
    @abstractmethod
    def get_resource_type(self) -> str:
        """Return the resource type (llm, vector_db, web_search)"""
        pass
    
    async def _execute_with_tracking(self,
                                   execution_id: int,
                                   operation_type: str,
                                   **kwargs) -> Dict[str, Any]:
        """Execute operation with usage tracking"""
        start_time = time.time()
        
        # Check rate limits
        await self.rate_limiter.check_rate_limit(execution_id)
        
        # Calculate estimated cost
        estimated_cost = self.calculate_cost(operation_type, **kwargs)
        
        # Execute the operation
        try:
            response = await self._execute_operation(operation_type, **kwargs)
            
            # Calculate actual cost and extract metrics
            actual_cost = self.calculate_cost(operation_type, response=response, **kwargs)
            metrics = self.extract_usage_metrics(response, kwargs)
            
            # Record usage
            duration_ms = int((time.time() - start_time) * 1000)
            await self._record_usage(
                execution_id=execution_id,
                operation_type=operation_type,
                cost=actual_cost,
                request_metadata=kwargs,
                response_metadata=response,
                duration_ms=duration_ms,
                **metrics
            )
            
            return response
            
        except Exception as e:
            # Record failed usage
            await self._record_usage(
                execution_id=execution_id,
                operation_type=operation_type,
                cost=0.0,
                request_metadata=kwargs,
                response_metadata={"error": str(e)},
                duration_ms=int((time.time() - start_time) * 1000)
            )
            raise
    
    @abstractmethod
    async def _execute_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        """Execute the specific operation (to be implemented by subclasses)"""
        pass


class RateLimiter:
    """Simple rate limiter for resources"""
    
    def __init__(self, provider: str, rate_limits: Dict[str, Any]):
        self.provider = provider
        self.rate_limits = rate_limits
        self.request_counts = {}  # In production, use Redis
    
    async def check_rate_limit(self, execution_id: int):
        """Check if rate limit is exceeded"""
        # Simple implementation - in production, use Redis with proper rate limiting
        current_time = int(time.time() / 60)  # 1-minute windows
        key = f"{self.provider}:{current_time}"
        
        if key not in self.request_counts:
            self.request_counts[key] = 0
        
        max_requests = self.rate_limits.get('requests_per_minute', 100)
        
        if self.request_counts[key] >= max_requests:
            raise Exception(f"Rate limit exceeded for {self.provider}")
        
        self.request_counts[key] += 1


class KeyManager:
    """Manages API keys for external services"""
    
    def __init__(self, db_session):
        self.db = db_session
        self._api_keys = None
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load API keys from api_keys.txt file"""
        import os
        from pathlib import Path
        
        # Find the api_keys.txt file relative to the server directory
        server_dir = Path(__file__).parent.parent.parent
        api_keys_file = server_dir / "api_keys.txt"
        
        self._api_keys = {}
        
        if api_keys_file.exists():
            with open(api_keys_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line.startswith('#') or not line or '=' not in line:
                        continue
                    
                    # Parse key=value format
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        self._api_keys[key] = value
        
        # Also check environment variables as fallback
        for key in self._api_keys:
            if not self._api_keys[key] or self._api_keys[key].startswith('your-'):
                env_value = os.getenv(key)
                if env_value:
                    self._api_keys[key] = env_value
    
    async def get_key(self, user_id: int, service: str) -> str:
        """Get API key for a service"""
        # Map service names to key names
        key_mapping = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'serper': 'SERPER_API_KEY',
            'serpapi': 'SERPAPI_API_KEY',
            'pinecone': 'PINECONE_API_KEY',
            'google': 'GOOGLE_API_KEY',
            'groq': 'GROQ_API_KEY',
            'together': 'TOGETHER_API_KEY',
            'perplexity': 'PERPLEXITY_API_KEY',
            'replicate': 'REPLICATE_API_TOKEN',
            'elevenlabs': 'ELEVENLABS_API_KEY',
            'assemblyai': 'ASSEMBLYAI_API_KEY',
            'weaviate': 'WEAVIATE_API_KEY',
            'qdrant': 'QDRANT_API_KEY',
            'huggingface': 'HUGGINGFACE_API_KEY',
            'cohere': 'COHERE_API_KEY'
        }
        
        key_name = key_mapping.get(service.lower(), f"{service.upper()}_API_KEY")
        
        if key_name in self._api_keys and self._api_keys[key_name]:
            key_value = self._api_keys[key_name]
            # Skip placeholder values
            if not key_value.startswith('your-'):
                return key_value
        
        # Try environment as fallback
        import os
        env_key = os.getenv(key_name)
        if env_key:
            return env_key
        
        raise Exception(f"No API key found for service {service} (key: {key_name})")
    
    async def store_key(self, user_id: int, service: str, key: str):
        """Store API key for a service"""
        # In production, implement proper key encryption and database storage
        # For now, just update the in-memory cache
        key_name = f"{service.upper()}_API_KEY"
        self._api_keys[key_name] = key


class UsageTracker:
    """Tracks resource usage for executions"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def record_usage(self, usage: ResourceUsage):
        """Record a resource usage"""
        try:
            # Import the model here to avoid circular imports
            from server.models.resource_usage import ExecutionResourceUsage
            from server.models.execution import Execution
            
            # Convert string execution_id to integer id
            execution_id_int = None
            if isinstance(usage.execution_id, str):
                # Look up the execution by execution_id string to get the integer id
                execution = self.db.query(Execution).filter(
                    Execution.execution_id == usage.execution_id
                ).first()
                if execution:
                    execution_id_int = execution.id
                else:
                    print(f"Warning: Execution with execution_id '{usage.execution_id}' not found in database")
                    return
            else:
                execution_id_int = usage.execution_id
            
            # Create database record
            db_usage = ExecutionResourceUsage(
                execution_id=execution_id_int,
                resource_type=usage.resource_type,
                resource_provider=usage.provider,
                resource_model=usage.model,
                operation_type=usage.operation_type,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                cost=usage.cost,
                request_metadata=usage.request_metadata,
                response_metadata=usage.response_metadata,
                duration_ms=usage.duration_ms
            )
            
            self.db.add(db_usage)
            self.db.commit()
            
            # Also log for debugging
            print(f"Resource Usage: {usage.resource_type}:{usage.provider} - Cost: ${usage.cost:.6f} - Execution ID: {usage.execution_id} -> {execution_id_int}")
            
        except Exception as e:
            print(f"Error recording usage: {e}")
            # Don't fail the operation if usage tracking fails
            pass
    
    async def get_execution_usage_summary(self, execution_id: int) -> Dict[str, Any]:
        """Get usage summary for an execution"""
        try:
            from server.models.resource_usage import ExecutionResourceUsage
            from server.models.execution import Execution
            
            # Convert string execution_id to integer id if needed
            execution_id_int = None
            if isinstance(execution_id, str):
                # Look up the execution by execution_id string to get the integer id
                execution = self.db.query(Execution).filter(
                    Execution.execution_id == execution_id
                ).first()
                if execution:
                    execution_id_int = execution.id
                else:
                    print(f"Warning: Execution with execution_id '{execution_id}' not found in database")
                    return {
                        "execution_id": execution_id,
                        "total_cost": 0.0,
                        "resource_breakdown": {},
                        "total_operations": 0
                    }
            else:
                execution_id_int = execution_id
            
            # Get all usage records for this execution
            usage_records = self.db.query(ExecutionResourceUsage).filter(
                ExecutionResourceUsage.execution_id == execution_id_int
            ).all()
            
            total_cost = sum(record.cost for record in usage_records)
            resource_breakdown = {}
            
            for record in usage_records:
                key = f"{record.resource_type}:{record.resource_provider}"
                if key not in resource_breakdown:
                    resource_breakdown[key] = {
                        "total_cost": 0.0,
                        "operations": 0,
                        "total_tokens": 0
                    }
                
                resource_breakdown[key]["total_cost"] += record.cost
                resource_breakdown[key]["operations"] += 1
                resource_breakdown[key]["total_tokens"] += (record.total_tokens or 0)
            
            return {
                "execution_id": execution_id,
                "total_cost": total_cost,
                "resource_breakdown": resource_breakdown,
                "total_operations": len(usage_records)
            }
            
        except Exception as e:
            print(f"Error getting usage summary: {e}")
            return {
                "execution_id": execution_id,
                "total_cost": 0.0,
                "resource_breakdown": {},
                "total_operations": 0
            } 