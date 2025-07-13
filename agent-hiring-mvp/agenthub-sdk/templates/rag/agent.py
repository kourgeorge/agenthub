import os
import logging
from typing import Dict, Any
from urllib.parse import urlparse
import requests
from pathlib import Path

from llama_index.core import Settings, VectorStoreIndex, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.readers.web import BeautifulSoupWebReader
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_url(source: str) -> bool:
    """Check if the source is a URL."""
    try:
        result = urlparse(source)
        return all([result.scheme, result.netloc])
    except:
        return False

def load_document_from_url(url: str) -> str:
    """Load document content from URL."""
    try:
        logger.info(f"Loading document from URL: {url}")
        reader = BeautifulSoupWebReader()
        documents = reader.load_data(urls=[url])
        if documents:
            return documents[0].text
        else:
            raise Exception("No content found at the URL")
    except Exception as e:
        logger.error(f"Error loading document from URL: {e}")
        raise Exception(f"Failed to load document from URL: {str(e)}")

def load_document_from_file(file_path: str) -> str:
    """Load document content from local file."""
    try:
        logger.info(f"Loading document from file: {file_path}")
        path = Path(file_path)
        if not path.exists():
            raise Exception(f"File not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading document from file: {e}")
        raise Exception(f"Failed to load document from file: {str(e)}")

def setup_llm_and_embeddings(config: Dict[str, Any]) -> None:
    """Setup LLM and embedding models."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise Exception("OPENAI_API_KEY environment variable not set")
        
        # Setup LLM
        Settings.llm = OpenAI(
            model=config.get("model_name", "gpt-3.5-turbo"),
            temperature=config.get("temperature", 0),
            max_tokens=config.get("max_tokens", 1000),
            api_key=api_key
        )
        
        # Setup embeddings
        Settings.embed_model = OpenAIEmbedding(
            model=config.get("embedding_model", "text-embedding-ada-002"),
            api_key=api_key
        )
        
        logger.info("LLM and embeddings setup completed")
    except Exception as e:
        logger.error(f"Error setting up LLM and embeddings: {e}")
        raise

def create_rag_index(document_content: str, config: Dict[str, Any]) -> VectorStoreIndex:
    """Create a RAG index from document content."""
    try:
        logger.info("Creating RAG index from document content")
        
        # Create document
        document = Document(text=document_content)
        
        # Setup node parser with configurable chunk size and overlap
        node_parser = SentenceSplitter(
            chunk_size=config.get("chunk_size", 1024),
            chunk_overlap=config.get("chunk_overlap", 200)
        )
        
        # Create index
        index = VectorStoreIndex.from_documents(
            documents=[document],
            transformations=[node_parser]
        )
        
        logger.info("RAG index created successfully")
        return index
    except Exception as e:
        logger.error(f"Error creating RAG index: {e}")
        raise

def answer_question(index: VectorStoreIndex, question: str, config: Dict[str, Any]) -> str:
    """Answer a question using the RAG index."""
    try:
        logger.info(f"Answering question: {question}")
        
        # Create query engine
        query_engine = index.as_query_engine(
            temperature=config.get("temperature", 0),
            max_tokens=config.get("max_tokens", 1000)
        )
        
        # Get response
        response = query_engine.query(question)
        
        logger.info("Question answered successfully")
        return str(response)
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise

def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function for the RAG agent.
    
    Args:
        input_data: Dictionary containing 'document_source' and 'question'
        config: Agent configuration dictionary
    
    Returns:
        Dictionary containing the answer and metadata
    """
    try:
        # Extract input parameters
        document_source = input_data.get("document_source")
        question = input_data.get("question")
        
        if not document_source:
            raise Exception("document_source is required")
        if not question:
            raise Exception("question is required")
        
        logger.info(f"Processing RAG request - Document: {document_source}, Question: {question}")
        
        # Setup LLM and embeddings
        setup_llm_and_embeddings(config)
        
        # Load document content
        if is_url(document_source):
            document_content = load_document_from_url(document_source)
        else:
            document_content = load_document_from_file(document_source)
        
        if not document_content.strip():
            raise Exception("No content found in the document")
        
        # Create RAG index
        index = create_rag_index(document_content, config)
        
        # Answer the question
        answer = answer_question(index, question, config)
        
        # Return result
        result = {
            "answer": answer,
            "document_source": document_source,
            "question": question,
            "model_used": config.get("model_name", "gpt-3.5-turbo"),
            "embedding_model": config.get("embedding_model", "text-embedding-ada-002"),
            "chunk_size": config.get("chunk_size", 1024),
            "chunk_overlap": config.get("chunk_overlap", 200)
        }
        

        logger.info("RAG processing completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error in RAG agent: {e}")
        return {
            "error": str(e),
            "document_source": input_data.get("document_source"),
            "question": input_data.get("question")
        }

