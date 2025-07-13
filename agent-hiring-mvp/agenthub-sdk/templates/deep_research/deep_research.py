#!/usr/bin/env python3
"""
deep_research - This agent performs a deep research on a subject given the query, depth and breadth parameters.
"""

import json
import os
import requests
from typing import List, Dict, Any, Optional
from openai import OpenAI
import dotenv


class DeepResearchAgent:

    def __init__(self):
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY environment variable is required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = OpenAI(api_key=self.openai_api_key)

    def search_web(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web using Serper API"""
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": num_results
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "domain": item.get("displayLink", "")
                })

            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def generate_search_queries(self, research_topic: str, num_queries: int = 3) -> List[str]:
        """Generate search queries for the research topic"""
        prompt = f"""Given the research topic: "{research_topic}", generate {num_queries} specific search queries to investigate this topic thoroughly. 
        Each query should be unique and target different aspects of the topic.
        Return only the queries, one per line. Do not include any quotes or numbering, just the search query."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7
            )

            queries = response.choices[0].message.content.strip().split('\n')
            return [q.strip() for q in queries if q.strip()][:num_queries]
        except Exception as e:
            print(f"Error generating queries: {e}")
            return [research_topic]

    def analyze_search_results(self, query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze search results and extract key insights"""
        if not results:
            return {"learnings": [], "follow_up_questions": []}

        # Prepare results for analysis
        results_text = "\n\n".join([
            f"Title: {r['title']}\nSnippet: {r['snippet']}\nURL: {r['url']}\nDomain: {r['domain']}"
            for r in results
        ])

        prompt = f"""Analyze the following search results for the query: "{query}"

Search Results:
{results_text}

Extract key learnings and generate follow-up questions. Return a JSON object with:
- "learnings": List of key insights found (3-5 items)
- "follow_up_questions": List of follow-up questions to explore further (2-3 items)
- "source_quality": Brief assessment of source reliability"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )

            content = response.choices[0].message.content.strip()
            # Try to extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            analysis = json.loads(content)
            return analysis
        except Exception as e:
            print(f"Error analyzing results: {e}")
            return {"learnings": [], "follow_up_questions": []}

    def generate_final_report(self, research_topic: str, all_learnings: List[str], all_sources: List[str]) -> str:
        """Generate a comprehensive final report"""
        learnings_text = "\n".join([f"- {learning}" for learning in all_learnings])
        sources_text = "\n".join([f"- {source}" for source in all_sources])

        prompt = f"""Write a comprehensive research report on: "{research_topic}"

Key Findings:
{learnings_text}

Sources:
{sources_text}

Write a detailed report (2-3 pages) that synthesizes all findings, includes all key learnings, and provides actionable insights. Use markdown format."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.3
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating report: {e}")
            return f"Error generating report: {e}"

    def research(self, topic: str, depth: int = 2, breadth: int = 3) -> Dict[str, Any]:
        """Main research function"""
        print(f"Starting deep research on: {topic}")
        print(f"Depth: {depth}, Breadth: {breadth}")

        all_learnings = []
        all_sources = []
        all_follow_up_questions = []

        # Generate initial search queries
        initial_queries = self.generate_search_queries(topic, breadth)

        for i, query in enumerate(initial_queries):
            print(f"\nResearching query {i + 1}/{len(initial_queries)}: {query}")

            # Search for this query
            results = self.search_web(query, 5)
            all_sources.extend([r['url'] for r in results])

            # Analyze results
            analysis = self.analyze_search_results(query, results)
            all_learnings.extend(analysis.get("learnings", []))
            all_follow_up_questions.extend(analysis.get("follow_up_questions", []))

            # If depth > 1, do follow-up research
            if depth > 1 and analysis.get("follow_up_questions"):
                print(f"  Following up with {len(analysis['follow_up_questions'])} questions...")

                for follow_up in analysis["follow_up_questions"][:2]:  # Limit follow-ups
                    print(f"    Researching: {follow_up}")
                    follow_up_results = self.search_web(follow_up, 3)
                    all_sources.extend([r['url'] for r in follow_up_results])

                    follow_up_analysis = self.analyze_search_results(follow_up, follow_up_results)
                    all_learnings.extend(follow_up_analysis.get("learnings", []))

        # Remove duplicates
        all_learnings = list(set(all_learnings))
        all_sources = list(set(all_sources))

        print(f"\nResearch completed!")
        print(f"Total learnings: {len(all_learnings)}")
        print(f"Total sources: {len(all_sources)}")

        # Generate final report
        final_report = self.generate_final_report(topic, all_learnings, all_sources)

        return {
            "topic": topic,
            "report": final_report,
            "learnings": all_learnings,
            "sources": all_sources,
            "follow_up_questions": all_follow_up_questions,
            "stats": {
                "total_learnings": len(all_learnings),
                "total_sources": len(all_sources),
                "total_follow_ups": len(all_follow_up_questions)
            }
        }


dotenv.load_dotenv()


def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main agent function.
    
    Args:
        input_data: User input data containing:
            - message: The research topic to investigate
            - depth: How deep to go in follow-up research (1-3, default: 2)
            - breadth: Number of initial search queries (1-5, default: 3)
        config: Agent configuration
    
    Returns:
        Agent response with research results
    """

    try:
        # Extract parameters from input
        topic = input_data.get("message", "Palestine-Israeli conflict")
        depth = input_data.get("depth", 2)
        breadth = input_data.get("breadth", 3)

        # Create agent and perform research
        agent = DeepResearchAgent()
        result = agent.research(topic, depth, breadth)

        # Return structured response
        return {
            "topic": result["topic"],
            "report": result["report"],
            "learnings": result["learnings"],
            "sources": result["sources"],
            "follow_up_questions": result["follow_up_questions"],
            "stats": result["stats"],
            "status": "success",
            "agent": "deep_research",
            "version": "1.0.0"
        }

    except Exception as e:
        return {
            "error": str(e),
            "status": "error",
            "agent": "deep_research",
            "version": "1.0.0"
        }


# For local testing
if __name__ == "__main__":
    test_input = {
        "message": "George Kour",
        "breadth": 3,
        "depth": 2
    }
    test_config = {}

    result = main(test_input, test_config)
    print(json.dumps(result, indent=2))
