#!/usr/bin/env python3
"""
Expertise Extractor

Handles all expertise domain extraction and analysis. This eliminates duplicate 
logic for domain extraction across the main agent class.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ExpertiseExtractor:
    """Unified extractor for all expertise domain operations."""
    
    def __init__(self):
        self.arxiv_taxonomy = self._load_arxiv_taxonomy()
        self.default_domains = [
            "NLP", "Security", "Machine Learning", "Quantum Computing",
            "Operating Systems", "Medicine", "Neurology", "Computer Vision",
            "Robotics", "Data Science", "Software Engineering", "AI Ethics",
            "Distributed Systems", "Database Systems", "Computer Networks",
            "Human-Computer Interaction", "Software Testing", "DevOps",
            "Cloud Computing", "Mobile Development", "Web Technologies"
        ]
        self.expertise_domains = self._extract_taxonomy_domains()

    def _load_arxiv_taxonomy(self) -> Dict[str, Any]:
        """
        Load ArXiv subject taxonomy from JSON file.
        
        Returns:
            Dictionary containing the taxonomy data
        """
        try:
            taxonomy_path = Path(__file__).parent / "arxiv_taxonomy.json"
            if taxonomy_path.exists():
                with open(taxonomy_path, 'r', encoding='utf-8') as f:
                    taxonomy = json.load(f)
                logger.info(f"Loaded ArXiv taxonomy with {len(taxonomy)} main subjects")
                return taxonomy
            else:
                logger.warning("ArXiv taxonomy file not found, using default domains")
                return {}
        except Exception as e:
            logger.error(f"Error loading ArXiv taxonomy: {str(e)}")
            return {}

    def _extract_taxonomy_domains(self) -> List[str]:
        """
        Extract all domain names from the ArXiv taxonomy.
        
        Returns:
            List of all domain names from the taxonomy
        """
        try:
            if not self.arxiv_taxonomy:
                return self.default_domains
            
            domains = []
            for subject, subject_data in self.arxiv_taxonomy.items():
                if "categories" in subject_data:
                    for category in subject_data["categories"]:
                        if "name" in category:
                            domains.append(category["name"])
            
            logger.info(f"Extracted {len(domains)} domains from ArXiv taxonomy")
            return domains
            
        except Exception as e:
            logger.error(f"Error extracting taxonomy domains: {str(e)}")
            return self.default_domains

    def extract_expertise_domains(self, text: str) -> List[str]:
        """
        Extract expertise domains from text content using ArXiv taxonomy.
        
        Args:
            text: Text content to analyze
            
        Returns:
            List of identified expertise domains
        """
        try:
            if not text:
                return []
            
            text_lower = text.lower()
            identified_domains = []
            
            # Check against ArXiv taxonomy domains
            for domain in self.expertise_domains:
                domain_lower = domain.lower()
                if domain_lower in text_lower:
                    identified_domains.append(domain)
            
            # Add some common variations and synonyms for better matching
            domain_variations = {
                "machine learning": ["Machine Learning", "ML", "AI/ML"],
                "artificial intelligence": ["Artificial Intelligence", "AI", "Intelligent Systems"],
                "natural language processing": ["Computation and Language", "NLP", "Natural Language Processing"],
                "computer vision": ["Computer Vision and Pattern Recognition", "CV", "Image Processing"],
                "data science": ["Data Structures and Algorithms", "Data Science", "Data Analytics"],
                "software engineering": ["Software Engineering", "Software Development", "Programming"],
                "cybersecurity": ["Cryptography and Security", "Security", "Information Security"],
                "distributed systems": ["Distributed, Parallel, and Cluster Computing", "Distributed Systems"],
                "robotics": ["Robotics", "Robots", "Automation"],
                "neural networks": ["Neural and Evolutionary Computing", "Neural Networks", "Deep Learning"],
                "database systems": ["Databases", "Database Systems", "Data Management"],
                "operating systems": ["Operating Systems", "OS", "System Programming"],
                "networks": ["Networking and Internet Architecture", "Computer Networks", "Network Security"],
                "human-computer interaction": ["Human-Computer Interaction", "HCI", "User Interface"],
                "quantum computing": ["Quantum Physics", "Quantum Computing", "Quantum Information"]
            }
            
            # Check for variations
            for variation, domains in domain_variations.items():
                if variation in text_lower:
                    for domain in domains:
                        if domain not in identified_domains:
                            identified_domains.append(domain)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_domains = []
            for domain in identified_domains:
                if domain not in seen:
                    seen.add(domain)
                    unique_domains.append(domain)
            
            return unique_domains[:8]  # Limit to top 8 domains for relevance
            
        except Exception as e:
            logger.error(f"Error extracting expertise domains: {str(e)}")
            return []

    def get_taxonomy_info(self) -> Dict[str, Any]:
        """
        Get taxonomy information for logging and debugging.
        
        Returns:
            Dictionary containing taxonomy details
        """
        try:
            if not self.arxiv_taxonomy:
                return {
                    "source": "default_domains",
                    "total_domains": len(self.default_domains),
                    "domains": self.default_domains[:10]  # Show first 10
                }
            
            # Count total categories across all subjects
            total_categories = 0
            subject_counts = {}
            for subject, subject_data in self.arxiv_taxonomy.items():
                if "categories" in subject_data:
                    category_count = len(subject_data["categories"])
                    total_categories += category_count
                    subject_counts[subject] = category_count
            
            return {
                "source": "arxiv_taxonomy",
                "total_subjects": len(self.arxiv_taxonomy),
                "total_categories": total_categories,
                "subject_breakdown": subject_counts,
                "sample_domains": self.expertise_domains[:15]  # Show first 15 domains
            }
            
        except Exception as e:
            logger.error(f"Error getting taxonomy info: {str(e)}")
            return {"source": "error", "message": str(e)}
