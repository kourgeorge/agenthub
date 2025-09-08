"""
LLM resource implementations for OpenAI and Anthropic.
"""

from abc import abstractmethod
from typing import Dict, Any, Optional
from .base import BaseResource


class LLMResource(BaseResource):
    """Base class for LLM resources"""
    
    def get_resource_type(self) -> str:
        return "llm"
    
    async def initialize(self, user_id: int) -> None:
        """Initialize LLM client with API key"""
        api_key = await self.key_manager.get_key(user_id, self.provider)
        self.client = await self._create_client(api_key)
    
    @abstractmethod
    async def _create_client(self, api_key: str):
        """Create the specific LLM client"""
        pass
    
    async def execute(self, 
                     execution_id: int,
                     operation_type: str,
                     **kwargs) -> Dict[str, Any]:
        """Execute LLM operation with usage tracking"""
        return await self._execute_with_tracking(execution_id, operation_type, **kwargs)


class OpenAIResource(LLMResource):
    """OpenAI LLM resource implementation"""
    
    async def _create_client(self, api_key: str):
        try:
            from openai import AsyncOpenAI
            return AsyncOpenAI(api_key=api_key)
        except ImportError:
            raise Exception("OpenAI library not installed. Install with: pip install openai")
    
    async def _execute_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        if operation_type == "completion":
            response = await self.client.chat.completions.create(
                model=kwargs['model'],
                messages=kwargs['messages'],
                max_tokens=kwargs.get('max_tokens'),
                temperature=kwargs.get('temperature', 0)
            )
            return {
                "content": response.choices[0].message.content,
                "usage": response.usage.model_dump(),
                "model": response.model
            }
        elif operation_type == "embedding":
            response = await self.client.embeddings.create(
                model=kwargs['model'],
                input=kwargs['input']
            )
            return {
                "embeddings": response.data[0].embedding,
                "usage": response.usage.model_dump(),
                "model": response.model
            }
        else:
            raise ValueError(f"Unsupported operation type: {operation_type}")
    
    def calculate_cost(self, operation_type: str, **kwargs) -> float:
        """Calculate OpenAI API cost"""
        rates = self.config.get('rates', {})
        
        if operation_type == "completion":
            model = kwargs.get('model', 'gpt-3.5-turbo')
            usage = kwargs.get('response', {}).get('usage', {})
            
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
            input_rate = rates.get(model, {}).get('input', 0.0015) / 1000
            output_rate = rates.get(model, {}).get('output', 0.002) / 1000
            
            return (input_tokens * input_rate) + (output_tokens * output_rate)
            
        elif operation_type == "embedding":
            model = kwargs.get('model', 'text-embedding-ada-002')
            usage = kwargs.get('response', {}).get('usage', {})
            total_tokens = usage.get('total_tokens', 0)
            
            rate = rates.get(model, {}).get('input', 0.0001) / 1000
            return total_tokens * rate
        
        return 0.0
    
    def extract_usage_metrics(self, response: Dict[str, Any], request_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage metrics from OpenAI response"""
        usage = response.get('usage', {})
        return {
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        }


class AnthropicResource(LLMResource):
    """Anthropic LLM resource implementation"""
    
    async def _create_client(self, api_key: str):
        try:
            import anthropic
            return anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise Exception("Anthropic library not installed. Install with: pip install anthropic")
    
    async def _execute_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        if operation_type == "completion":
            response = await self.client.messages.create(
                model=kwargs['model'],
                messages=kwargs['messages'],
                max_tokens=kwargs.get('max_tokens'),
                temperature=kwargs.get('temperature', 0)
            )
            return {
                "content": response.content[0].text,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                "model": response.model
            }
        else:
            raise ValueError(f"Unsupported operation type: {operation_type}")
    
    def calculate_cost(self, operation_type: str, **kwargs) -> float:
        """Calculate Anthropic API cost"""
        rates = self.config.get('rates', {})
        
        if operation_type == "completion":
            model = kwargs.get('model', 'claude-3-sonnet')
            usage = kwargs.get('response', {}).get('usage', {})
            
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            input_rate = rates.get(model, {}).get('input', 0.015) / 1000
            output_rate = rates.get(model, {}).get('output', 0.075) / 1000
            
            return (input_tokens * input_rate) + (output_tokens * output_rate)
        
        return 0.0
    
    def extract_usage_metrics(self, response: Dict[str, Any], request_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage metrics from Anthropic response"""
        usage = response.get('usage', {})
        return {
            'input_tokens': usage.get('input_tokens', 0),
            'output_tokens': usage.get('output_tokens', 0),
            'total_tokens': usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
        }


class LiteLLMResource(LLMResource):
    """LiteLLM resource implementation for unified LLM access"""
    
    async def _create_client(self, api_key: str):
        try:
            import litellm
            import os
            
            # Configure LiteLLM to use proxy
            litellm.use_litellm_proxy = True
            
            # Get base URL from environment
            base_url = os.getenv("LITELLM_BASE_URL", "http://theagenthub.cloud:4000")
            
            # Store configuration for later use
            self.base_url = base_url
            self.api_key = api_key
            
            return litellm
        except ImportError:
            raise Exception("LiteLLM library not installed. Install with: pip install litellm")
    
    async def _execute_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        if operation_type == "completion":
            try:
                response = await self.client.acompletion(
                    api_key=self.api_key,
                    model=kwargs['model'],
                    messages=kwargs['messages'],
                    max_tokens=kwargs.get('max_tokens'),
                    temperature=kwargs.get('temperature', 0),
                    base_url=self.base_url
                )
                
                # Extract cost information if available
                cost = 0.0
                if hasattr(response, '_hidden_params') and 'response_cost' in response._hidden_params:
                    cost = response._hidden_params['response_cost']
                
                return {
                    "content": response.choices[0].message.content,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0
                    },
                    "model": response.model,
                    "cost": cost
                }
            except Exception as e:
                raise Exception(f"LiteLLM completion failed: {str(e)}")
                
        elif operation_type == "embedding":
            try:
                response = await self.client.aembedding(
                    api_key=self.api_key,
                    model=kwargs['model'],
                    input=kwargs['input'],
                    base_url=self.base_url
                )
                
                return {
                    "embeddings": response.data[0].embedding,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0
                    },
                    "model": response.model
                }
            except Exception as e:
                raise Exception(f"LiteLLM embedding failed: {str(e)}")
        else:
            raise ValueError(f"Unsupported operation type: {operation_type}")
    
    def calculate_cost(self, operation_type: str, **kwargs) -> float:
        """Calculate LiteLLM API cost - use actual cost from response if available"""
        response = kwargs.get('response', {})
        
        # If we have actual cost from LiteLLM response, use it
        if 'cost' in response and response['cost'] > 0:
            return response['cost']
        
        # Fallback to estimated cost based on usage
        usage = response.get('usage', {})
        
        if operation_type == "completion":
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
            # Use conservative estimates for unknown models
            input_rate = 0.0015 / 1000  # $0.0015 per 1K tokens
            output_rate = 0.002 / 1000  # $0.002 per 1K tokens
            
            return (input_tokens * input_rate) + (output_tokens * output_rate)
            
        elif operation_type == "embedding":
            total_tokens = usage.get('total_tokens', 0)
            rate = 0.0001 / 1000  # $0.0001 per 1K tokens
            return total_tokens * rate
        
        return 0.0
    
    def extract_usage_metrics(self, response: Dict[str, Any], request_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage metrics from LiteLLM response"""
        usage = response.get('usage', {})
        return {
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        } 