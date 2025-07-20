import os
import logging
from typing import Dict, Any
from urllib.parse import urlparse
import requests
from pathlib import Path
import tempfile

from llama_index.core import Settings, VectorStoreIndex, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.readers.web import BeautifulSoupWebReader
from llama_index.readers.file import PDFReader
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


def is_pdf_url(url: str) -> bool:
    """Check if the URL points to a PDF file by examining content-type header."""
    try:
        # Make a HEAD request to check content-type without downloading the full file
        response = requests.head(url, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        
        # Check for PDF content type
        if 'application/pdf' in content_type:
            return True
        
        # Fallback: check file extension if content-type is not available
        parsed_url = urlparse(url)
        if parsed_url.path.lower().endswith('.pdf'):
            logger.warning(f"URL ends with .pdf but content-type is {content_type}")
            return True
            
        return False
        
    except Exception as e:
        logger.warning(f"Could not determine content-type for {url}: {e}")
        # Fallback to extension check if HEAD request fails
        parsed_url = urlparse(url)
        return parsed_url.path.lower().endswith('.pdf')


def load_document_from_url(url: str) -> str:
    """Load document content from URL."""
    try:
        logger.info(f"Loading document from URL: {url}")
        
        # Check if it's a PDF URL
        if is_pdf_url(url):
            logger.info("Detected PDF URL, using PDF reader")
            return load_pdf_from_url(url)
        else:
            logger.info("Using web reader for non-PDF URL")
            reader = BeautifulSoupWebReader()
            documents = reader.load_data(urls=[url])
            if documents:
                return documents[0].text
            else:
                raise Exception("No content found at the URL")
    except Exception as e:
        logger.error(f"Error loading document from URL: {e}")
        raise Exception(f"Failed to load document from URL: {str(e)}")


def load_pdf_from_url(url: str) -> str:
    """Load PDF content from URL."""
    try:
        logger.info(f"Loading PDF from URL: {url}")
        
        # Download PDF to temporary file
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # Read PDF content
            pdf_reader = PDFReader()
            documents = pdf_reader.load_data(file=temp_file_path)
            
            if documents:
                # Combine all pages into one text
                content = "\n\n".join([doc.text for doc in documents])
                logger.info(f"Successfully loaded PDF with {len(documents)} pages")
                return content
            else:
                raise Exception("No content found in PDF")
                
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error loading PDF from URL: {e}")
        raise Exception(f"Failed to load PDF from URL: {str(e)}")


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
        # Convert chunk_size to int since it comes from choice field as string
        chunk_size = int(config.get("chunk_size", "1024"))
        chunk_overlap = config.get("chunk_overlap", 200)
        
        node_parser = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
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


def answer_multiple_questions(index: VectorStoreIndex, questions: list, config: Dict[str, Any]) -> list:
    """Answer multiple questions using the RAG index."""
    try:
        logger.info(f"Answering {len(questions)} questions")
        
        answers = []
        
        for i, question in enumerate(questions):
            logger.info(f"Answering question {i+1}/{len(questions)}: {question}")
            
            # Create query engine
            query_engine = index.as_query_engine(
                temperature=config.get("temperature", 0),
                max_tokens=config.get("max_tokens", 1000)
            )

            # Get response
            response = query_engine.query(question)
            
            answers.append({
                "question": question,
                "answer": str(response),
                "question_number": i + 1
            })
            
            logger.info(f"Question {i+1} answered successfully")

        logger.info(f"All {len(questions)} questions answered successfully")
        return answers
    except Exception as e:
        logger.error(f"Error answering questions: {e}")
        raise


def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function for the RAG agent.
    
    Args:
        input_data: Dictionary containing 'document_source' and 'questions' (questions or document content)
        config: Agent configuration dictionary
    
    Returns:
        Dictionary containing the answers and metadata
    """
    try:
        # Extract input parameters
        document_source = input_data.get("document_source")
        questions_input = input_data.get("questions", "")
        
        # Handle backward compatibility - if 'question' is provided, convert to list
        if not questions_input and input_data.get("question"):
            questions_input = input_data.get("question")

        if not document_source and not questions_input:
            raise Exception("Either document_source or questions (as document content) is required")
        
        # Determine if questions_input is document content or actual questions
        is_document_content = False
        
        if questions_input:
            # Check if this looks like document content rather than questions
            # Criteria: longer text, no question marks, more paragraphs
            lines = questions_input.split('\n')
            non_empty_lines = [line.strip() for line in lines if line.strip()]
            
            # If it's a single long paragraph or multiple paragraphs without question marks
            if (len(non_empty_lines) == 1 and len(non_empty_lines[0]) > 200) or \
               (len(non_empty_lines) > 3 and not any('?' in line for line in non_empty_lines)):
                is_document_content = True
                logger.info("Detected questions input as document content")
        
        if is_document_content:
            # Use questions_input as document content and generate a default question
            document_content = questions_input
            questions = ["What is this document about? Please provide a comprehensive summary."]
            document_source = "pasted_content"
            logger.info("Using pasted content as document source")
        else:
            # Parse questions - handle both string and list inputs
            if isinstance(questions_input, list):
                questions = questions_input
            elif isinstance(questions_input, str):
                # Split by newlines and filter out empty lines
                questions = [q.strip() for q in questions_input.split('\n') if q.strip()]
            else:
                raise Exception("questions must be a string or list")

            if not questions:
                raise Exception("No valid questions provided")

            # Load document content from document_source
            if not document_source:
                raise Exception("document_source is required when providing questions")
                
            if is_url(document_source):
                document_content = load_document_from_url(document_source)
            else:
                document_content = load_document_from_file(document_source)

        if not document_content.strip():
            raise Exception("No content found in the document")

        logger.info(f"Processing RAG request - Document: {document_source}, Questions: {len(questions)} questions")

        # Setup LLM and embeddings
        setup_llm_and_embeddings(config)

        # Create RAG index
        index = create_rag_index(document_content, config)

        # Answer all questions
        answers = answer_multiple_questions(index, questions, config)

        # Return result
        result = {
            "answers": answers,
            "document_source": document_source,
            "questions": questions,
            "total_questions": len(questions),
            "model_used": config.get("model_name", "gpt-3.5-turbo"),
            "embedding_model": config.get("embedding_model", "text-embedding-ada-002"),
            "chunk_size": config.get("chunk_size", "1024"),
            "chunk_overlap": config.get("chunk_overlap", 200)
        }

        logger.info("RAG processing completed successfully")
        return result

    except Exception as e:
        logger.error(f"Error in RAG agent: {e}")
        return {
            "error": str(e),
            "document_source": input_data.get("document_source"),
            "questions": input_data.get("questions", [])
        }
