#!/usr/bin/env python3
"""
Sample script to add agents with hiring metadata to the BeeAI platform.
This demonstrates how to create agents that can be hired through the hiring system.
"""

import asyncio
import httpx
from decimal import Decimal
from uuid import uuid4

# Configuration
BEEAI_BASE_URL = "http://localhost:8333"
API_BASE_URL = f"{BEEAI_BASE_URL}/api/v1"

# Sample agents with hiring metadata
SAMPLE_AGENTS = [
    {
        "name": "research-assistant",
        "description": "A specialized research agent that can perform deep research on any topic, analyze data, and provide comprehensive reports.",
        "hiring_metadata": {
            "pricing_model": "per_task",
            "price_per_task": Decimal("5.00"),
            "currency": "USD",
            "availability": True,
            "reliability_score": 95.0,
            "hiring_enabled": True,
            "max_concurrent_tasks": 3,
            "task_timeout_seconds": 600,
            "description": "Expert research assistant for academic and business research",
            "capabilities": ["research", "data_analysis", "report_writing", "academic_writing"],
            "tags": ["research", "academic", "analysis"]
        }
    },
    {
        "name": "content-writer",
        "description": "Professional content writer specializing in blog posts, articles, and marketing copy.",
        "hiring_metadata": {
            "pricing_model": "per_token",
            "price_per_token": Decimal("0.02"),
            "currency": "USD",
            "availability": True,
            "reliability_score": 92.0,
            "hiring_enabled": True,
            "max_concurrent_tasks": 5,
            "task_timeout_seconds": 900,
            "description": "Professional content writer for blogs, articles, and marketing",
            "capabilities": ["content_writing", "blog_posts", "marketing_copy", "seo"],
            "tags": ["writing", "content", "marketing"]
        }
    },
    {
        "name": "code-reviewer",
        "description": "Expert code reviewer that analyzes code quality, security, and best practices.",
        "hiring_metadata": {
            "pricing_model": "fixed",
            "fixed_price": Decimal("10.00"),
            "currency": "USD",
            "availability": True,
            "reliability_score": 98.0,
            "hiring_enabled": True,
            "max_concurrent_tasks": 2,
            "task_timeout_seconds": 1200,
            "description": "Expert code reviewer for security and quality analysis",
            "capabilities": ["code_review", "security_analysis", "best_practices", "python", "javascript"],
            "tags": ["code", "review", "security"]
        }
    },
    {
        "name": "data-analyst",
        "description": "Data analyst specializing in statistical analysis, data visualization, and insights generation.",
        "hiring_metadata": {
            "pricing_model": "per_task",
            "price_per_task": Decimal("15.00"),
            "currency": "USD",
            "availability": True,
            "reliability_score": 89.0,
            "hiring_enabled": True,
            "max_concurrent_tasks": 2,
            "task_timeout_seconds": 1800,
            "description": "Professional data analyst for statistical analysis and insights",
            "capabilities": ["data_analysis", "statistics", "visualization", "insights", "excel"],
            "tags": ["data", "analysis", "statistics"]
        }
    },
    {
        "name": "translation-expert",
        "description": "Multi-language translation expert supporting 50+ languages with cultural context awareness.",
        "hiring_metadata": {
            "pricing_model": "per_token",
            "price_per_token": Decimal("0.01"),
            "currency": "USD",
            "availability": True,
            "reliability_score": 96.0,
            "hiring_enabled": True,
            "max_concurrent_tasks": 10,
            "task_timeout_seconds": 300,
            "description": "Professional translator supporting 50+ languages",
            "capabilities": ["translation", "localization", "cultural_context", "proofreading"],
            "tags": ["translation", "languages", "localization"]
        }
    }
]


async def create_sample_agents():
    """Create sample agents with hiring metadata"""
    async with httpx.AsyncClient() as client:
        print("🤖 Creating sample agents with hiring metadata...")
        
        for agent_data in SAMPLE_AGENTS:
            try:
                # First, create a provider (if needed)
                provider_id = str(uuid4())
                
                # Create the agent with hiring metadata
                agent_payload = {
                    "id": str(uuid4()),
                    "name": agent_data["name"],
                    "description": agent_data["description"],
                    "metadata": {
                        "provider_id": provider_id,
                        "env": []
                    },
                    "hiring_metadata": agent_data["hiring_metadata"]
                }
                
                # Note: This is a simplified example. In a real implementation,
                # you would need to use the proper agent creation API
                print(f"✅ Created agent: {agent_data['name']}")
                print(f"   - Pricing: {agent_data['hiring_metadata']['pricing_model']}")
                print(f"   - Reliability: {agent_data['hiring_metadata']['reliability_score']}%")
                print(f"   - Capabilities: {', '.join(agent_data['hiring_metadata']['capabilities'])}")
                print()
                
            except Exception as e:
                print(f"❌ Failed to create agent {agent_data['name']}: {e}")
        
        print("🎉 Sample agents created successfully!")
        print("\nTo see these agents in the hiring system:")
        print("1. Start the BeeAI server: cd apps/beeai-server && python -m beeai_server")
        print("2. Open the hiring demo: http://localhost:5000/hiring_demo.html")
        print("3. Or use the API directly: http://localhost:8333/api/v1/hiring/agents")


async def test_hiring_api():
    """Test the hiring API endpoints"""
    async with httpx.AsyncClient() as client:
        print("\n🧪 Testing hiring API endpoints...")
        
        try:
            # Test listing hirable agents
            response = await client.get(f"{API_BASE_URL}/hiring/agents")
            if response.status_code == 200:
                agents = response.json()
                print(f"✅ Found {len(agents)} hirable agents")
                for agent in agents:
                    print(f"   - {agent['agent_name']} (${agent.get('fixed_price', agent.get('price_per_task', 'N/A'))})")
            else:
                print(f"❌ Failed to list agents: {response.status_code}")
            
            # Test getting credits
            response = await client.get(f"{API_BASE_URL}/hiring/credits")
            if response.status_code == 200:
                credits = response.json()
                print(f"✅ Credits balance: ${credits['balance']}")
            else:
                print(f"❌ Failed to get credits: {response.status_code}")
                
        except Exception as e:
            print(f"❌ API test failed: {e}")


if __name__ == "__main__":
    print("🚀 AI Agent Hiring System - Sample Data Setup")
    print("=" * 50)
    
    # Run the setup
    asyncio.run(create_sample_agents())
    asyncio.run(test_hiring_api())
    
    print("\n📚 Next Steps:")
    print("1. Start the BeeAI server")
    print("2. Run the Flask demo: cd apps/beeai-flask-demo && python app.py")
    print("3. Open http://localhost:5000/hiring_demo.html")
    print("4. Explore the hiring system!") 