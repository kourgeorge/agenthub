#!/usr/bin/env python3
"""
ACL Review Agent - An agent that downloads academic papers, analyzes them, and generates comprehensive ACL ARR reviews.
"""

import json
import os
import re
import tempfile
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import getpass

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import dotenv
import openreview
import openreview.tools
import arxiv
import PyPDF2
import fitz  # PyMuPDF

try:
    from scholarly import scholarly
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from semanticscholar import SemanticScholar
    ARXIV_AVAILABLE = True
    NLTK_AVAILABLE = True
    OPENREVIEW_AVAILABLE = True
    SEMANTIC_SCHOLAR_AVAILABLE = False
except ImportError:
    ARXIV_AVAILABLE = False
    NLTK_AVAILABLE = False
    OPENREVIEW_AVAILABLE = False
    SEMANTIC_SCHOLAR_AVAILABLE = False
    print("Warning: Some dependencies not available. Some features may be limited.")

# Import prompts
from prompts import *
from consts import (
    OPENAI_DEFAULT_MODEL, OPENAI_DEFAULT_MAX_TOKENS, OPENAI_DEFAULT_TEMPERATURE,
    MAX_PAPER_SUMMARY_CHARS, MAX_SECTION_CHARS, MAX_BEST_PAPER_JUSTIFICATION_CHARS, MAX_CITED_PAPERS_CONTENT_CHARS,
    DEFAULT_REVIEW_DEPTH, MIN_REVIEW_DEPTH, MAX_REVIEW_DEPTH, LITERATURE_QUERIES_PER_DEPTH, MAX_SIMILAR_PAPERS, MAX_OPENREVIEW_REVIEWS,
    CONFIDENCE_MIN, CONFIDENCE_MAX, SOUNDNESS_MIN, SOUNDNESS_MAX, OVERALL_ASSESSMENT_MIN, OVERALL_ASSESSMENT_MAX,
    NOVELTY_MIN, NOVELTY_MAX, NOVELTY_DEFAULT, TITLE_SIMILARITY_THRESHOLD, FALLBACK_TOP_WORDS, FALLBACK_WORD_MIN_LENGTH,
    MAX_TFIDF_TEXTS, MAX_TFIDF_FEATURES, LITERATURE_QUERY_ROUNDS
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """Represents an academic paper"""
    title: str
    authors: List[str]
    abstract: str
    content: str
    url: str
    venue: Optional[str]
    year: Optional[int]
    keywords: List[str]
    references: List[str]
    citations: Optional[int]


@dataclass
class LiteratureReview:
    """Represents literature review findings"""
    related_papers: List[Dict[str, Any]]
    novelty_score: float
    contribution_analysis: Dict[str, Any]
    gaps_identified: List[str]
    methodology_comparison: Dict[str, Any]
    similar_papers: List[Dict[str, Any]]
    openreview_reviews: List[Dict[str, Any]]
    semantic_scholar_papers: List[Dict[str, Any]]
    cited_papers: List[Dict[str, Any]]  # NEW FIELD


@dataclass
class ACLReview:
    """Represents an ACL ARR review"""
    paper_summary: str
    strengths: str
    weaknesses: str
    comments_suggestions: str
    confidence: int
    soundness: float
    overall_assessment: float
    best_paper: str
    best_paper_justification: str
    literature_review: LiteratureReview
    additional_insights: Dict[str, Any]


class ACLReviewAgent:
    """ACL Review agent that analyzes papers and generates comprehensive reviews"""

    def __init__(self):
        """Initialize the ACL Review Agent"""
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.semantic_scholar_key = os.getenv("SEMANTIC_SCHOLAR_KEY")  # Optional
        self.openreview_username = os.getenv("OPENREVIEW_USERNAME")
        self.openreview_password = os.getenv("OPENREVIEW_PASSWORD")

        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY environment variable is required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = OpenAI(api_key=self.openai_api_key)
        
        # Initialize Semantic Scholar client (works with or without API key)
        if SEMANTIC_SCHOLAR_AVAILABLE:
            self.semantic_scholar = SemanticScholar(api_key=self.semantic_scholar_key)
            if self.semantic_scholar_key:
                logger.info("Semantic Scholar API key provided - using enhanced rate limits")
            else:
                logger.info("No Semantic Scholar API key - using shared rate limits")
        
        # Initialize OpenReview client
        if OPENREVIEW_AVAILABLE and self.openreview_username and self.openreview_password:
            try:
                self.openreview_client = openreview.api.OpenReviewClient(
                    baseurl='https://api2.openreview.net',
                    username=self.openreview_username,
                    password=self.openreview_password
                )
            except Exception as e:
                logger.warning(f"Failed to initialize OpenReview client: {e}")
                self.openreview_client = None
        else:
            self.openreview_client = None
        
        # Load ARR guidelines
        self.arr_guidelines = self.load_arr_guidelines()
        self.arr_form = self.load_arr_form()
        
        # Load prompts
        from prompts import (
            LITERATURE_QUERIES_PROMPT, KEY_TERMS_PROMPT, CITED_PAPERS_PROMPT,
            CONTRIBUTIONS_ANALYSIS_PROMPT, GAPS_ANALYSIS_PROMPT, METHODOLOGY_COMPARISON_PROMPT,
            PAPER_SUMMARY_PROMPT, STRENGTHS_PROMPT, WEAKNESSES_PROMPT, COMMENTS_SUGGESTIONS_PROMPT,
            RATINGS_PROMPT, BEST_PAPER_PROMPT, ADDITIONAL_INSIGHTS_PROMPT, REVIEWER_STYLE_PROMPT,
            LITERATURE_INFO_TEMPLATE, LITERATURE_REVIEW_NOT_PERFORMED
        )
        
        # Store prompts as instance variables
        self.LITERATURE_QUERIES_PROMPT = LITERATURE_QUERIES_PROMPT
        self.KEY_TERMS_PROMPT = KEY_TERMS_PROMPT
        self.CITED_PAPERS_PROMPT = CITED_PAPERS_PROMPT
        self.CONTRIBUTIONS_ANALYSIS_PROMPT = CONTRIBUTIONS_ANALYSIS_PROMPT
        self.GAPS_ANALYSIS_PROMPT = GAPS_ANALYSIS_PROMPT
        self.METHODOLOGY_COMPARISON_PROMPT = METHODOLOGY_COMPARISON_PROMPT
        self.PAPER_SUMMARY_PROMPT = PAPER_SUMMARY_PROMPT
        self.STRENGTHS_PROMPT = STRENGTHS_PROMPT
        self.WEAKNESSES_PROMPT = WEAKNESSES_PROMPT
        self.COMMENTS_SUGGESTIONS_PROMPT = COMMENTS_SUGGESTIONS_PROMPT
        self.RATINGS_PROMPT = RATINGS_PROMPT
        self.BEST_PAPER_PROMPT = BEST_PAPER_PROMPT
        self.ADDITIONAL_INSIGHTS_PROMPT = ADDITIONAL_INSIGHTS_PROMPT
        self.REVIEWER_STYLE_PROMPT = REVIEWER_STYLE_PROMPT
        self.LITERATURE_INFO_TEMPLATE = LITERATURE_INFO_TEMPLATE
        self.LITERATURE_REVIEW_NOT_PERFORMED = LITERATURE_REVIEW_NOT_PERFORMED
        
        # Download NLTK data if available
        if NLTK_AVAILABLE:
            try:
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
            except:
                pass

    def call_openai(self, prompt: str, max_tokens: int = OPENAI_DEFAULT_MAX_TOKENS, temperature: float = OPENAI_DEFAULT_TEMPERATURE, model: str = OPENAI_DEFAULT_MODEL) -> str:
        """Make a call to OpenAI API with standardized parameters"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise e

    def download_paper(self, url: str) -> Optional[Paper]:
        """Download and parse paper from URL"""
        try:
            if 'arxiv.org' in url:
                return self.download_arxiv_paper(url)
            elif 'aclweb.org' in url or 'aclanthology.org' in url:
                return self.download_acl_paper(url)
            else:
                return self.download_generic_paper(url)
        except Exception as e:
            logger.error(f"Error downloading paper: {e}")
            return None

    def download_arxiv_paper(self, url: str) -> Optional[Paper]:
        """Download paper from arXiv with metadata from abstract page"""
        try:
            # Extract arXiv ID from URL (handle both PDF and abs URLs)
            arxiv_id = url.split('/')[-1]
            if arxiv_id.endswith('.pdf'):
                arxiv_id = arxiv_id[:-4]
            
            # Construct abstract page URL
            abs_url = f"https://arxiv.org/abs/{arxiv_id}"
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
            
            logger.info(f"Downloading arXiv paper {arxiv_id} from abstract page: {abs_url}")
            
            # Download abstract page for metadata
            response = requests.get(abs_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = f"arXiv Paper {arxiv_id}"  # Default fallback
            title_elem = soup.find('h1', {'class': 'title'})
            if title_elem:
                # Remove Title: prefix if present
                title_text = title_elem.get_text().strip()
                if title_text.startswith('Title:'):
                    title = title_text[6:].strip()
                else:
                    title = title_text
            
            # Extract authors
            authors = ["Unknown"] # Default fallback
            authors_elem = soup.find('div', {'class': 'authors'})
            if authors_elem:
                author_links = authors_elem.find_all('a')
                for link in author_links:
                    author_name = link.get_text().strip()
                    if author_name and author_name != "Authors:":
                        authors.append(author_name)
            
            # Extract abstract
            abstract = "Abstract not available"  # Default fallback
            abstract_elem = soup.find('blockquote', {'class': 'abstract'})
            if abstract_elem:
                abstract_text = abstract_elem.get_text().strip()
                if abstract_text.startswith('Abstract:'):
                    abstract = abstract_text[9:].strip()
                else:
                    abstract = abstract_text
            
            # Extract submission date and other metadata
            submission_date = None
            subjects = []
            
            # Look for submission date
            date_elem = soup.find('div', {'class': 'dateline'})
            if date_elem:
                date_text = date_elem.get_text()
                # Extract year from date text
                import re
                year_match = re.search(r'(\d{4})', date_text)
                if year_match:
                    submission_date = int(year_match.group(1))
            
            # Extract subjects/categories
            subjects_elem = soup.find('td', {'class': 'tablecell subjects'})
            if subjects_elem:
                subjects_text = subjects_elem.get_text().strip()
                subjects = [s.strip() for s in subjects_text.split(';') if s.strip()]
            
            # Download PDF content for full text
            logger.info(f"Downloading PDF content from: {pdf_url}")
            pdf_bytes = self.download_pdf_bytes(pdf_url)
            content = ""
            
            if pdf_bytes:
                # Save to temporary file for text extraction
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                    tmp_file.write(pdf_bytes)
                    tmp_file.flush()
                    
                    # Extract text from PDF
                    content = self.extract_pdf_text(tmp_file.name)
                    
                    # Clean up
                    os.unlink(tmp_file.name)
            else:
                logger.warning("Failed to download PDF content, using abstract only")
                content = abstract
            
            return Paper(
                title=title,
                authors=authors,
                abstract=abstract,
                content=content,
                url=abs_url,  # Use abstract URL as primary URL
                venue="arXiv",
                year=submission_date,
                keywords=subjects,
                references=[],
                citations=None
            )
            
        except Exception as e:
            logger.error(f"Error downloading arXiv paper: {e}")
            return None

    def download_acl_paper(self, url: str) -> Optional[Paper]:
        """Download paper from ACL Anthology"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title_elem = soup.find('h1', {'id': 'title'})
            title = title_elem.get_text().strip() if title_elem else "Unknown Title"
            
            # Extract authors
            authors_elem = soup.find('div', {'class': 'authors'})
            authors = []
            if authors_elem:
                author_links = authors_elem.find_all('a')
                authors = [link.get_text().strip() for link in author_links]
            
            # Extract abstract
            abstract_elem = soup.find('div', {'class': 'abstract'})
            abstract = abstract_elem.get_text().strip() if abstract_elem else ""
            
            # Try to find PDF link
            pdf_link = soup.find('a', {'href': re.compile(r'\.pdf$')})
            content = ""
            if pdf_link:
                pdf_url = urllib.parse.urljoin(url, pdf_link['href'])
                content = self.download_pdf_content(pdf_url)
            
            return Paper(
                title=title,
                authors=authors,
                abstract=abstract,
                content=content,
                url=url,
                venue="ACL",
                year=None,
                keywords=[],
                references=[],
                citations=None
            )
            
        except Exception as e:
            logger.error(f"Error downloading ACL paper: {e}")
            return None

    def download_generic_paper(self, url: str) -> Optional[Paper]:
        """Download paper from generic URL"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            # Try to extract PDF content
            content = ""
            if url.endswith('.pdf'):
                content = self.download_pdf_content(url)
            
            # Extract basic info from HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.find('title')
            title = title.get_text().strip() if title else "Unknown Title"
            
            return Paper(
                title=title,
                authors=[],
                abstract="",
                content=content,
                url=url,
                venue=None,
                year=None,
                keywords=[],
                references=[],
                citations=None
            )
            
        except Exception as e:
            logger.error(f"Error downloading generic paper: {e}")
            return None

    def download_pdf_content(self, pdf_url: str) -> str:
        """Download and extract text from PDF"""
        try:
            response = requests.get(pdf_url)
            response.raise_for_status()
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_file.flush()
                
                content = self.extract_pdf_text(tmp_file.name)
                
                # Clean up
                os.unlink(tmp_file.name)
                
                return content
                
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return ""

    def download_pdf_bytes(self, pdf_url: str) -> bytes:
        """Download PDF as raw bytes"""
        try:
            response = requests.get(pdf_url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error downloading PDF bytes: {e}")
            return b""

    def extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            # Try PyMuPDF first (better text extraction)
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except:
            try:
                # Fallback to PyPDF2
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
                    return text
            except Exception as e:
                logger.error(f"Error extracting PDF text: {e}")
                return ""

    def search_web(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Search the web using Serper API"""
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": num_results
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "domain": item.get("displayLink", "")
                })

            return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def perform_literature_review(self, paper: Paper, depth: int = DEFAULT_REVIEW_DEPTH) -> LiteratureReview:
        """Perform comprehensive literature review"""
        logger.info("Performing literature review...")
        
        # Initialize default values
        related_papers = []
        all_abstracts = []
        similar_papers = []
        openreview_reviews = []
        semantic_scholar_papers = []
        cited_papers = []
        
        try:
            # Generate search queries based on paper content
            search_queries = self.generate_literature_queries(paper, depth)
            
            # Web search for related papers
            for query in search_queries:
                logger.info(f"Web searching: {query}")
                try:
                    results = self.search_web(query, 5)
                    
                    for result in results:
                        if any(domain in result['url'] for domain in ['arxiv.org', 'aclweb.org', 'aclanthology.org', 'scholar.google.com']):
                            paper_info = {
                                'title': result['title'],
                                'snippet': result['snippet'],
                                'url': result['url'],
                                'relevance_score': self.calculate_relevance(paper, result),
                                'source': 'Web Search'
                            }
                            related_papers.append(paper_info)
                            all_abstracts.append(result['snippet'])
                except Exception as e:
                    logger.error(f"Error in web search for query '{query}': {e}")
                    continue
            
            # Find most similar papers using multiple sources
            logger.info("Finding most similar papers...")
            try:
                similar_papers = self.find_most_similar_papers(paper, MAX_SIMILAR_PAPERS)
                all_abstracts.extend([p.get('abstract', '') for p in similar_papers])
            except Exception as e:
                logger.error(f"Error finding similar papers: {e}")
            
            # Get OpenReview reviews for similar papers
            logger.info("Searching OpenReview for similar reviews...")
            try:
                openreview_reviews = self.get_openreview_reviews(paper.title, MAX_OPENREVIEW_REVIEWS)
            except Exception as e:
                logger.error(f"Error getting OpenReview reviews: {e}")
            
            # Get Semantic Scholar papers
            logger.info("Searching Semantic Scholar...")
            try:
                for query in search_queries[:2]:  # Use first 2 queries
                    semantic_papers = self.search_semantic_scholar(query, 5)
                    semantic_scholar_papers.extend(semantic_papers)
            except Exception as e:
                logger.error(f"Error searching Semantic Scholar: {e}")
            
            # Extract cited papers from the paper content
            try:
                cited_papers = self.extract_cited_papers(paper.content)
            except Exception as e:
                logger.error(f"Error extracting cited papers: {e}")
            
        except Exception as e:
            logger.error(f"Error in literature review: {e}")
        
        # Analyze novelty (with fallback)
        try:
            novelty_score = self.analyze_novelty(paper, all_abstracts)
        except Exception as e:
            logger.error(f"Error analyzing novelty: {e}")
            novelty_score = 0.5  # Default fallback
        
        # Analyze contributions (with fallback)
        try:
            contribution_analysis = self.analyze_contributions(paper)
        except Exception as e:
            logger.error(f"Error analyzing contributions: {e}")
            contribution_analysis = {"contributions": ["Analysis failed due to API limits"], "significance": "medium"}
        
        # Identify gaps (with fallback)
        try:
            gaps_identified = self.identify_gaps(paper, related_papers + similar_papers)
        except Exception as e:
            logger.error(f"Error identifying gaps: {e}")
            gaps_identified = ["Gap analysis failed due to API limits"]
        
        # Compare methodologies (with fallback)
        try:
            methodology_comparison = self.compare_methodologies(paper, related_papers + similar_papers)
        except Exception as e:
            logger.error(f"Error comparing methodologies: {e}")
            methodology_comparison = {"comparison": "Methodology comparison failed due to API limits"}
        
        # Ensure we don't exceed list limits
        max_papers = 10
        related_papers = related_papers[:max_papers] if related_papers else []
        similar_papers = similar_papers[:max_papers] if similar_papers else []
        semantic_scholar_papers = semantic_scholar_papers[:max_papers] if semantic_scholar_papers else []
        
        return LiteratureReview(
            related_papers=related_papers,
            novelty_score=novelty_score,
            contribution_analysis=contribution_analysis,
            gaps_identified=gaps_identified,
            methodology_comparison=methodology_comparison,
            similar_papers=similar_papers,
            openreview_reviews=openreview_reviews,
            semantic_scholar_papers=semantic_scholar_papers,
            cited_papers=cited_papers
        )

    def generate_literature_queries(self, paper: Paper, depth: int) -> List[str]:
        """Generate search queries for literature review using LLM"""
        try:
            prompt = self.LITERATURE_QUERIES_PROMPT.format(
                title=paper.title,
                abstract=paper.abstract,
                authors=', '.join(paper.authors) if paper.authors else 'Unknown',
                depth=depth * LITERATURE_QUERIES_PER_DEPTH
            )

            content = self.call_openai(prompt)
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            queries = json.loads(content)
            
            # Ensure we have the basic paper title query
            if f'"{paper.title}"' not in queries:
                queries.insert(0, f'"{paper.title}"')
            
            # Limit to requested depth
            return queries[:depth * LITERATURE_QUERIES_PER_DEPTH]
            
        except Exception as e:
            logger.error(f"Error generating literature queries with LLM: {e}")
            # Fallback to basic queries
            queries = [f'"{paper.title}"']
            
            # Add author-based queries
            if paper.authors:
                for author in paper.authors[:2]:
                    queries.append(f'"{author}" "research" "NLP"')
            
            return queries[:depth * LITERATURE_QUERIES_PER_DEPTH]

    def extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text using LLM"""
        try:
            prompt = self.KEY_TERMS_PROMPT.format(text=text)

            content = self.call_openai(prompt)
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Error extracting key terms with LLM: {e}")
            # Fallback to simple extraction
            try:
                words = word_tokenize(text.lower())
                stop_words = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
                words = [word for word in words if word.isalpha() and word not in stop_words and len(word) > 3]
                from collections import Counter
                word_freq = Counter(words)
                return [word for word, freq in word_freq.most_common(10)]
            except:
                return []

    def extract_cited_papers(self, content: str) -> List[Dict[str, Any]]:
        """Extract cited papers from the paper content using LLM"""
        try:
            prompt = self.CITED_PAPERS_PROMPT.format(content=content[:MAX_CITED_PAPERS_CONTENT_CHARS])  # Truncate to avoid token limits

            content = self.call_openai(prompt)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error extracting cited papers with LLM: {e}")
            return []

    def calculate_relevance(self, paper: Paper, result: Dict[str, Any]) -> float:
        """Calculate relevance score between paper and search result"""
        try:
            # Simple TF-IDF based similarity
            texts = [paper.abstract, result['snippet']]
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except:
            return 0.0

    def analyze_novelty(self, paper: Paper, related_abstracts: List[str]) -> float:
        """Analyze novelty of the paper"""
        try:
            # Combine all related abstracts
            all_text = " ".join(related_abstracts)
            
            # Calculate similarity between paper and related work
            texts = [paper.abstract, all_text]
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Novelty is inverse of similarity
            novelty = 1.0 - similarity
            return max(0.0, min(1.0, novelty))
        except:
            return 0.5

    def analyze_contributions(self, paper: Paper) -> Dict[str, Any]:
        """Analyze contributions of the paper"""
        try:
            prompt = self.CONTRIBUTIONS_ANALYSIS_PROMPT.format(
                title=paper.title,
                abstract=paper.abstract
            )

            content = self.call_openai(prompt)
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            return json.loads(content)
        except Exception as e:
            logger.error(f"Error analyzing contributions: {e}")
            return {
                "novelty": {"score": 3, "explanation": "Unable to analyze"},
                "technical": {"score": 3, "explanation": "Unable to analyze"},
                "empirical": {"score": 3, "explanation": "Unable to analyze"},
                "practical": {"score": 3, "explanation": "Unable to analyze"},
                "theoretical": {"score": 3, "explanation": "Unable to analyze"}
            }

    def identify_gaps(self, paper: Paper, related_papers: List[Dict[str, Any]]) -> List[str]:
        """Identify research gaps addressed by the paper"""
        try:
            related_summary = "\n".join([f"- {p['title']}: {p['snippet']}" for p in related_papers[:5]])
            
            prompt = self.GAPS_ANALYSIS_PROMPT.format(
                title=paper.title,
                abstract=paper.abstract,
                related_summary=related_summary
            )

            content = self.call_openai(prompt)
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            return json.loads(content)
        except Exception as e:
            logger.error(f"Error identifying gaps: {e}")
            return ["Unable to identify specific gaps"]

    def compare_methodologies(self, paper: Paper, related_papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare methodologies with related work"""
        try:
            related_summary = "\n".join([f"- {p['title']}: {p['snippet']}" for p in related_papers[:5]])
            
            prompt = self.METHODOLOGY_COMPARISON_PROMPT.format(
                title=paper.title,
                abstract=paper.abstract,
                related_summary=related_summary
            )

            content = self.call_openai(prompt)
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            return json.loads(content)
        except Exception as e:
            logger.error(f"Error comparing methodologies: {e}")
            return {
                "differences": "Unable to analyze",
                "advantages": "Unable to analyze",
                "limitations": "Unable to analyze",
                "comparison": "Unable to analyze"
            }

    def generate_acl_review(self, paper: Paper, literature_review: LiteratureReview, reviewer_style_summary: str = "") -> ACLReview:
        """Generate comprehensive ACL ARR review, optionally using reviewer style"""
        logger.info("Generating ACL review...")
        
        # Use reviewer_style_summary in prompts if available
        style_note = f"\nReviewer Style Guidance:\n{reviewer_style_summary}\n" if reviewer_style_summary else ""
        
        # Generate each section using ARR guidelines
        paper_summary = self.generate_paper_summary(paper, style_note)
        strengths = self.generate_strengths(paper, literature_review, style_note)
        weaknesses = self.generate_weaknesses(paper, literature_review, style_note)
        comments_suggestions = self.generate_comments_suggestions(paper, style_note)
        
        # Generate ratings
        confidence, soundness, overall_assessment = self.generate_ratings(paper, literature_review)
        best_paper, best_paper_justification = self.assess_best_paper(paper, literature_review)
        
        # Generate additional insights
        additional_insights = self.generate_additional_insights(paper, literature_review)
        
        return ACLReview(
            paper_summary=paper_summary,
            strengths=strengths,
            weaknesses=weaknesses,
            comments_suggestions=comments_suggestions,
            confidence=confidence,
            soundness=soundness,
            overall_assessment=overall_assessment,
            best_paper=best_paper,
            best_paper_justification=best_paper_justification,
            literature_review=literature_review,
            additional_insights=additional_insights
        )

    def generate_paper_summary(self, paper: Paper, style_note: str = "") -> str:
        """Generate paper summary"""
        try:
            prompt = self.PAPER_SUMMARY_PROMPT.format(
                style_note=style_note,
                title=paper.title,
                abstract=paper.abstract
            )

            content = self.call_openai(prompt)
            
            return content
        except Exception as e:
            logger.error(f"Error generating paper summary: {e}")
            return f"Error generating paper summary: {e}"

    def generate_strengths(self, paper: Paper, literature_review: LiteratureReview, style_note: str = "") -> str:
        """Generate strengths section"""
        try:
            # Handle case where literature_review is None or has missing attributes
            if literature_review is None:
                literature_info = self.LITERATURE_REVIEW_NOT_PERFORMED
            else:
                novelty_score = getattr(literature_review, 'novelty_score', 'N/A')
                contribution_analysis = getattr(literature_review, 'contribution_analysis', {})
                gaps_identified = getattr(literature_review, 'gaps_identified', [])
                similar_papers = getattr(literature_review, 'similar_papers', [])
                openreview_reviews = getattr(literature_review, 'openreview_reviews', [])
                
                literature_info = self.LITERATURE_INFO_TEMPLATE.format(
                    novelty_score=f"{novelty_score:.2f}" if isinstance(novelty_score, (int, float)) else novelty_score,
                    contribution_analysis=json.dumps(contribution_analysis, indent=2),
                    gaps_identified=gaps_identified,
                    similar_papers_count=len(similar_papers),
                    openreview_count=len(openreview_reviews)
                )

            prompt = self.STRENGTHS_PROMPT.format(
                style_note=style_note,
                arr_guidelines=self.arr_guidelines,
                title=paper.title,
                abstract=paper.abstract,
                literature_info=literature_info
            )

            content = self.call_openai(prompt)
            
            return content
        except Exception as e:
            logger.error(f"Error generating strengths: {e}")
            return f"Error generating strengths: {e}"

    def generate_weaknesses(self, paper: Paper, literature_review: LiteratureReview, style_note: str = "") -> str:
        """Generate weaknesses section"""
        try:
            # Handle case where literature_review is None or has missing attributes
            if literature_review is None:
                literature_info = "Literature Review not performed"
            else:
                novelty_score = getattr(literature_review, 'novelty_score', 'N/A')
                methodology_comparison = getattr(literature_review, 'methodology_comparison', {})
                
                # Format novelty score safely
                novelty_display = f"{novelty_score:.2f}" if isinstance(novelty_score, (int, float)) else str(novelty_score)
                literature_info = f"""Literature Review Findings:
- Novelty Score: {novelty_display}
- Methodology Comparison: {json.dumps(methodology_comparison, indent=2)}"""

            prompt = self.WEAKNESSES_PROMPT.format(
                style_note=style_note,
                title=paper.title,
                abstract=paper.abstract,
                literature_info=literature_info,
                max_chars=MAX_SECTION_CHARS
            )

            content = self.call_openai(prompt)
            
            return content
        except Exception as e:
            logger.error(f"Error generating weaknesses: {e}")
            return f"Error generating weaknesses: {e}"

    def generate_comments_suggestions(self, paper: Paper, style_note: str = "") -> str:
        """Generate comments and suggestions section"""
        try:
            prompt = self.COMMENTS_SUGGESTIONS_PROMPT.format(
                style_note=style_note,
                title=paper.title,
                abstract=paper.abstract,
                max_chars=MAX_SECTION_CHARS
            )

            content = self.call_openai(prompt)
            
            return content
        except Exception as e:
            logger.error(f"Error generating comments: {e}")
            return f"Error generating comments: {e}"

    def generate_ratings(self, paper: Paper, literature_review: LiteratureReview) -> Tuple[int, float, float]:
        """Generate confidence, soundness, and overall assessment ratings"""
        try:
            # Handle case where literature_review is None or has missing attributes
            if literature_review is None:
                literature_info = "Literature Review not performed"
            else:
                novelty_score = getattr(literature_review, 'novelty_score', 'N/A')
                contribution_analysis = getattr(literature_review, 'contribution_analysis', {})
                
                # Format novelty score safely
                novelty_display = f"{novelty_score:.2f}" if isinstance(novelty_score, (int, float)) else str(novelty_score)
                literature_info = f"""Literature Review:
- Novelty Score: {novelty_display}
- Contributions: {json.dumps(contribution_analysis, indent=2)}"""

            prompt = self.RATINGS_PROMPT.format(
                title=paper.title,
                abstract=paper.abstract,
                literature_info=literature_info
            )

            content = self.call_openai(prompt)
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            ratings = json.loads(content)
            return (
                int(ratings.get("confidence", 3)),
                float(ratings.get("soundness", 3.0)),
                float(ratings.get("overall_assessment", 3.0))
            )
        except Exception as e:
            logger.error(f"Error generating ratings: {e}")
            return (3, 3.0, 3.0)

    def assess_best_paper(self, paper: Paper, literature_review: LiteratureReview) -> Tuple[str, str]:
        """Assess if paper merits best paper consideration"""
        try:
            # Handle case where literature_review is None or has missing attributes
            if literature_review is None:
                literature_info = "Literature Review not performed"
            else:
                novelty_score = getattr(literature_review, 'novelty_score', 'N/A')
                contribution_analysis = getattr(literature_review, 'contribution_analysis', {})
                
                # Format novelty score safely
                novelty_display = f"{novelty_score:.2f}" if isinstance(novelty_score, (int, float)) else str(novelty_score)
                literature_info = f"""Literature Review:
- Novelty Score: {novelty_display}
- Contributions: {json.dumps(contribution_analysis, indent=2)}"""

            prompt = self.BEST_PAPER_PROMPT.format(
                title=paper.title,
                abstract=paper.abstract,
                literature_info=literature_info,
                max_chars=MAX_BEST_PAPER_JUSTIFICATION_CHARS
            )

            content = self.call_openai(prompt)
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            result = json.loads(content)
            return (
                result.get("decision", "No"),
                result.get("justification", "")
            )
        except Exception as e:
            logger.error(f"Error assessing best paper: {e}")
            return ("No", "Unable to assess")

    def generate_additional_insights(self, paper: Paper, literature_review: LiteratureReview) -> Dict[str, Any]:
        """Generate additional insights for the reviewer"""
        try:
            # Handle case where literature_review is None or has missing attributes
            if literature_review is None:
                literature_info = "Literature Review not performed"
            else:
                novelty_score = getattr(literature_review, 'novelty_score', 'N/A')
                related_papers = getattr(literature_review, 'related_papers', [])
                gaps_identified = getattr(literature_review, 'gaps_identified', [])
                
                # Format novelty score safely
                novelty_display = f"{novelty_score:.2f}" if isinstance(novelty_score, (int, float)) else str(novelty_score)
                literature_info = f"""Literature Review:
- Novelty Score: {novelty_display}
- Related Papers: {len(related_papers)}
- Gaps Identified: {gaps_identified}"""

            prompt = self.ADDITIONAL_INSIGHTS_PROMPT.format(
                title=paper.title,
                abstract=paper.abstract,
                literature_info=literature_info
            )

            content = self.call_openai(prompt)
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            return json.loads(content)
        except Exception as e:
            logger.error(f"Error generating additional insights: {e}")
            return {"error": str(e)}

    def format_review(self, review: ACLReview) -> str:
        """Format the review in ACL ARR format"""
        # Handle case where literature_review is None or has missing attributes
        if review.literature_review is None:
            literature_summary = """## Literature Review Summary
- Literature review not performed"""
            similar_papers_section = ""
            openreview_section = ""
        else:
            novelty_score = getattr(review.literature_review, 'novelty_score', 'N/A')
            related_papers = getattr(review.literature_review, 'related_papers', [])
            similar_papers = getattr(review.literature_review, 'similar_papers', [])
            openreview_reviews = getattr(review.literature_review, 'openreview_reviews', [])
            semantic_scholar_papers = getattr(review.literature_review, 'semantic_scholar_papers', [])
            gaps_identified = getattr(review.literature_review, 'gaps_identified', [])
            # Format novelty score safely
            novelty_display = f"{novelty_score:.2f}" if isinstance(novelty_score, (int, float)) else str(novelty_score)
            literature_summary = f"""## Literature Review Summary
- Novelty Score: {novelty_display}
- Related Papers Found: {len(related_papers)}
- Most Similar Papers: {len(similar_papers)}
- OpenReview Reviews: {len(openreview_reviews)}
- Semantic Scholar Papers: {len(semantic_scholar_papers)}
- Research Gaps Identified: {len(gaps_identified)}"""
            
            # Add similar papers section
            similar_papers_section = "\n## Most Similar Papers (for Reviewer Reference)\n"
            if similar_papers:
                similar_papers_section += "\n### Top Similar Papers:\n"
                for i, paper in enumerate(similar_papers[:5], 1):
                    similar_papers_section += f"{i}. **{paper.get('title', 'Unknown')}**\n"
                    similar_papers_section += f"   - Authors: {', '.join(paper.get('authors', []))}\n"
                    similar_papers_section += f"   - Year: {paper.get('year', 'Unknown')}\n"
                    similar_papers_section += f"   - Venue: {paper.get('venue', 'Unknown')}\n"
                    similar_papers_section += f"   - Similarity Score: {paper.get('similarity_score', 0):.3f}\n"
                    similar_papers_section += f"   - Source: {paper.get('source', 'Unknown')}\n"
                    if paper.get('url'):
                        similar_papers_section += f"   - URL: {paper['url']}\n"
                    similar_papers_section += "\n"
            else:
                similar_papers_section += "No similar papers found.\n"

            # Add OpenReview reviews section
            openreview_section = "\n## OpenReview Reviews for Similar Papers:\n"
            if openreview_reviews:
                for i, review_info in enumerate(openreview_reviews[:3], 1):
                    openreview_section += f"{i}. **{review_info.get('submission_title', 'Unknown')}**\n"
                    openreview_section += f"   - Rating: {review_info.get('rating', 'Unknown')}\n"
                    openreview_section += f"   - Confidence: {review_info.get('confidence', 'Unknown')}\n"
                    openreview_section += f"   - Reviewer: {review_info.get('reviewer', 'Anonymous')}\n"
                    openreview_section += f"   - Review Link: {review_info.get('review_link', 'N/A')}\n"
                    openreview_section += "\n"
            else:
                openreview_section += "No OpenReview reviews found for similar papers.\n"

        review_text = f"""# ACL ARR Review Report

## Paper Summary
{review.paper_summary}

## Summary of Strengths
{review.strengths}

## Summary of Weaknesses
{review.weaknesses}

## Comments, Suggestions and Typos
{review.comments_suggestions}

## Confidence
{review.confidence}/5

## Soundness
{review.soundness}/5

## Overall Assessment
{review.overall_assessment}/5

## Best Paper
{review.best_paper}

## Best Paper Justification
{review.best_paper_justification}

{literature_summary}{similar_papers_section}{openreview_section}
## Additional Insights for Reviewer
{json.dumps(review.additional_insights, indent=2)}

---
*Review generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*This review follows ACL ARR guidelines and includes comprehensive literature analysis from multiple sources including arXiv, Semantic Scholar, Google Scholar, and OpenReview.*
"""
        return review_text

    def review_paper(self, paper_url: str, review_depth: int = DEFAULT_REVIEW_DEPTH, 
                    include_related_work: bool = True, novelty_analysis: bool = True,
                    technical_analysis: bool = True, experimental_validation: bool = True,
                    openreview_username: str = "", openreview_password: str = "") -> Dict[str, Any]:
        """Main function to review a paper"""
        logger.info(f"Starting review of paper: {paper_url}")
        
        try:
            # Download paper
            paper = self.download_paper(paper_url)
            if not paper:
                return {
                    "status": "error",
                    "error": "Failed to download paper",
                    "result": None
                }
            
            logger.info(f"Successfully downloaded paper: {paper.title}")
            
            # Perform literature review with error handling
            literature_review = None
            if include_related_work:
                try:
                    literature_review = self.perform_literature_review(paper, review_depth)
                except Exception as e:
                    logger.error(f"Literature review failed: {e}")
                    # Create a minimal literature review as fallback
                    literature_review = LiteratureReview(
                        related_papers=[],
                        novelty_score=0.5,
                        contribution_analysis={"contributions": ["Analysis failed"], "significance": "medium"},
                        gaps_identified=["Analysis failed due to API limits"],
                        methodology_comparison={"comparison": "Analysis failed"},
                        similar_papers=[],
                        openreview_reviews=[],
                        semantic_scholar_papers=[],
                        cited_papers=[]
                    )
            
            # Handle OpenReview credentials and reviewer style analysis
            reviewer_style_summary = ""
            if openreview_username and openreview_password:
                logger.info("Using provided OpenReview credentials for reviewer style analysis")
                try:
                    own_reviews = self.fetch_reviewer_own_reviews(openreview_username, openreview_password)
                    reviewer_style_summary = self.analyze_reviewer_style(own_reviews)
                except Exception as e:
                    logger.error(f"OpenReview analysis failed: {e}")
            else:
                logger.info("No OpenReview credentials provided, skipping reviewer style analysis")
            
            # Generate ACL review, passing reviewer_style_summary if available
            try:
                acl_review = self.generate_acl_review(paper, literature_review, reviewer_style_summary=reviewer_style_summary)
            except Exception as e:
                logger.error(f"ACL review generation failed: {e}")
                # Create a minimal review as fallback
                acl_review = ACLReview(
                    paper_summary=f"Paper: {paper.title} by {', '.join(paper.authors) if paper.authors else 'Unknown authors'}",
                    strengths="Analysis failed due to API limits",
                    weaknesses="Analysis failed due to API limits", 
                    comments_suggestions="Unable to generate detailed review due to API limits",
                    confidence=1,
                    soundness=0.5,
                    overall_assessment=0.5,
                    best_paper="No",
                    best_paper_justification="Unable to assess due to API limits",
                    literature_review=literature_review or LiteratureReview(
                        related_papers=[], novelty_score=0.5, contribution_analysis={},
                        gaps_identified=[], methodology_comparison={}, similar_papers=[],
                        openreview_reviews=[], semantic_scholar_papers=[], cited_papers=[]
                    ),
                    additional_insights={"error": "Review generation failed due to API limits"}
                )
            
            # Format review
            try:
                formatted_review = self.format_review(acl_review)
            except Exception as e:
                logger.error(f"Review formatting failed: {e}")
                formatted_review = f"Review generation failed: {str(e)}"
            
            return {
                "status": "success",
                "result": {
                    "paper": {
                        "title": paper.title,
                        "authors": paper.authors,
                        "url": paper.url,
                        "venue": paper.venue,
                        "year": paper.year
                    },
                    "review": {
                        "paper_summary": acl_review.paper_summary,
                        "strengths": acl_review.strengths,
                        "weaknesses": acl_review.weaknesses,
                        "comments_suggestions": acl_review.comments_suggestions,
                        "confidence": acl_review.confidence,
                        "soundness": acl_review.soundness,
                        "overall_assessment": acl_review.overall_assessment,
                        "best_paper": acl_review.best_paper,
                        "best_paper_justification": acl_review.best_paper_justification
                    },
                    "literature_review": {
                        "novelty_score": literature_review.novelty_score if literature_review else None,
                        "related_papers_count": len(literature_review.related_papers) if literature_review else 0,
                        "gaps_identified": literature_review.gaps_identified if literature_review else [],
                        "contribution_analysis": literature_review.contribution_analysis if literature_review else {}
                    },
                    "additional_insights": acl_review.additional_insights,
                    "formatted_review": formatted_review,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error reviewing paper: {e}")
            return {
                "status": "error",
                "error": str(e),
                "result": None
            }

    def load_arr_guidelines(self) -> str:
        """Load ARR guidelines from file"""
        try:
            guidelines_path = os.path.join(os.path.dirname(__file__), "ARRguidelines.txt")
            with open(guidelines_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Failed to load ARR guidelines: {e}")
            return ""

    def load_arr_form(self) -> str:
        """Load ARR review form from file"""
        try:
            form_path = os.path.join(os.path.dirname(__file__), "ARRform.txt")
            with open(form_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Failed to load ARR form: {e}")
            return ""

    def fetch_reviewer_own_reviews(self, username: str, password: str):
        """Fetch all reviews written by the reviewer using OpenReview credentials"""
        if not OPENREVIEW_AVAILABLE:
            logger.warning("OpenReview library not available.")
            return []

        client = openreview.api.OpenReviewClient(
            baseurl='https://api2.openreview.net',
                username=username,
                password=password
            )
        result = openreview.tools.get_own_reviews(client)
        return result


    def analyze_reviewer_style(self, own_reviews: list) -> str:
        """Analyze the reviewer's style from their OpenReview reviews (returns a style summary)"""
        if not own_reviews:
            return ""
        # Concatenate all review texts
        all_reviews = "\n\n".join([r.get('review_link', '') for r in own_reviews])
        prompt = self.REVIEWER_STYLE_PROMPT.format(reviews=all_reviews)
        try:
            content = self.call_openai(prompt, max_tokens=500, temperature=0.3)
            return content
        except Exception as e:
            logger.error(f"Error analyzing reviewer style: {e}")
            return ""

    def search_semantic_scholar(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search papers using Semantic Scholar API"""
        if not SEMANTIC_SCHOLAR_AVAILABLE or not self.semantic_scholar:
            return []

        try:
            search_results = self.semantic_scholar.search_paper(query, limit=max_results)
            papers = []
            
            for paper in search_results:
                paper_info = {
                    'title': paper.title,
                    'abstract': paper.abstract,
                    'authors': [author.name for author in paper.authors] if paper.authors else [],
                    'year': paper.year,
                    'venue': paper.venue,
                    'url': paper.url,
                    'paperId': paper.paperId,
                    'citations': len(paper.citations) if paper.citations else 0,
                    'influential_citations': len([c for c in paper.citations if c.isInfluential]) if paper.citations else 0
                }
                papers.append(paper_info)
            
            return papers
        except Exception as e:
            logger.error(f"Error searching Semantic Scholar: {e}")
            return []

    def search_google_scholar(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search papers using Google Scholar via scholarly"""
        if not NLTK_AVAILABLE:
            return []

        try:
            search_query = scholarly.search_pubs(query)
            papers = []
            
            for i, paper in enumerate(search_query):
                if i >= max_results:
                    break
                    
                paper_info = {
                    'title': paper.get('bib', {}).get('title', ''),
                    'abstract': paper.get('bib', {}).get('abstract', ''),
                    'authors': paper.get('bib', {}).get('author', []),
                    'year': paper.get('bib', {}).get('year'),
                    'venue': paper.get('bib', {}).get('venue', ''),
                    'url': paper.get('pub_url', ''),
                    'citations': paper.get('num_citations', 0),
                    'source': 'Google Scholar'
                }
                papers.append(paper_info)
            
            return papers
        except Exception as e:
            logger.error(f"Error searching Google Scholar: {e}")
            return []

    def get_openreview_reviews(self, paper_title: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Get reviews from OpenReview for similar papers"""
        if not OPENREVIEW_AVAILABLE or not self.openreview_client:
            return []

        try:
            # Search for papers with similar titles
            submissions = self.openreview_client.search_notes(
                term=paper_title,
                limit=max_results
            )
            
            reviews = []
            for submission in submissions:
                # Get reviews for this submission
                submission_reviews = self.openreview_client.search_notes(
                    invitation=f"{submission.forum}/-/Official_Review",
                    limit=10
                )
                
                for review in submission_reviews:
                    review_info = {
                        'submission_title': submission.content.get('title', ''),
                        'submission_link': f"https://openreview.net/forum?id={submission.forum}",
                        'review_link': f"https://openreview.net/forum?id={submission.forum}&noteId={review.id}",
                        'review_content': review.content.get('review', ''),
                        'rating': review.content.get('rating', ''),
                        'confidence': review.content.get('confidence', ''),
                        'reviewer': review.signatures[0] if review.signatures else 'Anonymous'
                    }
                    reviews.append(review_info)
            
            return reviews
        except Exception as e:
            logger.error(f"Error getting OpenReview reviews: {e}")
            return []

    def find_most_similar_papers(self, paper: Paper, max_results: int = 10) -> List[Dict[str, Any]]:
        """Find the most similar papers using multiple sources"""
        logger.info("Finding most similar papers...")
        
        all_papers = []
        
        # Search using different sources
        search_queries = self.generate_literature_queries(paper, LITERATURE_QUERY_ROUNDS)
        
        for query in search_queries:
            # Semantic Scholar search
            if SEMANTIC_SCHOLAR_AVAILABLE:
                semantic_papers = self.search_semantic_scholar(query, max_results // 2)
                all_papers.extend(semantic_papers)
            
            # Google Scholar search
            scholar_papers = self.search_google_scholar(query, max_results // 2)
            all_papers.extend(scholar_papers)
            
            # arXiv search (if available)
            if ARXIV_AVAILABLE:
                try:
                    arxiv_search = arxiv.Search(query=query, max_results=max_results // 3)
                    for result in arxiv_search.results():
                        arxiv_paper = {
                            'title': result.title,
                            'abstract': result.summary,
                            'authors': [author.name for author in result.authors],
                            'year': result.published.year,
                            'venue': 'arXiv',
                            'url': result.entry_id,
                            'source': 'arXiv'
                        }
                        all_papers.append(arxiv_paper)
                except Exception as e:
                    logger.error(f"Error searching arXiv: {e}")
        
        # Calculate similarity scores
        similar_papers = []
        for candidate_paper in all_papers:
            similarity_score = self.calculate_paper_similarity(paper, candidate_paper)
            candidate_paper['similarity_score'] = similarity_score
            similar_papers.append(candidate_paper)
        
        # Sort by similarity score and remove duplicates
        similar_papers.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # Remove duplicates based on title similarity
        unique_papers = []
        seen_titles = set()
        
        for paper_info in similar_papers:
            title_lower = paper_info['title'].lower()
            is_duplicate = False
            
            for seen_title in seen_titles:
                if self.calculate_title_similarity(title_lower, seen_title) > TITLE_SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_papers.append(paper_info)
                seen_titles.add(title_lower)
            
            if len(unique_papers) >= max_results:
                break
        
        return unique_papers

    def calculate_paper_similarity(self, paper: Paper, candidate_paper: Dict[str, Any]) -> float:
        """Calculate similarity between two papers"""
        try:
            # Combine title and abstract for comparison
            paper_text = f"{paper.title} {paper.abstract}"
            candidate_text = f"{candidate_paper.get('title', '')} {candidate_paper.get('abstract', '')}"
            
            # Use TF-IDF similarity
            texts = [paper_text, candidate_text]
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except:
            return 0.0

    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles"""
        try:
            # Simple word overlap similarity
            words1 = set(title1.lower().split())
            words2 = set(title2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union)
        except:
            return 0.0


def execute(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point for the ACL review agent"""
    try:
        # Load environment variables
        dotenv.load_dotenv()

        # Extract parameters with proper boolean conversion
        paper_url = input_data.get("paper_url", config.get("paper_url", ""))
        paper_title = input_data.get("paper_title", config.get("paper_title", ""))
        review_depth = input_data.get("review_depth", config.get("review_depth", DEFAULT_REVIEW_DEPTH))
        
        # Ensure boolean parameters are properly converted
        def ensure_boolean(value, default=True):
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            else:
                return bool(value) if value is not None else default
        
        include_related_work = ensure_boolean(
            input_data.get("include_related_work", config.get("include_related_work", True))
        )
        novelty_analysis = ensure_boolean(
            input_data.get("novelty_analysis", config.get("novelty_analysis", True))
        )
        technical_analysis = ensure_boolean(
            input_data.get("technical_analysis", config.get("technical_analysis", True))
        )
        experimental_validation = ensure_boolean(
            input_data.get("experimental_validation", config.get("experimental_validation", True))
        )
        
        # Extract OpenReview credentials (optional)
        openreview_username = input_data.get("openreview_username", config.get("openreview_username", ""))
        openreview_password = input_data.get("openreview_password", config.get("openreview_password", ""))

        # Debug logging
        logger.info(f"Parameters: include_related_work={include_related_work} (type: {type(include_related_work)})")
        logger.info(f"Parameters: novelty_analysis={novelty_analysis} (type: {type(novelty_analysis)})")
        logger.info(f"Parameters: technical_analysis={technical_analysis} (type: {type(technical_analysis)})")
        logger.info(f"Parameters: experimental_validation={experimental_validation} (type: {type(experimental_validation)})")

        if not paper_url and not paper_title:
            return {
                "status": "error",
                "error": "Either paper_url or paper_title must be provided",
                "result": None
            }

        # Create and run ACL review agent
        agent = ACLReviewAgent()
        result = agent.review_paper(
            paper_url=paper_url,
            review_depth=review_depth,
            include_related_work=include_related_work,
            novelty_analysis=novelty_analysis,
            technical_analysis=technical_analysis,
            experimental_validation=experimental_validation,
            openreview_username=openreview_username,
            openreview_password=openreview_password
        )

        return result

    except Exception as e:
        logger.error(f"Error in main function: {e}")
        return {
            "status": "error",
            "error": str(e),
            "result": None
        }


if __name__ == "__main__":
    # Test the agent
    test_input = {
        "paper_url": "https://arxiv.org/pdf/2505.19621",
        "review_depth": 1,
        "include_related_work": True,
        "novelty_analysis": True,
        "technical_analysis": True,
        "experimental_validation": True,
        # Optional: Provide OpenReview credentials for reviewer style analysis
        "openreview_username": "",
        "openreview_password": ""
    }
    
    test_config = {
        "paper_url": "",
        "paper_title": "",
        "review_depth": 4,
        "include_related_work": True,
        "novelty_analysis": True,
        "technical_analysis": True,
        "experimental_validation": True,
        # Optional: OpenReview credentials can also be provided in config
        # "openreview_username": "",
        # "openreview_password": ""
    }
    
    result = main(test_input, test_config)
    print(json.dumps(result, indent=2)) 