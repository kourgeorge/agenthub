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

class TeamExpertiseAgent:

    def __init__(self):
        self.max_pubs = 50
        self.llm = None
        self.team_data = {}
        self.publications_data = {}
        self.collaboration_network = None
        
        # Initialize the team member extractor (will be configured in initialize method)
        self.member_extractor = None
        
        # Initialize our new modular classes
        self.publication_processor = PublicationProcessor()
        self.expertise_extractor = ExpertiseExtractor()

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:

        try:
            # Validate configuration
            team_members_input = input_data.get("team_members")
            if not team_members_input:
                raise ValueError("team_members is required for initialization")
            
            # Parse team members input string into list
            team_members = self._parse_team_members(team_members_input)
            
            # Use config expertise_domains if provided, otherwise use taxonomy domains
            config_expertise_domains = input_data.get("expertise_domains")

            self.expertise_extractor.expertise_domains = config_expertise_domains

            self.max_pubs = input_data.get("max_publications_per_member", 50)

            self.llm = LiteLLMHandler(
                    model=input_data.get("model_name", "gpt-4o-mini"),
                    temperature=input_data.get("temperature", 0.1)
                )

            # Initialize team member extractor with LLM handler
            self.member_extractor = ResearcherDataExtractor(
                llm_handler=self.llm,
            )

            # STEP 1: Data Collection
            team_members_data = {member_name: self.member_extractor.extract_researcher_info(member_name, self.max_pubs) for member_name in team_members}

            team_members_data = self.sort_members_by_rank(team_members_data)
            self.team_data = team_members_data  # Store for later use
            logger.info(f"Collected data for {len(team_members_data)} team members.\nHighly ranked: {list(team_members_data.keys())[:5]}")

            # STEP 2: Publication Collection and Deduplication
            team_publications = self.publication_processor.get_team_publications(team_members_data)

            # STEP 3: Team-level Analysis (based on deduplicated publications)
            logger.info("👥 STEP 3: Team-level Analysis")
            team_analysis = self._build_team_expertise_map(team_members_data, team_publications)
            
            # STEP 4: Generate Comprehensive Team Summary
            logger.info("📝 STEP 4: Generating Comprehensive Team Summary")
            team_summary = self._generate_comprehensive_team_summary(team_members_data, team_analysis)

            # Calculate total publications

            return {
                "status": "success",
                "team_members_analyzed": len(team_members_data),
                "individual_profiles": team_members_data,
                "team_analysis": team_analysis,
                "team_summary": team_summary,
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

    def sort_members_by_rank(self, team_members_data):
        sorted_members = sorted(team_members_data.items(),
                                key=lambda x: x[1].get("citation_metrics", {}).get("h_index", 0), reverse=True)
        if not sorted_members or all(v.get("citation_metrics", {}).get("h_index", 0) == 0 for k, v in sorted_members):
            sorted_members = sorted(team_members_data.items(),
                                    key=lambda x: x[1].get("citation_metrics", {}).get("total_citations", 0),
                                    reverse=True)

        return dict(sorted_members)


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
            for member in team_data.values():
                member_expertise_data = member.get("domain_expertise", [])
                domains = [d["domain"] for d in member_expertise_data]

                # Update team expertise counts
                for domain in domains:
                    member_rank = member_expertise_data[next(i for i, d in enumerate(member_expertise_data) if d["domain"] == domain)]["rank"]
                    if domain not in team_expertise_domains:
                        team_expertise_domains[domain] = {"count": 0, "contributing_members": set()}

                    team_expertise_domains[domain]["count"] += member_rank
                    team_expertise_domains[domain]["contributing_members"].update([member.get("name", "Unknown")])
                
                # Track member contributions
                      

            # Calculate key metrics
            total_domains = len(team_expertise_domains)
            total_publications = len(team_publications)
            total_citations = sum(pub.get("citations", 0) for pub in team_publications)
            
            # Get detailed citation analysis
            citation_analysis = self.publication_processor.get_citation_analysis(team_publications)
            
            # Get collaboration network analysis
            team_members = list(team_data.keys())
            collaboration_network = self.publication_processor.get_team_collaboration_network(team_publications, team_members)
            
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
                "collaboration_network": collaboration_network,
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
                textual_summary = profile.get("textual_summary", "No summary available")
                domains = profile.get("domain_expertise", []),
                influential_members.append({
                    "member_name": name,
                    "h_index": h_index,
                    "total_citations": total_citations,
                    "domain_expertise": ";".join([(f"Domain: {d['domain']}. Rank:{d['rank']}") for d in domains[0]]),
                    "summary": textual_summary,
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
                
                prompt = f"""Summarize this research team in few paragraphs by characterizing their expertise, publication impact, and collaboration dynamics.:
                You should mention the top expertise domains, the most influential members, and any notable collaboration patterns.
                
                Team: {team_size} members, {total_publications} publications, {total_domains} expertise domains
                Top domains: {domain_summary}
                Top members: {'\n'.join([f'{m["member_name"]} (H-index: {m["h_index"]}, {m["total_citations"]} citations), summary: {m["summary"]}. domains info: {m['domain_expertise']}' for m in top_influential])}"""
                
                messages = [SystemMessage(content="You are a research analyst. Your goal is to give a high level overview of the team expertise levels and domains."), HumanMessage(content=prompt)]
                try:
                    response = self.llm.invoke(messages)
                    summary_text = response.content if hasattr(response, 'content') else "Team summary generated"
                except Exception as e:
                    logger.warning(f"LLM summary generation failed: {str(e)}")
                    summary_text = "Team summary generation failed"

            return {
                "total_domains": total_domains,
                "top_expertise_domains": top_domains,
                "most_influential_members": top_influential,
                "summary_text": summary_text
            }
            
        except Exception as e:
            logger.error(f"Error generating team summary: {str(e)}")
            return {"error": str(e), "summary_text": "Error generating summary"}


def main(config):
    """
    Simple example of using the Team Expertise Analysis Agent.
    """
    try:
        # Create agent and execute
        agent = TeamExpertiseAgent()
        result = agent.execute(input_data=config)

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
    input_data = {
        "team_members": "George Kour, Boaz Carmeli",
        "model_name": "azure/gpt-4o-2024-08-06",
        "temperature": 0.1,
        "max_publications_per_member": 30
    }

    main(input_data)