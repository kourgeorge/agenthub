#!/usr/bin/env python3
"""
Publication Processor

Handles all publication-related operations including deduplication, enrichment, 
and analysis. This eliminates duplicate logic across the main agent class.
"""

import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import OpenAlex client for citation enrichment
from open_alex import OpenAlexClient

logger = logging.getLogger(__name__)


class PublicationProcessor:
    """Unified processor for all publication operations."""

    def __init__(self):
        self.cache = {}
        # Initialize OpenAlex client for citation enrichment
        self.openalex_client = OpenAlexClient()

    def enrich_publication_data(self, pub: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich publications with comprehensive information from multiple sources.
        
        This method collects information from OpenAlex, ArXiv, and Semantic Scholar APIs
        and intelligently combines the data to provide the most complete publication information.
        
        Args:
            publications: List of publication dictionaries
            
        Returns:
            List of publications enriched with comprehensive data from multiple sources
        """

        title = pub.get("title", "").strip()

        # Create enriched publication entry with existing data
        enriched_pub = {
            "title": title,
            "authors": pub.get("authors", []),
            "abstract": pub.get("abstract", ""),
            "url": pub.get("url", ""),
            "source": pub.get("source", "manual_extraction"),
            "year": pub.get("year"),
            "venue": pub.get("venue", ""),
            "citations": pub.get("citations"),
            "paper_id": pub.get("paper_id"),
            "fields_of_study": pub.get("fields_of_study", []),
            "doi": pub.get("doi"),
            "arxiv_id": pub.get("arxiv_id")
        }

        # Check cache first for citation data
        cache_key = title.lower().strip()
        if cache_key in self.cache:
            enriched_pub["citations"] = self.cache[cache_key]
        else:
            # Collect data from multiple sources and combine intelligently
            combined_data = self._collect_publication_data_from_sources(title)

            if combined_data:
                # Intelligently merge data from multiple sources
                enriched_pub = self._merge_publication_data(enriched_pub, combined_data)

                # Cache the citation count
                if enriched_pub["citations"] is not None:
                    self.cache[cache_key] = enriched_pub["citations"]

                logger.debug(f"Enriched publication '{title[:50]}...' with data from {enriched_pub['source']}")
            else:
                # No enrichment data found, set defaults
                enriched_pub["citations"] = 0
                logger.debug(f"No enrichment data found for '{title[:50]}...'")

        return enriched_pub

    def _collect_publication_data_from_sources(self, title: str) -> Dict[str, Any]:
        """
        Collect publication data from multiple sources (OpenAlex, ArXiv, Semantic Scholar).
        
        Args:
            title: Title of the publication to search for
            
        Returns:
            Dictionary containing combined data from all sources
        """
        combined_data = {
            "source": "manual_extraction",
            "citations": 0,
            "abstract": "",
            "url": "",
            "doi": "",
            "year": None,
            "venue": "",
            "arxiv_id": "",
            "openalex_id": ""
        }

        try:
            # 1. Try OpenAlex first for citation data and basic info
            openalex_results = self.openalex_client.get_publication_citations(title)
            if openalex_results:
                combined_data.update({
                    "citations": openalex_results.get("cited_by_count", 0),
                    "doi": openalex_results.get("doi", ""),
                    "venue": openalex_results.get("venue", ""),
                    "year": openalex_results.get("year"),
                    "openalex_id": openalex_results.get("id", ""),
                    "source": "openalex"
                })
                logger.debug(f"Found OpenAlex data for '{title[:50]}...': {combined_data['citations']} citations")

            # 2. Try ArXiv for additional metadata
            arxiv_results = self._search_arxiv_for_paper(title)
            if arxiv_results:
                # Update with ArXiv data, preserving existing data if better
                if arxiv_results.get("abstract") and not combined_data["abstract"]:
                    combined_data["abstract"] = arxiv_results["abstract"]
                if arxiv_results.get("url") and not combined_data["url"]:
                    combined_data["url"] = arxiv_results["url"]
                if arxiv_results.get("arxiv_id"):
                    combined_data["arxiv_id"] = arxiv_results["arxiv_id"]
                if arxiv_results.get("year") and not combined_data["year"]:
                    combined_data["year"] = arxiv_results["year"]

                # Update source to indicate ArXiv enrichment
                if combined_data["source"] == "manual_extraction":
                    combined_data["source"] = "arxiv"
                elif combined_data["source"] == "openalex":
                    combined_data["source"] = "openalex+arxiv"

                logger.debug(f"Found ArXiv data for '{title[:50]}...'")

            # 3. Try Semantic Scholar for additional metadata
            scholar_results = self._search_semantic_scholar_for_paper(title)
            if scholar_results:
                # Update with Semantic Scholar data, preserving existing data if better
                if scholar_results.get("abstract") and not combined_data["abstract"]:
                    combined_data["abstract"] = scholar_results["abstract"]
                if scholar_results.get("url") and not combined_data["url"]:
                    combined_data["url"] = scholar_results["url"]
                if scholar_results.get("doi") and not combined_data["doi"]:
                    combined_data["doi"] = scholar_results["doi"]
                if scholar_results.get("year") and not combined_data["year"]:
                    combined_data["year"] = scholar_results["year"]
                if scholar_results.get("venue") and not combined_data["venue"]:
                    combined_data["venue"] = scholar_results["venue"]

                # Update source to indicate Semantic Scholar enrichment
                if combined_data["source"] == "manual_extraction":
                    combined_data["source"] = "semantic_scholar"
                elif combined_data["source"] == "openalex":
                    combined_data["source"] = "openalex+semantic_scholar"
                elif combined_data["source"] == "arxiv":
                    combined_data["source"] = "arxiv+semantic_scholar"
                elif combined_data["source"] == "openalex+arxiv":
                    combined_data["source"] = "openalex+arxiv+semantic_scholar"

                logger.debug(f"Found Semantic Scholar data for '{title[:50]}...'")

        except Exception as e:
            logger.warning(f"Failed to collect publication data from sources for '{title[:50]}...': {e}")

        return combined_data

    def _merge_publication_data(self, original_pub: Dict[str, Any], source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intelligently merge publication data from multiple sources.
        
        Args:
            original_pub: Original publication data
            source_data: Data collected from various sources
            
        Returns:
            Merged publication data with best available information
        """
        merged_pub = original_pub.copy()

        # Merge data intelligently, preferring source data when available
        for key, source_value in source_data.items():
            if key == "source":
                # Always update source to reflect enrichment
                merged_pub[key] = source_value
            elif source_value and (not merged_pub.get(key) or merged_pub[key] == ""):
                # Use source value if original is empty/None
                merged_pub[key] = source_value
            elif key == "citations" and source_value is not None:
                # Always use citation count from sources when available
                merged_pub[key] = source_value
            elif key == "year" and source_value and not merged_pub.get(key):
                # Use year from sources if not available in original
                merged_pub[key] = source_value
            elif key == "abstract" and source_value and len(source_value) > len(merged_pub.get(key, "")):
                # Use longer abstract if available
                merged_pub[key] = source_value

        return merged_pub

    def _search_arxiv_for_paper(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Search for paper on ArXiv.
        
        Args:
            title: Title of the paper to search for
            
        Returns:
            Dictionary with ArXiv data or None if not found
        """
        try:
            # Check if arxiv library is available
            try:
                import arxiv
            except ImportError:
                logger.debug("ArXiv library not available, skipping ArXiv search")
                return None

            # Search ArXiv for the paper
            search = arxiv.Search(
                query=title,
                max_results=1,
                sort_by=arxiv.SortCriterion.Relevance
            )

            # Use the newer Client.results() approach to avoid deprecation warnings
            client = arxiv.Client()
            for result in client.results(search):
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
            # Check if semantic_scholar library is available
            try:
                from semantic_scholar import SemanticScholar
                if not hasattr(self, 'semantic_scholar_client'):
                    self.semantic_scholar_client = SemanticScholar()
            except ImportError:
                logger.debug("Semantic Scholar library not available, skipping Semantic Scholar search")
                return None

            # Search Semantic Scholar for the paper
            search_results = self.semantic_scholar_client.search_paper(title, limit=1)

            for paper in search_results:
                return {
                    "abstract": paper.abstract if hasattr(paper, 'abstract') else "",
                    "url": paper.url if hasattr(paper, 'url') else "",
                    "doi": paper.doi if hasattr(paper, 'doi') else "",
                    "year": paper.year if hasattr(paper, 'year') else None,
                    "venue": paper.venue if hasattr(paper, 'venue') else ""
                }

            return None

        except Exception as e:
            logger.warning(f"Semantic Scholar search failed for '{title[:50]}...': {e}")
            return None

    def deduplicate_publications(self, publications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate publications based on title only.
        Enhanced to handle shared papers between team members.
        
        Args:
            publications: List of publication dictionaries
            
        Returns:
            List of unique publications
        """
        if not publications:
            return []

        unique_pubs = []
        seen_titles = set()

        for pub in publications:
            title = pub.get("title", "").lower().strip()

            if not title:
                # Skip publications without title
                continue

            # Normalize the title for deduplication
            normalized_title = re.sub(r'[^\w\s]', '', title)  # Remove punctuation
            normalized_title = re.sub(r'\s+', ' ', normalized_title).strip()  # Normalize whitespace

            if normalized_title not in seen_titles:
                unique_pubs.append(pub)
                seen_titles.add(normalized_title)

        return unique_pubs

    def publications_match(self, pub1: Dict[str, Any], pub2: Dict[str, Any]) -> bool:
        """
        Check if two publications are the same paper based on title only.
        
        Args:
            pub1: First publication
            pub2: Second publication
            
        Returns:
            True if publications match, False otherwise
        """
        try:
            title1 = pub1.get("title", "").lower().strip()
            title2 = pub2.get("title", "").lower().strip()

            if not title1 or not title2:
                return False

            # Normalize titles for comparison
            norm_title1 = re.sub(r'[^\w\s]', '', title1)
            norm_title1 = re.sub(r'\s+', ' ', norm_title1).strip()
            norm_title2 = re.sub(r'[^\w\s]', '', title2)
            norm_title2 = re.sub(r'\s+', ' ', norm_title2).strip()

            # Exact match on normalized titles
            return norm_title1 == norm_title2

        except Exception as e:
            logger.error(f"Error comparing publications: {str(e)}")
            return False

    def get_team_publications(self, team_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all team publications with deduplication to handle shared papers between members."""
        try:
            if not team_data: return []
            all_pubs = []
            for member_name, member_data in team_data.items():
                if member_data and "publications" in member_data:
                    for pub in member_data.get("publications", []):
                        pub_copy = pub.copy()
                        pub_copy["_member_contributors"] = [member_name]
                        all_pubs.append(pub_copy)

            unique_pubs = self.deduplicate_publications(all_pubs)

            for unique_pub in unique_pubs:
                contributors = set()
                for pub in all_pubs:
                    if pub.get("title", "").lower().strip() == unique_pub.get("title", "").lower().strip():
                        contributors.update(pub.get("_member_contributors", []))
                unique_pub["_member_contributors"] = list(contributors)

            logger.info(f"Team publications: {len(all_pubs)} total -> {len(unique_pubs)} unique")
            return unique_pubs

        except Exception as e:
            logger.error(f"Error getting team publications: {str(e)}")
            return []

    def analyze_publications_by_year(self, publications: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """
        Analyze publications by year to identify trends.
        
        Args:
            publications: List of publications
            
        Returns:
            Dictionary mapping year to list of publications
        """
        year_publications = {}

        for pub in publications:
            year = pub.get("year")
            if year:
                if year not in year_publications:
                    year_publications[year] = []
                year_publications[year].append(pub)

        return year_publications

    def get_publication_metrics(self, publications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate comprehensive publication metrics.
        
        Args:
            publications: List of publications
            
        Returns:
            Dictionary containing publication metrics
        """
        if not publications:
            return {
                "total_count": 0,
                "recent_count": 0,
                "cited_count": 0,
                "average_citations": 0,
                "year_range": None
            }

        total_count = len(publications)
        current_year = datetime.now().year

        # Recent publications (last 3 years)
        recent_count = len([p for p in publications if p.get("year") and p.get("year") >= current_year - 3])

        # Cited publications
        cited_publications = [p for p in publications if p.get("citations", 0) > 0]
        cited_count = len(cited_publications)

        # Average citations
        total_citations = sum(p.get("citations", 0) for p in publications)
        average_citations = total_citations / total_count if total_count > 0 else 0

        # Year range
        years = [p.get("year") for p in publications if p.get("year")]
        year_range = (min(years), max(years)) if years else None

        return {
            "total_count": total_count,
            "recent_count": recent_count,
            "cited_count": cited_count,
            "average_citations": round(average_citations, 2),
            "year_range": year_range,
            "total_citations": total_citations
        }

    def get_citation_analysis(self, publications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get detailed citation analysis for publications.
        
        Args:
            publications: List of publications with citation data
            
        Returns:
            Dictionary containing detailed citation analysis
        """
        if not publications:
            return {
                "total_citations": 0,
                "average_citations": 0,
                "citation_distribution": {},
                "high_impact_papers": [],
                "citation_trends": {}
            }

        # Basic metrics
        total_citations = sum(p.get("citations", 0) for p in publications)
        average_citations = total_citations / len(publications) if publications else 0

        # Citation distribution
        citation_distribution = {
            "0 citations": len([p for p in publications if p.get("citations", 0) == 0]),
            "1-10 citations": len([p for p in publications if 1 <= p.get("citations", 0) <= 10]),
            "11-50 citations": len([p for p in publications if 11 <= p.get("citations", 0) <= 50]),
            "51-100 citations": len([p for p in publications if 51 <= p.get("citations", 0) <= 100]),
            "100+ citations": len([p for p in publications if p.get("citations", 0) > 100])
        }

        # High impact papers (top 10% by citations)
        sorted_by_citations = sorted(publications, key=lambda x: x.get("citations", 0), reverse=True)
        top_count = max(1, len(publications) // 10)  # Top 10%
        high_impact_papers = [
            {
                "title": p.get("title", "Unknown"),
                "citations": p.get("citations", 0),
                "year": p.get("year"),
                "doi": p.get("doi"),
                "venue": p.get("venue")
            }
            for p in sorted_by_citations[:top_count]
        ]

        # Citation trends by year
        citation_trends = {}
        for pub in publications:
            year = pub.get("year")
            citations = pub.get("citations", 0)
            if year:
                if year not in citation_trends:
                    citation_trends[year] = {"count": 0, "total_citations": 0}
                citation_trends[year]["count"] += 1
                citation_trends[year]["total_citations"] += citations

        # Calculate average citations per year
        for year in citation_trends:
            citation_trends[year]["average_citations"] = (
                    citation_trends[year]["total_citations"] / citation_trends[year]["count"]
            )

        return {
            "total_citations": total_citations,
            "average_citations": round(average_citations, 2),
            "citation_distribution": citation_distribution,
            "high_impact_papers": high_impact_papers,
            "citation_trends": citation_trends,
            "median_citations": sorted_by_citations[len(sorted_by_citations) // 2].get("citations",
                                                                                       0) if sorted_by_citations else 0
        }
