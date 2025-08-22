#!/usr/bin/env python3
"""
deep_research - This agent performs a deep research on a subject given the query, depth and breadth parameters.

Updated to use the AgentHub Resource Management System for external resource access.
"""

import json
import os
import aiohttp
import asyncio
import time
from typing import List, Dict, Any, Optional
import dotenv


async def get_resource(resource_name: str, **kwargs):
    """
    Get a resource from the AgentHub server.
    
    Args:
        resource_name: Name of the resource (e.g., 'llm', 'web_search', 'vector_db')
        **kwargs: Resource-specific parameters
    
    Returns:
        Resource response or None if not available
    """
    try:
        # Get server URL from environment or use default
        # Use host.docker.internal for Docker containers to access host machine
        server_url = os.getenv("AGENTHUB_SERVER_URL", "http://host.docker.internal:8002")
        
        # Automatically get execution_id from environment variable
        execution_id = os.getenv("AGENTHUB_EXECUTION_ID")
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if execution_id:
            headers["X-Execution-ID"] = execution_id
        
        # Make async request to server resource endpoint
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{server_url}/api/v1/resources/{resource_name}",
                json=kwargs,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Resource {resource_name} not available: {response.status}")
                    return None
                    
    except Exception as e:
        print(f"Error accessing resource {resource_name}: {e}")
        return None


class DeepResearchAgent:

    def __init__(self):
        """
        Initialize the deep research agent.
        
        The agent will use the AgentHub server for external resources.
        Falls back to direct API calls if server resources are not available.
        """


    async def search_web(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web using AgentHub server or fallback to direct API"""
        # Try to use server resource first
        search_response = await get_resource(
            "web_search",
            query=query,
            provider="serper",
            num_results=num_results
        )
        
        if search_response and search_response.get("success"):
            # Convert server response to expected format
            results = []
            for item in search_response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "domain": item.get("displayLink", "")
                })
            return results
        else:
            raise Exception("Web search resource not available or failed")


    async def generate_search_queries(self, research_topic: str, num_queries: int = 3, model_name: str = "gpt-3.5-turbo") -> List[str]:
        """Generate search queries using AgentHub server or fallback to direct API"""
        prompt = f"""Given the research topic: "{research_topic}", generate {num_queries} specific search queries to investigate this topic thoroughly. 
        Each query should be unique and target different aspects of the topic.
        Return only the queries, one per line. Do not include any quotes or numbering, just the search query."""

        # Try to use server resource first
        llm_response = await get_resource(
            "llm",
            provider="openai",
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )
        
        if llm_response and llm_response.get("success"):
            content = llm_response.get("content", "")
            queries = content.strip().split('\n')
            return [q.strip() for q in queries if q.strip()][:num_queries]
        
        # Fallback to direct API call
        if hasattr(self, 'client'):
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.7
                )

                queries = response.choices[0].message.content.strip().split('\n')
                return [q.strip() for q in queries if q.strip()][:num_queries]
            except Exception as e:
                print(f"Error generating queries: {e}")
                return [research_topic]
        else:
            print("No LLM API key available")
            return [research_topic]

    async def analyze_search_results(self, query: str, results: List[Dict[str, Any]], model_name: str = "gpt-3.5-turbo") -> Dict[str, Any]:
        """Analyze search results using AgentHub server or fallback to direct API"""
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

        # Try to use server resource first
        llm_response = await get_resource(
            "llm",
            provider="openai",
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3
        )
        
        if llm_response and llm_response.get("success"):
            content = llm_response.get("content", "")
            # Try to extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            try:
                analysis = json.loads(content)
                return analysis
            except:
                return {"learnings": [], "follow_up_questions": []}
        
        # Fallback to direct API call
        if hasattr(self, 'client'):
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
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
        else:
            print("No LLM API key available")
            return {"learnings": [], "follow_up_questions": []}

    async def generate_final_report(self, research_topic: str, all_learnings: List[str], all_sources: List[str], model_name: str = "gpt-3.5-turbo") -> str:
        """Generate final report using AgentHub server or fallback to direct API"""
        learnings_text = "\n".join([f"- {learning}" for learning in all_learnings])
        sources_text = "\n".join([f"- {source}" for source in all_sources])

        prompt = f"""Write a comprehensive research report on: "{research_topic}"

Key Findings:
{learnings_text}

Sources:
{sources_text}

Write a detailed report (2-3 pages) that synthesizes all findings, includes all key learnings, and provides actionable insights. Use markdown format."""

        # Try to use server resource first
        llm_response = await get_resource(
            "llm",
            provider="openai",
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.3
        )
        
        if llm_response and llm_response.get("success"):
            return llm_response.get("content", "")
        
        # Fallback to direct API call
        if hasattr(self, 'client'):
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1500,
                    temperature=0.3
                )

                return response.choices[0].message.content
            except Exception as e:
                print(f"Error generating report: {e}")
                return f"Error generating report: {e}"
        else:
            return "Error: No LLM API key available for report generation"

    async def research(self, topic: str, depth: int = 2, breadth: int = 3, model_name: str = "gpt-3.5-turbo") -> Dict[str, Any]:
        """Main research function"""
        print(f"Starting deep research on: {topic}")
        print(f"Depth: {depth}, Breadth: {breadth}, Model: {model_name}")

        all_learnings = []
        all_sources = []
        all_follow_up_questions = []

        # Generate initial search queries
        initial_queries = await self.generate_search_queries(topic, breadth, model_name)

        for i, query in enumerate(initial_queries):
            print(f"\nResearching query {i + 1}/{len(initial_queries)}: {query}")

            # Search for this query
            results = await self.search_web(query, 5)
            all_sources.extend([r['url'] for r in results])

            # Analyze results
            analysis = await self.analyze_search_results(query, results, model_name)
            all_learnings.extend(analysis.get("learnings", []))
            all_follow_up_questions.extend(analysis.get("follow_up_questions", []))

            # If depth > 1, do follow-up research
            if depth > 1 and analysis.get("follow_up_questions"):
                print(f"  Following up with {len(analysis['follow_up_questions'])} questions...")

                for follow_up in analysis["follow_up_questions"][:2]:  # Limit follow-ups
                    print(f"    Researching: {follow_up}")
                    follow_up_results = await self.search_web(follow_up, 3)
                    all_sources.extend([r['url'] for r in follow_up_results])

                    follow_up_analysis = await self.analyze_search_results(follow_up, follow_up_results, model_name)
                    all_learnings.extend(follow_up_analysis.get("learnings", []))

        # Remove duplicates
        all_learnings = list(set(all_learnings))
        all_sources = list(set(all_sources))

        print(f"\nResearch completed!")
        print(f"Total learnings: {len(all_learnings)}")
        print(f"Total sources: {len(all_sources)}")

        # Generate final report
        final_report = await self.generate_final_report(topic, all_learnings, all_sources, model_name)

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


async def _main_async(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async main agent function.
    
    Args:
        input_data: User input data containing:
            - topic: The research topic to investigate
            - depth: How deep to go in follow-up research (1-3, default: 2)
            - breadth: Number of initial search queries (1-5, default: 3)
            - execution_id: Execution ID for resource tracking (optional)
        config: Agent configuration
    
    Returns:
        Agent response with research results matching the new outputSchema
    """
    start_time = time.time()
    
    try:
        # Extract parameters from input
        topic = input_data.get("topic", "Advances in Quantum Computing")
        depth = input_data.get("depth", 2)
        breadth = input_data.get("breadth", 3)
        model_name = input_data.get("model_name", "gpt-3.5-turbo") # Get model_name from input
        execution_id = input_data.get("execution_id")  # Get execution ID for resource tracking

        # Create agent and perform research
        agent = DeepResearchAgent()
        result = await agent.research(topic, depth, breadth, model_name)
        
        # Calculate processing time
        processing_time = time.time() - start_time

        # Return structured response matching the new outputSchema
        return {
            "research_results": {
                "summary": result["report"],
                "key_insights": result["learnings"],
                "sources": result["sources"]
            },
            "metadata": {
                "processing_time": processing_time,
                "searches_performed": breadth + (depth > 1 and len(result.get("follow_up_questions", [])) or 0),
                "depth_level": depth,
                "model_used": model_name # Add model_used to metadata
            },
            "status": "success"
        }

    except Exception as e:
        return {
            "research_results": {
                "summary": f"Error during research: {str(e)}",
                "key_insights": [],
                "sources": []
            },
            "metadata": {
                "processing_time": time.time() - start_time,
                "searches_performed": 0,
                "depth_level": 0,
                "model_used": "N/A" # Add model_used to metadata
            },
            "status": "error"
        }


def execute(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute function - main entry point for the agent.
    
    This function matches the function name expected in the new config schema.
    
    Args:
        input_data: User input data containing:
            - topic: The research topic to investigate
            - depth: How deep to go in follow-up research (1-3, default: 2)
            - breadth: Number of initial search queries (1-5, default: 3)
        config: Agent configuration
    
    Returns:
        Agent response with research results matching the new outputSchema
    """
    import asyncio
    
    try:
        # Check if there's already an event loop running
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, we need to run the coroutine differently
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _main_async(input_data, config))
                return future.result()
        except RuntimeError:
            # No event loop running, we can create one
            return asyncio.run(_main_async(input_data, config))
            
    except Exception as e:
        return {
            "research_results": {
                "summary": f"Error during execution: {str(e)}",
                "key_insights": [],
                "sources": []
            },
            "metadata": {
                "processing_time": 0,
                "searches_performed": 0,
                "depth_level": 0,
                "model_used": "N/A" # Add model_used to metadata
            },
            "status": "error"
        }


def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main agent function (legacy support).
    
    This is a synchronous wrapper around the async implementation.
    
    Args:
        input_data: User input data containing:
            - topic: The research topic to investigate
            - depth: How deep to go in follow-up research (1-3, default: 2)
            - breadth: Number of initial search queries (1-5, default: 3)
        config: Agent configuration
    
    Returns:
        Agent response with research results
    """
    return execute(input_data, config)


# For local testing
if __name__ == "__main__":
    test_input = {
        "topic": "George Kour",
        "breadth": 3,
        "depth": 2,
        "model_name": "gpt-4o"
    }
    test_config = {}

    result = execute(test_input, test_config)
    print(json.dumps(result, indent=2))
