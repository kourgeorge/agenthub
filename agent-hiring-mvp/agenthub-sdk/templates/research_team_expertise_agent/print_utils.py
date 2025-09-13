from typing import Dict, Any, Optional, List, Tuple
import logging
import json

logger = logging.getLogger(__name__)


def print_team_report(result: Dict[str, Any]) -> None:
    """
    Generate and print a visually appealing report containing important items
    per individual and the entire team from the team expertise analysis result.
    
    Args:
        result: The complete result dictionary from TeamExpertiseAgent.execute()
    """
    try:
        # Extract data from result
        status = result.get("status", "unknown")
        individual_profiles = result.get("individual_profiles", {})
        team_profile = result.get("team_profile", {})

        if status != "success":
            print("❌ Analysis failed - no report available")
            return

        print("\n" + "=" * 80)
        print("🔬 RESEARCH TEAM EXPERTISE ANALYSIS REPORT")
        print("=" * 80)

        # Team Overview Section
        print_team_overview(team_profile)

        # Individual Members Section
        print_individual_members(individual_profiles)

        # Team Expertise Domains Section
        print_team_expertise_domains(team_profile)

        # Publications Analysis Section
        print_publications_analysis(team_profile)

        # Team Collaboration Section
        print_team_collaboration(team_profile)

        # AI-Generated Summary Section
        print_ai_summary(team_profile)

        print("\n" + "=" * 80)
        print("📊 Report generated successfully!")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Error generating team report: {str(e)}")
        print(f"❌ Error generating report: {str(e)}")


def print_team_overview(team_profile: Dict[str, Any]) -> None:
    """Print team overview section."""
    print(f"\n📈 TEAM OVERVIEW")
    print("-" * 50)
    print(f"👥 Total Members Analyzed: {team_profile.get("member_count", 0)}")

    publications_data = team_profile.get("publications", {})
    total_pubs = publications_data.get("total_publications", 0)
    total_citations = publications_data.get("total_citations", 0)

    print(f"📚 Total Publications: {total_pubs:,}")
    print(f"📊 Total Citations: {total_citations:,}")

    if total_pubs > 0:
        avg_citations = total_citations / total_pubs
        print(f"📈 Average Citations per Paper: {avg_citations:.1f}")

    expertise_domains = team_profile.get("expertise_domains", {})
    print(f"🎯 Expertise Domains: {len(expertise_domains)}")


def print_individual_members(individual_profiles: Dict[str, Any]) -> None:
    """Print individual members section."""
    print(f"\n👤 INDIVIDUAL MEMBER PROFILES")
    print("-" * 50)

    if not individual_profiles:
        print("No individual profiles available")
        return

    # Sort members by h-index for display
    sorted_members = sorted(
        individual_profiles.items(),
        key=lambda x: x[1].get("citation_metrics", {}).get("h_index", 0),
        reverse=True
    )

    for i, (name, profile) in enumerate(sorted_members, 1):
        print(f"\n{i}. {name}")
        print("   " + "-" * (len(name) + 3))

        # Basic info

        # Citation metrics
        citation_metrics = profile.get("citation_metrics", {})
        h_index = citation_metrics.get("h_index", 0)
        total_citations = citation_metrics.get("total_citations", 0)
        publication_count = citation_metrics.get("publication_count", 0)

        print(f"   📊 H-index: {h_index}")
        print(f"   📚 Total Citations: {total_citations:,}")
        print(f"   📄 Publications: {publication_count}")

        # Domain expertise
        domain_expertise = profile.get("domain_expertise", [])
        if domain_expertise:
            print(f"   🎯 Top Expertise Domains:")
            for domain_info in domain_expertise[:3]:  # Show top 3
                domain = domain_info.get("domain", "Unknown")
                rank = domain_info.get("rank", 0)
                print(f"      • {domain} (Rank: {rank})")

        # Textual summary (truncated)
        textual_summary = profile.get("textual_summary", "")
        if textual_summary:
            # Truncate summary to 150 characters
            summary_preview = textual_summary
            print(f"   📝 Summary: {summary_preview}")


def print_team_expertise_domains(team_profile: Dict[str, Any]) -> None:
    """Print team expertise domains section."""
    print(f"\n🎯 TEAM EXPERTISE DOMAINS")
    print("-" * 50)

    expertise_domains = team_profile.get("expertise_domains", {})
    if not expertise_domains:
        print("No expertise domains data available")
        return

    print(f"Total Domains: {len(expertise_domains)}")
    print("\nTop Expertise Areas:")

    for i, (domain, data) in enumerate(list(expertise_domains.items())[:5], 1):
        total_rank = data.get("total_rank", 0)
        contributing_members = data.get("contributing_members", [])
        member_count = len(contributing_members)

        print(f"   {i}. {domain}")
        print(f"      📊 Total Rank: {total_rank}")
        print(f"      👥 Contributing Members: {member_count}")
        if contributing_members:
            members_str = ", ".join([f'{name} ({rank})' for name, rank in contributing_members.items()][:5])   # Show first 5 members
            if len(contributing_members) > 5:
                members_str += f" (+{len(contributing_members) - 5} more)"
            print(f"      👤 Members: {members_str}")


def print_publications_analysis(team_profile: Dict[str, Any]) -> None:
    """Print publications analysis section."""
    print(f"\n📚 PUBLICATIONS ANALYSIS")
    print("-" * 50)

    publications_data = team_profile.get("publications", {})
    total_pubs = publications_data.get("total_publications", 0)
    total_citations = publications_data.get("total_citations", 0)

    print(f"📄 Total Publications: {total_pubs:,}")
    print(f"📊 Total Citations: {total_citations:,}")

    if total_pubs > 0:
        avg_citations = total_citations / total_pubs
        print(f"📈 Average Citations per Paper: {avg_citations:.1f}")

    # Citation analysis
    citation_analysis = team_profile.get("citation_analysis", {})
    citation_distribution = citation_analysis.get("citation_distribution")
    if citation_distribution:
        print(f"\n📊 Citation Distribution:")
        highly_cited = citation_distribution.get("100+ citations", 0)
        moderately_cited = citation_analysis.get("11-100 citations", 0)
        low_cited = citation_analysis.get("0-10 citations", 0)

        print(f"   🔥 Highly Cited (100+): {highly_cited}")
        print(f"   📈 Moderately Cited (11-99): {moderately_cited}")
        print(f"   📄 Low Cited (<=10): {low_cited}")

        # Recent publications
        recent_pubs = citation_analysis.get("recent_publications", 0)
        if recent_pubs > 0:
            print(f"   🆕 Recent Publications (2020+): {recent_pubs}")


def print_team_collaboration(team_profile: Dict[str, Any]) -> None:
    """Print team collaboration section."""
    print(f"\n🤝 TEAM COLLABORATION")
    print("-" * 50)

    team_collaboration = team_profile.get("team_collaboration", {})
    if not team_collaboration:
        print("No collaboration data available")
        return

    multi_author = team_collaboration.get("multi_author_papers", 0)
    single_author = team_collaboration.get("single_author_papers", 0)
    total_papers = multi_author + single_author

    print(f"📄 Multi-author Papers: {multi_author}")
    print(f"📄 Single-author Papers: {single_author}")

    if total_papers > 0:
        collaboration_rate = (multi_author / total_papers) * 100
        print(f"🤝 Collaboration Rate: {collaboration_rate:.1f}%")

        if collaboration_rate >= 70:
            print("   🌟 High collaboration team!")
        elif collaboration_rate >= 40:
            print("   📈 Moderate collaboration team")
        else:
            print("   📊 Lower collaboration team")


def print_ai_summary(team_profile: Dict[str, Any]) -> None:
    """Print AI-generated summary section."""
    print(f"\n🤖 AI-GENERATED TEAM SUMMARY")
    print("-" * 50)

    summary = team_profile.get("summary", "")
    if summary:
        print(summary)
    else:
        print("No AI summary available")


if __name__ == "__main__":
    # Also save the raw result to JSON for reference
    with open("Mark_Purcell_output.json", "r") as f:
        result = json.load(f)
    print_team_report(result)
