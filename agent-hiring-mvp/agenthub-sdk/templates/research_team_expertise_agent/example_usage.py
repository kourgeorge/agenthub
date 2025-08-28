#!/usr/bin/env python3
"""
Example Usage of Team Expertise Analysis Agent

This file demonstrates how to use the Team Expertise Analysis Agent
to initialize and analyze team expertise by collecting information 
from academic sources and generating comprehensive reports.
"""

import os
import sys
import json
from dotenv import load_dotenv
from team_expertise_agent import TeamExpertiseAgent

# Add the current directory to Python path to import the agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Load arXiv taxonomy for expertise domains
def load_arxiv_taxonomy():
    """Load the arXiv taxonomy from the JSON file."""
    try:
        import json
        taxonomy_path = os.path.join(os.path.dirname(__file__), 'arxiv_taxonomy.json')
        with open(taxonomy_path, 'r') as f:
            taxonomy = json.load(f)
        return taxonomy
    except Exception as e:
        print(f"Warning: Could not load arXiv taxonomy: {e}")
        return {}

# Load taxonomy and extract expertise domains
ARXIV_TAXONOMY = load_arxiv_taxonomy()

def get_expertise_domains_from_taxonomy():
    """Extract expertise domains from the arXiv taxonomy."""
    domains = []
    if ARXIV_TAXONOMY:
        for subject, subject_data in ARXIV_TAXONOMY.items():
            if 'categories' in subject_data:
                for category in subject_data['categories']:
                    domains.append(category['name'])
    return domains

EXAMPLE_TEAM_CONFIG = {
    "team_members": """George Kour
Boaz Carmeli""",
    # expertise_domains is optional - agent will use arXiv taxonomy by default
    "model_name": "gpt-4o-mini",
    "temperature": 0.1,
    "max_publications_per_member": 30,
    "include_citations": True,
    "include_collaboration_network": True,
    "enable_paper_enrichment": False  # Set to False to disable paper enrichment
}

def test_team_members_parsing():
    """
    Test the new team members parsing functionality.
    
    This function demonstrates how the agent now accepts team_members as a string
    that can be parsed in multiple formats.
    """
    # Import just the parsing function to avoid heavy dependencies

    sys.path.append(os.path.dirname(__file__))

    # Import the agent
    from team_expertise_agent import TeamExpertiseAgent

    # Create agent instance
    agent = TeamExpertiseAgent()

    # Test different input formats
    test_cases = [
        ("Comma-separated format", "George Kour, Boaz Carmeli"),
    ]

    print("🧪 Testing Team Members Parsing")
    print("=" * 50)

    for test_name, test_input in test_cases:
        parsed = agent._parse_team_members(test_input)


def test_agent_initialization():
    # Create agent instance
    agent = TeamExpertiseAgent()

    return agent.initialize(EXAMPLE_TEAM_CONFIG)


def test_basic_execution():
    """
    Test basic execution after successful initialization.
    """
    print("\n🧪 Testing Basic Execution...")
    
    try:
        from team_expertise_agent import TeamExpertiseAgent
        
        # Create and initialize agent
        agent = TeamExpertiseAgent()
        init_result = agent.initialize(EXAMPLE_TEAM_CONFIG)
        
        if init_result.get("status") != "success":
            print("❌ Cannot test execution - initialization failed")
            return False
        
        # Test a simple query
        print("   Testing team overview query...")
        query = {
            "query_type": "team_overview",
            "query": "What is our team's overall composition?",
            "analysis_depth": "summary"
        }
        
        response = agent.execute(query)
        
        if response.get("status") != "error":
            print("   ✅ Execution test successful")
            print(f"   Answer preview: {response.get('answer', 'No answer')[:100]}...")
            return True
        else:
            print(f"   ❌ Execution test failed: {response.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Execution test error: {e}")
        return False

def cleanup_test():
    """
    Test cleanup functionality.
    """
    print("\n🧹 Testing Cleanup...")
    
    try:
        from team_expertise_agent import TeamExpertiseAgent
        
        agent = TeamExpertiseAgent()
        cleanup_result = agent.cleanup()
        
        if cleanup_result.get("status") == "success":
            print("   ✅ Cleanup test successful")
            return True
        else:
            print(f"   ⚠️  Cleanup completed with warnings: {cleanup_result.get('message', 'Unknown')}")
            return True
            
    except Exception as e:
        print(f"   ❌ Cleanup test error: {e}")
        return False

def display_team_member_backgrounds():
    """
    Display detailed executive summaries and backgrounds for each team member.
    This function can be called independently to show team member information.
    """
    print("\n📋 TEAM MEMBER BACKGROUND ANALYSIS")
    print("=" * 60)
    
    # Show taxonomy information first
    if ARXIV_TAXONOMY:
        print("🏷️  Using arXiv Taxonomy for Expertise Domains:")
        print(f"   Total Subjects: {len(ARXIV_TAXONOMY)}")
        total_categories = sum(len(subject_data.get('categories', [])) for subject_data in ARXIV_TAXONOMY.values())
        print(f"   Total Categories: {total_categories}")
        print(f"   Agent will automatically load and use this taxonomy")
        print()
    
    try:
        from team_expertise_agent import TeamExpertiseAgent
        
        # Create and initialize agent
        print("🔧 Creating and initializing agent...")
        agent = TeamExpertiseAgent()
        init_result = agent.initialize(EXAMPLE_TEAM_CONFIG)
        
        if init_result.get("status") != "success":
            print(f"❌ Cannot display backgrounds - initialization failed: {init_result.get('message', 'Unknown error')}")
            return False
        
        # Get individual profiles
        individual_profiles = init_result.get("individual_profiles", [])
        if not individual_profiles:
            print("❌ No individual profiles available")
            return False
        
        print(f"✅ Successfully initialized agent with {len(individual_profiles)} team members")
        print(f"📊 Total publications collected: {init_result.get('total_publications', 0)}")
        
        # Display detailed backgrounds for each member
        for name, profile in individual_profiles.items():
            member_name = name
            print(f"\n👤 {member_name.upper()}")
            print("=" * 60)
            
            # Profile information
            print(f"📝 Profile Information:")
            print(f"   - Member Name: {member_name}")
            
            # Expertise domains (from arXiv taxonomy)
            expertise_domains = profile.get('expertise_domains', [])
            if expertise_domains:
                print(f"\n🏷️  EXPERTISE DOMAINS (arXiv Taxonomy):")
                print(f"   Primary: {', '.join(expertise_domains[:5])}")
                if len(expertise_domains) > 5:
                    print(f"   Additional: {', '.join(expertise_domains[5:10])}")
                if len(expertise_domains) > 10:
                    print(f"   Total Domains: {len(expertise_domains)}")
            
            # Research timeline
            research_timeline = profile.get('research_timeline', {})
            if research_timeline:
                print(f"\n📅 Research Timeline:")
                print(f"   - Total Years: {len(research_timeline)}")
                years = sorted(research_timeline.keys())
                if years:
                    print(f"   - Years with Publications: {', '.join(map(str, years[:5]))}")
                    if len(years) > 5:
                        print(f"   - Additional Years: {', '.join(map(str, years[5:10]))}")
            
            # Citation metrics
            citation_metrics = profile.get('citation_metrics', {})
            if citation_metrics:
                print(f"\n📊 Citation Metrics:")
                print(f"   - H-Index: {citation_metrics.get('h_index', 'N/A')}")
                print(f"   - Total Citations: {citation_metrics.get('total_citations', 'N/A')}")
                print(f"   - Publication Count: {citation_metrics.get('publication_count', 'N/A')}")
            
            # Publications
            publications = profile.get('publications', [])
            if publications:
                print(f"\n📚 PUBLICATIONS ({len(publications)} total):")
                
                # Show top publications by citations
                cited_papers = [p for p in publications if p.get('citations', 0) > 0]
                if cited_papers:
                    top_papers = sorted(cited_papers, key=lambda x: x.get('citations', 0), reverse=True)[:5]
                    print(f"   Top Cited Papers:")
                    for i, paper in enumerate(top_papers, 1):
                        title = paper.get('title', 'Unknown title')
                        citations = paper.get('citations', 0)
                        year = paper.get('year', 'Unknown year')
                        venue = paper.get('venue', 'Unknown venue')
                        print(f"     {i}. {title}")
                        print(f"        {venue} ({year}) - {citations} citations")
                else:
                    print(f"   No citation data available")
            
            print("\n" + "=" * 60)
        
        # Cleanup
        cleanup_result = agent.cleanup()
        if cleanup_result.get("status") == "success":
            print("✅ Cleanup completed successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importing TeamExpertiseAgent: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    Main function to run all tests or specific functionality.
    """
    import sys
    
    # Check if user wants to run just the background analysis
    if len(sys.argv) > 1 and sys.argv[1] == "--backgrounds":
        print("📋 Team Expertise Analysis Agent - Background Analysis Only")
        print("=" * 60)
        success = display_team_member_backgrounds()
        if success:
            print("\n🎉 Background analysis completed successfully!")
        else:
            print("\n❌ Background analysis failed. Check the output above for details.")
        return
    
    # Check if user wants to test just the parsing functionality
    if len(sys.argv) > 1 and sys.argv[1] == "--parsing":
        print("🔍 Team Expertise Analysis Agent - Parsing Test Only")
        print("=" * 60)
        test_team_members_parsing()
        return
    
    print("🧪 Team Expertise Analysis Agent - Complete Test Suite")
    print("=" * 60)
    
    # Test 0: Team Members Parsing (new functionality)
    print("\n🔍 Testing Team Members Parsing...")
    test_team_members_parsing()
    
    # Test 1: Initialization
    init_results = test_agent_initialization()
    
    if init_results:
        # Test 2: Basic Execution
        exec_success = test_basic_execution()
        
        # Test 3: Cleanup
        cleanup_success = cleanup_test()

        if all([init_results, exec_success, cleanup_success]):
            print("\n🎉 All tests passed! The agent is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Check the output above for details.")
    else:
        print("\n❌ Initialization test failed. Cannot proceed with other tests.")
    

if __name__ == "__main__":
    # Run the complete test suite
    main()
