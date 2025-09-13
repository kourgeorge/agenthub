#!/usr/bin/env python3

import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage, HumanMessage
from lite_llm_handler import LiteLLMHandler
from researcher_data_extractor import ResearcherDataExtractor
from publication_processor import PublicationProcessor
from expertise_extractor import ExpertiseExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class TeamExpertiseAgent:

    def __init__(self):
        self.max_pubs = 50
        self.llm = None

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
            member_extractor = ResearcherDataExtractor(
                llm_handler=self.llm,
            )

            # Data Collection
            field_of_study = input_data.get("field_of_study", "Computer Science")

            team_members_data = {}
            for member_name, institution, author_id in team_members:
                team_members_data[member_name] = member_extractor.extract_researcher_info(
                    member_name, institution, self.max_pubs, field_of_study, author_id
                )

            team_members_data = self._sort_members_by_rank(team_members_data)

            # Team-level Analysis and Summary Generation
            logger.info("👥 STEP 3: Team-level Analysis and Summary Generation")
            team_profile = self._build_team_profile(team_members_data)

            # Calculate total publications
            return {
                "status": "success",
                "individual_profiles": team_members_data,
                "team_profile": team_profile,
            }

        except Exception as e:
            logger.error(f"Execution failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Execution failed: {str(e)}",
                "team_members_analyzed": 0,
                "total_publications": 0,
                "workflow_summary": "Workflow failed"
            }

    def _sort_members_by_rank(self, team_members_data):
        sorted_members = sorted(team_members_data.items(),
                                key=lambda x: x[1].get("citation_metrics", {}).get("h_index", 0), reverse=True)
        if not sorted_members or all(v.get("citation_metrics", {}).get("h_index", 0) == 0 for k, v in sorted_members):
            sorted_members = sorted(team_members_data.items(),
                                    key=lambda x: x[1].get("citation_metrics", {}).get("total_citations", 0),
                                    reverse=True)

        return dict(sorted_members)

    def _parse_team_members(self, team_members_input: str) -> List[tuple]:
        """
        Parse team members input string into a list of (name, institution, author_id) tuples.
        
        Supports formats:
        - "name, institution; name2, institution2, id" (comma separated)
        - "name, institution, id; name2, institution2, id2" (comma separated)
        - "name, institution\nname2, institution2, id" (comma separated)
        - "name\tinstitution; name2\tinstitution2\tid" (tab separated)
        - "name\tinstitution\tauthor_id; name2\tinstitution2\tauthor_id2" (tab separated)
        - "name\nname2" (institution and author_id will be None)
        
        Args:
            team_members_input: String containing team member names, institutions, and optional author IDs
            
        Returns:
            List of (name, institution, author_id) tuples
        """
        if not team_members_input or not isinstance(team_members_input, str):
            raise ValueError("team_members must be a non-empty string")

        # Split by semicolons first, then by newlines
        entries = []
        if ';' in team_members_input:
            entries = team_members_input.strip().split(';')
        else:
            entries = team_members_input.strip().split('\n')

        members = []

        for entry in entries:
            entry = entry.strip()
            if entry:
                # Determine separator: prefer tab if present, otherwise use comma
                if '\t' in entry:
                    # Tab-separated format (name\tinstitution\tauthor_id)
                    parts = [part.strip() for part in entry.split('\t')]
                elif ',' in entry:
                    # Comma-separated format (name, institution, author_id)
                    parts = [part.strip() for part in entry.split(',')]
                else:
                    # No separator, treat as name only
                    parts = [entry]

                # Parse parts based on length
                if len(parts) >= 2:
                    name = parts[0]
                    institution = parts[1] if len(parts) > 1 else None
                    author_id = parts[2] if len(parts) > 2 else None
                    if name:  # Only add if name is not empty
                        members.append((name, institution, author_id))
                elif len(parts) == 1 and parts[0]:
                    # Single part, treat as name only
                    members.append((parts[0], None, None))

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

    def _build_team_profile(self, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build comprehensive team analysis and generate summary insights.
        Combines team expertise mapping and summary generation functionality.
        """
        try:
            if not team_data:
                return {}

            team_publications = self.publication_processor.get_team_publications(team_data)

            # Expertise mapping
            team_expertise_domains = TeamExpertiseAgent.analyze_team_expertise(team_data)

            # Publications
            total_publications = len(team_publications)
            total_citations = sum(pub.get("citations", 0) for pub in team_publications)

            # Identify most influential members
            influential_members = []
            for name, profile in team_data.items():
                h_index = profile.get("citation_metrics", {}).get("h_index", 0)
                member_total_citations = profile.get("citation_metrics", {}).get("total_citations", 0)
                influence_score = (h_index * 0.6) + (total_citations * 0.4)
                textual_summary = profile.get("textual_summary", "No summary available")
                domains = profile.get("domain_expertise", [])
                influential_members.append({
                    "member_name": name,
                    "h_index": h_index,
                    "total_citations": member_total_citations,
                    "domain_expertise": ";".join([(f"Domain: {d['domain']}. Rank:{d['rank']}") for d in domains]),
                    "summary": textual_summary,
                    "influence_score": influence_score
                })

            # Sort and get top 3
            influential_members.sort(key=lambda x: x["influence_score"], reverse=True)
            top_influential = influential_members[:5]

            # Build domain summary safely
            domain_summary = ', '.join(
                [f'{domain} ({data.get("total_rank", 0) if isinstance(data, dict) else 0} rank)' for
                 domain, data in team_expertise_domains.items()])

            # Create the top members summary outside the f-string to avoid backslash issue
            top_members_summary = '\n'.join([
                                                f'{m["member_name"]} (H-index: {m["h_index"]}, {m["total_citations"]} citations), summary: {m["summary"]}. domains info: {m["domain_expertise"]}'
                                                for m in top_influential])

            prompt = f"""Summarize this research team in few paragraphs by characterizing their expertise, publication impact, and collaboration dynamics:
                You should mention the top expertise domains, the most influential members, and any notable collaboration patterns.
                
                Team: {len(team_data)} members, {total_publications} publications, {len(team_expertise_domains)} expertise domains
                Team Domains: {domain_summary}
                Top members: {top_members_summary}"""

            messages = [SystemMessage(
                content="You are a research analyst. Your goal is to give a high level overview of the team expertise levels and domains."),
                HumanMessage(content=prompt)]

            response = self.llm.invoke(messages)
            summary_text = response.content if hasattr(response, 'content') else "Team summary generated"

            # Build team analysis
            return {
                "member_count": len(team_data),
                "publications": {
                    "papers": team_publications,
                    "total_publications": total_publications,
                    "total_citations": total_citations,
                },
                "citation_analysis": self.publication_processor.get_citation_analysis(team_publications),
                "team_collaboration": {
                    "multi_author_papers": len(
                        [p for p in team_publications if len(p.get("_member_contributors", [])) > 1]),
                    "single_author_papers": len(
                        [p for p in team_publications if len(p.get("_member_contributors", [])) == 1])
                },
                "expertise_domains": team_expertise_domains,
                "summary": summary_text
            }

        except Exception as e:
            logger.error(f"Error building team analysis and summary: {str(e)}")
            return {"team_analysis": {}, "team_summary": {"error": str(e), "summary_text": "Error generating summary"}}

    @staticmethod
    def analyze_team_expertise(team_data):

        team_expertise_domains = {}
        # Process each member expertise to build team expertise map
        for member in team_data.values():
            member_expertise_data = member.get("domain_expertise", [])
            domains = [d["domain"] for d in member_expertise_data]

            # Update team expertise counts
            for domain in domains:
                member_rank = \
                    member_expertise_data[
                        next(i for i, d in enumerate(member_expertise_data) if d["domain"] == domain)][
                        "rank"]
                if domain not in team_expertise_domains:
                    team_expertise_domains[domain] = {"total_rank": 0, "contributing_members": {}}

                team_expertise_domains[domain]["total_rank"] += member_rank
                member_name = member.get("name", "Unknown")
                team_expertise_domains[domain]["contributing_members"][member_name] = member_rank

                #sort contributing members by rank
                team_expertise_domains[domain]["contributing_members"] = dict(sorted(
                    team_expertise_domains[domain]["contributing_members"].items(),
                    key=lambda x: x[1],
                    reverse=True
                ))

        # Sort team_expertise_domains by total_rank in descending order
        team_expertise_domains = dict(sorted(
            team_expertise_domains.items(),
            key=lambda x: x[1].get("total_rank", 0),
            reverse=True
        ))
        return team_expertise_domains


def execute(input_data):
    """
    Simple example of using the Team Expertise Analysis Agent.
    """
    # Create agent and execute
    agent = TeamExpertiseAgent()
    result = agent.execute(input_data=input_data)
    return result


if __name__ == '__main__':
    # Load environment variables
    load_dotenv()

    # Example configuration
    input_data = {
        "team_members": """
Mark Purcell	IBM Research	47296533
Stefano Braghin	IBM Research	2971861
Giandomenico Cornacchia	IBM Research	2112895513
Greta Dolcetti	IBM Research	2160343749
Kieran Fraser	IBM Research	40626466
Anisa Halimi	IBM Research	32779570
Muhammad Zaid Hameed	IBM Research	3207859
Naoise Holohan	IBM Research	2946928
Liubov Nedoshivina	IBM Research	2304392989
Ambrish Rawat	IBM Research	22261698
Yara Schütt	IBM Research	2370929411
Mohamed Suliman	IBM Research	2189156764
Giulio Zizzo	IBM Research	152109289
""",
        "model_name": "azure/gpt-4o-2024-08-06",
        "temperature": 0,
        "max_publications_per_member": 30
    }

    result = execute(input_data)
    with open("Mark_Purcell_output.json", "w") as f:
        json.dump(result, f, indent=4)  # indent=4 makes the file pretty-printed
