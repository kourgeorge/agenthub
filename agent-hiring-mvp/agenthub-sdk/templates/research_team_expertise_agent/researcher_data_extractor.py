"""
Team Member Extractor

A focused class for extracting comprehensive information about individual team members
from academic sources like Semantic Scholar and arXiv.
"""

import logging
import requests
import arxiv
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re
from publication_processor import PublicationProcessor
from dotenv import load_dotenv
from dataclasses import asdict

from langchain.schema import HumanMessage, SystemMessage
from open_alex import OpenAlexClient
from ddgs import DDGS
from semanticscholar import SemanticScholar

load_dotenv()
logger = logging.getLogger(__name__)


class ResearcherDataExtractor:
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
        self.semantic_scholar = SemanticScholar()
        self.publication_processor = PublicationProcessor()
        self.openalex_client = OpenAlexClient()

    def extract_researcher_info(self, name: str, max_pubs: int = 50) -> Optional[Dict[str, Any]]:
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
                "sources_used": []
            }

            researcher_metric = asdict(self.openalex_client.get_author_metrics(name))
            if researcher_metric:
                member_data["metrics"] = researcher_metric

            # Extract from Semantic Scholar (primary source for citations and publications)
            semantic_data = self._extract_publications_from_semantic_scholar(name, max_pubs)
            if semantic_data:
                member_data["sources_used"].append("Semantic Scholar")

                # Extract citation metrics from Semantic Scholar
                if semantic_data.get("citation_metrics"):
                    member_data["citation_metrics"] = semantic_data["citation_metrics"]

                # Add publications from Semantic Scholar
                member_data["publications"].extend(semantic_data.get("publications", []))

                # Merge collaborators
                member_data["collaborators"].update(semantic_data.get("collaborators", []))

                # Merge research timeline
                self._update_research_timeline(member_data["research_timeline"],
                                               semantic_data.get("research_timeline", {}))

                # Calculate average citations per paper
                if member_data["publications"] and member_data["citation_metrics"].get("total_citations"):
                    total_citations = sum(pub.get('citations', 0) for pub in member_data["publications"])
                    member_data["citation_metrics"]["avg_citations_per_paper"] = (
                            total_citations / len(member_data["publications"])
                    )

            # Extract from arXiv (for additional publications)
            arxiv_data = self._extract_publications_from_arxiv(name, max_pubs // 2)
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
                self._update_research_timeline(member_data["research_timeline"],
                                               arxiv_data.get("research_timeline", {}))

            # Post-process the data
            if member_data["publications"]:
                member_data["publications"] = self.publication_processor.deduplicate_publications(
                    member_data["publications"])
                member_data["expertise_characterization"] = self._analyze_and_characterize_expertise(name, member_data[
                    "publications"])
                member_data["collaborators"] = list(member_data["collaborators"])

                # Update citation metrics with final calculated values
                if not member_data.get("citation_metrics"):
                    member_data["citation_metrics"] = {}
                total_citations = sum(pub.get('citations', 0) for pub in member_data["publications"])
                member_data["metrics"].update({
                    "total_citations": max(member_data["citation_metrics"].get("total_citations", 0), total_citations),
                    "publication_count": len(member_data["publications"]),
                    "avg_citations_per_paper": total_citations / len(
                        member_data["publications"]) if total_citations > 0 else 0
                })

                # Ensure source reflects all contributors
                sources = member_data["sources_used"]
                if len(sources) > 1:
                    member_data["citation_metrics"]["source"] = " + ".join(sources)
                    member_data["textual_summary"] = self._generate_member_summary(member_data)

                return member_data
            else:
                logger.warning(f"No publications found for {name}")
                return None

        except Exception as e:
            logger.error(f"Error extracting member info for {name}: {str(e)}")
            return None

    def _extract_publications_from_semantic_scholar(self, name: str, max_pubs: int) -> Dict[str, Any]:
        """Extract data from Semantic Scholar using the official client library."""
        try:

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

    def _extract_publications_from_arxiv(self, name: str, max_pubs: int) -> Dict[str, Any]:
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

            # Use the newer Client.results() approach to avoid deprecation warnings
            client = arxiv.Client()
            for i, result in enumerate(client.results(search)):
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

    def _merge_citation_metrics(self, current_metrics: Dict[str, Any], new_metrics: Dict[str, Any], source_name: str) -> \
    Dict[str, Any]:
        """Merge citation metrics from different sources, preferring higher values and tracking sources."""
        if not current_metrics:
            current_metrics = {}

        merged_metrics = current_metrics.copy()

        # Merge metrics, preferring higher values
        merged_metrics.update({
            "h_index": max(current_metrics.get("h_index", 0), new_metrics.get("h_index", 0)),
            "total_citations": max(current_metrics.get("total_citations", 0), new_metrics.get("total_citations", 0)),
            "publication_count": max(current_metrics.get("publication_count", 0),
                                     new_metrics.get("publication_count", 0)),
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

    def _generate_member_summary(self, member_data) -> str:
        """
        Generate a comprehensive textual summary for a team member using LLM.
        
        Args:
            name: Name of the team member
            publications: List of publications with titles and abstracts
            
        Returns:
            Textual summary (1-4 paragraphs)
        """

        name = member_data.get("name")
        publications = member_data.get("publications", [])
        if not publications:
            return f"{name} is a researcher whose publication record could not be retrieved."

        metrics = member_data.get("metrics", {})

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

    def _analyze_and_characterize_expertise(self, member_name: str, publications: List[Dict[str, Any]]) -> Dict[
        str, int]:
        """
        Analyze publications and characterize expertise domains with paper counts using LLM.
        
        Args:
            member_name: Name of the team member
            publications: List of publications for this member
            
        Returns:
            Dictionary mapping expertise domains to number of papers in that domain
        """
        try:
            logger.info(
                f"Analyzing and characterizing expertise for {member_name} with {len(publications)} publications")

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

    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 1000, temperature: float = None) -> \
    Optional[str]:
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
                # Handle different response formats to reduce Pydantic warnings
                if hasattr(response, 'content'):
                    content = response.content.strip()
                elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                    content = response.message.content.strip()
                elif isinstance(response, str):
                    content = response.strip()
                else:
                    logger.warning(f"Unexpected LLM response format: {type(response)}")
                    content = str(response)

                logger.info("Successfully called LLM via provided handler")
                return content

            except Exception as e:
                logger.warning(f"LLM invocation failed: {str(e)}")
                return None

        # No LLM available
        logger.warning("No LLM handler available for this request")
        return None