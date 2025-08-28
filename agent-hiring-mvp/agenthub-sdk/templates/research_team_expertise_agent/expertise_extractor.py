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

    def analyze_member_expertise(self, publications: List[Dict[str, Any]]) -> List[str]:
        """
        Analyze and rank expertise domains for a team member.
        
        Args:
            publications: List of publications for the member
            
        Returns:
            List of top expertise domains
        """
        if not publications:
            return []

        domain_scores = {}

        for pub in publications:
            text_content = f"{pub.get('title', '')} {pub.get('abstract', '')}"
            domains = self.extract_expertise_domains(text_content)

            for domain in domains:
                if domain not in domain_scores:
                    domain_scores[domain] = 0
                domain_scores[domain] += 1

        # Sort domains by frequency and return top ones
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        return [domain for domain, score in sorted_domains[:10]]  # Top 10 domains

    def characterize_expertise_domains(self, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hierarchically aggregate expertise domains from papers → team members → team level using arXiv taxonomy.
        
        Args:
            team_data: Dictionary containing member data and publications
            
        Returns:
            Dictionary containing hierarchical expertise mapping
        """
        try:
            logger.info("Performing hierarchical expertise domain aggregation using arXiv taxonomy...")
            
            # Step 1: Paper-level domain identification and counting
            paper_domain_counts = self._identify_paper_domains(team_data)
            
            # Step 2: Team member-level aggregation
            member_expertise = self._aggregate_member_expertise(team_data, paper_domain_counts)
            
            # Step 3: Team-level aggregation
            team_expertise = self._aggregate_team_expertise(member_expertise)
            
            # Create comprehensive mapping
            expertise_mapping = {
                "paper_level": paper_domain_counts,
                "member_level": member_expertise,
                "team_level": team_expertise,
                "hierarchy_summary": {
                    "total_papers_analyzed": sum(len(member_data.get("publications", [])) for member_data in team_data.values()),
                    "total_domains_identified": len(team_expertise["expertise_domains"]),
                    "total_publications_by_domain": sum(team_expertise["expertise_domains"].values()),
                    "taxonomy_coverage": len(team_expertise["expertise_domains"]) / len(self.expertise_domains) if self.expertise_domains else 0
                }
            }
            
            logger.info(f"Hierarchical aggregation completed: {len(member_expertise)} members, {len(team_expertise['domain_counts'])} domains")
            return expertise_mapping

        except Exception as e:
            logger.error(f"Error in hierarchical expertise aggregation: {str(e)}")
            return {}

    def _identify_paper_domains(self, team_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Step 1: Identify relevant domains for each paper using arXiv taxonomy.
        
        Args:
            team_data: Dictionary containing member data and publications
            
        Returns:
            Dictionary mapping member_name -> paper_id -> domain_counts
        """
        try:
            logger.info("Identifying domains for each paper using arXiv taxonomy...")
            
            paper_domain_counts = {}
            
            for member_name, member_data in team_data.items():
                publications = member_data.get("publications", [])
                if not publications:
                    continue
                
                member_papers = {}
                for i, paper in enumerate(publications):
                    paper_id = paper.get("id", f"{member_name}_paper_{i}")
                    
                    # Extract domains from paper content using taxonomy
                    paper_domains = self._extract_paper_domains(paper)
                    
                    # Count domains for this paper
                    domain_counts = {}
                    for domain in paper_domains:
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1
                    
                    member_papers[paper_id] = {
                        "title": paper.get("title", "Unknown"),
                        "domains": paper_domains,
                        "domain_counts": domain_counts,
                        "total_domains": len(paper_domains)
                    }
                
                paper_domain_counts[member_name] = member_papers
            
            logger.info(f"Identified domains for {sum(len(papers) for papers in paper_domain_counts.values())} papers")
            return paper_domain_counts
            
        except Exception as e:
            logger.error(f"Error identifying paper domains: {str(e)}")
            return {}

    def _extract_paper_domains(self, paper: Dict[str, Any]) -> List[str]:
        """
        Extract relevant domains from a single paper using arXiv taxonomy.
        
        Args:
            paper: Paper data dictionary
            
        Returns:
            List of relevant domain names from arXiv taxonomy
        """
        try:
            # Combine paper text content
            text_content = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            if not text_content.strip():
                return []
            
            # Use the taxonomy-based domain extraction
            domains = []
            text_lower = text_content.lower()
            
            for subject, subject_data in self.arxiv_taxonomy.items():
                if "categories" in subject_data:
                    for category in subject_data["categories"]:
                        if "name" in category:
                            domain_name = category["name"]
                            if self._domain_matches_text(domain_name, text_lower):
                                domains.append(domain_name)
            
            return list(set(domains))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting paper domains: {str(e)}")
            return []

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

    def _aggregate_member_expertise(self, team_data: Dict[str, Any], paper_domain_counts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Step 2: Aggregate expertise for each team member from their papers.
        
        Args:
            team_data: Dictionary containing member data and publications
            paper_domain_counts: Paper-level domain counts from step 1
            
        Returns:
            Dictionary containing member-level expertise aggregation
        """
        try:
            logger.info("Aggregating expertise at team member level...")
            
            member_expertise = {}
            
            for member_name, member_data in team_data.items():
                if member_name not in paper_domain_counts:
                    continue
                
                # Aggregate domains from all papers
                member_domain_counts = {}
                total_papers = len(paper_domain_counts[member_name])
                
                for paper_id, paper_data in paper_domain_counts[member_name].items():
                    for domain, count in paper_data["domain_counts"].items():
                        member_domain_counts[domain] = member_domain_counts.get(domain, 0) + count
                
                # Sort domains by publication count
                sorted_domains = sorted(member_domain_counts.items(), key=lambda x: x[1], reverse=True)
                
                member_expertise[member_name] = {
                    "total_papers": total_papers,
                    "expertise_domains": dict(sorted_domains),  # Single dict: domain -> count
                    "expertise_diversity": len(member_domain_counts),
                    "total_publications_by_domain": sum(member_domain_counts.values()),
                    "average_domains_per_paper": sum(member_domain_counts.values()) / total_papers if total_papers > 0 else 0
                }
            
            logger.info(f"Aggregated expertise for {len(member_expertise)} team members")
            return member_expertise
            
        except Exception as e:
            logger.error(f"Error aggregating member expertise: {str(e)}")
            return {}

    def _aggregate_team_expertise(self, member_expertise: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: Aggregate expertise at the team level from all members.
        
        Args:
            member_expertise: Member-level expertise from step 2
            
        Returns:
            Dictionary containing team-level expertise aggregation
        """
        try:
            logger.info("Aggregating expertise at team level...")
            
            # Aggregate all domains across team
            team_domain_counts = {}
            member_contributions = {}
            
            for member_name, member_data in member_expertise.items():
                member_contributions[member_name] = {}
                
                for domain, count in member_data["expertise_domains"].items():
                    # Add to team total
                    team_domain_counts[domain] = team_domain_counts.get(domain, 0) + count
                    
                    # Track member contribution to this domain
                    member_contributions[member_name][domain] = count
            
            # Sort domains by total count
            sorted_team_domains = sorted(team_domain_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Calculate team-level metrics
            total_domains = len(team_domain_counts)
            total_publications = sum(team_domain_counts.values())
            member_count = len(member_expertise)
            
            team_expertise = {
                "expertise_domains": dict(sorted_team_domains),  # Single dict: domain -> count
                "member_contributions": member_contributions,
                "team_metrics": {
                    "total_domains": total_domains,
                    "total_publications": total_publications,
                    "member_count": member_count,
                    "average_domains_per_member": total_domains / member_count if member_count > 0 else 0,
                    "average_publications_per_domain": total_publications / total_domains if total_domains > 0 else 0
                },
                "domain_strength_analysis": {
                    "strong_domains": [domain for domain, count in sorted_team_domains if count >= 3],  # 3+ publications
                    "moderate_domains": [domain for domain, count in sorted_team_domains if 1 <= count < 3],  # 1-2 publications
                    "emerging_domains": [domain for domain, count in sorted_team_domains if count == 1]  # 1 publication
                }
            }
            
            logger.info(f"Team expertise aggregated: {total_domains} domains, {total_publications} total publications")
            return team_expertise
            
        except Exception as e:
            logger.error(f"Error aggregating team expertise: {str(e)}")
            return {}

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
