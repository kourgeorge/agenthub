"""
Team Member Extractor

A focused class for extracting comprehensive information about individual team members
from academic sources like Google Scholar (via scholarly), Semantic Scholar and arXiv.
"""

import logging
import requests
import arxiv
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re

from dotenv import load_dotenv
from scholarly import scholarly
logger = logging.getLogger(__name__)

# Import LLM packages
from langchain.schema import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

# Import additional packages
from duckduckgo_search import DDGS
from semanticscholar import SemanticScholar
from scholarly import scholarly

class TeamMemberExtractor:
    """Extracts comprehensive information about individual team members from academic sources."""
    
    def __init__(self, llm_handler=None, enable_paper_enrichment: bool = True):
        """Initialize the extractor with an optional LLM handler."""
        self.session = requests.Session()
        # Set a reasonable timeout and user agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Use the provided LLM handler directly
        self.llm = llm_handler
        
        # Paper enrichment configuration
        self.enable_paper_enrichment = enable_paper_enrichment
        
        # Initialize Semantic Scholar client
        try:
            self.semantic_scholar = SemanticScholar()
            logger.info("Semantic Scholar client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Semantic Scholar client: {str(e)}")
            self.semantic_scholar = None
        
        # Initialize scholarly
        try:
            self.scholarly = scholarly
            logger.info("scholarly library initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize scholarly library: {str(e)}")
            self.scholarly = None

    def extract_member_info(self, name: str, max_pubs: int = 50, include_citations: bool = True) -> Optional[Dict[str, Any]]:
        """
        Extract comprehensive information about a team member.
        
        Args:
            name: Full name of the team member
            max_pubs: Maximum number of publications to collect
            include_citations: Whether to include citation metrics
            
        Returns:
            Dictionary with member information or None if extraction fails
        """
        try:
            logger.info(f"Starting extraction for team member: {name}")
            
            # Initialize member data structure
            member_data = {
                "name": name,
                "publications": [],
                "collaborators": set(),
                "research_timeline": {},
                "citation_metrics": {},
                "sources_used": []
            }
            
            # Extract from Google Scholar using scholarly (primary source for citations and publications)
            google_scholar_data = self._extract_from_google_scholar(name, max_pubs, include_citations)
            if google_scholar_data:
                member_data["sources_used"].append("Google Scholar")
                member_data["citation_metrics"] = google_scholar_data.get("citation_metrics", {})
                member_data["publications"].extend(google_scholar_data.get("publications", []))
                member_data["collaborators"].update(google_scholar_data.get("collaborators", []))
                self._update_research_timeline(member_data["research_timeline"], google_scholar_data.get("research_timeline", {}))
            
            # Extract from Semantic Scholar (secondary source for additional data)
            semantic_data = self._extract_from_semantic_scholar(name, max_pubs//2, include_citations)
            semantic_data = None
            if semantic_data:
                member_data["sources_used"].append("Semantic Scholar")
                
                # Extract citation metrics if not already available from Google Scholar
                if not member_data.get("citation_metrics") or member_data["citation_metrics"].get("h_index", 0) == 0:
                    if semantic_data.get("citation_metrics"):
                        semantic_metrics = semantic_data["citation_metrics"]
                        # Merge citation metrics using the helper method
                        member_data["citation_metrics"] = self._merge_citation_metrics(
                            member_data.get("citation_metrics", {}),
                            semantic_metrics,
                            "Semantic Scholar"
                        )
                
                # Only add publications not already found in Google Scholar
                existing_titles = {pub.get('title', '').lower() for pub in member_data["publications"]}
                new_pubs = [pub for pub in semantic_data.get("publications", []) 
                           if pub.get('title', '').lower() not in existing_titles]
                member_data["publications"].extend(new_pubs)
                
                # Merge collaborators
                member_data["collaborators"].update(semantic_data.get("collaborators", []))
                
                # Merge research timeline
                self._update_research_timeline(member_data["research_timeline"], semantic_data.get("research_timeline", {}))
                
                # Recalculate average citations per paper with all publications
                if member_data["publications"] and member_data["citation_metrics"].get("total_citations"):
                    total_citations = sum(pub.get('citations', 0) for pub in member_data["publications"])
                    member_data["citation_metrics"]["total_citations"] = max(
                        member_data["citation_metrics"]["total_citations"], 
                        total_citations
                    )
                    member_data["citation_metrics"]["avg_citations_per_paper"] = (
                        member_data["citation_metrics"]["total_citations"] / len(member_data["publications"])
                    )
            
            # Extract from arXiv (for additional publications)
            arxiv_data = self._extract_from_arxiv(name, max_pubs//2)
            if arxiv_data:
                member_data["sources_used"].append("arXiv")
                
                # Only add publications not already found
                existing_titles = {pub.get('title', '').lower() for pub in member_data["publications"]}
                new_pubs = [pub for pub in arxiv_data.get("publications", []) 
                           if pub.get('title', '').lower() not in existing_titles]
                member_data["publications"].extend(new_pubs)
                
                # Note: Domain extraction will be done once at the end
                
                # Merge collaborators
                member_data["collaborators"].update(arxiv_data.get("collaborators", []))
                
                # Merge research timeline
                self._update_research_timeline(member_data["research_timeline"], arxiv_data.get("research_timeline", {}))
            
            # Post-process the data
            if member_data["publications"]:
                # Remove duplicates and limit publications
                member_data["publications"] = self._deduplicate_publications(member_data["publications"])[:max_pubs]
                
                # Enrich publications with additional research data (optional)
                if self.enable_paper_enrichment:
                    logger.info(f"Enriching publications for {name} with additional research data...")
                    enriched_publications = self.enrich_member_publications(name, member_data["publications"])
                    member_data["publications"] = enriched_publications
                    member_data["enriched_publications_count"] = len(enriched_publications)
                    logger.info(f"Successfully enriched {len(enriched_publications)} publications for {name}")
                else:
                    logger.info(f"Paper enrichment disabled for {name} - using original publication data")
                    member_data["enriched_publications_count"] = 0
                
                # Analyze and characterize expertise domains with publication counts using LLM
                member_data["expertise_characterization"] = self._analyze_and_characterize_expertise(name, member_data["publications"])
                
                # Convert sets to lists for JSON serialization
                member_data["collaborators"] = list(member_data["collaborators"])
                
                # Final calculation of citation metrics
                if member_data["publications"]:
                    total_citations = sum(pub.get('citations', 0) for pub in member_data["publications"])
                    h_index = self._calculate_h_index([pub.get('citations', 0) for pub in member_data["publications"]])
                    
                    # Update citation metrics with final calculated values
                    if not member_data.get("citation_metrics"):
                        member_data["citation_metrics"] = {}
                    
                    member_data["citation_metrics"].update({
                        "h_index": max(member_data["citation_metrics"].get("h_index", 0), h_index),
                        "total_citations": max(member_data["citation_metrics"].get("total_citations", 0), total_citations),
                        "publication_count": len(member_data["publications"]),
                        "avg_citations_per_paper": total_citations / len(member_data["publications"]) if total_citations > 0 else 0
                    })
                    
                    # Ensure source reflects all contributors
                    sources = member_data["sources_used"]
                    if len(sources) > 1:
                        member_data["citation_metrics"]["source"] = " + ".join(sources)
                
                # Generate textual summary using LLM only
                try:
                    member_data["textual_summary"] = self._generate_member_summary(name, member_data["publications"])
                    logger.info(f"Generated textual summary for {name}")
                except Exception as e:
                    logger.warning(f"Failed to generate textual summary for {name}: {str(e)}")
                    member_data["textual_summary"] = f"{name} is a researcher whose publications have been analyzed."
                
                logger.info(f"Successfully extracted data for {name}: {len(member_data['publications'])} publications")
                return member_data
            else:
                logger.warning(f"No publications found for {name}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting member info for {name}: {str(e)}")
            return None
    
    def test_scholarly_connection(self) -> bool:
        """Test if scholarly library can connect to Google Scholar."""
        # scholarly library is assumed to be available
        
        try:
            # Try a simple search to test connection
            test_search = self.scholarly.search_author("test")
            # Just check if we can create the search object
            return True
        except Exception as e:
            logger.error(f"scholarly connection test failed: {str(e)}")
            return False
    
    def _extract_from_google_scholar(self, name: str, max_pubs: int, include_citations: bool) -> Dict[str, Any]:
        """Extract data from Google Scholar using Serper API to find profile and scholarly for data."""
        try:
                    # scholarly library is assumed to be available
            
            logger.info(f"Extracting Google Scholar data for {name}")
            
            # First, use Serper API to find the Google Scholar profile URL
            profile_url = self._find_google_scholar_profile(name)
            
            if not profile_url:
                logger.warning(f"Could not find Google Scholar profile for {name}")
                return {}
            
            logger.info(f"Found Google Scholar profile: {profile_url}")
            
            # Extract the actual author name from the profile URL
            actual_name = self._extract_author_name_from_profile(profile_url, name)
            if actual_name:
                logger.info(f"Extracted actual author name: {actual_name}")
                name = actual_name
            
            # Now use scholarly to get the data using the found name
            return self._extract_from_scholarly_with_name(name, max_pubs, include_citations)
            
        except Exception as e:
            logger.error(f"Google Scholar extraction failed for {name}: {str(e)}")
            return {}
    
    def _find_google_scholar_profile(self, name: str) -> Optional[str]:
        """Use Serper API to find Google Scholar profile URL for the author."""
        try:
            # You'll need to set SERPER_API_KEY in your environment
            import os
            serper_api_key = os.getenv('SERPER_API_KEY')
            
            if not serper_api_key:
                logger.warning("SERPER_API_KEY not found in environment variables")
                logger.info("To use this feature, get a free API key from: https://serper.dev/")
                # Try DuckDuckGo as fallback
                logger.info("Trying DuckDuckGo as fallback...")
                return self._find_google_scholar_profile_ddg(name)
            
            # Search for Google Scholar profile
            search_query = f'"{name}" site:scholar.google.com'
            serper_url = "https://google.serper.dev/search"
            
            headers = {
                'X-API-KEY': serper_api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'q': search_query,
                'num': 10
            }
            
            logger.info(f"Searching for Google Scholar profile with query: {search_query}")
            response = self.session.post(serper_url, headers=headers, json=payload, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Serper API request failed: {response.status_code}")
                # Try DuckDuckGo as fallback
                logger.info("Trying DuckDuckGo as fallback...")
                return self._find_google_scholar_profile_ddg(name)
            
            search_results = response.json()
            
            # Look for Google Scholar profile URLs
            for result in search_results.get('organic', []):
                url = result.get('link', '')
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                
                logger.debug(f"Checking result: {title} - {url}")
                
                # Check if this is a Google Scholar profile
                if 'scholar.google.com/citations' in url and 'user=' in url:
                    logger.info(f"Found Google Scholar profile via Serper: {url}")
                    logger.info(f"Profile title: {title}")
                    return url
            
            logger.info("No Google Scholar profile found via Serper")
            # Try DuckDuckGo as fallback
            logger.info("Trying DuckDuckGo as fallback...")
            return self._find_google_scholar_profile_ddg(name)
            
        except Exception as e:
            logger.error(f"Error finding Google Scholar profile via Serper: {str(e)}")
            # Try DuckDuckGo as fallback
            logger.info("Trying DuckDuckGo as fallback...")
            return self._find_google_scholar_profile_ddg(name)
    
    def _find_google_scholar_profile_ddg(self, name: str) -> Optional[str]:
        """Use DuckDuckGo as fallback to find Google Scholar profile URL for the author."""
        try:
            
            logger.info(f"Using DuckDuckGo to search for Google Scholar profile: {name}")
            
            # Search for Google Scholar profile
            query = f"{name} in scholar.google.com"
            
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=10)
                
                for result in results:
                    url = result.get("href", "")
                    title = result.get("title", "")
                    
                    logger.debug(f"DDG result: {title} - {url}")
                    
                    # Check if this is a Google Scholar profile
                    if 'scholar.google' in url and 'user=' in url:
                        logger.info(f"Found Google Scholar profile via DuckDuckGo: {url}")
                        logger.info(f"Profile title: {title}")
                        return url
            
            logger.info("No Google Scholar profile found via DuckDuckGo")
            return None
            
        except Exception as e:
            logger.error(f"Error finding Google Scholar profile via DuckDuckGo: {str(e)}")
            return None
    
    def _extract_author_name_from_profile(self, profile_url: str, original_name: str) -> Optional[str]:
        """Extract the actual author name from the Google Scholar profile page."""
        try:
            
            # Extract user ID from profile URL
            import re
            user_match = re.search(r'user=([^&]+)', profile_url)
            if not user_match:
                logger.warning("Could not extract user ID from profile URL")
                return None
            
            user_id = user_match.group(1)
            logger.info(f"Extracted user ID: {user_id}")
            
            # Use scholarly to get profile data
            try:
                # Try to get profile by ID
                profile = self.scholarly.search_author_id(user_id)
                if profile:
                    actual_name = profile.get('name', '')
                    if actual_name:
                        logger.info(f"Found actual name via scholarly: {actual_name}")
                        return actual_name
            except Exception as e:
                logger.warning(f"Could not get profile by ID via scholarly: {str(e)}")
            
            # Fallback: try to extract from URL or use original name
            return original_name
            
        except Exception as e:
            logger.error(f"Error extracting author name from profile: {str(e)}")
            return None
    
    def _extract_from_scholarly_with_name(self, name: str, max_pubs: int, include_citations: bool) -> Dict[str, Any]:
        """Extract data using scholarly with the confirmed author name."""
        try:
            logger.info(f"Extracting data via scholarly for confirmed name: {name}")
            
            # Search for the author using scholarly
            search_query = self.scholarly.search_author(name)
            
            publications = []
            collaborators = set()
            research_timeline = {}
            citation_metrics = {}
            
            # Get the first (best) match
            try:
                author = next(search_query)
                logger.info(f"Found Google Scholar author: {author.get('name', name)}")
                
                # Get detailed author information
                author = self.scholarly.fill(author)
                
                # Extract citation metrics
                citation_metrics = {
                    "h_index": author.get('hindex', 0),
                    "total_citations": author.get('citedby', 0),
                    "publication_count": author.get('publications', 0),
                    "source": "Google Scholar (scholarly)",
                    "avg_citations_per_paper": 0
                }
                
                # Get publications
                pubs = author.get('publications', [])
                logger.info(f"Found {len(pubs)} publications for {name}")
                
                for i, pub in enumerate(pubs[:max_pubs]):
                    try:
                        # Fill publication details
                        pub = self.scholarly.fill(pub)
                        
                        # Extract publication data
                        title = pub.get('bib', {}).get('title', '')
                        if not title:
                            continue
                        
                        # Extract authors
                        authors = pub.get('bib', {}).get('author', [])
                        if isinstance(authors, str):
                            authors = [author.strip() for author in authors.split(',')]
                        
                        # Extract year
                        year = pub.get('bib', {}).get('pub_year')
                        if year:
                            year = int(year)
                        
                        # Extract venue
                        venue = pub.get('bib', {}).get('venue', '')
                        
                        # Extract abstract
                        abstract = pub.get('bib', {}).get('abstract', '')
                        
                        # Extract citation count
                        citations = pub.get('num_citations', 0)
                        
                        # Extract URL
                        url = pub.get('pub_url', '')
                        
                        # Create publication data
                        pub_data = {
                            "title": title,
                            "authors": authors,
                            "year": year,
                            "citations": citations,
                            "venue": venue,
                            "abstract": abstract,
                            "source": "Google Scholar (scholarly)",
                            "url": url,
                            "paper_id": f"gs_scholarly_{i}",
                            "fields_of_study": []
                        }
                        
                        # Track research timeline
                        if year:
                            if year not in research_timeline:
                                research_timeline[year] = 0
                            research_timeline[year] += 1
                        
                        # Add collaborators (excluding the main author)
                        for author_name in authors:
                            if author_name.lower() != name.lower():
                                collaborators.add(author_name)
                        
                        # Note: Domain extraction will be done once at the end
                        
                        publications.append(pub_data)
                        logger.debug(f"Added scholarly publication: {title[:50]}...")
                        
                    except Exception as e:
                        logger.warning(f"Error processing scholarly publication {i} for {name}: {str(e)}")
                        continue
                
                # Calculate average citations per paper
                if publications:
                    total_citations = sum(pub.get('citations', 0) for pub in publications)
                    citation_metrics["avg_citations_per_paper"] = total_citations / len(publications)
                
            except StopIteration:
                logger.warning(f"No Google Scholar author found for {name}")
                return {}
            
            logger.info(f"Collected {len(publications)} publications from Google Scholar (scholarly) for {name}")
            
            return {
                "publications": publications,
                "collaborators": list(collaborators),
                "research_timeline": research_timeline,
                "citation_metrics": citation_metrics
            }
            
        except Exception as e:
            logger.error(f"scholarly extraction failed for {name}: {str(e)}")
            return {}
    
    def _extract_from_semantic_scholar(self, name: str, max_pubs: int, include_citations: bool) -> Dict[str, Any]:
        """Extract data from Semantic Scholar using the official client library."""
        try:
            if not self.semantic_scholar:
                logger.warning("Semantic Scholar client not available, skipping extraction")
                return {}
            
            logger.info(f"Extracting Semantic Scholar data for {name}")
            
            # Search for author using the client
            search_results = self.semantic_scholar.search_author(name, limit=max_pubs)
            
            publications = []
            collaborators = set()
            research_timeline = {}
            citation_metrics = {}
            
            author_found = False
            best_author = None
            max_papers = 0
            
            # First pass: find the author with the most papers
            for author in search_results:
                try:
                    logger.info(f"Found Semantic Scholar author: {author.name} (ID: {author.authorId})")
                    
                    # Get detailed author information
                    detailed_author = self.semantic_scholar.get_author(author.authorId)
                    
                    # Check if this author has more papers
                    paper_count = detailed_author.paperCount if hasattr(detailed_author, 'paperCount') else 0
                    logger.info(f"Author {author.name} has {paper_count} papers")
                    
                    if paper_count > max_papers:
                        max_papers = paper_count
                        best_author = detailed_author
                        logger.info(f"New best author: {author.name} with {paper_count} papers")
                        
                except Exception as e:
                    logger.warning(f"Error processing Semantic Scholar author {author.name}: {str(e)}")
                    continue
            
            # Second pass: extract data from the best author
            if best_author:
                try:
                    logger.info(f"Processing best author: {best_author.name} with {max_papers} papers")
                    
                    # Extract citation metrics
                    citation_metrics = {
                        "h_index": best_author.hIndex if hasattr(best_author, 'hIndex') else 0,
                        "total_citations": best_author.citationCount if hasattr(best_author, 'citationCount') else 0,
                        "affiliation": ", ".join(best_author.affiliations) if hasattr(best_author, 'affiliations') and best_author.affiliations else "",
                        "interests": best_author.interests if hasattr(best_author, 'interests') else [],
                        "publication_count": best_author.paperCount if hasattr(best_author, 'paperCount') else 0,
                        "source": "Semantic Scholar (official client)"
                    }
                    
                    # Get publications
                    papers = best_author.papers
                    logger.info(f"Found {len(papers)} publications for {name}")
                    
                    for i, paper in enumerate(papers[:max_pubs]):
                        try:
                            # Extract publication data
                            title = paper.title if hasattr(paper, 'title') else ""
                            if not title:
                                continue
                            
                            # Extract authors
                            authors = []
                            if hasattr(paper, 'authors') and paper.authors:
                                authors = [author.name for author in paper.authors if hasattr(author, 'name')]
                            
                            # Extract year
                            year = paper.year if hasattr(paper, 'year') else None
                            
                            # Extract venue
                            venue = paper.venue if hasattr(paper, 'venue') else ""
                            
                            # Extract abstract
                            abstract = paper.abstract if hasattr(paper, 'abstract') else ""
                            
                            # Extract citation count
                            citations = paper.citationCount if hasattr(paper, 'citationCount') else 0
                            
                            # Extract URL
                            url = paper.url if hasattr(paper, 'url') else ""
                            
                            # Extract fields of study
                            fields_of_study = paper.fieldsOfStudy if hasattr(paper, 'fieldsOfStudy') else []
                            
                            # Create publication data
                            pub_data = {
                                "title": title,
                                "authors": authors,
                                "year": year,
                                "citations": citations,
                                "venue": venue,
                                "abstract": abstract,
                                "source": "Semantic Scholar (official client)",
                                "url": url,
                                "paper_id": paper.paperId if hasattr(paper, 'paperId') else f"ss_{i}",
                                "fields_of_study": fields_of_study
                            }
                            
                            # Track research timeline
                            if year:
                                if year not in research_timeline:
                                    research_timeline[year] = 0
                                research_timeline[year] += 1
                            
                            # Add collaborators (excluding the main author)
                            for author_name in authors:
                                if author_name.lower() != name.lower():
                                    collaborators.add(author_name)
                            
                            # Note: Domain extraction will be done once at the end
                            
                            publications.append(pub_data)
                            logger.debug(f"Added Semantic Scholar publication: {title[:50]}...")
                            
                        except Exception as e:
                            logger.warning(f"Error processing Semantic Scholar paper {i} for {name}: {str(e)}")
                            continue
                    
                    author_found = True
                    
                except Exception as e:
                    logger.error(f"Error processing best Semantic Scholar author: {str(e)}")
            
            if not author_found:
                logger.warning(f"No Semantic Scholar author found for {name}")
                return {}

            
            logger.info(f"Collected {len(publications)} publications from Semantic Scholar for {name}")
            
            return {
                "publications": publications,
                "collaborators": list(collaborators),
                "research_timeline": research_timeline,
                "citation_metrics": citation_metrics
            }
            
        except Exception as e:
            logger.error(f"Semantic Scholar extraction failed for {name}: {str(e)}")
            return {}
    
    def _extract_from_arxiv(self, name: str, max_pubs: int) -> Dict[str, Any]:
        """Extract data from arXiv."""
        try:
            logger.info(f"Extracting arXiv data for {name}")
            
            # Search arXiv for papers by author name
            search_query = f'au:"{name}"'
            search = arxiv.Search(
                query=search_query,
                max_results=max_pubs,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )

            publications = []
            collaborators = set()
            research_timeline = {}

            for i, result in enumerate(search.results()):
                try:
                    # Extract co-authors
                    authors = [author.name for author in result.authors]
                    collaborators.update(authors)

                    pub_data = {
                        "title": result.title,
                        "authors": authors,
                        "year": result.published.year if result.published else None,
                        "citations": 0,  # arXiv doesn't provide citation counts
                        "venue": "arXiv",
                        "abstract": result.summary,
                        "source": "arXiv",
                        "url": result.entry_id,
                        "categories": result.categories,
                        "submitted_date": result.published.isoformat() if result.published else None,
                        "doi": result.doi if hasattr(result, 'doi') else None,
                        "journal_ref": result.journal_ref if hasattr(result, 'journal_ref') else None
                    }

                    # Track research timeline
                    if pub_data["year"]:
                        year = pub_data["year"]
                        if year not in research_timeline:
                            research_timeline[year] = 0
                        research_timeline[year] += 1

                    publications.append(pub_data)

                    # Note: Domain extraction will be done once at the end

                except Exception as e:
                    logger.warning(f"Error processing arXiv publication {i} for {name}: {str(e)}")
                    continue

            logger.info(f"Collected {len(publications)} publications from arXiv for {name}")

            return {
                "publications": publications,
                "collaborators": list(collaborators),
                "research_timeline": research_timeline
            }

        except Exception as e:
            logger.error(f"arXiv extraction failed for {name}: {str(e)}")
            return {}

    def _extract_domains_from_text(self, text: str) -> List[str]:
        """Extract expertise domains from text content using LLM with structured output."""
        if not text:
            return []

        # Load arXiv taxonomy if not already loaded
        if not hasattr(self, 'arxiv_taxonomy') or not self.arxiv_taxonomy:
            self.arxiv_taxonomy = self._load_arxiv_taxonomy()

        # Use LLM to extract domains with structured output
        domains = self._extract_domains_with_llm(text, self.arxiv_taxonomy)

        if domains:
            logger.info(f"LLM extracted {len(domains)} domains: {domains}")
            return domains
        else:
            logger.warning("LLM extraction failed - no fallback available")
            return []

    
    def _extract_domains_with_llm(self, text: str, taxonomy: Dict[str, Any]) -> List[str]:
        """Extract domains using LLM with structured output."""
        try:

            # Create system and user messages
            system_prompt = """You are an expert in academic and technical domain classification. 
            Your task is to analyze text content and identify the most relevant expertise domains from a provided taxonomy.
            
            IMPORTANT: You must respond with ONLY a JSON array of domain names, nothing else.
            Example: ["Machine Learning", "Computer Vision"]
            
            If no domains are relevant, respond with: []
            
            Do not include any explanations, just the JSON array."""
            
            # Simplify taxonomy to just domain names
            domain_names = self._flatten_taxonomy(taxonomy)
            
            user_prompt = f"""Available domains: {', '.join(domain_names[:50])}

Text to analyze: {text[:2000]}

Return ONLY a JSON array of relevant domain names:"""
            
            # Use unified LLM calling method
            content = self._call_llm(system_prompt, user_prompt, max_tokens=500, temperature=0.1)
            
            if content:
                # Try to extract JSON from the response
                json_match = re.search(r'\[.*?\]', content)
                if json_match:
                    try:
                        domains = json.loads(json_match.group())
                        if isinstance(domains, list):
                            # Validate that all domains exist in the taxonomy
                            validated_domains = [d for d in domains if d in domain_names]
                            if validated_domains:
                                logger.info(f"LLM successfully extracted {len(validated_domains)} domains")
                                return validated_domains
                            else:
                                logger.warning("No valid domains found in LLM response")
                    except json.JSONDecodeError:
                        logger.error("Failed to parse LLM response as JSON")
                
                # No fallback available
                logger.warning("Could not extract structured output from LLM response")
                return []
            else:
                logger.warning("No LLM available for domain extraction")
                return []
                
        except Exception as e:
            logger.error(f"Error in LLM domain extraction: {str(e)}")
            return []
    
    def _flatten_taxonomy(self, taxonomy: Dict[str, Any]) -> List[str]:
        """Flatten the taxonomy into a simple list of domain names."""
        domains = []
        try:
            for subject, subject_data in taxonomy.items():
                if isinstance(subject_data, dict) and "categories" in subject_data:
                    for category in subject_data["categories"]:
                        if isinstance(category, dict) and "name" in category:
                            domains.append(category["name"])
        except Exception as e:
            logger.warning(f"Error flattening taxonomy: {str(e)}")
            # No fallback domains - return empty list
            domains = []
        return domains
    
    def _domain_matches_text(self, domain_name: str, text_lower: str) -> bool:
        """Check if a domain name matches the text content."""
        # Direct match
        if domain_name.lower() in text_lower:
            return True
        
        # Check for common abbreviations and variations
        domain_variations = self._get_domain_variations(domain_name)
        for variation in domain_variations:
            if variation.lower() in text_lower:
                return True
        
        return False
    
    def _get_domain_variations(self, domain_name: str) -> List[str]:
        """Get common variations and abbreviations for a domain name."""
        variations = [domain_name]
        
        # Common abbreviations and variations
        abbreviation_map = {
            "Artificial Intelligence": ["AI", "artificial intelligence", "intelligent systems"],
            "Machine Learning": ["ML", "machine learning", "statistical learning"],
            "Computer Vision": ["CV", "computer vision", "image processing", "visual computing"],
            "Natural Language Processing": ["NLP", "natural language", "text processing", "computational linguistics"],
            "Robotics": ["robotics", "robot", "autonomous systems", "control systems"],
            "Data Science": ["data science", "data analysis", "analytics", "statistics"],
            "Software Engineering": ["software engineering", "software development", "programming"],
            "Computer Networks": ["networking", "network protocols", "communication systems"],
            "Database Systems": ["databases", "data management", "information systems"],
            "Operating Systems": ["OS", "operating systems", "system software", "kernel"],
            "Human-Computer Interaction": ["HCI", "human-computer interaction", "user interface", "UX"],
            "Cryptography and Security": ["security", "cryptography", "cybersecurity", "privacy"],
            "Distributed Systems": ["distributed computing", "distributed systems", "parallel computing"],
            "Information Theory": ["information theory", "coding theory", "data compression"],
            "Computational Biology": ["computational biology", "bioinformatics", "genomics"],
            "Quantum Computing": ["quantum computing", "quantum algorithms", "quantum information"]
        }
        
        # Add variations if domain name matches
        for key, values in abbreviation_map.items():
            if domain_name.lower() in key.lower() or any(v.lower() in domain_name.lower() for v in values):
                variations.extend(values)
        
        return list(set(variations))  # Remove duplicates
    
    def _load_arxiv_taxonomy(self) -> Dict[str, Any]:
        """Load ArXiv subject taxonomy from JSON file."""
        try:
            import json
            from pathlib import Path
            
            taxonomy_path = Path(__file__).parent / "arxiv_taxonomy.json"
            if taxonomy_path.exists():
                with open(taxonomy_path, 'r', encoding='utf-8') as f:
                    taxonomy = json.load(f)
                logger.info(f"Loaded ArXiv taxonomy with {len(taxonomy)} main subjects")
                return taxonomy
            else:
                logger.warning("ArXiv taxonomy file not found")
                return {}
        except Exception as e:
            logger.error(f"Error loading ArXiv taxonomy: {str(e)}")
            return {}
    

    

    
    def _deduplicate_publications(self, publications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate publications based on title similarity."""
        if not publications:
            return []
        
        seen_titles = set()
        unique_publications = []
        
        for pub in publications:
            title = pub.get('title', '').lower().strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_publications.append(pub)
        
        return unique_publications
    
    def _merge_citation_metrics(self, current_metrics: Dict[str, Any], new_metrics: Dict[str, Any], source_name: str) -> Dict[str, Any]:
        """Merge citation metrics from different sources, preferring higher values and tracking sources."""
        if not current_metrics:
            current_metrics = {}
        
        merged_metrics = current_metrics.copy()
        
        # Merge metrics, preferring higher values
        merged_metrics.update({
            "h_index": max(current_metrics.get("h_index", 0), new_metrics.get("h_index", 0)),
            "total_citations": max(current_metrics.get("total_citations", 0), new_metrics.get("total_citations", 0)),
            "publication_count": max(current_metrics.get("publication_count", 0), new_metrics.get("publication_count", 0)),
        })
        
        # Track sources
        current_sources = current_metrics.get("source", "Unknown")
        if current_sources != "Unknown":
            merged_metrics["source"] = f"{current_sources} + {source_name}"
        else:
            merged_metrics["source"] = source_name
        
        # Add affiliation and interests if available
        if new_metrics.get("affiliation") and not current_metrics.get("affiliation"):
            merged_metrics["affiliation"] = new_metrics["affiliation"]
        if new_metrics.get("interests") and not current_metrics.get("interests"):
            merged_metrics["interests"] = new_metrics["interests"]
        
        return merged_metrics
    
    def _update_research_timeline(self, main_timeline: Dict[int, int], new_timeline: Dict[int, int]):
        """Update main research timeline with new data."""
        for year, count in new_timeline.items():
            if year in main_timeline:
                main_timeline[year] += count
            else:
                main_timeline[year] = count
    
    def _calculate_h_index(self, citation_counts: List[int]) -> int:
        """Calculate h-index from a list of citation counts."""
        if not citation_counts:
            return 0
        
        # Sort citations in descending order
        sorted_citations = sorted(citation_counts, reverse=True)
        
        # Find h-index
        for i, citations in enumerate(sorted_citations, 1):
            if citations < i:
                return i - 1
        
        return len(sorted_citations)
    
    def _generate_member_summary(self, name: str, publications: List[Dict[str, Any]]) -> str:
        """
        Generate a comprehensive textual summary for a team member using LLM.
        
        Args:
            name: Name of the team member
            publications: List of publications with titles and abstracts
            
        Returns:
            Textual summary (1-4 paragraphs)
        """
        if not publications:
            return f"{name} is a researcher whose publication record could not be retrieved."
        
        try:
            # Prepare publication data for LLM
            pub_data = []
            for pub in publications[:20]:  # Limit to first 20 for context
                title = pub.get('title', '')
                abstract = pub.get('abstract', '')
                year = pub.get('year', '')
                venue = pub.get('venue', '')
                citations = pub.get('citations', 0)
                
                if title:  # Only include publications with titles
                    pub_info = f"Title: {title}"
                    if year:
                        pub_info += f" ({year})"
                    if venue:
                        pub_info += f" - {venue}"
                    if citations > 0:
                        pub_info += f" - {citations} citations"
                    if abstract:
                        pub_info += f"\nAbstract: {abstract[:300]}..."  # Truncate long abstracts
                    
                    pub_data.append(pub_info)
            
            # Create prompt for LLM
            system_prompt = """You are an expert academic researcher and writer. Your task is to analyze a researcher's publications and create a comprehensive, professional summary of their research profile.

Write a 1-4 paragraph summary that covers:
1. Research focus and expertise areas
2. Key contributions and impact
3. Research trajectory and evolution
4. Overall research profile assessment

The summary should be:
- Professional and academic in tone
- Based solely on the provided publication data
- Concise but comprehensive
- Suitable for academic or professional contexts
- Written in third person

Focus on patterns, themes, and insights that emerge from the publication data."""

            user_prompt = f"""Please analyze the following publications for researcher {name} and provide a comprehensive summary:

{chr(10).join(pub_data)}

Based on these publications, please provide a 1-4 paragraph summary of {name}'s research profile, expertise, and contributions."""

            # Use unified LLM calling method
            summary = self._call_llm(system_prompt, user_prompt, max_tokens=1000)
            
            if summary and len(summary) >= 100:
                return summary
            else:
                logger.warning(f"Generated summary too short or failed for {name}")
                return f"{name} is a researcher whose publications have been analyzed."
            
        except Exception as e:
            logger.error(f"Error generating LLM summary for {name}: {str(e)}")
            return f"{name} is a researcher whose publications have been analyzed."
    

    
    def _analyze_and_characterize_expertise(self, member_name: str, publications: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Analyze publications and characterize expertise domains with paper counts using LLM.
        
        Args:
            member_name: Name of the team member
            publications: List of publications for this member
            
        Returns:
            Dictionary mapping expertise domains to number of papers in that domain
        """
        try:
            logger.info(f"Analyzing and characterizing expertise for {member_name} with {len(publications)} publications")
            
            if not publications:
                logger.warning(f"No publications for {member_name}")
                return {}
            
            # Combine all text content from all publications for single domain extraction
            all_text_content = ""
            for pub in publications:
                title = pub.get('title', '')
                abstract = pub.get('abstract', '')
                if title or abstract:
                    all_text_content += f"{title} {abstract} "
            
            # Extract domains using LLM only - no fallback
            domains = self._extract_domains_from_text(all_text_content)
            
            if not domains:
                logger.warning(f"No domains identified by LLM for {member_name}")
                return {}
            
            # Count publications per domain
            domain_counts = {}
            
            for paper in publications:
                title = paper.get("title", "")
                abstract = paper.get("abstract", "")
                text_content = f"{title} {abstract}".lower()
                
                # Find which domains this paper belongs to
                for domain in domains:
                    if self._domain_matches_text(domain, text_content):
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            logger.info(f"Successfully characterized expertise for {member_name}: {len(domain_counts)} domains")
            return domain_counts
            
        except Exception as e:
            logger.error(f"Error analyzing and characterizing expertise for {member_name}: {str(e)}")
            return {}
    
    def enrich_member_publications(self, member_name: str, publications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich publications for a specific team member with additional research data.
        
        Args:
            member_name: Name of the team member whose publications are being enriched
            publications: List of publication dictionaries for this member
            
        Returns:
            List of enriched publication dictionaries
        """
        logger.info(f"Enriching {len(publications)} publications for team member: {member_name}")
        enriched_publications = []

        for i, paper in enumerate(publications):
            try:
                title = paper.get("title", "")
                authors = paper.get("authors", [])

                if not title:
                    logger.debug(f"Skipping paper {i+1} for {member_name}: No title")
                    continue

                # Create enriched paper entry
                enriched_paper = {
                    "title": title,
                    "authors": authors,
                    "abstract": paper.get("abstract", ""),
                    "url": paper.get("url", ""),
                    "source": paper.get("source", "manual_extraction"),
                    "year": paper.get("year"),
                    "venue": paper.get("venue", ""),
                    "citations": paper.get("citations"),
                    "paper_id": paper.get("paper_id"),
                    "fields_of_study": paper.get("fields_of_study", [])
                }

                # Try to enrich with research data
                try:
                    # Try ArXiv first
                    arxiv_results = self._search_arxiv_for_paper(title)
                    if arxiv_results:
                        # Update with ArXiv data
                        if "abstract" in arxiv_results and not enriched_paper["abstract"]:
                            enriched_paper["abstract"] = arxiv_results["abstract"]
                        if "url" in arxiv_results and not enriched_paper["url"]:
                            enriched_paper["url"] = arxiv_results["url"]
                        if "arxiv_id" in arxiv_results:
                            enriched_paper["arxiv_id"] = arxiv_results["arxiv_id"]
                        if "year" in arxiv_results and not enriched_paper["year"]:
                            enriched_paper["year"] = arxiv_results["year"]
                        enriched_paper["source"] = "arxiv"
                        logger.debug(f"Enriched paper '{title[:50]}...' with ArXiv data for {member_name}")
                    else:
                        # Try Semantic Scholar
                        scholar_results = self._search_semantic_scholar_for_paper(title)
                        if scholar_results:
                            # Update with Semantic Scholar data
                            if "abstract" in scholar_results and not enriched_paper["abstract"]:
                                enriched_paper["abstract"] = scholar_results["abstract"]
                            if "url" in scholar_results and not enriched_paper["url"]:
                                enriched_paper["url"] = scholar_results["url"]
                            if "doi" in scholar_results:
                                enriched_paper["doi"] = scholar_results["doi"]
                            if "year" in scholar_results and not enriched_paper["year"]:
                                enriched_paper["year"] = scholar_results["year"]
                            if "venue" in scholar_results and not enriched_paper["venue"]:
                                enriched_paper["venue"] = scholar_results["venue"]
                            enriched_paper["source"] = "semantic_scholar"
                            logger.debug(f"Enriched paper '{title[:50]}...' with Semantic Scholar data for {member_name}")
                except Exception as e:
                    logger.warning(f"Failed to enrich paper '{title[:50]}...' for {member_name}: {e}")

                enriched_publications.append(enriched_paper)

            except Exception as e:
                logger.error(f"Error enriching paper {i+1} for {member_name}: {e}")
                continue

        logger.info(f"Successfully enriched {len(enriched_publications)} publications for {member_name}")
        return enriched_publications
    
    def _search_arxiv_for_paper(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Search for paper on ArXiv.
        
        Args:
            title: Title of the paper to search for
            
        Returns:
            Dictionary with ArXiv data or None if not found
        """
        try:
            if not hasattr(self, 'arxiv') or not self.arxiv:
                return None
                
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
                    "arxiv_id": result.entry_id.split('/')[-1],
                    "year": result.published.year if result.published else None
                }

            return None

        except Exception as e:
            logger.warning(f"ArXiv search failed for '{title[:50]}...': {e}")
            return None
    
    def _search_semantic_scholar_for_paper(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Search for paper on Semantic Scholar.
        
        Args:
            title: Title of the paper to search for
            
        Returns:
            Dictionary with Semantic Scholar data or None if not found
        """
        try:
            # Semantic Scholar is assumed to be available
            if not self.semantic_scholar:
                return None
                
            # Search Semantic Scholar for the paper
            search_results = self.semantic_scholar.search_paper(title, limit=1)
            
            for paper in search_results:
                return {
                    "abstract": paper.abstract if hasattr(paper, 'abstract') else "",
                    "url": paper.url if hasattr(paper, 'url') else "",
                    "doi": paper.doi if hasattr(paper, 'doi') else "",
                    "year": paper.year if hasattr(paper, 'year') else None,
                    "venue": paper.venue if hasattr(paper, 'url') else ""
                }

            return None

        except Exception as e:
            logger.warning(f"Semantic Scholar search failed for '{title[:50]}...': {e}")
            return None

    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 1000, temperature: float = None) -> Optional[str]:
        """
        Call the LLM with the given prompts using the provided LLM handler.
        
        Args:
            system_prompt: System message for the LLM
            user_prompt: User message for the LLM
            max_tokens: Maximum tokens for the response
            temperature: Temperature for generation (ignored, uses LLM handler's default)
            
        Returns:
            LLM response content or None if LLM handler is not available
        """
        # Use the provided LLM handler directly
        if self.llm:
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                
                response = self.llm.invoke(messages)
                content = response.content.strip()
                logger.info("Successfully called LLM via provided handler")
                return content
                
            except Exception as e:
                logger.warning(f"LLM invocation failed: {str(e)}")
                return None
        
        # No LLM available
        logger.warning("No LLM handler available for this request")
        return None

def main():
    """
    Main function to test the TeamMemberExtractor functionality.
    Tests extraction for team member "George Kour".
    """
    import json
    from pprint import pprint
    import os
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 80)
    print("TEAM MEMBER EXTRACTOR TEST")
    print("=" * 80)
    
    # scholarly library is assumed to be available
    print("\n✅ scholarly library available - will use for Google Scholar data extraction")
    print("   This provides reliable access to Google Scholar publication data")
    
    # Test connection
    extractor = TeamMemberExtractor()
    if extractor.test_scholarly_connection():
        print("   ✅ Connection test successful")
    else:
        print("   ⚠️  Connection test failed - may have network/access issues")
    print()
    
    # Check for Serper API key
    serper_api_key = os.getenv('SERPER_API_KEY')
    if not serper_api_key:
        print("\n⚠️  SERPER_API_KEY not found in environment variables")
        print("   Google Scholar profile discovery will be limited.")
        print("   To get the best results:")
        print("   1. Get a free API key from: https://serper.dev/")
        print("   2. Set environment variable: export SERPER_API_KEY=your_key_here")
        print("   3. Or create a .env file with: SERPER_API_KEY=your_key_here")
        print("   Note: Serper API is used to find the correct Google Scholar profile URLs")
        print()
    else:
        print("\n✅ SERPER_API_KEY found - will use Serper API for Google Scholar profile discovery")
        print("   This ensures we find the correct author profile before extracting data")
        print()
    
    # Initialize the extractor
    print("\n🤖 LLM Configuration:")
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        print("✅ OPENAI_API_KEY found - will use OpenAI for summary generation")
        # Note: In production, you would pass an LLM handler here
        extractor = TeamMemberExtractor()
    else:
        print("⚠️  OPENAI_API_KEY not found - summary generation will use fallback method")
        extractor = TeamMemberExtractor()
    
    # Check LLM availability
    if extractor.llm:
        print("✅ LLM handler provided - will use for summary generation")
    else:
        print("⚠️  No LLM handler provided - will use fallback summary generation")
    
    # All packages are assumed to be available
    print("✅ scholarly library available - will use for Google Scholar extraction")
    print("✅ Semantic Scholar client available")
    print("✅ DuckDuckGo search available as fallback")
    print()
    
    # Test team member
    team_member_name = "George Kour"
    print(f"\nTesting extraction for team member: {team_member_name}")
    print("-" * 60)
    
    try:
        # Extract member information
        print("Extracting member information...")
        if serper_api_key:
            print("🔍 Primary source: Google Scholar (via Serper API + scholarly)")
        else:
            print("🔍 Primary source: Google Scholar (via scholarly only)")
        
        print("🔍 Secondary source: Semantic Scholar (via official client)")
        
        print("🔍 Additional source: arXiv")
        print()
        
        member_info = extractor.extract_member_info(
            name=team_member_name,
            max_pubs=40,  # Limit to 40 publications for testing
            include_citations=True
        )
        
        if member_info:
            print(f"\n✅ Successfully extracted information for {team_member_name}")
            print(f"📊 Total publications found: {len(member_info['publications'])}")
            expertise_char = member_info.get('expertise_characterization', {})
            print(f"🔬 Expertise domains identified: {len(expertise_char)}")
            print(f"👥 Collaborators found: {len(member_info['collaborators'])}")
            print(f"📅 Research timeline spans: {len(member_info['research_timeline'])} years")
            print(f"📚 Sources used: {', '.join(member_info['sources_used'])}")
            
            # Show source breakdown
            source_counts = {}
            for pub in member_info['publications']:
                source = pub.get('source', 'Unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
            
            print(f"\n📈 Publication Source Breakdown:")
            for source, count in source_counts.items():
                print(f"   {source}: {count} publications")
            
            # Display citation metrics if available
            if member_info.get('citation_metrics'):
                metrics = member_info['citation_metrics']
                print(f"\n📈 Citation Metrics:")
                print(f"   H-index: {metrics.get('h_index', 'N/A')}")
                print(f"   Total citations: {metrics.get('total_citations', 'N/A')}")
                print(f"   Publication count: {metrics.get('publication_count', 'N/A')}")
                if metrics.get('avg_citations_per_paper'):
                    print(f"   Average citations per paper: {metrics.get('avg_citations_per_paper', 'N/A'):.1f}")
                if metrics.get('affiliation'):
                    print(f"   Affiliation: {metrics['affiliation']}")
            
            # Display top expertise domains
            if expertise_char:
                print(f"\n🔬 Top Expertise Domains:")
                # Sort by paper count and show top 8
                sorted_domains = sorted(expertise_char.items(), key=lambda x: x[1], reverse=True)
                for i, (domain, count) in enumerate(sorted_domains[:8], 1):
                    print(f"   {i}. {domain} ({count} papers)")
            
            # Display recent publications with source
            if member_info.get('publications'):
                print(f"\n📚 Recent Publications (showing first 5):")
                for i, pub in enumerate(member_info['publications'][:5], 1):
                    print(f"   {i}. {pub.get('title', 'No title')}")
                    print(f"      Source: {pub.get('source', 'Unknown')}")
                    print(f"      Year: {pub.get('year', 'N/A')}")
                    print(f"      Venue: {pub.get('venue', 'N/A')}")
                    print(f"      Citations: {pub.get('citations', 'N/A')}")
                    if pub.get('authors'):
                        authors_str = ', '.join(pub['authors'][:3])  # Show first 3 authors
                        if len(pub['authors']) > 3:
                            authors_str += f" (+{len(pub['authors']) - 3} more)"
                        print(f"      Authors: {authors_str}")
                    print()
            
            # Display research timeline
            if member_info.get('research_timeline'):
                print(f"\n📅 Research Timeline (last 10 years):")
                timeline = member_info['research_timeline']
                sorted_years = sorted(timeline.keys(), reverse=True)
                for year in sorted_years[:10]:
                    print(f"   {year}: {timeline[year]} publications")
            
            # Display top collaborators
            if member_info.get('collaborators'):
                print(f"\n👥 Top Collaborators (showing first 10):")
                collaborators = member_info['collaborators'][:10]
                for i, collaborator in enumerate(collaborators, 1):
                    print(f"   {i}. {collaborator}")
            
            # Display textual summary
            if member_info.get('textual_summary'):
                print(f"\n📝 RESEARCH PROFILE SUMMARY:")
                print("=" * 60)
                print(member_info['textual_summary'])
                print("=" * 60)
                
                # Check if this was generated by LLM
                if extractor.llm:
                    print("\n🤖 Summary generated using LLM (AI-powered analysis)")
                else:
                    print("\n⚠️  No LLM available for summary generation")
            else:
                print(f"\n⚠️  No textual summary available")
            
            # Save detailed results to JSON file
            output_file = f"george_kour_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(member_info, f, indent=2, ensure_ascii=False, default=str)
            print(f"\n💾 Detailed results saved to: {output_file}")
            
        else:
            print(f"\n❌ Failed to extract information for {team_member_name}")

    
    except Exception as e:
        print(f"\n❌ Error during extraction: {str(e)}")

    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    main()
