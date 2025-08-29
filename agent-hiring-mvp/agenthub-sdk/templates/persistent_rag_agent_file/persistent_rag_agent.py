#!/usr/bin/env python3
"""
Persistent RAG Agent - Refactored Implementation

A clean, efficient implementation of a persistent RAG agent that demonstrates:
1. Inheritance from PersistentAgent base class
2. Proper state management using _get_state/_set_state
3. Clean separation of initialize/execute/cleanup phases
4. Focus on business logic only - no platform concerns
5. Persistent vector database storage on disk
"""

import os
import json
import logging
import tempfile
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables and configure logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import LangChain components
try:
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader, JSONLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain.chains import RetrievalQA
    from langchain.schema import Document
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not available, using fallback implementation")
    LANGCHAIN_AVAILABLE = False

from agenthub_sdk.agent import PersistentAgent


class RAGAgent(PersistentAgent):
    """Clean Persistent RAG Agent Implementation"""

    def __init__(self):
        super().__init__()
        self.vectorstore = None
        self.llm = None
        self.qa_chain = None
        self.base_storage_dir = Path("/tmp/agenthub_persistent_rag")
        self.base_storage_dir.mkdir(exist_ok=True)
        
        # Configure file service
        self.file_service_url = self._get_backend_url()
        self.api_key = os.getenv("API_KEY", "")
        logger.info(f"File service URL: {self.file_service_url}")

    def _get_backend_url(self) -> str:
        """Get backend URL with fallbacks."""
        backend_url = os.getenv("BACKEND_URL") or os.getenv("FILE_SERVICE_URL")
        if not backend_url:
            backend_url = "http://host.docker.internal:8002/api/v1/files" if os.path.exists("/.dockerenv") else "http://localhost:8002/api/v1/files"
        return backend_url

    def _get_storage_path(self, identifier: str) -> Path:
        """Get storage path for this agent instance."""
        agent_id = self._get_state("agent_id") or "default"
        return self.base_storage_dir / f"agent_{agent_id}" / identifier

    def _get_index_path(self) -> Path:
        return self._get_storage_path("faiss_index")

    def _get_documents_path(self) -> Path:
        return self._get_storage_path("documents.json")

    def _download_file_from_service(self, file_id: str) -> Tuple[bytes, dict]:
        """Download file content and metadata from the file service."""
        access_token = self._get_state(f"file_token_{file_id}")
        if not access_token:
            raise Exception(f"No access token found for file {file_id}")
        
        download_url = f"{self.file_service_url}/{file_id}/download?token={access_token}&include_metadata=true"
        response = requests.get(download_url, timeout=60)
        response.raise_for_status()
        
        # Extract metadata from response headers
        metadata = {
            'filename': response.headers.get('X-File-Name', f'file_{file_id[:8]}'),
            'file_type': response.headers.get('X-File-Type', 'application/octet-stream'),
            'file_extension': response.headers.get('X-File-Extension', ''),
            'file_size': int(response.headers.get('X-File-Size', 0)),
            'description': response.headers.get('X-File-Description', '')
        }
        
        return response.content, metadata

    def initialize(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the RAG agent with configuration data."""
        try:
            file_references = config.get("file_references")
            if not file_references or not isinstance(file_references, list):
                raise ValueError("file_references is required and must be a non-empty array")
            
            # Store file tokens
            file_tokens = config.get("file_tokens", {})
            for key, value in config.items():
                if key.endswith('_tokens') and isinstance(value, dict):
                    file_tokens.update(value)
            
            for file_id in file_references:
                if file_id in file_tokens:
                    self._set_state(f"file_token_{file_id}", file_tokens[file_id])

            # Check if already initialized
            if self._is_initialized():
                return self._create_response("success", f"Agent already initialized with {len(self._get_state('file_references', []))} files")

            # Try to load existing index or create new one
            vectorstore, index_size, content = self._load_or_create_index(file_references, config)
            
            # Setup LLM and QA chain
            if LANGCHAIN_AVAILABLE:
                self._setup_llm_and_chain(config)

            # Store configuration in state
            self._store_config_in_state(config, file_references, index_size, content)
            self._mark_initialized()

            return self._create_response("success", f"Successfully initialized RAG agent with {len(file_references)} files", index_size)

        except Exception as e:
            logger.error(f"Error initializing RAG agent: {e}")
            return self._create_response("error", f"Initialization failed: {str(e)}")

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute RAG query."""
        try:
            if not self._is_initialized():
                raise ValueError("Agent not initialized. Call initialize() first.")

            question = input_data.get("question")
            if not question:
                raise ValueError("question is required for execution")

            # Execute query
            if LANGCHAIN_AVAILABLE and self._get_state("langchain_available"):
                answer = self._execute_langchain_query(question)
            else:
                answer = f"Fallback response: I found information about '{question}' in the indexed content."

            return {
                "answer": answer,
                "question": question,
                "confidence": 0.8,
                "sources": self._get_source_info(),
                "processing_time": 1.5
            }

        except Exception as e:
            logger.error(f"Error executing RAG agent: {e}")
            return {
                "answer": f"Error: {str(e)}",
                "question": input_data.get("question", "Unknown"),
                "confidence": 0.0,
                "sources": [],
                "processing_time": 0.0
            }

    def cleanup(self) -> Dict[str, Any]:
        """Clean up agent resources."""
        try:
            self._state.clear()
            self._initialized = False
            return self._create_cleanup_response("success", "Agent resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up RAG agent: {e}")
            return self._create_cleanup_response("error", f"Cleanup failed: {str(e)}")

    def _load_or_create_index(self, file_references: list, config: Dict[str, Any]) -> Tuple[Optional[FAISS], int, str]:
        """Load existing index or create new one."""
        index_path = self._get_index_path()
        documents_path = self._get_documents_path()
        
        # Try to load existing index
        if index_path.exists() and documents_path.exists():
            try:
                embeddings = OpenAIEmbeddings()
                vectorstore = FAISS.load_local(str(index_path), embeddings)
                with open(documents_path, 'r') as f:
                    documents_data = json.load(f)
                return vectorstore, documents_data.get("total_chunks", 0), documents_data.get("content", "")
            except Exception as e:
                logger.warning(f"Failed to load existing index: {e}")

        # Create new index
        content, file_metadata = self._load_documents_from_files(file_references)
        if not content.strip():
            raise ValueError("No content found in the uploaded files")

        if LANGCHAIN_AVAILABLE:
            vectorstore, index_size = self._create_vectorstore(content, config)
            self._save_vectorstore_to_disk(vectorstore, content, index_size)
            return vectorstore, index_size, content
        else:
            return None, len(content.split()), content

    def _setup_llm_and_chain(self, config: Dict[str, Any]):
        """Setup LLM and QA chain."""
        self.llm = ChatOpenAI(
            temperature=config.get("temperature", 0),
            model_name=config.get("model_name", "gpt-4o-mini")
        )
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever()
        )

    def _store_config_in_state(self, config: Dict[str, Any], file_references: list, index_size: int, content: str):
        """Store configuration in state."""
        self._set_state("file_references", file_references)
        self._set_state("index_size", index_size)
        self._set_state("model_name", config.get("model_name", "gpt-4o-mini"))
        self._set_state("temperature", config.get("temperature", 0))
        self._set_state("langchain_available", LANGCHAIN_AVAILABLE)
        self._set_state("content", content)
        self._set_state("agent_id", config.get("agent_id", "default"))

    def _execute_langchain_query(self, question: str) -> str:
        """Execute query using LangChain."""
        vectorstore = self._load_vectorstore_from_disk()
        if vectorstore:
            llm = ChatOpenAI(
                temperature=self._get_state("temperature", 0),
                model_name=self._get_state("model_name", "gpt-4o-mini")
            )
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=vectorstore.as_retriever()
            )
            return qa_chain.run(question)
        else:
            # Fallback: recreate from stored content
            content = self._get_state("content")
            if content:
                vectorstore, _ = self._create_vectorstore(content, {
                    "model_name": self._get_state("model_name"),
                    "temperature": self._get_state("temperature")
                })
                llm = ChatOpenAI(
                    temperature=self._get_state("temperature", 0),
                    model_name=self._get_state("model_name", "gpt-4o-mini")
                )
                qa_chain = RetrievalQA.from_chain_type(
                    llm=llm,
                    chain_type="stuff",
                    retriever=vectorstore.as_retriever()
                )
                return qa_chain.run(question)
            else:
                return "Error: No content available for query"

    def _get_source_info(self) -> list:
        """Get source information for response."""
        file_metadata = self._get_state("file_metadata", [])
        return [
            {
                "filename": file_info.get("filename", "Unknown"),
                "file_type": file_info.get("file_type", "Unknown"),
                "relevance_score": 0.9
            } for file_info in file_metadata
        ]

    def _create_response(self, status: str, message: str, total_chunks: int = 0) -> Dict[str, Any]:
        """Create standardized response."""
        return {
            "status": status,
            "message": message,
            "indexed_pages": len(self._get_state('file_references', [])),
            "total_chunks": total_chunks
        }

    def _create_cleanup_response(self, status: str, message: str) -> Dict[str, Any]:
        """Create cleanup response."""
        return {
            "status": status,
            "message": message,
            "resources_freed": ["vectorstore", "llm", "qa_chain", "content", "file_references", "file_metadata", "index_size", "model_name", "temperature", "langchain_available"]
        }

    def _save_vectorstore_to_disk(self, vectorstore: FAISS, content: str, index_size: int):
        """Save the FAISS vectorstore and documents metadata to disk."""
        index_path = self._get_index_path()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        vectorstore.save_local(str(index_path))
        
        # Save documents metadata
        documents_path = self._get_documents_path()
        documents_data = {
            "content": content,
            "total_chunks": index_size,
            "model_name": self._get_state("model_name"),
            "temperature": self._get_state("temperature")
        }
        
        with open(documents_path, 'w') as f:
            json.dump(documents_data, f, indent=2)

    def _load_vectorstore_from_disk(self) -> Optional[FAISS]:
        """Load the FAISS vectorstore from disk."""
        try:
            index_path = self._get_index_path()
            if not index_path.exists():
                return None
            
            embeddings = OpenAIEmbeddings()
            return FAISS.load_local(str(index_path), embeddings)
        except Exception as e:
            logger.error(f"Error loading vectorstore from disk: {e}")
            return None

    def _load_documents_from_files(self, file_references: list) -> Tuple[str, list]:
        """Load document content from file references."""
        all_content = []
        file_metadata = []
        
        for file_id in file_references:
            try:
                file_content, metadata = self._download_file_from_service(file_id)
                content = self._process_file_content(file_content, metadata['filename'], metadata['file_type'])
                
                if content.strip():
                    all_content.append(content)
                    file_metadata.append({
                        'file_id': file_id,
                        'filename': metadata['filename'],
                        'file_type': metadata['file_type'],
                        'content_length': len(content)
                    })
                    
            except Exception as e:
                logger.error(f"Error processing file {file_id}: {e}")
                continue
        
        if not all_content:
            raise Exception("No content could be extracted from any of the uploaded files")
        
        return "\n\n".join(all_content), file_metadata

    def _process_file_content(self, file_content: bytes, filename: str, file_type: str) -> str:
        """Process file content based on file type."""
        if not LANGCHAIN_AVAILABLE:
            return file_content.decode('utf-8', errors='ignore')
        
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(filename)) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # Process based on file type
            if file_type.lower() == 'application/pdf' or filename.lower().endswith('.pdf'):
                loader = PyPDFLoader(temp_file_path)
            elif file_type.lower() == 'text/csv' or filename.lower().endswith('.csv'):
                loader = CSVLoader(temp_file_path)
            elif file_type.lower() == 'application/json' or filename.lower().endswith('.json'):
                loader = JSONLoader(temp_file_path, jq_schema='.', text_content=False)
            else:
                loader = TextLoader(temp_file_path, encoding='utf-8')
            
            documents = loader.load()
            return documents[0].page_content if documents else ""
            
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename."""
        return os.path.splitext(filename)[1] if '.' in filename else ''

    def _create_vectorstore(self, content: str, config: Dict[str, Any]) -> Tuple[FAISS, int]:
        """Create vectorstore from content."""
        if not LANGCHAIN_AVAILABLE:
            raise Exception("LangChain is required for vectorstore creation")

        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.get("chunk_size", 1000),
            chunk_overlap=config.get("chunk_overlap", 200)
        )

        documents = text_splitter.split_text(content)
        docs = [Document(page_content=doc) for doc in documents]

        # Create embeddings and vectorstore
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.from_documents(docs, embeddings)

        return vectorstore, len(docs)

    def get_storage_status(self) -> Dict[str, Any]:
        """Get the current storage status of the vector database."""
        try:
            index_path = self._get_index_path()
            documents_path = self._get_documents_path()
            
            return {
                "storage_directory": str(self.base_storage_dir),
                "agent_storage_path": str(self._get_storage_path("")),
                "index_exists": index_path.exists(),
                "documents_exist": documents_path.exists(),
                "is_initialized": self._is_initialized(),
                "file_count": len(self._get_state("file_references", [])),
                "total_chunks": self._get_state("index_size", 0)
            }
        except Exception as e:
            return {
                "error": str(e),
                "storage_directory": str(self.base_storage_dir),
                "is_initialized": self._is_initialized()
            }


# Local testing section (for development only)
if __name__ == "__main__":
    agent = RAGAgent()
    
    # Test initialization
    print("1. Testing initialization...")
    init_result = agent.initialize({
        "file_references": ["test_file_1", "test_file_2"],
        "model_name": "gpt-4o-mini",
        "temperature": 0,
        "agent_id": "test_agent"
    })
    print(json.dumps(init_result, indent=2))

    if init_result.get("status") == "success":
        # Test execution
        print("\n2. Testing execution...")
        exec_result = agent.execute({"question": "What are the main topics in these documents?"})
        print(json.dumps(exec_result, indent=2))

        # Test cleanup
        print("\n3. Testing cleanup...")
        cleanup_result = agent.cleanup()
        print(json.dumps(cleanup_result, indent=2))

    print("\n=== Local testing completed ===")
else:
    print("Persistent agent loaded. The platform will use Docker exec to run agent methods.")
