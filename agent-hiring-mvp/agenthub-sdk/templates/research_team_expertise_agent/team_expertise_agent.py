#!/usr/bin/env python3

import os
import json
import logging
import time
import re
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from urllib.parse import urlparse, quote
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.chains import RetrievalQA
import arxiv
from lite_llm_handler import LiteLLMHandler

# Import our modular team member extractor
from researcher_data_extractor import ResearcherDataExtractor

# Import our new modular classes
from publication_processor import PublicationProcessor
from expertise_extractor import ExpertiseExtractor
from analysis_engine import AnalysisEngine

class TeamExpertiseAgent:

    def __init__(self):
        """Initialize the team expertise agent."""
        super().__init__()
        # Instance variables for components
        self.vectorstore = None
        self.llm = None
        self.qa_chain = None
        self.team_data = {}
        self.publications_data = {}
        self.collaboration_network = None
        
        # Initialize the team member extractor (will be configured in initialize method)
        self.member_extractor = None
        
        # Initialize our new modular classes
        self.publication_processor = PublicationProcessor()
        self.expertise_extractor = ExpertiseExtractor()
        self.analysis_engine = None  # Will be initialized after LLM setup

    def execute(self, config: Dict[str, Any]) -> Dict[str, Any]:

        try:
            # Validate configuration
            team_members_input = config.get("team_members")
            if not team_members_input:
                raise ValueError("team_members is required for initialization")
            
            # Parse team members input string into list
            team_members = self._parse_team_members(team_members_input)
            
            # Store configuration in state
            self._set_state("config", config)
            
            # Extract configuration parameters
            # Use config expertise_domains if provided, otherwise use taxonomy domains
            config_expertise_domains = config.get("expertise_domains")
            if config_expertise_domains:
                self.expertise_extractor.expertise_domains = config_expertise_domains
                logger.info(f"Using {len(self.expertise_extractor.expertise_domains)} expertise domains from config")
            else:
                # Use taxonomy domains by default
                logger.info(f"Using {len(self.expertise_extractor.expertise_domains)} expertise domains from arXiv taxonomy")
            model_name = config.get("model_name", "gpt-4o-mini")
            temperature = config.get("temperature", 0.1)
            max_pubs = config.get("max_publications_per_member", 50)

            # LLM Configuration - use litellm directly from env
            self.llm_provider = config.get("llm_provider") or os.getenv("LLM_PROVIDER", "azure")
            self.llm_model = model_name
            self.llm = LiteLLMHandler(
                    model=model_name,
                    temperature=temperature
                )
            logger.info(f"Initialized OpenAI LLM via LiteLLM: {model_name}")
            
            # Initialize embeddings - use OpenAI embeddings directly
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            logger.info(f"Initialized OpenAI embeddings")
            
            # Initialize team member extractor with LLM handler
            self.member_extractor = ResearcherDataExtractor(
                llm_handler=self.llm,
            )
            logger.info(f"Initialized TeamMemberExtractor.")
            
            # Initialize analysis engine
            self.analysis_engine = AnalysisEngine(self.publication_processor, self.expertise_extractor)
            logger.info("Initialized AnalysisEngine with PublicationProcessor and ExpertiseExtractor")

            # STEP 1: Data Collection
            logger.info("🔄 STEP 1: Data Collection")
            team_members_data = {member_name: self.member_extractor.extract_researcher_info(member_name, max_pubs) for member_name in team_members}

            # STEP 2: Publication Collection and Deduplication
            logger.info("📚 STEP 2: Publication Collection and Deduplication")
            team_publications = self.publication_processor.get_team_publications(team_members_data)
            logger.info(f"Collected {len(team_publications)} unique publications across team")

            # STEP 3: Team-level Analysis (based on deduplicated publications)
            logger.info("👥 STEP 3: Team-level Analysis")
            team_analysis = self._build_team_expertise_map(team_members_data, team_publications)
            
            # STEP 4: Generate Comprehensive Team Summary
            logger.info("📝 STEP 4: Generating Comprehensive Team Summary")
            team_summary = self._generate_comprehensive_team_summary(team_members_data, team_analysis)
            

            # Create knowledge base for future queries
            if len(team_members_data) > 0:
                self._create_knowledge_base()
            
            # Calculate total publications
            total_publications = sum(len(member.get("publications", [])) for member in team_members_data.values())

            return {
                "status": "success",
                "team_members_analyzed": len(team_members_data),
                "total_publications": total_publications,
                "individual_profiles": team_members_data,
                "team_analysis": team_analysis,
                "team_summary": team_summary,
                "llm_configuration": self._get_llm_config_info(),
                "taxonomy_info": self.expertise_extractor.get_taxonomy_info()
            }
            
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Initialization failed: {str(e)}",
                "team_members_analyzed": 0,
                "total_publications": 0,
                "workflow_summary": "Workflow failed"
            }

    def _parse_team_members(self, team_members_input: str) -> List[str]:
        """
        Parse team members input string into a list of names.
        
        Args:
            team_members_input: String containing team member names (multiline or comma-separated)
            
        Returns:
            List of cleaned team member names
        """
        if not team_members_input or not isinstance(team_members_input, str):
            raise ValueError("team_members must be a non-empty string")
        
        # Split by newlines first, then by commas for any remaining lines
        lines = team_members_input.strip().split('\n')
        members = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Split by comma if the line contains commas
                if ',' in line:
                    comma_separated = [name.strip() for name in line.split(',') if name.strip()]
                    members.extend(comma_separated)
                else:
                    members.append(line)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_members = []
        for member in members:
            if member not in seen:
                seen.add(member)
                unique_members.append(member)
        
        if not unique_members:
            raise ValueError("No valid team member names found in input")
        
        logger.info(f"Parsed {len(unique_members)} team members from input")
        return unique_members

    def _build_team_expertise_map(self, team_data: Dict[str, Any], team_publications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build team expertise map from deduplicated publications."""
        try:
            if not team_data or not team_publications: return {}
            
            team_expertise_domains = {}
            
            # Process each publication to build expertise map
            for pub in team_publications:
                title = pub.get("title", "")
                abstract = pub.get("abstract", "")
                year = pub.get("year")
                citations = pub.get("citations", 0)
                contributors = pub.get("_member_contributors", [])
                
                # Extract expertise domains from existing categories
                publication_domains = pub.get("categories", [])
                if not publication_domains:
                    # Fallback to general research if no categories
                    publication_domains = ["general research"]
                
                # Update team expertise counts
                for domain in publication_domains:
                    if domain not in team_expertise_domains:
                        team_expertise_domains[domain] = {"count": 0, "total_citations": 0, "contributing_members": set()}
                    
                    team_expertise_domains[domain]["count"] += 1
                    team_expertise_domains[domain]["total_citations"] += citations
                    team_expertise_domains[domain]["contributing_members"].update(contributors)
                
                # Track member contributions
                      
            # Convert sets to lists for JSON serialization
            for domain_data in team_expertise_domains.values():
                domain_data["contributing_members"] = list(domain_data["contributing_members"])
            
            # Calculate key metrics
            total_domains = len(team_expertise_domains)
            total_publications = len(team_publications)
            total_citations = sum(pub.get("citations", 0) for pub in team_publications)
            
            # Get detailed citation analysis
            citation_analysis = self.publication_processor.get_citation_analysis(team_publications)
            
            # Build analysis
            team_analysis = {
                "expertise_domains": team_expertise_domains,
                "team_metrics": {
                    "total_domains": total_domains,
                    "total_publications": total_publications,
                    "total_citations": total_citations,
                    "member_count": len(team_data)
                },
                "collaboration_insights": {
                    "multi_author_papers": len([p for p in team_publications if len(p.get("_member_contributors", [])) > 1]),
                    "single_author_papers": len([p for p in team_publications if len(p.get("_member_contributors", [])) == 1])
                },
                "citation_analysis": citation_analysis
            }
            
            logger.info(f"Team expertise map built: {total_domains} domains, {total_publications} publications")
            return team_analysis
            
        except Exception as e:
            logger.error(f"Error building team expertise map: {str(e)}")
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
                
                for domain, count in member_data["domain_counts"].items():
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

    def _generate_comprehensive_team_summary(self, individual_profiles: Dict[str, Any], team_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate team summary with key insights."""
        try:
            # Handle case where team_analysis might be None or empty
            if not team_analysis:
                team_analysis = {}
            
            # Extract key metrics with safe defaults
            team_size = len(individual_profiles)
            team_metrics = team_analysis.get("team_metrics", {})
            total_publications = team_metrics.get("total_publications", 0) if team_metrics else 0
            total_domains = team_metrics.get("total_domains", 0) if team_metrics else 0
            
            # Get top expertise domains with safe defaults
            expertise_domains = team_analysis.get("expertise_domains", {})
            top_domains = []
            if expertise_domains:
                try:
                    top_domains = sorted(expertise_domains.items(), key=lambda x: x[1].get("count", 0) if isinstance(x[1], dict) else 0, reverse=True)[:3]
                except (KeyError, TypeError):
                    top_domains = []
            
            # Identify most influential members
            influential_members = []
            for name, profile in individual_profiles.items():
                h_index = profile.get("citation_metrics", {}).get("h_index", 0)
                total_citations = profile.get("citation_metrics", {}).get("total_citations", 0)
                influence_score = (h_index * 0.6) + (total_citations * 0.4)
                
                influential_members.append({
                    "member_name": name,
                    "h_index": h_index,
                    "total_citations": total_citations,
                    "influence_score": influence_score
                })
            
            # Sort and get top 3
            influential_members.sort(key=lambda x: x["influence_score"], reverse=True)
            top_influential = influential_members[:3]
            
            # Generate LLM summary if available
            summary_text = "Team summary not available"
            if hasattr(self, 'llm') and self.llm:
                from langchain.schema import HumanMessage, SystemMessage
                
                # Build domain summary safely
                domain_summary = "None identified"
                if top_domains:
                    try:
                        domain_summary = ', '.join([f'{domain} ({data.get("count", 0) if isinstance(data, dict) else 0} pubs)' for domain, data in top_domains])
                    except (KeyError, TypeError):
                        domain_summary = "Multiple domains identified"
                
                prompt = f"""Summarize this research team in 2-3 paragraphs:
                Team: {team_size} members, {total_publications} publications, {total_domains} expertise domains
                Top domains: {domain_summary}
                Top members: {', '.join([f'{m["member_name"]} (H-index: {m["h_index"]}, {m["total_citations"]} citations)' for m in top_influential])}"""
                
                messages = [SystemMessage(content="You are a research analyst."), HumanMessage(content=prompt)]
                try:
                    response = self.llm.invoke(messages)
                    summary_text = response.content if hasattr(response, 'content') else "Team summary generated"
                except Exception as e:
                    logger.warning(f"LLM summary generation failed: {str(e)}")
                    summary_text = "Team summary generation failed"
            
            return {
                "team_overview": {"team_size": team_size, "total_publications": total_publications, "total_domains": total_domains},
                "top_expertise_domains": top_domains,
                "most_influential_members": top_influential,
                "summary_text": summary_text
            }
            
        except Exception as e:
            logger.error(f"Error generating team summary: {str(e)}")
            return {"error": str(e), "summary_text": "Error generating summary"}
    
    def _create_knowledge_base(self):
        """Create knowledge base and vector store for future queries."""
        try:
            # Check if embeddings are available
            if not self.embeddings:
                logger.warning("OpenAI embeddings not available. Skipping knowledge base creation.")
                return
                
            logger.info("Creating knowledge base...")

            # Prepare documents for vector store
            documents = []
            for member_name, member_data in self.team_data.items():
                if member_data and "publications" in member_data:
                    # Create document from member profile
                    profile_text = f"""
                    Team Member: {member_name}
                    Expertise: {', '.join(member_data.get('expertise_domains', []))}
                    Publications: {len(member_data.get('publications', []))}
                    Citations: {member_data.get('citation_metrics', {}).get('total_citations', 0)}
                    """
                    
                    documents.append(Document(
                        page_content=profile_text,
                        metadata={"member_name": member_name, "type": "profile"}
                    ))
                    
                    # Add publication documents
                    for pub in member_data.get("publications", [])[:10]:  # Limit to first 10
                        pub_text = f"""
                        Title: {pub.get('title', '')}
                        Authors: {', '.join(pub.get('authors', []))}
                        Abstract: {pub.get('abstract', '')}
                        Year: {pub.get('year', '')}
                        Venue: {pub.get('venue', '')}
                        """
                        
                        documents.append(Document(
                            page_content=pub_text,
                            metadata={"member_name": member_name, "type": "publication", "title": pub.get('title', '')}
                        ))
            
            if documents:
                # Create vector store
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                texts = text_splitter.split_documents(documents)
                
                self.vectorstore = FAISS.from_documents(texts, self.embeddings)
                logger.info(f"Created knowledge base with {len(texts)} text chunks")
            else:
                logger.warning("No documents available for knowledge base creation")
                
        except Exception as e:
            logger.error(f"Error creating knowledge base: {str(e)}")

    def _set_state(self, key: str, value: Any) -> None:
        """Set state for the agent (placeholder for function agents)."""
        # Function agents don't maintain persistent state, but we can store in instance
        if not hasattr(self, '_state'):
            self._state = {}
        self._state[key] = value

    def _get_llm_config_info(self) -> Dict[str, Any]:
        """Get LLM configuration information."""
        return {
            "model": self.llm_model,
            "provider": self.llm_provider,
            "temperature": getattr(self.llm, 'temperature', 0.1)
        }


def main(config):
    """
    Simple example of using the Team Expertise Analysis Agent.
    """
    try:
        # Create agent and execute
        agent = TeamExpertiseAgent()
        result = agent.execute(config=config)

        # Display results
        if result.get("status") == "success":
            print(
                f"✅ Analysis completed: {result.get('team_members_analyzed', 0)} members, {result.get('total_publications', 0)} publications")
        else:
            print(f"❌ Analysis failed: {result.get('message', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    # Load environment variables
    load_dotenv()

    # Example configuration
    config = {
        "team_members": "George Kour, Boaz Carmeli",
        "model_name": "azure/gpt-4o-2024-08-06",
        "temperature": 0.1,
        "max_publications_per_member": 30
    }

    main(config)