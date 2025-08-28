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

logger = logging.getLogger(__name__)

class PublicationProcessor:
    """Unified processor for all publication operations."""
    
    def __init__(self):
        self.cache = {}
    
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
