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