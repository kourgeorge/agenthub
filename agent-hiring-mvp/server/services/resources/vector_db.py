"""
Vector database resource implementations.
"""

from abc import abstractmethod
from typing import Dict, Any, List, Optional
from .base import BaseResource


class VectorDBResource(BaseResource):
    """Base class for vector database resources"""
    
    def get_resource_type(self) -> str:
        return "vector_db"
    
    async def initialize(self, user_id: int) -> None:
        """Initialize vector database client with API key"""
        api_key = await self.key_manager.get_key(user_id, self.provider)
        self.client = await self._create_client(api_key)
    
    @abstractmethod
    async def _create_client(self, api_key: str):
        """Create the specific vector database client"""
        pass
    
    async def execute(self, 
                     execution_id: int,
                     operation_type: str,
                     **kwargs) -> Dict[str, Any]:
        """Execute vector database operation with usage tracking"""
        return await self._execute_with_tracking(execution_id, operation_type, **kwargs)


class PineconeResource(VectorDBResource):
    """Pinecone vector database resource implementation"""
    
    async def _create_client(self, api_key: str):
        try:
            import pinecone
            pinecone.init(api_key=api_key, environment=self.config.get('environment'))
            return pinecone
        except ImportError:
            raise Exception("Pinecone library not installed. Install with: pip install pinecone-client")
    
    async def _execute_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        index_name = kwargs.get('index_name', self.config.get('default_index'))
        index = self.client.Index(index_name)
        
        if operation_type == "upsert":
            vectors = kwargs['vectors']
            response = index.upsert(vectors=vectors)
            return {
                "upserted_count": response.get('upserted_count', 0),
                "operation": "upsert"
            }
            
        elif operation_type == "query":
            query_vector = kwargs['query_vector']
            top_k = kwargs.get('top_k', 10)
            response = index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=kwargs.get('include_metadata', True)
            )
            return {
                "matches": response.get('matches', []),
                "operation": "query",
                "top_k": top_k
            }
            
        elif operation_type == "delete":
            ids = kwargs['ids']
            response = index.delete(ids=ids)
            return {
                "deleted_count": len(ids),
                "operation": "delete"
            }
            
        else:
            raise ValueError(f"Unsupported operation type: {operation_type}")
    
    def calculate_cost(self, operation_type: str, **kwargs) -> float:
        """Calculate Pinecone API cost"""
        rates = self.config.get('rates', {})
        
        if operation_type == "upsert":
            vectors = kwargs.get('vectors', [])
            vector_count = len(vectors)
            rate = rates.get('upsert', 0.0001)  # $0.0001 per vector
            return vector_count * rate
            
        elif operation_type == "query":
            # Pinecone queries are typically free or very low cost
            return rates.get('query', 0.0)
            
        elif operation_type == "delete":
            # Deletes are typically free
            return rates.get('delete', 0.0)
        
        return 0.0
    
    def extract_usage_metrics(self, response: Dict[str, Any], request_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage metrics from Pinecone response"""
        operation = response.get('operation', '')
        
        if operation == "upsert":
            return {
                'vectors_processed': response.get('upserted_count', 0)
            }
        elif operation == "query":
            return {
                'queries_processed': 1,
                'results_returned': len(response.get('matches', []))
            }
        elif operation == "delete":
            return {
                'vectors_deleted': response.get('deleted_count', 0)
            }
        
        return {}


class ChromaResource(VectorDBResource):
    """Chroma vector database resource implementation (local)"""
    
    async def _create_client(self, api_key: str):
        try:
            import chromadb
            # Chroma is typically local, so api_key might be ignored
            return chromadb.Client()
        except ImportError:
            raise Exception("Chroma library not installed. Install with: pip install chromadb")
    
    async def _execute_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        collection_name = kwargs.get('collection_name', 'default')
        collection = self.client.get_or_create_collection(name=collection_name)
        
        if operation_type == "upsert":
            documents = kwargs['documents']
            metadatas = kwargs.get('metadatas', [])
            ids = kwargs.get('ids', [])
            
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            return {
                "upserted_count": len(documents),
                "operation": "upsert"
            }
            
        elif operation_type == "query":
            query_texts = kwargs['query_texts']
            n_results = kwargs.get('n_results', 10)
            
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results
            )
            return {
                "results": results,
                "operation": "query",
                "n_results": n_results
            }
            
        else:
            raise ValueError(f"Unsupported operation type: {operation_type}")
    
    def calculate_cost(self, operation_type: str, **kwargs) -> float:
        """Chroma is local, so costs are minimal"""
        return 0.0
    
    def extract_usage_metrics(self, response: Dict[str, Any], request_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage metrics from Chroma response"""
        operation = response.get('operation', '')
        
        if operation == "upsert":
            return {
                'documents_processed': response.get('upserted_count', 0)
            }
        elif operation == "query":
            return {
                'queries_processed': 1,
                'results_returned': response.get('n_results', 0)
            }
        
        return {} 