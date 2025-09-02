#!/usr/bin/env python3
"""
Analysis Engine

Handles all analysis operations including team analysis, individual analysis, 
and domain analysis. This eliminates duplicate analysis patterns across different query types.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AnalysisEngine:
    """Unified engine for all analysis operations."""

    def __init__(self, publication_processor, expertise_extractor):
        self.pub_processor = publication_processor
        self.expertise_extractor = expertise_extractor

    def analyze_team_overview(self, team_data: Dict[str, Any], analysis_depth: str = "detailed") -> Tuple[
        str, Dict[str, Any]]:
        """Analyze overall team composition and strengths."""
        try:
            if not team_data:
                return "No team data available for analysis.", {}

            # Basic team statistics
            team_size = len(team_data)
            team_publications = self.pub_processor.get_team_publications(team_data)
            total_publications = len(team_publications)

            # Role distribution
            role_counts = {}
            for member_data in team_data.values():
                role = member_data.get("role", "Unknown")
                role_counts[role] = role_counts.get(role, 0) + 1

            # Expertise domain analysis
            all_domains = []
            for member_data in team_data.values():
                all_domains.extend(member_data.get("expertise_domains", []))

            domain_counts = {}
            for domain in all_domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

            top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            # Generate analysis text
            analysis_parts = [
                f"## Team Overview Analysis",
                f"",
                f"**Team Composition:**",
                f"- Total Members: {team_size}",
                f"- Total Publications: {total_publications}",
                f"- Role Distribution: {', '.join([f'{role}: {count}' for role, count in role_counts.items()])}",
                f"",
                f"**Top Expertise Domains:**",
            ]

            for domain, count in top_domains:
                analysis_parts.append(f"- {domain}: {count} team members")

            # Add individual highlights for detailed analysis
            if analysis_depth in ["detailed", "comprehensive"]:
                analysis_parts.extend([
                    f"",
                    f"**Individual Highlights:**"
                ])

                for member_name, member_data in team_data.items():
                    pubs_count = len(member_data.get("publications", []))
                    top_domains = member_data.get("expertise_domains", [])[:3]
                    role = member_data.get("role", "Unknown")

                    if pubs_count > 0:
                        analysis_parts.append(f"- **{member_name}** ({role}): {pubs_count} publications")
                        if top_domains:
                            analysis_parts.append(f"  - Expertise: {', '.join(top_domains)}")

            answer = "\n".join(analysis_parts)

            insights = {
                "team_strengths": [
                    f"Strong publication record with {total_publications} publications",
                    f"Expertise coverage across {len(top_domains)} domains",
                    f"Balanced role distribution"
                ],
                "individual_highlights": [
                                             {
                                                 "name": member_name,
                                                 "expertise": member_data.get("expertise_domains", [])[:3],
                                                 "key_contributions": f"{len(member_data.get('publications', []))} publications"
                                             }
                                             for member_name, member_data in team_data.items()
                                             if len(member_data.get("publications", [])) > 0
                                         ][:5],  # Top 5 members
                "research_directions": [
                    f"Focus on {top_domains[0][0]} research" if top_domains else "Diverse research interests",
                    "Potential for interdisciplinary collaboration",
                    "Strong foundation for future research projects"
                ],
                "collaboration_patterns": {
                    "team_size": team_size,
                    "expertise_diversity": len(top_domains),
                    "collaboration_potential": "High" if team_size > 2 else "Moderate"
                }
            }

            return answer, insights

        except Exception as e:
            logger.error(f"Error in team overview analysis: {str(e)}")
            return f"Error analyzing team overview: {str(e)}", {}

    def analyze_individual_member(self, team_data: Dict[str, Any], member_name: str,
                                  analysis_depth: str = "detailed") -> Tuple[str, Dict[str, Any]]:
        """Analyze a specific team member's expertise and contributions."""
        try:
            if not member_name or member_name not in team_data:
                return f"Team member '{member_name}' not found.", {}

            member_data = team_data[member_name]
            publications = member_data.get("publications", [])
            expertise_domains = member_data.get("expertise_domains", [])

            # Publication analysis (considering shared papers)
            pubs_count = len(publications)
            if pubs_count > 0:
                recent_pubs = [p for p in publications if p.get("year") and p.get("year") >= datetime.now().year - 3]
                cited_pubs = [p for p in publications if p.get("citations", 0) > 10]

                # Top publications by citations
                top_pubs = sorted(publications, key=lambda x: x.get("citations", 0), reverse=True)[:5]

                # Note about shared papers
                shared_papers_note = ""
                if member_name in team_data:
                    team_pubs = self.pub_processor.get_team_publications(team_data)
                    shared_count = sum(1 for pub in publications if any(
                        self.pub_processor.publications_match(pub, team_pub) for team_pub in team_pubs))
                    if shared_count < pubs_count:
                        shared_papers_note = f" (includes {shared_count} shared papers with team)"
            else:
                recent_pubs = []
                cited_pubs = []
                top_pubs = []
                shared_papers_note = ""

            # Generate analysis
            analysis_parts = [
                f"## Individual Analysis: {member_name}",
                f"",
                f"**Profile:**",
                f"- Role: {role}",
                f"- Institution: {institution or 'Not specified'}",
                f"- Total Publications: {pubs_count}{shared_papers_note}",
                f"- Expertise Domains: {', '.join(expertise_domains[:5])}",
                f""
            ]

            if pubs_count > 0:
                analysis_parts.extend([
                    f"**Publication Analysis:**",
                    f"- Recent Publications (last 3 years): {len(recent_pubs)}",
                    f"- Highly Cited Publications (>10 citations): {len(cited_pubs)}",
                    f""
                ])

                if top_pubs:
                    analysis_parts.append("**Top Publications by Citations:**")
                    for i, pub in enumerate(top_pubs, 1):
                        title = pub.get("title", "Unknown Title")
                        citations = pub.get("citations", 0)
                        year = pub.get("year", "Unknown")
                        analysis_parts.append(f"{i}. {title} ({year}) - {citations} citations")
                    analysis_parts.append("")

            # Research timeline analysis
            if member_data.get("research_timeline"):
                timeline = member_data["research_timeline"]
                if timeline:
                    analysis_parts.extend([
                        f"**Research Timeline:**",
                        f"- Most Active Year: {max(timeline.items(), key=lambda x: x[1])[0] if timeline else 'N/A'}",
                        f"- Publication Distribution: {', '.join([f'{year}: {count}' for year, count in sorted(timeline.items(), reverse=True)[:5]])}",
                        f""
                    ])

            # Collaboration analysis
            collaborators = member_data.get("collaborators", [])
            if collaborators:
                analysis_parts.extend([
                    f"**Collaboration Network:**",
                    f"- Total Collaborators: {len(collaborators)}",
                    f"- Team Collaborators: {len([c for c in collaborators if c in team_data])}",
                    f""
                ])

            answer = "\n".join(analysis_parts)

            insights = {
                "team_strengths": [
                    f"Expertise in {len(expertise_domains)} domains",
                    f"Strong publication record with {pubs_count} papers",
                    f"Active collaboration network"
                ] if pubs_count > 0 else ["Role-based expertise", "Team contribution potential"],
                "individual_highlights": [{
                    "name": member_name,
                    "expertise": expertise_domains[:5],
                    "key_contributions": f"{pubs_count} publications, {len(collaborators)} collaborators"
                }],
                "research_directions": [
                    f"Focus on {expertise_domains[0]}" if expertise_domains else "General expertise",
                    "Potential for interdisciplinary research",
                    "Collaboration opportunities within team"
                ],
                "collaboration_patterns": {
                    "team_collaborations": len([c for c in collaborators if c in team_data]),
                    "external_collaborations": len([c for c in collaborators if c not in team_data]),
                    "collaboration_strength": "High" if len(collaborators) > 5 else "Moderate"
                }
            }

            return answer, insights

        except Exception as e:
            logger.error(f"Error in individual member analysis: {str(e)}")
            return f"Error analyzing individual member: {str(e)}", {}

    def analyze_expertise_domain(self, team_data: Dict[str, Any], domain: str, analysis_depth: str = "detailed") -> \
    Tuple[str, Dict[str, Any]]:
        """Analyze expertise in a specific domain across the team."""
        try:
            if not domain:
                return "No domain specified for analysis.", {}

            # Find team members with expertise in this domain
            domain_experts = []
            for member_name, member_data in team_data.items():
                if domain.lower() in [d.lower() for d in member_data.get("expertise_domains", [])]:
                    domain_experts.append({
                        "name": member_name,
                        "role": member_data.get("role", "Unknown"),
                        "publications": member_data.get("publications", []),
                        "expertise_level": len(
                            [d for d in member_data.get("expertise_domains", []) if d.lower() == domain.lower()])
                    })

            if not domain_experts:
                return f"No team members found with expertise in {domain}.", {}

            # Sort by expertise level
            domain_experts.sort(key=lambda x: x["expertise_level"], reverse=True)

            # Generate analysis
            analysis_parts = [
                f"## Domain Analysis: {domain}",
                f"",
                f"**Team Expertise:**",
                f"- Total Experts: {len(domain_experts)}",
                f"- Primary Experts: {len([e for e in domain_experts if e['expertise_level'] > 1])}",
                f""
            ]

            # List domain experts
            analysis_parts.append("**Domain Experts:**")
            for expert in domain_experts[:5]:  # Top 5 experts
                pubs_count = len(expert["publications"])
                analysis_parts.append(f"- **{expert['name']}** ({expert['role']}): {pubs_count} publications")

            # Domain-specific publications (deduplicated)
            domain_publications = []
            all_team_pubs = self.pub_processor.get_team_publications(team_data)

            for pub in all_team_pubs:
                if domain.lower() in pub.get("title", "").lower() or domain.lower() in pub.get("abstract", "").lower():
                    # Find which experts contributed to this paper
                    contributing_experts = []
                    for expert in domain_experts:
                        if any(self.pub_processor.publications_match(pub, expert_pub) for expert_pub in
                               expert["publications"]):
                            contributing_experts.append(expert["name"])

                    if contributing_experts:
                        domain_publications.append({
                            "title": pub.get("title", ""),
                            "authors": pub.get("authors", []),
                            "year": pub.get("year", ""),
                            "citations": pub.get("citations", 0),
                            "experts": contributing_experts
                        })

            if domain_publications:
                # Sort by citations
                domain_publications.sort(key=lambda x: x.get("citations", 0), reverse=True)

                analysis_parts.extend([
                    f"",
                    f"**Key Publications in {domain}:**"
                ])

                for i, pub in enumerate(domain_publications[:5], 1):
                    title = pub["title"]
                    year = pub["year"]
                    citations = pub["citations"]
                    experts = ", ".join(pub["experts"])
                    analysis_parts.append(f"{i}. {title} ({year}) - {experts} - {citations} citations")

            answer = "\n".join(analysis_parts)

            insights = {
                "team_strengths": [
                    f"Strong expertise in {domain} with {len(domain_experts)} team members",
                    f"Deep knowledge base with {len(domain_publications)} domain-specific publications",
                    f"Potential for {domain} research leadership"
                ],
                "individual_highlights": [
                    {
                        "name": expert["name"],
                        "expertise": [domain],
                        "key_contributions": f"{len(expert['publications'])} publications in {domain}"
                    }
                    for expert in domain_experts[:3]
                ],
                "research_directions": [
                    f"Expand {domain} research initiatives",
                    f"Leverage team expertise for collaborative projects",
                    f"Establish {domain} as a team strength area"
                ],
                "collaboration_patterns": {
                    "domain_experts": len(domain_experts),
                    "collaboration_potential": "High" if len(domain_experts) > 1 else "Moderate",
                    "research_capacity": "Strong" if len(domain_publications) > 10 else "Moderate"
                }
            }

            return answer, insights

        except Exception as e:
            logger.error(f"Error in domain analysis: {str(e)}")
            return f"Error analyzing domain: {str(e)}", {}

    def analyze_research_directions(self, team_data: Dict[str, Any], analysis_depth: str = "detailed") -> Tuple[
        str, Dict[str, Any]]:
        """Analyze potential research directions and opportunities."""
        try:
            if not team_data:
                return "No team data available for research direction analysis.", {}

            # Analyze current research trends with deduplication
            all_publications = self.pub_processor.get_team_publications(team_data)

            # Analyze by year to identify trends
            year_publications = self.pub_processor.analyze_publications_by_year(all_publications)

            # Identify emerging domains
            recent_years = [y for y in year_publications.keys() if y >= datetime.now().year - 3]
            older_years = [y for y in year_publications.keys() if y < datetime.now().year - 3]

            recent_domains = []
            older_domains = []

            for year, pubs in year_publications.items():
                for pub in pubs:
                    domains = self.expertise_extractor.extract_expertise_domains(
                        f"{pub.get('title', '')} {pub.get('abstract', '')}")
                    if year in recent_years:
                        recent_domains.extend(domains)
                    else:
                        older_domains.extend(domains)

            # Count domain frequencies
            recent_domain_counts = {}
            older_domain_counts = {}

            for domain in recent_domains:
                recent_domain_counts[domain] = recent_domain_counts.get(domain, 0) + 1

            for domain in older_domains:
                older_domain_counts[domain] = older_domain_counts.get(domain, 0) + 1

            # Identify emerging and declining domains
            emerging_domains = []
            for domain, count in recent_domain_counts.items():
                older_count = older_domain_counts.get(domain, 0)
                if count > older_count:
                    emerging_domains.append((domain, count - older_count))

            emerging_domains.sort(key=lambda x: x[1], reverse=True)

            # Generate analysis
            analysis_parts = [
                f"## Research Directions Analysis",
                f"",
                f"**Current Research Focus:**",
                f"- Total Publications: {len(all_publications)}",
                f"- Research Timeline: {min(year_publications.keys()) if year_publications else 'N/A'} - {max(year_publications.keys()) if year_publications else 'N/A'}",
                f""
            ]

            if emerging_domains:
                analysis_parts.extend([
                    f"**Emerging Research Areas:**",
                ])
                for domain, growth in emerging_domains[:5]:
                    analysis_parts.append(f"- {domain}: +{growth} publications in recent years")
                analysis_parts.append("")

            # Identify interdisciplinary opportunities
            interdisciplinary_opportunities = []
            for member_name, member_data in team_data.items():
                domains = member_data.get("expertise_domains", [])
                if len(domains) > 2:  # Multi-domain expertise
                    interdisciplinary_opportunities.append({
                        "member": member_name,
                        "domains": domains[:3],
                        "potential": "High" if len(domains) > 3 else "Moderate"
                    })

            if interdisciplinary_opportunities:
                analysis_parts.extend([
                    f"**Interdisciplinary Research Opportunities:**",
                ])
                for opp in interdisciplinary_opportunities[:3]:
                    domains_str = ", ".join(opp["domains"])
                    analysis_parts.append(f"- {opp['member']}: {domains_str} ({opp['potential']} potential)")
                analysis_parts.append("")

            # Future recommendations
            analysis_parts.extend([
                f"**Recommended Research Directions:**",
                f"1. **Strengthen Emerging Areas**: Focus on {emerging_domains[0][0] if emerging_domains else 'identified growth areas'}",
                f"2. **Interdisciplinary Projects**: Leverage multi-domain expertise for innovative research",
                f"3. **Collaboration Expansion**: Build on existing team strengths for larger projects",
                f"4. **Industry Partnerships**: Apply research expertise to real-world challenges"
            ])

            answer = "\n".join(analysis_parts)

            insights = {
                "team_strengths": [
                    f"Research expertise across {len(set(recent_domains))} domains",
                    f"Strong publication record with {len(all_publications)} papers",
                    f"Interdisciplinary research potential"
                ],
                "individual_highlights": [
                    {
                        "name": opp["member"],
                        "expertise": opp["domains"],
                        "key_contributions": f"Multi-domain expertise in {len(opp['domains'])} areas"
                    }
                    for opp in interdisciplinary_opportunities[:3]
                ],
                "research_directions": [
                    f"Focus on {emerging_domains[0][0] if emerging_domains else 'growth areas'}",
                    "Develop interdisciplinary research projects",
                    "Build industry and academic partnerships",
                    "Expand team size and expertise coverage"
                ],
                "collaboration_patterns": {
                    "research_diversity": len(set(recent_domains)),
                    "interdisciplinary_potential": len(interdisciplinary_opportunities),
                    "collaboration_opportunities": "High"
                }
            }

            return answer, insights

        except Exception as e:
            logger.error(f"Error in research directions analysis: {str(e)}")
            return f"Error analyzing research directions: {str(e)}", {}

    def analyze_team_competency(self, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simple team competency analysis - aggregate member expertise from expertise_characterization.
        
        Args:
            team_data: Dictionary with member names as keys and profiles as values
            
        Returns:
            Dictionary containing aggregated team expertise
        """
        try:
            logger.info("Analyzing team competency...")

            if not team_data:
                logger.warning("No team data available")
                return {}

            # Simple aggregation of member expertise
            team_expertise = {}
            total_papers = 0

            for member_name, member_data in team_data.items():
                expertise = member_data.get("expertise_characterization", {})
                papers = member_data.get("publications", [])

                # Add to team totals
                for domain, count in expertise.items():
                    team_expertise[domain] = team_expertise.get(domain, 0) + count

                total_papers += len(papers)

            # Simple team analysis
            team_analysis = {
                "team_expertise": team_expertise,  # domain -> total count
            }

            logger.info(f"Team analysis complete: {len(team_expertise)} domains, {total_papers} papers")

            return team_analysis

        except Exception as e:
            logger.error(f"Error analyzing team competency: {str(e)}")
            return {}

    def calculate_confidence_score(self, query_type: str, analysis_depth: str, team_data: Dict[str, Any]) -> float:
        """Calculate confidence score for the analysis."""
        try:
            base_confidence = 0.7

            # Adjust based on query type
            type_confidence = {
                "team_overview": 0.9,
                "individual_analysis": 0.8,
                "expertise_domain_analysis": 0.85,
                "research_directions": 0.75,
                "collaboration_insights": 0.8,
                "future_recommendations": 0.7,
                "custom_question": 0.6
            }

            base_confidence = type_confidence.get(query_type, 0.7)

            # Adjust based on analysis depth
            depth_confidence = {
                "summary": 0.8,
                "detailed": 0.9,
                "comprehensive": 0.95
            }

            base_confidence *= depth_confidence.get(analysis_depth, 0.8)

            # Adjust based on data quality
            if team_data and len(team_data) > 0:
                total_pubs = sum(len(member.get("publications", [])) for member in team_data.values())
                if total_pubs > 50:
                    base_confidence *= 1.1  # Boost confidence for rich data
                elif total_pubs < 10:
                    base_confidence *= 0.9  # Reduce confidence for limited data

            # Ensure confidence is within bounds
            return min(max(base_confidence, 0.0), 1.0)

        except Exception as e:
            logger.error(f"Error calculating confidence score: {str(e)}")
            return 0.7
