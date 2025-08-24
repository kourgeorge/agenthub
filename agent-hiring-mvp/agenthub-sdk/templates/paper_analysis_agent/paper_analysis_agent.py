#!/usr/bin/env python3
"""
Paper Analysis Agent - Clean Implementation

This is a clean implementation of a persistent agent that demonstrates:
1. Inheritance from PersistentAgent base class
2. Proper state management using _get_state/_set_state
3. Clean separation of initialize/execute/cleanup phases
4. Focus on business logic only - no platform concerns
5. Persistent vector database storage on disk
6. Paper metadata extraction and enrichment using OpenAI Structured Outputs
7. Similarity analysis using vector embeddings

The platform will:
- Load this class using importlib
- Create an instance
- Call initialize(), execute(), cleanup() directly
- Handle all platform concerns (IDs, tracking, etc.) itself
"""

import os
import json
import logging
import re
from datetime import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Pydantic for structured outputs
from pydantic import BaseModel, Field

# Import modern OpenAI client for structured outputs
from openai import OpenAI

# Import LangChain components (keeping for embeddings and vectorstore)
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

# Import research APIs
import arxiv
from scholarly import scholarly

# Import the base PersistentAgent class from the SDK
from agenthub_sdk.agent import PersistentAgent


# Pydantic models for structured outputs
class PaperMetadata(BaseModel):
    """Schema for individual paper metadata extracted from content."""
    title: str = Field(description="The title of the research paper")
    authors: List[str] = Field(description="List of authors of the paper")


class PaperMetadataList(BaseModel):
    """Schema for list of paper metadata extracted from content."""
    papers: List[PaperMetadata] = Field(description="List of extracted papers")


class EnrichedPaper(BaseModel):
    """Schema for enriched paper with additional research data."""
    title: str = Field(description="The title of the research paper")
    authors: List[str] = Field(description="List of authors of the paper")
    abstract: str = Field(description="Abstract or summary of the paper", default="")
    url: str = Field(description="URL to the paper if available", default="")
    source: str = Field(description="Source of the enrichment data", default="manual_extraction")
    arxiv_id: Optional[str] = Field(description="ArXiv ID if available", default=None)
    doi: Optional[str] = Field(description="DOI if available", default=None)
    year: Optional[int] = Field(description="Publication year if available", default=None)
    venue: Optional[str] = Field(description="Publication venue if available", default=None)


class PaperAnalysisAgent(PersistentAgent):
    """
    Clean Persistent Paper Analysis Agent Implementation
    
    This agent demonstrates the proper way to implement a persistent agent:
    1. Inherit from PersistentAgent
    2. Implement initialize(), execute(), cleanup()
    3. Use _get_state()/_set_state() for state management
    4. Use _is_initialized()/_mark_initialized() for lifecycle management
    5. Focus on business logic only - no platform concerns
    6. Persist paper database and vector embeddings on disk for efficient reuse
    
    The platform will call these methods directly:
    - initialize(config) -> called once to set up the agent
    - execute(input_data) -> called for each query
    - cleanup() -> called when agent is no longer needed
    """

    def __init__(self):
        """Initialize the Paper Analysis agent."""
        super().__init__()
        # Instance variables for LangChain components
        self.vectorstore = None
        self.papers_database = []
        # Base directory for persistent storage
        self.base_storage_dir = Path("/tmp/agenthub_paper_analysis")
        self.base_storage_dir.mkdir(exist_ok=True)

    def _get_storage_path(self, identifier: str) -> Path:
        """Get storage path for this agent instance."""
        # Use agent ID from state if available, otherwise use a fallback
        agent_id = self._get_state("agent_id") or "default"
        return self.base_storage_dir / f"agent_{agent_id}" / identifier

    def _get_index_path(self) -> Path:
        """Get the path for the FAISS index."""
        return self._get_storage_path("faiss_index")

    def _get_papers_database_path(self) -> Path:
        """Get the path for the papers database."""
        return self._get_storage_path("papers_database.json")


    def initialize(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the paper analysis agent with configuration data.
        
        This method is called once by the platform to set up the agent.
        It should:
        1. Validate the configuration
        2. Load and process the paper list from the URL
        3. Extract paper metadata using LLM
        4. Enrich papers with research data from APIs
        5. Create vector embeddings and store in database
        6. Store configuration in state
        7. Mark as initialized
        8. Save paper database and embeddings to disk for persistence
        
        Args:
            config: Configuration data containing paper_list_content and other settings
            
        Returns:
            Dict with initialization result (no platform concerns)
        """
        try:
            # Validate configuration
            paper_list_content = config.get("paper_list_content")
            if not paper_list_content:
                raise ValueError("paper_list_content is required for initialization")

            # Check if already initialized
            if self._is_initialized():
                return {
                    "status": "success",  # Must match schema enum: ["success", "error"]
                    "message": f"Agent already initialized with {self._get_state('paper_list_content', 'content')}",
                    "papers_processed": self._get_state("papers_processed", 0),
                    "total_embeddings": self._get_state("total_embeddings", 0),
                    "storage_location": str(self._get_storage_path(""))
                }

            logger.info(f"Initializing Paper Analysis agent with content length: {len(paper_list_content)}")

            # Check if we have a saved database to load

            papers_result = self.extract_papers_with_structured_outputs(paper_list_content, config)
            if papers_result.get("status") != "success":
                raise ValueError(f"Failed to extract papers: {papers_result.get('error', 'Unknown error')}")
            
            papers_metadata = papers_result.get("papers", [])
            logger.info(f"Extracted metadata for {len(papers_metadata)} papers")

            # Enrich papers with research data
            logger.info("Enriching papers with research data...")
            enriched_papers = self._enrich_papers_with_research_data(papers_metadata)
            logger.info(f"Enriched {len(enriched_papers)} papers with research data")

            # Create vector embeddings and store
            logger.info("Creating vector embeddings...")
            total_embeddings = self._create_vector_embeddings(enriched_papers, config)
            logger.info(f"Created {total_embeddings} vector embeddings")

            # Store the enriched papers in the instance variable for persistence
            self.papers_database = enriched_papers
            logger.info(f"Stored {len(self.papers_database)} papers in database")

            # Store configuration in state FIRST (before saving files)
            self._set_state("agent_id", config.get("agent_id", "default"))  # Store agent ID for storage paths
            self._set_state("papers_count", len(self.papers_database))
            self._set_state("model_name", config.get("model_name", "gpt-4o-mini"))
            self._set_state("temperature", config.get("temperature", 0))
            self._set_state("is_initialized", True)

            # Save to disk AFTER setting agent_id in state
            logger.info("Saving paper database and embeddings to disk...")
            index_path = self._get_index_path()
            index_path.parent.mkdir(parents=True, exist_ok=True)
            self.vectorstore.save_local(str(index_path))
            logger.info(f"FAISS index saved to {index_path}")

            # Save papers database to disk
            papers_database_path = self._get_papers_database_path()
            papers_database_path.parent.mkdir(parents=True, exist_ok=True)
            with open(papers_database_path, 'w') as f:
                json.dump(self.papers_database, f, indent=2)
            logger.info(f"Papers database saved to {papers_database_path}")

            # Mark as initialized (important for platform)
            self._mark_initialized()

            logger.info(f"Paper Analysis agent initialized successfully with {len(self.papers_database)} papers")

            return {
                "status": "success",  # Must match schema enum: ["success", "error"]
                "papers_processed": len(enriched_papers),  # Must match schema: papers_processed field
                "total_embeddings": total_embeddings,  # Must match schema: total_embeddings field
                "storage_location": str(self._get_storage_path(""))  # Must match schema: storage_location field
            }

        except Exception as e:
            logger.error(f"Error initializing Paper Analysis agent: {e}")
            return {
                "status": "error",  # Must match schema enum: ["success", "error"]
                "message": f"Initialization failed: {str(e)}",  # Must match schema: message field
                "papers_processed": 0,  # Must match schema: papers_processed field
                "total_embeddings": 0,  # Must match schema: total_embeddings field
                "storage_location": ""  # Must match schema: storage_location field
            }

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute paper analysis to find related papers.
        
        This method is called by the platform for each query.
        It should:
        1. Check if agent is initialized
        2. Validate input data
        3. Load paper database and vector embeddings from disk
        4. Process the input paper content
        5. Find related papers using similarity search
        6. Return the result
        
        Args:
            input_data: Input data containing the paper content to analyze
            
        Returns:
            Dict with execution result (no platform concerns)
        """

        try:
            # Check if agent is initialized (important for platform)
            if not self._is_initialized():
                raise ValueError("Agent not initialized. Call initialize() first.")

            # Validate input
            paper_content = input_data.get("paper_content")
            if not paper_content:
                raise ValueError("paper_content is required for execution")

            max_results = input_data.get("max_results", 10)

            logger.info(f"Executing paper analysis for content length: {len(paper_content)}")

                        # Always load paper database and vectorstore from disk
            self._load_papers_database_from_disk()
            
            # Verify that both database and vectorstore are loaded
            if not self.papers_database:
                raise ValueError("Failed to load papers database from disk")
            if not self.vectorstore:
                raise ValueError("Failed to load vectorstore from disk")

            # Vectorstore and database loaded successfully

            # Find related papers
            related_papers = self._find_related_papers(
                paper_content,
                max_results
            )

            # Return output that matches the outputSchema exactly
            return {
                "status": "success",  # Must match schema: status field
                "input_paper": paper_content,  # Must match schema: input_paper field
                "related_papers": related_papers,  # Must match schema: related_papers field
                "total_papers_analyzed": len(self.papers_database),  # Must match schema: total_papers_analyzed field
                "max_results": max_results,  # Must match schema: max_results field

                "vectorstore_loaded": self.vectorstore is not None,  # Additional info for debugging
                "papers_database_size": len(self.papers_database)  # Additional info for debugging
            }

        except Exception as e:
            logger.error(f"Error executing Paper Analysis agent: {e}")

            return {
                "status": "error",  # Must match schema: status field
                "message": f"Execution failed: {str(e)}",  # Must match schema: message field
                "input_paper": input_data.get("paper_content", "Error: Invalid input"),
                # Must match schema: input_paper field
                "related_papers": [],  # Must match schema: related_papers field
                "total_papers_analyzed": 0,  # Must match schema: total_papers_analyzed field
                "max_results": input_data.get("max_results", 10),  # Must match schema: max_results field

                "vectorstore_loaded": False,  # Additional info for debugging
                "papers_database_size": 0  # Additional info for debugging
            }

    def cleanup(self) -> Dict[str, Any]:
        """
        Clean up agent resources.
        
        This method is called by the platform when the agent is no longer needed.
        It should:
        1. Clean up any resources (files, connections, etc.)
        2. Clear instance variables
        3. Clear state (platform will handle persistence)
        4. Optionally clean up disk storage
        
        Returns:
            Dict with cleanup result (no platform concerns)
        """
        try:
            logger.info("Cleaning up Paper Analysis agent resources")

            # Clear state (platform will handle persistence)
            self._state.clear()
            self._initialized = False

            return {
                "status": "success",  # Must match schema enum: ["success", "error"]
                "message": "Agent resources cleaned up successfully",
                "resources_freed": ["vectorstore", "llm", "papers_database", "paper_list_content", "papers_processed",
                                    "total_embeddings", "model_name", "temperature", "chunk_size", "chunk_overlap"]
                # Must match schema: list of resources freed
            }
        except Exception as e:
            logger.error(f"Error cleaning up Paper Analysis agent: {e}")
            return {
                "status": "error",  # Must match schema enum: ["success", "error"]
                "message": f"Cleanup failed: {str(e)}",  # Must match schema: message field
                "resources_freed": []  # Must match schema: list of resources freed
            }

    def _extract_papers_metadata(self, content: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract paper titles and authors from content using OpenAI Structured Outputs."""
        try:
            # Check for API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")

            # Initialize OpenAI client
            client = OpenAI(api_key=api_key)

            # Get model name from config
            model_name = config.get("model_name", "gpt-4o-mini")
            temperature = config.get("temperature", 0)

            prompt = f"""
            Extract paper titles and authors from the following content. 
            Return the result as a JSON object with a "papers" array containing paper objects.
            
            Content to analyze:
            {content[:8000]}  # Limit content length for LLM processing
            
            Each paper should have a title and authors list.
            """

            try:
                # Use OpenAI Structured Outputs with Pydantic model
                completion = client.chat.completions.parse(
                    model=model_name,
                    messages=[
                        {"role": "system",
                         "content": "You are an expert at extracting structured paper metadata from text content."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format=PaperMetadataList,
                    temperature=temperature
                )

                # Get the parsed, validated data
                papers_data = completion.choices[0].message.parsed
                logger.info(
                    f"Successfully extracted metadata for {len(papers_data.papers)} papers using Structured Outputs")

                # Convert Pydantic models to dictionaries for compatibility
                return [paper.model_dump() for paper in papers_data.papers]

            except Exception as structured_error:
                logger.warning(f"Structured Outputs failed, falling back to JSON mode: {structured_error}")

                # Fallback to JSON mode for older models
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system",
                         "content": "You are an expert at extracting structured paper metadata. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=temperature
                )

                response_text = response.choices[0].message.content.strip()

                # Parse JSON response
                try:
                    response_data = json.loads(response_text)

                    # Handle different response formats
                    if "papers" in response_data:
                        papers_data = response_data["papers"]
                    elif isinstance(response_data, list):
                        papers_data = response_data
                    else:
                        # Try to find papers array in the response
                        papers_data = response_data.get("papers", [])

                    logger.info(
                        f"Successfully extracted metadata for {len(papers_data)} papers using JSON mode fallback")
                    return papers_data

                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse JSON response: {e}")

        except Exception as e:
            logger.error(f"Error extracting papers metadata: {e}")
            raise

    def _enrich_papers_with_research_data(self, papers_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich papers with additional research data from APIs."""
        enriched_papers = []

        for paper in papers_metadata:
            try:
                title = paper.get("title", "")
                authors = paper.get("authors", [])

                if not title:
                    continue

                # Create base paper entry using Pydantic model
                enriched_paper = EnrichedPaper(
                    title=title,
                    authors=authors,
                    abstract="",
                    url="",
                    source="manual_extraction"
                )

                # Try to enrich with research data
                try:
                    # Try ArXiv first
                    arxiv_results = self._search_arxiv(title)
                    if arxiv_results:
                        # Update the Pydantic model with ArXiv data
                        if "abstract" in arxiv_results:
                            enriched_paper.abstract = arxiv_results["abstract"]
                        if "url" in arxiv_results:
                            enriched_paper.url = arxiv_results["url"]
                        if "arxiv_id" in arxiv_results:
                            enriched_paper.arxiv_id = arxiv_results["arxiv_id"]
                        if "year" in arxiv_results:
                            enriched_paper.year = arxiv_results["year"]
                        enriched_paper.source = "arxiv"
                    else:
                        # Try Semantic Scholar
                        scholar_results = self._search_semantic_scholar(title)
                        if scholar_results:
                            # Update the Pydantic model with Semantic Scholar data
                            if "abstract" in scholar_results:
                                enriched_paper.abstract = scholar_results["abstract"]
                            if "url" in scholar_results:
                                enriched_paper.url = scholar_results["url"]
                            if "doi" in scholar_results:
                                enriched_paper.doi = scholar_results["doi"]
                            if "year" in scholar_results:
                                enriched_paper.year = scholar_results["year"]
                            if "venue" in scholar_results:
                                enriched_paper.venue = scholar_results["venue"]
                            enriched_paper.source = "semantic_scholar"
                except Exception as e:
                    logger.warning(f"Failed to enrich paper '{title}' with research data: {e}")

                # Convert Pydantic model to dictionary for compatibility
                enriched_papers.append(enriched_paper.model_dump())

            except Exception as e:
                logger.error(f"Error enriching paper: {e}")
                continue

        logger.info(f"Enriched {len(enriched_papers)} papers with research data")
        return enriched_papers

    def _search_arxiv(self, title: str) -> Optional[Dict[str, Any]]:
        """Search for paper on ArXiv."""
        try:
            # Search ArXiv for the paper
            search = arxiv.Search(
                query=title,
                max_results=1,
                sort_by=arxiv.SortCriterion.Relevance
            )

            for result in search.results():
                return {
                    "abstract": result.summary,
                    "url": result.entry_id,
                    "publication_date": result.published.strftime("%Y-%m-%d") if result.published else ""
                }

            return None

        except Exception as e:
            logger.warning(f"ArXiv search failed for '{title}': {e}")
            return None

    def _search_semantic_scholar(self, title: str) -> Optional[Dict[str, Any]]:
        """Search for paper on Semantic Scholar."""
        try:
            # Search Semantic Scholar for the paper
            search_query = scholarly.search_pubs(title)
            result = next(search_query, None)

            if result:
                return {
                    "abstract": result.get('bib', {}).get('abstract', ''),
                    "url": result.get('pub_url', ''),
                    "publication_date": result.get('bib', {}).get('pub_year', '')
                }

            return None

        except Exception as e:
            logger.warning(f"Semantic Scholar search failed for '{title}': {e}")
            return None

    def _create_vector_embeddings(self, papers: List[Dict[str, Any]], config: Dict[str, Any]) -> int:
        """Create vector embeddings for papers and store in FAISS."""
        try:
            # Check for OpenAI API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")

            # Prepare documents for embedding
            documents = []
            for paper in papers:
                # Create text representation of the paper
                paper_text = f"Title: {paper.get('title', '')}\n"
                paper_text += f"Authors: {', '.join(paper.get('authors', []))}\n"
                paper_text += f"Abstract: {paper.get('abstract', '')}"

                documents.append(Document(
                    page_content=paper_text,
                    metadata={"paper_id": len(documents)}
                ))

            # Split text into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=config.get("chunk_size", 1000),
                chunk_overlap=config.get("chunk_overlap", 200)
            )

            split_docs = text_splitter.split_documents(documents)
            logger.info(f"Split papers into {len(split_docs)} chunks")

            # Create embeddings and vectorstore
            embeddings = OpenAIEmbeddings(openai_api_key=api_key)
            vectorstore = FAISS.from_documents(split_docs, embeddings)

            # Store vectorstore for later use
            self.vectorstore = vectorstore

            return len(split_docs)

        except Exception as e:
            logger.error(f"Error creating vector embeddings: {e}")
            raise

    def _convert_numpy_types(self, obj):
        """Convert numpy types to Python native types for JSON serialization."""
        import numpy as np
        
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        else:
            return obj

    def _find_related_papers(self, paper_content: str, max_results: int) -> List[
        Dict[str, Any]]:
        """Find related papers using vector similarity search."""
        try:
            if not self.vectorstore:
                raise ValueError("Vector store not initialized. Please run initialize() first.")

            logger.info(f"Starting similarity search with vectorstore containing {len(self.papers_database)} papers")

            # Search for similar papers with scores
            logger.info(f"Searching for similar papers (max: {max_results})...")
            similar_docs_with_scores = self.vectorstore.similarity_search_with_score(
                paper_content,
                k=max_results  # Get exactly the number of results requested
            )
            logger.info(f"Found {len(similar_docs_with_scores)} similar documents from vectorstore")

            # Process results - papers are already ordered by similarity from FAISS
            related_papers = []
            seen_paper_ids = set()

            for doc, score in similar_docs_with_scores:
                paper_id = doc.metadata.get("paper_id", 0)

                # Avoid duplicates
                if paper_id in seen_paper_ids:
                    continue

                seen_paper_ids.add(paper_id)

                # Get paper data
                if paper_id < len(self.papers_database):
                    paper = self.papers_database[paper_id]

                    # Use the actual FAISS similarity score (already normalized)
                    similarity_score = float(score)  # Convert numpy.float32 to Python float

                    paper_data = {
                        "title": paper.get("title", ""),
                        "authors": paper.get("authors", []),
                        "abstract": paper.get("abstract", ""),
                        "similarity_score": round(similarity_score, 3),
                        "url": paper.get("url", ""),
                        "source": paper.get("source", ""),
                        "paper_id": int(paper_id)  # Ensure paper_id is Python int
                    }
                    
                    # Convert any numpy types to Python native types
                    paper_data = self._convert_numpy_types(paper_data)
                    related_papers.append(paper_data)

                    if len(related_papers) >= max_results:
                        break
                else:
                    logger.warning(
                        f"Paper ID {paper_id} not found in database (database size: {len(self.papers_database)})")

            # Results are already ordered by similarity from FAISS
            # No need to sort again as FAISS returns them in order

            logger.info(f"Found {len(related_papers)} related papers")
            return related_papers

        except Exception as e:
            logger.error(f"Error finding related papers: {e}")
            raise

    def _load_papers_database_from_disk(self) -> None:
        """Load the papers database from disk using dynamic path calculation."""
        try:
            papers_database_path = self._get_papers_database_path()
            index_path = self._get_index_path()
            
            logger.info(f"Loading from calculated paths:")
            logger.info(f"  Papers database: {papers_database_path}")
            logger.info(f"  FAISS index: {index_path}")
            
            # Check if both files exist
            if not papers_database_path.exists():
                raise ValueError(f"Papers database not found at {papers_database_path}")
            
            if not index_path.exists():
                raise ValueError(f"FAISS index not found at {index_path}")
            
            # Load papers database
            with open(papers_database_path, 'r') as f:
                self.papers_database = json.load(f)
            logger.info(f"Loaded papers database with {len(self.papers_database)} papers")
            
            # Load FAISS index
            embeddings = OpenAIEmbeddings()
            self.vectorstore = FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
            logger.info(f"Loaded FAISS index successfully")
            
        except Exception as e:
            logger.error(f"Failed to load papers database from disk: {e}")
            raise ValueError(f"Failed to load papers database from disk: {e}")

    def extract_papers_with_structured_outputs(self, content: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Demonstrate the new Structured Outputs approach for paper extraction.
        This method shows how to use Pydantic models with OpenAI's structured outputs.
        """
        try:
            # Check for API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")

            # Initialize OpenAI client
            client = OpenAI(api_key=api_key)

            # Get model name from config
            model_name = config.get("model_name", "gpt-4o-mini")
            temperature = config.get("temperature", 0)

            prompt = f"""
            Analyze the following content and extract research paper information.
            Return a structured response with paper details.

            Content to analyze:
            {content[:8000]}

            Focus on identifying research papers, their titles, authors, and any other relevant metadata.
            """

            try:
                # Use OpenAI Structured Outputs with Pydantic model
                completion = client.chat.completions.parse(
                    model=model_name,
                    messages=[
                        {"role": "system",
                         "content": "You are an expert research analyst. Extract structured paper metadata from the given content."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format=PaperMetadataList,
                    temperature=temperature
                )

                # Get the parsed, validated data
                papers_data = completion.choices[0].message.parsed

                result = {
                    "status": "success",
                    "papers": [paper.model_dump() for paper in papers_data.papers],
                    "model_used": model_name,
                }

                logger.info(f"Successfully extracted {len(papers_data.papers)} papers using Structured Outputs")
                return result

            except Exception as structured_error:
                logger.warning(f"Structured Outputs failed: {structured_error}")

                # Return error information
                return {
                    "status": "error",
                    "error": str(structured_error),
                }

        except Exception as e:
            logger.error(f"Error in structured outputs extraction: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


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

    agent = PaperAnalysisAgent()

    # Test initialization
    print("1. Testing initialization...")
    init_result = agent.initialize({
        "paper_list_content": "Paper Title 1\nAuthor1, Author2\nPaper Title 2\nAuthor3, Author4",
        # Replace with actual content
        "model_name": "gpt-4o-mini",
        "temperature": 0,
        "agent_id": "test_paper_agent"
    })
    print(json.dumps(init_result, indent=2))

    if init_result.get("status") == "success":
        # Test the new Structured Outputs approach
        print("\n2. Testing Structured Outputs extraction...")
        structured_result = agent.extract_papers_with_structured_outputs(
            "This paper discusses machine learning algorithms for natural language processing. Authors: Smith, J. and Johnson, A.",
            {"model_name": "gpt-4o-mini", "temperature": 0}
        )
        print(json.dumps(structured_result, indent=2))

        # Test first execution
        print("\n3. Testing first execution...")
        exec_result1 = agent.execute({
            "paper_content": "This paper discusses machine learning algorithms for natural language processing.",
            "max_results": 5
        })
        print(json.dumps(exec_result1, indent=2))

        # Test second execution (should use same state and loaded database)
        print("\n4. Testing second execution...")
        exec_result2 = agent.execute({
            "paper_content": "Research on deep learning approaches for computer vision.",
            "max_results": 3
        })
        print(json.dumps(exec_result2, indent=2))

        # Test cleanup
        print("\n4. Testing cleanup...")
        cleanup_result = agent.cleanup()
        print(json.dumps(cleanup_result, indent=2))

    print("\n=== Local testing completed ===")
    print("Note: The platform will call these methods directly and handle all platform concerns")
else:
    print("Paper Analysis agent loaded. The platform will use Docker exec to run agent methods.")
    print("Set RUN_LOCAL_TESTING=true to run local testing.")
