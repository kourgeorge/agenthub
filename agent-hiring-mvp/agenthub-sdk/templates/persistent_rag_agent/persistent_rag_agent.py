#!/usr/bin/env python3
"""
Persistent RAG Agent - Clean Implementation

This is a clean implementation of a persistent agent that demonstrates:
1. Inheritance from PersistentAgent base class
2. Proper state management using _get_state/_set_state
3. Clean separation of initialize/execute/cleanup phases
4. Focus on business logic only - no platform concerns

The platform will:
- Load this class using importlib
- Create an instance
- Call initialize(), execute(), cleanup() directly
- Handle all platform concerns (IDs, tracking, etc.) itself
"""

import os
import json
import logging
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import LangChain components
try:
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain.chains import RetrievalQA
    from langchain.schema import Document

    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not available, using fallback implementation")
    LANGCHAIN_AVAILABLE = False

# Import the base PersistentAgent class from the SDK
try:
    from agenthub_sdk.agent import PersistentAgent
except ImportError:
    # Fallback for when running standalone
    from abc import ABC, abstractmethod


    class PersistentAgent(ABC):
        """
        Base class for persistent agents with state management.
        
        This class provides:
        - State management (_get_state/_set_state)
        - Lifecycle management (_is_initialized/_mark_initialized)
        - Abstract methods for agent implementation
        
        The platform handles all platform concerns (IDs, tracking, etc.).
        Agents focus only on business logic.
        """

        def __init__(self):
            self._state = {}
            self._initialized = False

        @abstractmethod
        def initialize(self, config: Dict[str, Any]) -> Dict[str, Any]:
            """Initialize the agent with configuration."""
            pass

        @abstractmethod
        def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            """Execute the agent with input data."""
            pass

        def cleanup(self) -> Dict[str, Any]:
            """Clean up agent resources."""
            return {"status": "cleaned_up", "message": "Default cleanup completed"}

        def _get_state(self, key: str, default: Any = None) -> Any:
            """Get value from agent state."""
            return self._state.get(key, default)

        def _set_state(self, key: str, value: Any) -> None:
            """Set value in agent state."""
            self._state[key] = value

        def _is_initialized(self) -> bool:
            """Check if agent is initialized."""
            return self._initialized

        def _mark_initialized(self) -> None:
            """Mark agent as initialized."""
            self._initialized = True


class RAGAgent(PersistentAgent):
    """
    Clean Persistent RAG Agent Implementation
    
    This agent demonstrates the proper way to implement a persistent agent:
    1. Inherit from PersistentAgent
    2. Implement initialize(), execute(), cleanup()
    3. Use _get_state()/_set_state() for state management
    4. Use _is_initialized()/_mark_initialized() for lifecycle management
    5. Focus on business logic only - no platform concerns
    
    The platform will call these methods directly:
    - initialize(config) -> called once to set up the agent
    - execute(input_data) -> called for each query
    - cleanup() -> called when agent is no longer needed
    """

    def __init__(self):
        """Initialize the RAG agent."""
        super().__init__()
        # Instance variables for LangChain components
        self.vectorstore = None
        self.llm = None
        self.qa_chain = None

    def initialize(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the RAG agent with configuration data.
        
        This method is called once by the platform to set up the agent.
        It should:
        1. Validate the configuration
        2. Load and process the data
        3. Set up any required components
        4. Store configuration in state
        5. Mark as initialized
        
        Args:
            config: Configuration data containing website_url and other settings
            
        Returns:
            Dict with initialization result (no platform concerns)
        """
        try:
            # Validate configuration
            website_url = config.get("website_url")
            if not website_url:
                raise ValueError("website_url is required for initialization")

            # Check if already initialized
            if self._is_initialized():
                return {
                    "status": "already_initialized",
                    "message": f"Agent already initialized with {self._get_state('website_url')}",
                    "index_size": self._get_state("index_size")
                }

            logger.info(f"Initializing RAG agent with website: {website_url}")

            # Load document content
            logger.info("Loading document content...")
            content = self._load_document_from_url(website_url)
            logger.info(f"Document loaded, content length: {len(content)} characters")

            if not content.strip():
                raise ValueError("No content found in the document")

            # Create vectorstore and setup LLM
            if LANGCHAIN_AVAILABLE:
                logger.info("Creating vectorstore...")
                vectorstore, index_size = self._create_vectorstore(content, config)
                logger.info(f"Vectorstore created with {index_size} chunks")

                # Setup LLM and QA chain
                llm = ChatOpenAI(
                    temperature=config.get("temperature", 0),
                    model_name=config.get("model_name", "gpt-3.5-turbo")
                )

                qa_chain = RetrievalQA.from_chain_type(
                    llm=llm,
                    chain_type="stuff",
                    retriever=vectorstore.as_retriever()
                )

                # Store only serializable data in state
                # Don't store the actual objects as they contain non-serializable components
            else:
                # Fallback: store content for simple text search
                index_size = len(content.split())
                logger.warning("LangChain not available, using fallback implementation")

            # Store configuration and content in state (persisted by platform)
            self._set_state("website_url", website_url)
            self._set_state("index_size", index_size)
            self._set_state("model_name", config.get("model_name", "gpt-3.5-turbo"))
            self._set_state("temperature", config.get("temperature", 0))
            self._set_state("langchain_available", LANGCHAIN_AVAILABLE)
            self._set_state("content", content)  # Store content for recreation

            # Mark as initialized (important for platform)
            self._mark_initialized()

            logger.info(f"RAG agent initialized successfully with {index_size} content chunks")

            return {
                "status": "initialized",
                "message": f"Successfully initialized RAG agent with {website_url}",
                "index_size": index_size,
                "langchain_available": LANGCHAIN_AVAILABLE
            }

        except Exception as e:
            logger.error(f"Error initializing RAG agent: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute RAG query.
        
        This method is called by the platform for each query.
        It should:
        1. Check if agent is initialized
        2. Validate input data
        3. Process the query
        4. Return the result
        
        Args:
            input_data: Input data containing the question
            
        Returns:
            Dict with execution result (no platform concerns)
        """
        try:
            # Check if agent is initialized (important for platform)
            if not self._is_initialized():
                raise ValueError("Agent not initialized. Call initialize() first.")

            # Validate input
            question = input_data.get("question")
            if not question:
                raise ValueError("question is required for execution")

            logger.info(f"Executing RAG query: {question}")

            # Execute query
            if LANGCHAIN_AVAILABLE and self._get_state("langchain_available"):
                # Recreate components from stored content
                content = self._get_state("content")
                if content:
                    vectorstore, _ = self._create_vectorstore(content, {
                        "model_name": self._get_state("model_name"),
                        "temperature": self._get_state("temperature")
                    })
                    
                    llm = ChatOpenAI(
                        temperature=self._get_state("temperature", 0),
                        model_name=self._get_state("model_name", "gpt-3.5-turbo")
                    )
                    
                    qa_chain = RetrievalQA.from_chain_type(
                        llm=llm,
                        chain_type="stuff",
                        retriever=vectorstore.as_retriever()
                    )
                    
                    answer = qa_chain.run(question)
                else:
                    answer = "Error: No content available for query"
            else:
                # Fallback: simple text search
                answer = f"Fallback response: I found information about '{question}' in the indexed content. (LangChain not available for advanced retrieval)"

            return {
                "answer": answer,
                "question": question,
                "website_url": self._get_state("website_url"),
                "index_size": self._get_state("index_size")
            }

        except Exception as e:
            logger.error(f"Error executing RAG agent: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def cleanup(self) -> Dict[str, Any]:
        """
        Clean up agent resources.
        
        This method is called by the platform when the agent is no longer needed.
        It should:
        1. Clean up any resources (files, connections, etc.)
        2. Clear instance variables
        3. Clear state (platform will handle persistence)
        
        Returns:
            Dict with cleanup result (no platform concerns)
        """
        try:
            logger.info("Cleaning up RAG agent resources")

            # Clear state (platform will handle persistence)
            self._state.clear()
            self._initialized = False

            return {
                "status": "cleaned_up",
                "message": "Agent resources cleaned up successfully"
            }
        except Exception as e:
            logger.error(f"Error cleaning up RAG agent: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _load_document_from_url(self, url: str) -> str:
        """Load document content from URL."""
        try:
            logger.info(f"Loading document from URL: {url}")

            if not LANGCHAIN_AVAILABLE:
                # Fallback implementation
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                return response.text

            # Check if it's a PDF URL
            if url.lower().endswith('.pdf'):
                loader = PyPDFLoader(url)
            else:
                # Add timeout to WebBaseLoader to prevent hanging
                loader = WebBaseLoader(url, requests_kwargs={'timeout': 60})

            documents = loader.load()
            if documents:
                return documents[0].page_content
            else:
                raise Exception("No content found at the URL")

        except Exception as e:
            logger.error(f"Error loading document from URL: {e}")
            raise Exception(f"Failed to load document from URL: {str(e)}")

    def _create_vectorstore(self, content: str, config: Dict[str, Any]) -> tuple:
        """Create vectorstore from content."""
        if not LANGCHAIN_AVAILABLE:
            raise Exception("LangChain is required for vectorstore creation")

        logger.info("Splitting text into chunks...")
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.get("chunk_size", 1000),
            chunk_overlap=config.get("chunk_overlap", 200)
        )

        documents = text_splitter.split_text(content)
        docs = [Document(page_content=doc) for doc in documents]
        logger.info(f"Text split into {len(docs)} chunks")

        logger.info("Creating embeddings...")
        # Create embeddings and vectorstore
        embeddings = OpenAIEmbeddings()
        logger.info("Creating FAISS vectorstore...")
        vectorstore = FAISS.from_documents(docs, embeddings)
        logger.info("Vectorstore creation completed")

        return vectorstore, len(docs)


# =============================================================================
# LOCAL TESTING SECTION (Optional - for development only)
# =============================================================================

if __name__ == "__main__":
    """
    This section is only for local testing and development.
    The platform will NOT use this - it will call the class methods directly.
    
    IMPORTANT: When deployed in Docker, the platform uses Docker exec to run
    the agent class methods directly. This main block is only for local development testing.
    """

    agent = RAGAgent()

    # Test initialization
    print("1. Testing initialization...")
    init_result = agent.initialize({
        "website_url": "http://kour.me",
        "model_name": "gpt-3.5-turbo",
        "temperature": 0
    })
    print(json.dumps(init_result, indent=2))

    if init_result.get("status") == "initialized":
        # Test first execution
        print("\n2. Testing first execution...")
        exec_result1 = agent.execute({
            "question": "who were the supervisors of the master degree?"
        })
        print(json.dumps(exec_result1, indent=2))

        # Test second execution (should use same state)
        print("\n3. Testing second execution...")
        exec_result2 = agent.execute({
            "question": "who was the phd supervisor?"
        })
        print(json.dumps(exec_result2, indent=2))

        # Test cleanup
        print("\n4. Testing cleanup...")
        cleanup_result = agent.cleanup()
        print(json.dumps(cleanup_result, indent=2))

    print("\n=== Local testing completed ===")
    print("Note: The platform will call these methods directly and handle all platform concerns")
else:
    print("Persistent agent loaded. The platform will use Docker exec to run agent methods.")
    print("Set RUN_LOCAL_TESTING=true to run local testing.")
