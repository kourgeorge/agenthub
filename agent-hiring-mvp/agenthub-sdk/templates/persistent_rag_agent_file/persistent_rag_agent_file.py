#!/usr/bin/env python3
"""
File RAG Agent - Simplified and Fixed Implementation

A clean, efficient implementation of a RAG agent that handles
full URLs with access tokens directly from the widget.
"""

import os
import json
import logging
import tempfile
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from dotenv import load_dotenv

# Load environment variables and configure logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import LangChain components
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader, JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.schema import Document

from agenthub_sdk.agent import PersistentAgent


class FileRAGAgent(PersistentAgent):
    """Simplified File RAG Agent Implementation"""

    def __init__(self):
        super().__init__()
        # Instance variables for LangChain components
        self.base_storage_dir = Path("/tmp/agenthub_persistent_rag")
        self.base_storage_dir.mkdir(exist_ok=True)

    def _get_storage_path(self, identifier: str) -> Path:
        """Get storage path for this agent instance."""
        agent_id = self._get_state("agent_id") or "default"
        return self.base_storage_dir / f"agent_{agent_id}" / identifier

    def _get_index_path(self) -> Path:
        return self._get_storage_path("faiss_index")

    def _get_documents_path(self) -> Path:
        return self._get_storage_path("documents.json")

    def _download_file_from_url(self, file_url: str) -> Tuple[bytes, dict]:
        """Download file content directly from the full URL with access token."""
        # First attempt: try the original URL
        try:
            logger.info(f"Downloading file from: {file_url}")
            with urlopen(file_url, timeout=60) as response:
                file_content = response.read()

            file_size = len(file_content)
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                raise ValueError(f"File too large ({file_size} bytes). Maximum size is 10MB.")

            # Extract metadata from response headers
            metadata = {
                'filename': response.headers.get('X-File-Name', 'unknown_file'),
                'file_type': response.headers.get('X-File-Type', 'application/octet-stream'),
                'file_extension': response.headers.get('X-File-Extension', ''),
                'file_size': file_size,
                'description': response.headers.get('X-File-Description', '')
            }

            logger.info(f"File downloaded successfully. File size: {file_size} bytes")
            return file_content, metadata
        except Exception as e:
            logger.warning(f"Initial download failed from {file_url}: {e}")

            # Second attempt: try with host.docker.internal as fallback
            try:
                # Replace localhost/127.0.0.1 with host.docker.internal
                fallback_url = file_url
                if 'localhost' in file_url or '127.0.0.1' in file_url:
                    fallback_url = file_url.replace('localhost', 'host.docker.internal').replace('127.0.0.1',
                                                                                                 'host.docker.internal')
                    logger.info(f"Attempting fallback download from: {fallback_url}")

                    with urlopen(fallback_url, timeout=60) as response:
                        file_content = response.read()

                    file_size = len(file_content)
                    if file_size > 10 * 1024 * 1024:  # 10MB limit
                        raise ValueError(f"File too large ({file_size} bytes). Maximum size is 10MB.")

                    # Extract metadata from response headers
                    metadata = {
                        'filename': response.headers.get('X-File-Name', 'unknown_file'),
                        'file_type': response.headers.get('X-File-Type', 'application/octet-stream'),
                        'file_extension': response.headers.get('X-File-Extension', ''),
                        'file_size': file_size,
                        'description': response.headers.get('X-File-Description', '')
                    }

                    logger.info(f"Fallback download successful from {fallback_url}. File size: {file_size} bytes")
                    return file_content, metadata
                else:
                    logger.info("No localhost detected in URL, skipping host.docker.internal fallback")
                    raise e

            except Exception as fallback_e:
                logger.error(
                    f"Fallback download also failed from {fallback_url if 'fallback_url' in locals() else 'N/A'}: {fallback_e}")
                raise Exception(
                    f"Failed to download file from both original URL and host.docker.internal fallback: {str(e)} -> {str(fallback_e)}")

    def initialize(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the RAG agent with configuration data."""
        try:
            logger.info(f"Initializing RAG agent with config: {config}")
            self._set_state("agent_id", config.get("agent_id", "default"))
            file_references = config.get("file_references")
            if not file_references or not isinstance(file_references, list):
                raise ValueError("file_references is required and must be a non-empty array")

            # Check if already initialized
            if self._is_initialized():
                logger.info("Agent already initialized, returning existing state")
                return self._create_response("success",
                                             f"Agent already initialized with {len(self._get_state('file_references', []))} files")

            # Try to load existing index or create new one
            content, files_metadata = self._load_documents_from_urls(file_references)

            vectorstore, index_size = self._create_vectorstore(content, config)
            self._save_vectorstore_to_disk(vectorstore, content, index_size)

            # Store configuration in state
            self._store_config_in_state(config, file_references, index_size, content)
            self._mark_initialized()

            logger.info("Initialization completed successfully")
            return self._create_response("success",
                                         f"Successfully initialized RAG agent with {len(file_references)} files",
                                         index_size)

        except Exception as e:
            logger.error(f"Error initializing RAG agent: {e}")
            return self._create_response("error", f"Initialization failed!!!!!!: {str(e)}")

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute RAG query."""

        if not self._is_initialized():
            logger.error("Agent not initialized. Current state:")

        question = input_data.get("question")
        if not question:
            raise ValueError("question is required for execution")

        vectorstore = self._load_vectorstore_from_disk()

        retriever = vectorstore.as_retriever()
            
        # Retrieve most relevant documents for the question
        relevant_docs = retriever.get_relevant_documents(question)
        for i, doc in enumerate(relevant_docs[:3]):
            logger.info(
                f"--- Document {i + 1} (Relevance Score: {getattr(doc, 'metadata', {}).get('score', 'N/A')}) ---")
            logger.info(f"Content preview: {doc.page_content}...")
            logger.info(f"Metadata: {doc.metadata}")

        # Setup LLM and QA chain
        llm = ChatOpenAI(
            temperature=self._get_state("temperature", 0),
            model_name=self._get_state("model_name", "gpt-4o-mini")
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever()
        )

        answer = qa_chain.run(question)

        # Return output that matches the outputSchema exactly
        return {
            "answer": answer,  # Must match schema: answer field
            "confidence": 0.8,  # Must match schema: confidence score (0-1)
            "sources": self._get_source_info(),  # Must match schema: list of source documents
        }

    def cleanup(self) -> Dict[str, Any]:
        """Clean up agent resources."""
        self._state.clear()
        return self._create_cleanup_response("success", "Agent resources cleaned up successfully")

    def _store_config_in_state(self, config: Dict[str, Any], file_references: list, index_size: int, content: str):
        """Store configuration in state."""
        self._set_state("file_references", file_references)
        self._set_state("index_size", index_size)
        self._set_state("model_name", config.get("model_name", "gpt-4o-mini"))
        self._set_state("temperature", config.get("temperature", 0))
        self._set_state("content", content)  # Store content for recreation if needed
        self._set_state("agent_id", config.get("agent_id", "default"))
        logger.info(
            f"Configuration stored in state: file_references={len(file_references)}, content_length={len(content)}")

    def _get_source_info(self) -> list:
        """Get source information for response."""
        file_metadata = self._get_state("file_metadata", [])
        if file_metadata:
            return [
                {
                    "filename": file_info.get("filename", "Unknown"),
                    "file_type": file_info.get("file_type", "Unknown"),
                    "relevance_score": 0.9
                } for file_info in file_metadata
            ]
        else:
            # Fallback to file references if no metadata
            file_references = self._get_state("file_references", [])
            return [
                {
                    "filename": f"File {i + 1}",
                    "file_type": "Unknown",
                    "relevance_score": 0.9
                } for i in range(len(file_references))
            ]

    def _create_response(self, status: str, message: str, total_chunks: int = 0) -> Dict[str, Any]:
        """Create standardized response."""
        return {
            "status": status,  # Must match schema enum: ["success", "error"]
            "message": message,  # Must match schema: message field
            "indexed_pages": len(self._get_state('file_references', [])),  # Must match schema: number of pages indexed
            "total_chunks": total_chunks  # Must match schema: total chunks created
        }

    def _create_cleanup_response(self, status: str, message: str) -> Dict[str, Any]:
        """Create cleanup response."""
        return {
            "status": status,  # Must match schema enum: ["success", "error"]
            "message": message,  # Must match schema: message field
            "resources_freed": ["vectorstore", "llm", "qa_chain", "content", "file_references", "file_metadata",
                                "index_size", "model_name", "temperature", "langchain_available"]
            # Must match schema: list of resources freed
        }

    def _save_vectorstore_to_disk(self, vectorstore: FAISS, content: str, index_size: int):
        """Save the FAISS vectorstore and documents metadata to disk."""
        index_path = self._get_index_path()
        index_path.parent.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        vectorstore.save_local(str(index_path))
        logger.info(f"FAISS index saved into {index_path}. It contains: {vectorstore.index.ntotal} vectors.")

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
        logger.info(f"Successfully saved vectorstore to disk at {index_path}")

    def _load_documents_from_urls(self, file_urls: list) -> Tuple[str, list]:
        """Load document content directly from URLs."""
        all_content = []
        file_metadata = []

        for file_url in file_urls:
            try:
                file_content, metadata = self._download_file_from_url(file_url)
                content = self._process_file_content(file_content, metadata['filename'], metadata['file_type'])

                if content.strip():
                    all_content.append(content)
                    file_metadata.append({
                        'file_url': file_url,
                        'filename': metadata['filename'],
                        'file_type': metadata['file_type'],
                        'content_length': len(content)
                    })
                    logger.info(f"Successfully processed file: {metadata['filename']}")

            except Exception as e:
                logger.error(f"Error processing file from {file_url}: {e}")
                continue

        if not all_content:
            raise Exception("No content could be extracted from any of the uploaded files")

        # Store file metadata in state

        return "\n\n".join(all_content), file_metadata

    def _process_file_content(self, file_content: bytes, filename: str, file_type: str) -> str:
        """Process file content based on file type."""

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

    def _load_vectorstore_from_disk(self) -> Optional[FAISS]:
        """Load the FAISS vectorstore from disk."""
        try:
            index_path = self._get_index_path()
            documents_path = self._get_documents_path()

            if not index_path.exists() or not documents_path.exists():
                logger.warning("No saved vector database found on disk")
                return None

            # Load FAISS index with security setting for trusted sources
            embeddings = OpenAIEmbeddings()
            vectorstore = FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
            logger.info(f"FAISS index loaded from {index_path}. It contains: {vectorstore.index.ntotal} vectors.")

            return vectorstore

        except Exception as e:
            logger.error(f"Error loading vectorstore from disk: {e}")
            return None


if __name__ == "__main__":
    agent = FileRAGAgent()

    # Test initialization
    print("1. Testing initialization...")
    init_result = agent.initialize({
        "file_references": [
            "https://drive.google.com/uc?export=download&id=1z1jVSzUX6OE-6o4ZnPXImzq5GUdTbKn_"
        ],
        "model_name": "gpt-4o-mini",
        "temperature": 0,
        "agent_id": "test_agent"
    })
    print(json.dumps(init_result, indent=2))

    if init_result.get("status") == "success":
        # Test execution
        print("\n2. Testing execution...")
        exec_result = agent.execute({"question": "who were the supervisors of the master degree?"})
        print(json.dumps(exec_result, indent=2))

        # Test cleanup
        print("\n3. Testing cleanup...")
        cleanup_result = agent.cleanup()
        print(json.dumps(cleanup_result, indent=2))

    else:
        print("File RAG agent loaded. The platform will use Docker exec to run agent methods.")
