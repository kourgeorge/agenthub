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


# Import the base PersistentAgent class from the SDK
from agenthub_sdk.agent import PersistentAgent

# Import our modular team member extractor
from researcher_data_extractor import ResearcherDataExtractor

# Import our new modular classes
from publication_processor import PublicationProcessor
from expertise_extractor import ExpertiseExtractor
from analysis_engine import AnalysisEngine

class TeamExpertiseAgent(PersistentAgent):
    """
    Team Expertise Analysis Agent
    
    This agent demonstrates the proper way to implement a persistent agent:
    1. Inherit from PersistentAgent
    2. Implement initialize(), execute(), cleanup()
    3. Use _get_state()/_set_state() for state management
    4. Use _is_initialized()/_mark_initialized() for lifecycle management
    5. Focus on business logic only - no platform concerns
    
    The platform will call these methods directly:
    - initialize(config) -> called once to set up the agent
    - execute(input_data) -> called for each query
    - cleanup() -> called when agent is no longer needed
    """

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



    def initialize(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the agent with team configuration following a structured workflow:
        
        1. Data Collection: Collect accessible information for each team member
        1.5. Resource Enrichment: Enrich papers and extract domain keywords
        2. Analysis: Extract textual profile summaries and objective metrics
        2.5. Expertise Characterization: Map expertise domains with publication counts
        3. Team Analysis: Analyze team competency and interests
        """
        start_time = time.time()
        
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
            
            # Store all results in state
            self.team_data = team_members_data
            self._set_state("team_members_data", team_members_data)
            self._set_state("individual_profiles", team_members_data)
            self._set_state("team_analysis", team_analysis)
            self._set_state("team_summary", team_summary)
            
            # Create knowledge base for future queries
            if len(team_members_data) > 0:
                self._create_knowledge_base()
            
            # Mark as initialized
            self._mark_initialized()

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


    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute queries about team expertise, individual analysis, or research insights.
        
        Args:
            input_data: Input data containing query and analysis parameters
            
        Returns:
            Dict with comprehensive analysis results
        """
        start_time = time.time()

        try:
            # Check if agent is initialized
            if not self._is_initialized():
                return {
                    "status": "error",
                    "message": "Agent not initialized. Please call initialize() first.",
                    "query": input_data.get("query", ""),
                    "query_type": input_data.get("query_type", "unknown")
                }

            # Extract query parameters
            query = input_data.get("query", "")
            query_type = input_data.get("query_type", "team_overview")
            focus_member = input_data.get("focus_member", "")
            focus_domain = input_data.get("focus_domain", "")
            analysis_depth = input_data.get("analysis_depth", "detailed")
            include_visualizations = input_data.get("include_visualizations", True)

            # Load state data
            self.team_data = self._get_state("team_data", {})
            self.publications_data = self._get_state("publications_data", {})
            self.team_expertise_report = self._get_state("team_expertise_report", {})
            self.individual_research_reports = self._get_state("individual_research_reports", [])

            # Process query based on type using our analysis engine
            if query_type == "team_overview":
                answer, insights = self.analysis_engine.analyze_team_overview(self.team_data, analysis_depth)
            elif query_type == "individual_analysis":
                answer, insights = self.analysis_engine.analyze_individual_member(self.team_data, focus_member, analysis_depth)
            elif query_type == "expertise_domain_analysis":
                answer, insights = self.analysis_engine.analyze_expertise_domain(self.team_data, focus_domain, analysis_depth)
            elif query_type == "research_directions":
                answer, insights = self.analysis_engine.analyze_research_directions(self.team_data, analysis_depth)
            elif query_type == "collaboration_insights":
                answer, insights = self._analyze_collaboration_insights(analysis_depth)
            elif query_type == "future_recommendations":
                answer, insights = self._generate_future_recommendations(analysis_depth)
            elif query_type == "custom_question":
                answer, insights = self._process_custom_question(query, analysis_depth)
            else:
                answer, insights = self._process_custom_question(query, analysis_depth)

            # Generate data sources information
            data_sources = self._generate_data_sources_info()

            # Calculate confidence score using our analysis engine
            confidence_score = self.analysis_engine.calculate_confidence_score(query_type, analysis_depth, self.team_data)

            return {
                "answer": answer,
                "query": query,
                "query_type": query_type,
                "insights": insights,
                "data_sources": data_sources,
                "confidence_score": confidence_score
            }

        except Exception as e:
            logger.error(f"Execution failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Execution failed: {str(e)}",
                "query": input_data.get("query", ""),
                "query_type": input_data.get("query_type", "unknown")
            }

    def _analyze_collaboration_insights(self, analysis_depth: str) -> Tuple[str, Dict[str, Any]]:
        """Analyze collaboration patterns and insights."""
        try:
            collaboration_metrics = self._get_state("collaboration_metrics", {})

            if not collaboration_metrics:
                return "No collaboration data available for analysis.", {}

            # Generate analysis
            analysis_parts = [
                f"## Collaboration Insights Analysis",
                f"",
                f"**Collaboration Metrics:**",
                f"- Total Collaborations: {collaboration_metrics.get('total_collaborations', 0)}",
                f"- Collaboration Density: {collaboration_metrics.get('collaboration_density', 0):.3f}",
                f"- Clustering Coefficient: {collaboration_metrics.get('clustering_coefficient', 0):.3f}",
                f""
            ]

            # Centrality analysis
            centrality_measures = collaboration_metrics.get("centrality_measures", {})
            if centrality_measures:
                analysis_parts.append("**Team Member Centrality:**")

                # Sort by degree centrality
                sorted_members = sorted(
                    centrality_measures.items(),
                    key=lambda x: x[1].get("degree", 0),
                    reverse=True
                )

                for member_name, measures in sorted_members[:5]:
                    degree = measures.get("degree", 0)
                    betweenness = measures.get("betweenness", 0)
                    closeness = measures.get("closeness", 0)

                    analysis_parts.append(f"- **{member_name}**:")
                    analysis_parts.append(f"  - Degree Centrality: {degree:.3f}")
                    analysis_parts.append(f"  - Betweenness Centrality: {betweenness:.3f}")
                    analysis_parts.append(f"  - Closeness Centrality: {closeness:.3f}")

                analysis_parts.append("")

            # Collaboration recommendations
            analysis_parts.extend([
                f"**Collaboration Insights:**",
                f"1. **Central Members**: {sorted_members[0][0] if sorted_members else 'N/A'} shows highest collaboration activity",
                f"2. **Bridge Builders**: Members with high betweenness centrality facilitate team communication",
                f"3. **Collaboration Density**: {'High' if collaboration_metrics.get('collaboration_density', 0) > 0.5 else 'Moderate'} team collaboration",
                f"4. **Network Structure**: {'Clustered' if collaboration_metrics.get('clustering_coefficient', 0) > 0.3 else 'Distributed'} collaboration patterns"
            ])

            answer = "\n".join(analysis_parts)

            insights = {
                "team_strengths": [
                    f"Strong collaboration network with {collaboration_metrics.get('total_collaborations', 0)} connections",
                    f"Balanced collaboration distribution",
                    f"Effective team communication patterns"
                ],
                "individual_highlights": [
                    {
                        "name": member_name,
                        "expertise": ["Collaboration Leadership"],
                        "key_contributions": f"Centrality score: {measures.get('degree', 0):.3f}"
                    }
                    for member_name, measures in sorted_members[:3]
                ] if sorted_members else [],
                "research_directions": [
                    "Leverage central members for project coordination",
                    "Develop collaboration opportunities for peripheral members",
                    "Build on existing collaboration strengths"
                ],
                "collaboration_patterns": {
                    "network_density": collaboration_metrics.get("collaboration_density", 0),
                    "clustering": collaboration_metrics.get("clustering_coefficient", 0),
                    "centrality_distribution": "Balanced" if len(sorted_members) > 2 else "Concentrated"
                }
            }

            return answer, insights

        except Exception as e:
            logger.error(f"Error in collaboration insights analysis: {str(e)}")
            return f"Error analyzing collaboration insights: {str(e)}", {}

    def _generate_future_recommendations(self, analysis_depth: str) -> Tuple[str, Dict[str, Any]]:
        """Generate future recommendations for the team."""
        try:
            if not self.team_data:
                return "No team data available for future recommendations.", {}

            # Analyze current state
            team_size = len(self.team_data)
            total_publications = sum(len(member.get("publications", [])) for member in self.team_data.values())

            # Identify strengths and opportunities
            all_domains = []
            for member_data in self.team_data.values():
                all_domains.extend(member_data.get("expertise_domains", []))

            domain_counts = {}
            for domain in all_domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

            top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            # Generate recommendations
            analysis_parts = [
                f"## Future Recommendations",
                f"",
                f"**Current Team Assessment:**",
                f"- Team Size: {team_size} members",
                f"- Total Publications: {total_publications}",
                f"- Top Expertise Areas: {', '.join([domain for domain, count in top_domains[:3]])}",
                f""
            ]

            # Strategic recommendations
            analysis_parts.extend([
                f"**Strategic Recommendations:**",
                f"",
                f"1. **Research Leadership**",
                f"   - Establish {top_domains[0][0] if top_domains else 'key areas'} as team signature research",
                f"   - Pursue high-impact publications in core expertise areas",
                f"   - Develop research roadmap for next 3-5 years",
                f"",
                f"2. **Team Growth**",
                f"   - Consider expanding team size to {min(team_size + 2, 15)} members",
                f"   - Focus hiring on complementary expertise areas",
                f"   - Develop junior team members through mentorship programs",
                f"",
                f"3. **Collaboration Expansion**",
                f"   - Build partnerships with industry leaders in {top_domains[0][0] if top_domains else 'core areas'}",
                f"   - Establish academic collaborations with top institutions",
                f"   - Participate in international research consortia",
                f"",
                f"4. **Innovation Focus**",
                f"   - Invest in emerging technologies related to team expertise",
                f"   - Develop interdisciplinary research initiatives",
                f"   - Create innovation labs or research centers",
                f"",
                f"5. **Knowledge Management**",
                f"   - Implement systematic knowledge sharing processes",
                f"   - Develop team knowledge base and best practices",
                f"   - Regular team research presentations and discussions"
            ])

            # Implementation timeline
            analysis_parts.extend([
                f"",
                f"**Implementation Timeline:**",
                f"",
                f"**Short-term (3-6 months):**",
                f"- Define research priorities and roadmap",
                f"- Initiate collaboration discussions",
                f"- Develop knowledge sharing processes",
                f"",
                f"**Medium-term (6-18 months):**",
                f"- Execute research roadmap",
                f"- Establish key partnerships",
                f"- Implement team growth initiatives",
                f"",
                f"**Long-term (18+ months):**",
                f"- Achieve research leadership position",
                f"- Expand team to target size",
                f"- Establish innovation centers"
            ])

            answer = "\n".join(analysis_parts)

            insights = {
                "team_strengths": [
                    f"Strong foundation with {total_publications} publications",
                    f"Expertise in {len(top_domains)} key domains",
                    f"Potential for research leadership"
                ],
                "individual_highlights": [
                    {
                        "name": "Team Collective",
                        "expertise": [domain for domain, count in top_domains[:3]],
                        "key_contributions": f"Combined expertise across {len(top_domains)} domains"
                    }
                ],
                "research_directions": [
                    f"Establish {top_domains[0][0] if top_domains else 'core areas'} as signature research",
                    "Develop interdisciplinary research initiatives",
                    "Build industry and academic partnerships",
                    "Expand team size and expertise coverage"
                ],
                "collaboration_patterns": {
                    "current_capacity": team_size,
                    "growth_potential": "High" if team_size < 15 else "Moderate",
                    "collaboration_opportunities": "Extensive"
                }
            }

            return answer, insights

        except Exception as e:
            logger.error(f"Error generating future recommendations: {str(e)}")
            return f"Error generating recommendations: {str(e)}", {}

    def _process_custom_question(self, query: str, analysis_depth: str) -> Tuple[str, Dict[str, Any]]:
        """Process custom questions using the knowledge base."""
        try:
            if not query:
                return "No query provided.", {}

            # Try to use RAG if available
            if self.qa_chain:
                try:
                    rag_answer = self.qa_chain.run(query)
                    answer = f"## Custom Query Analysis\n\n**Query:** {query}\n\n**Answer:** {rag_answer}"
                except Exception as e:
                    logger.warning(f"RAG query failed: {str(e)}")
                    answer = self._generate_custom_answer(query, analysis_depth)
            else:
                answer = self._generate_custom_answer(query, analysis_depth)

            insights = {
                "team_strengths": ["Custom analysis capability", "Comprehensive team knowledge base"],
                "individual_highlights": [],
                "research_directions": ["Custom research inquiries", "Specialized analysis requests"],
                "collaboration_patterns": {"analysis_type": "custom", "depth": analysis_depth}
            }

            return answer, insights

        except Exception as e:
            logger.error(f"Error processing custom question: {str(e)}")
            return f"Error processing custom question: {str(e)}", {}

    def _generate_custom_answer(self, query: str, analysis_depth: str) -> str:
        """Generate custom answer when RAG is not available."""
        try:
            # Simple keyword-based analysis
            query_lower = query.lower()

            if "publication" in query_lower or "paper" in query_lower:
                return self._analyze_publications_custom(query)
            elif "expertise" in query_lower or "skill" in query_lower:
                return self._analyze_expertise_custom(query)
            elif "collaboration" in query_lower or "team" in query_lower:
                return self._analyze_collaboration_custom(query)
            elif "research" in query_lower or "direction" in query_lower:
                return self._analyze_research_custom(query)
            else:
                return f"## Custom Analysis\n\n**Query:** {query}\n\n**Answer:** This is a general query about the team. Based on the available data, I can provide insights about team composition, expertise areas, and research activities. Please specify if you'd like more detailed information about publications, expertise, collaboration, or research directions."

        except Exception as e:
            logger.error(f"Error generating custom answer: {str(e)}")
            return f"Error generating custom answer: {str(e)}"

    def _analyze_publications_custom(self, query: str) -> str:
        """Custom analysis of publications."""
        try:
            total_pubs = sum(len(member.get("publications", [])) for member in self.team_data.values())
            recent_pubs = sum(
                len([p for p in member.get("publications", []) if
                     p.get("year") and p.get("year") >= datetime.now().year - 3])
                for member in self.team_data.values()
            )

            return f"""
## Publication Analysis

**Query:** {query}

**Key Findings:**
- Total Publications: {total_pubs}
- Recent Publications (last 3 years): {recent_pubs}
- Publication Distribution: {', '.join([f'{member}: {len(member_data.get("publications", []))}' for member, member_data in list(self.team_data.items())[:5]])}

**Insights:**
The team has a strong publication record with {total_pubs} total publications. {recent_pubs} publications were published in the last 3 years, indicating ongoing research activity.
            """.strip()

        except Exception as e:
            return f"Error analyzing publications: {str(e)}"

    def _analyze_expertise_custom(self, query: str) -> str:
        """Custom analysis of expertise."""
        try:
            all_domains = []
            for member_data in self.team_data.values():
                all_domains.extend(member_data.get("expertise_domains", []))

            domain_counts = {}
            for domain in all_domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

            top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            return f"""
## Expertise Analysis

**Query:** {query}

**Key Findings:**
- Total Expertise Domains: {len(set(all_domains))}
- Top Expertise Areas: {', '.join([f'{domain} ({count} members)' for domain, count in top_domains])}

**Insights:**
The team covers {len(set(all_domains))} expertise domains with strong representation in {top_domains[0][0] if top_domains else 'key areas'}.
            """.strip()

        except Exception as e:
            return f"Error analyzing expertise: {str(e)}"

    def _analyze_collaboration_custom(self, query: str) -> str:
        """Custom analysis of collaboration."""
        try:
            collaboration_metrics = self._get_state("collaboration_metrics", {})

            return f"""
## Collaboration Analysis

**Query:** {query}

**Key Findings:**
- Total Collaborations: {collaboration_metrics.get('total_collaborations', 0)}
- Collaboration Density: {collaboration_metrics.get('collaboration_density', 0):.3f}
- Team Size: {len(self.team_data)}

**Insights:**
The team shows {'strong' if collaboration_metrics.get('collaboration_density', 0) > 0.5 else 'moderate'} collaboration patterns with {collaboration_metrics.get('total_collaborations', 0)} total collaborations.
            """.strip()

        except Exception as e:
            return f"Error analyzing collaboration: {str(e)}"

    def _analyze_research_custom(self, query: str) -> str:
        """Custom analysis of research directions."""
        try:
            all_domains = []
            for member_data in self.team_data.values():
                all_domains.extend(member_data.get("expertise_domains", []))

            domain_counts = {}
            for domain in all_domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

            top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            total_pubs = sum(len(member.get("publications", [])) for member in self.team_data.values())

            return f"""
## Research Direction Analysis

**Query:** {query}

**Key Findings:**
- Total Publications: {total_pubs}
- Research Areas: {len(set(all_domains))}
- Top Research Directions: {', '.join([f'{domain} ({count} members)' for domain, count in top_domains])}

**Insights:**
The team demonstrates strong research capabilities with {total_pubs} publications across {len(set(all_domains))} research areas, indicating diverse and active research programs.
            """.strip()

        except Exception as e:
            return f"Error analyzing research directions: {str(e)}"


    def _generate_data_sources_info(self) -> List[Dict[str, str]]:
        """Generate information about data sources used."""
        try:
            sources = []

            # Add academic sources
            sources.extend([
                {
                    "source": "Semantic Scholar",
                    "type": "Academic Profile",
                    "relevance": "High - Author profiles and publications"
                },
                {
                    "source": "arXiv",
                    "type": "Preprint Repository",
                    "relevance": "High - Research papers and abstracts"
                }
            ])

            # Add team data
            sources.append({
                "source": "Team Member Profiles",
                "type": "Structured Data",
                "relevance": "High - Role, institution, research interests"
            })

            # Add publications
            total_pubs = sum(len(member.get("publications", [])) for member in self.team_data.values())
            if total_pubs > 0:
                sources.append({
                    "source": f"{total_pubs} Publications",
                    "type": "Research Output",
                    "relevance": "High - Titles, abstracts, citations, venues"
                })

            return sources

        except Exception as e:
            logger.error(f"Error generating data sources info: {str(e)}")
            return []

    def cleanup(self) -> Dict[str, Any]:
        """
        Clean up resources and perform cleanup operations.
        
        Returns:
            Dict with cleanup result
        """
        try:
            # Clear instance variables
            self.vectorstore = None
            self.llm = None
            self.qa_chain = None
            self.team_data = {}
            self.expertise_domains = []
            self.publications_data = {}
            self.collaboration_network = None

            # Clear state
            self._set_state("team_data", {})
            self._set_state("expertise_domains", [])
            self._set_state("publications_data", {})
            self._set_state("collaboration_metrics", {})
            self._set_state("team_expertise_report", {})
            self._set_state("individual_research_reports", [])

            logger.info("Team expertise agent cleanup completed successfully")

            return {
                "status": "success",
                "message": "Cleanup completed successfully",
                "resources_freed": [
                    "vectorstore",
                    "llm_instances",
                    "team_data",
                    "publications_data",
                    "collaboration_network"
                ]
            }

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Cleanup failed: {str(e)}",
                "resources_freed": []
            }

    def _get_llm_config_info(self) -> Dict[str, Any]:
        """
        Get LLM configuration information for logging and debugging.
        
        Returns:
            Dictionary containing LLM configuration details
        """
        config_info = {
            "provider": self.llm_provider,
            "model": self.llm_model,
            "temperature": getattr(self, 'llm', None) and getattr(self.llm, 'temperature', None)
        }
        
        if self.llm_provider == "azure":
            config_info.update({
                "azure_model": os.getenv("AZURE_MODEL"),
                "azure_configured": bool(os.getenv("AZURE_API_BASE") and os.getenv("AZURE_API_KEY"))
            })
        else:
            config_info.update({
                "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
            })
        
        return config_info

