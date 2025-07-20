"""
Web search resource implementations.
"""

from abc import abstractmethod
from typing import Dict, Any, List, Optional
import aiohttp
from .base import BaseResource


class WebSearchResource(BaseResource):
    """Base class for web search resources"""
    
    def get_resource_type(self) -> str:
        return "web_search"
    
    async def initialize(self, user_id: int) -> None:
        """Initialize web search client with API key"""
        api_key = await self.key_manager.get_key(user_id, self.provider)
        self.client = await self._create_client(api_key)
    
    @abstractmethod
    async def _create_client(self, api_key: str):
        """Create the specific web search client"""
        pass
    
    async def execute(self, 
                     execution_id: int,
                     operation_type: str,
                     **kwargs) -> Dict[str, Any]:
        """Execute web search operation with usage tracking"""
        return await self._execute_with_tracking(execution_id, operation_type, **kwargs)


class SerperResource(WebSearchResource):
    """Serper web search resource implementation"""
    
    async def _create_client(self, api_key: str):
        """Create Serper client (uses aiohttp)"""
        return {
            'api_key': api_key,
            'base_url': 'https://google.serper.dev'
        }
    
    async def _execute_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        if operation_type == "search":
            query = kwargs['query']
            num_results = kwargs.get('num_results', 10)
            
            headers = {
                'X-API-KEY': self.client['api_key'],
                'Content-Type': 'application/json'
            }
            
            payload = {
                'q': query,
                'num': num_results
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.client['base_url']}/search",
                    headers=headers,
                    json=payload
                ) as response:
                    data = await response.json()
                    
                    return {
                        "results": data.get('organic', []),
                        "total_results": len(data.get('organic', [])),
                        "query": query,
                        "operation": "search"
                    }
        else:
            raise ValueError(f"Unsupported operation type: {operation_type}")
    
    def calculate_cost(self, operation_type: str, **kwargs) -> float:
        """Calculate Serper API cost"""
        rates = self.config.get('rates', {})
        
        if operation_type == "search":
            # Serper charges per search
            return rates.get('search', 0.001)  # $0.001 per search
        
        return 0.0
    
    def extract_usage_metrics(self, response: Dict[str, Any], request_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage metrics from Serper response"""
        return {
            'input_tokens': 1,  # One search query
            'output_tokens': response.get('total_results', 0)
        }


class SerpapiResource(WebSearchResource):
    """SerpAPI web search resource implementation"""
    
    async def _create_client(self, api_key: str):
        """Create SerpAPI client"""
        return {
            'api_key': api_key,
            'base_url': 'https://serpapi.com'
        }
    
    async def _execute_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        if operation_type == "search":
            query = kwargs['query']
            num_results = kwargs.get('num_results', 10)
            
            params = {
                'api_key': self.client['api_key'],
                'q': query,
                'num': num_results,
                'engine': 'google'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.client['base_url']}/search",
                    params=params
                ) as response:
                    data = await response.json()
                    
                    return {
                        "results": data.get('organic_results', []),
                        "total_results": len(data.get('organic_results', [])),
                        "query": query,
                        "operation": "search"
                    }
        else:
            raise ValueError(f"Unsupported operation type: {operation_type}")
    
    def calculate_cost(self, operation_type: str, **kwargs) -> float:
        """Calculate SerpAPI cost"""
        rates = self.config.get('rates', {})
        
        if operation_type == "search":
            # SerpAPI charges per search
            return rates.get('search', 0.005)  # $0.005 per search
        
        return 0.0
    
    def extract_usage_metrics(self, response: Dict[str, Any], request_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage metrics from SerpAPI response"""
        return {
            'input_tokens': 1,  # One search query
            'output_tokens': response.get('total_results', 0)
        }


class DuckDuckGoResource(WebSearchResource):
    """DuckDuckGo web search resource implementation (free)"""
    
    async def _create_client(self, api_key: str):
        """DuckDuckGo doesn't require API key"""
        return {
            'base_url': 'https://api.duckduckgo.com'
        }
    
    async def _execute_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        if operation_type == "search":
            query = kwargs['query']
            
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.client['base_url']}/",
                    params=params
                ) as response:
                    data = await response.json()
                    
                    # Transform DuckDuckGo results to standard format
                    results = []
                    if data.get('Abstract'):
                        results.append({
                            'title': data.get('AbstractSource', ''),
                            'snippet': data.get('Abstract', ''),
                            'link': data.get('AbstractURL', '')
                        })
                    
                    for result in data.get('RelatedTopics', []):
                        if isinstance(result, dict) and result.get('Text'):
                            results.append({
                                'title': result.get('FirstURL', ''),
                                'snippet': result.get('Text', ''),
                                'link': result.get('FirstURL', '')
                            })
                    
                    return {
                        "results": results,
                        "total_results": len(results),
                        "query": query,
                        "operation": "search"
                    }
        else:
            raise ValueError(f"Unsupported operation type: {operation_type}")
    
    def calculate_cost(self, operation_type: str, **kwargs) -> float:
        """DuckDuckGo is free"""
        return 0.0
    
    def extract_usage_metrics(self, response: Dict[str, Any], request_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage metrics from DuckDuckGo response"""
        return {
            'input_tokens': 1,  # One search query
            'output_tokens': response.get('total_results', 0)
        } 