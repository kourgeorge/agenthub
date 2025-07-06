#!/usr/bin/env python3
"""
Example: Create and Publish an Agent using AgentHub SDK

This example demonstrates:
1. Creating an agent using the SDK
2. Setting up agent configuration
3. Creating agent code
4. Publishing the agent to the platform
5. Testing the published agent

Run this example with:
    python examples/create_and_publish_agent.py
"""

import os
import sys
import asyncio
import tempfile
import shutil
from pathlib import Path

# Add the SDK to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "agenthub-sdk"))

from agenthub_sdk import Agent, AgentConfig, AgentHubClient


class WeatherAgent(Agent):
    """A simple weather information agent that provides weather data."""
    
    def __init__(self):
        super().__init__()
        
        # Configure the agent
        self.config = AgentConfig(
            name="weather-agent",
            description="A helpful weather information agent that provides current weather data and forecasts",
            version="1.0.0",
            author="Weather Expert",
            email="weather@example.com",
            entry_point="weather_agent.py",
            requirements=["requests>=2.25.0"],
            config_schema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "OpenWeatherMap API key"
                    },
                    "units": {
                        "type": "string",
                        "enum": ["metric", "imperial"],
                        "default": "metric",
                        "description": "Temperature units"
                    }
                },
                "required": ["api_key"]
            },
            tags=["weather", "forecast", "api"],
            category="utilities",
            pricing_model="per_use",
            price_per_use=0.01,
            monthly_price=None
        )
    
    def get_config(self) -> AgentConfig:
        return self.config
    
    def process(self, input_data: dict, config: dict = None) -> dict:
        """Process weather requests."""
        # This is just a placeholder - the actual logic will be in the agent code
        return {"message": "Weather processing logic implemented in agent code"}


async def create_agent_code(directory: str):
    """Create the agent code files."""
    agent_dir = Path(directory)
    
    # Create the main agent file
    agent_code = '''#!/usr/bin/env python3
"""
Weather Agent - Provides weather information and forecasts.
"""

import json
import requests
from typing import Dict, Any, Optional


def get_weather(city: str, api_key: str, units: str = "metric") -> Dict[str, Any]:
    """Get current weather for a city."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": units
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
            "units": units
        }
    except requests.RequestException as e:
        return {"error": f"Failed to get weather data: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def get_forecast(city: str, api_key: str, units: str = "metric") -> Dict[str, Any]:
    """Get 5-day forecast for a city."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": city,
            "appid": api_key,
            "units": units
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Group forecasts by day
        daily_forecasts = {}
        for item in data["list"]:
            date = item["dt_txt"].split(" ")[0]
            if date not in daily_forecasts:
                daily_forecasts[date] = {
                    "temp_min": item["main"]["temp_min"],
                    "temp_max": item["main"]["temp_max"],
                    "description": item["weather"][0]["description"],
                    "humidity": item["main"]["humidity"]
                }
        
        return {
            "city": data["city"]["name"],
            "country": data["city"]["country"],
            "forecasts": daily_forecasts,
            "units": units
        }
    except requests.RequestException as e:
        return {"error": f"Failed to get forecast data: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main agent function.
    
    Args:
        input_data: User input containing query and parameters
        config: Agent configuration (API key, units, etc.)
    
    Returns:
        Weather information or error message
    """
    try:
        # Get configuration
        api_key = config.get("api_key")
        if not api_key:
            return {"error": "API key is required. Please configure the agent with an OpenWeatherMap API key."}
        
        units = config.get("units", "metric")
        
        # Parse input
        query = input_data.get("query", "").lower()
        city = input_data.get("city")
        
        if not city:
            return {"error": "City is required. Please provide a city name."}
        
        # Process different types of queries
        if "forecast" in query or "5-day" in query:
            result = get_forecast(city, api_key, units)
        else:
            # Default to current weather
            result = get_weather(city, api_key, units)
        
        # Add metadata
        result["query_type"] = "forecast" if "forecast" in query else "current"
        result["city_requested"] = city
        
        return result
        
    except Exception as e:
        return {"error": f"Agent execution failed: {str(e)}"}


# For testing
if __name__ == "__main__":
    # Test the agent
    test_input = {
        "query": "current weather",
        "city": "London"
    }
    
    test_config = {
        "api_key": "your_api_key_here",
        "units": "metric"
    }
    
    result = main(test_input, test_config)
    print(json.dumps(result, indent=2))
'''
    
    # Write the agent code
    with open(agent_dir / "weather_agent.py", "w") as f:
        f.write(agent_code)
    
    # Create requirements.txt
    requirements = '''requests>=2.25.0
'''
    
    with open(agent_dir / "requirements.txt", "w") as f:
        f.write(requirements)
    
    # Create README.md
    readme = '''# Weather Agent

A simple weather information agent that provides current weather data and forecasts.

## Features

- Get current weather for any city
- Get 5-day weather forecast
- Support for metric and imperial units
- Uses OpenWeatherMap API

## Configuration

The agent requires an OpenWeatherMap API key. You can get one for free at:
https://openweathermap.org/api

## Usage

The agent accepts the following input format:

```json
{
    "query": "current weather",
    "city": "London"
}
```

Or for forecasts:

```json
{
    "query": "5-day forecast",
    "city": "New York"
}
```

## Configuration Schema

- `api_key` (required): OpenWeatherMap API key
- `units` (optional): Temperature units ("metric" or "imperial"), defaults to "metric"
'''
    
    with open(agent_dir / "README.md", "w") as f:
        f.write(readme)


async def main():
    """Main example function."""
    print("🌤️  Weather Agent Creation Example")
    print("=" * 50)
    
    # Create a temporary directory for the agent code
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Created temporary directory: {temp_dir}")
        
        # Create the agent code
        await create_agent_code(temp_dir)
        print("📝 Created agent code files")
        
        # Create the agent instance
        agent = WeatherAgent()
        print("🤖 Created agent instance")
        
        # Validate the agent configuration
        config = agent.get_config()
        errors = config.validate()
        if errors:
            print(f"❌ Agent validation failed: {errors}")
            return
        
        print("✅ Agent configuration is valid")
        
        # Connect to the AgentHub platform
        base_url = "http://localhost:8002"
        print(f"🔗 Connecting to AgentHub at: {base_url}")
        
        async with AgentHubClient(base_url) as client:
            # Check if server is healthy
            if not await client.health_check():
                print("❌ Server is not responding. Make sure the server is running.")
                return
            
            print("✅ Server is healthy")
            
            # Submit the agent
            print("📤 Submitting agent to platform...")
            try:
                result = await client.submit_agent(agent, temp_dir)
                print(f"✅ Agent submitted successfully!")
                print(f"   Agent ID: {result.get('agent_id')}")
                print(f"   Status: {result.get('status')}")
                
                # List available agents to confirm
                print("\n📋 Listing available agents...")
                agents_result = await client.list_agents()
                agents = agents_result.get("agents", [])
                
                if agents:
                    print(f"Found {len(agents)} agents:")
                    for agent_info in agents:
                        print(f"  - {agent_info['name']} (ID: {agent_info['id']}) - {agent_info['status']}")
                else:
                    print("No agents found")
                
                # Test hiring the agent
                print("\n💼 Testing agent hiring...")
                agent_id = result.get("agent_id")
                if agent_id:
                    hire_result = await client.hire_agent(
                        agent_id=agent_id,
                        config={"api_key": "demo_key", "units": "metric"},
                        billing_cycle="per_use"
                    )
                    print(f"✅ Agent hired successfully!")
                    print(f"   Hiring ID: {hire_result.get('hiring_id')}")
                    
                    # Test execution
                    print("\n🚀 Testing agent execution...")
                    execution_result = await client.run_agent(
                        agent_id=agent_id,
                        input_data={
                            "query": "current weather",
                            "city": "London"
                        },
                        wait_for_completion=True,
                        timeout=30
                    )
                    
                    execution = execution_result.get("execution", {})
                    print(f"✅ Execution completed!")
                    print(f"   Status: {execution.get('status')}")
                    print(f"   Result: {execution.get('result', 'No result')}")
                
            except Exception as e:
                print(f"❌ Failed to submit agent: {e}")
                return
        
        print("\n🎉 Example completed successfully!")
        print("\nNext steps:")
        print("1. The agent is now available on the platform")
        print("2. Users can hire and execute the agent")
        print("3. You can view the agent in the web interface")
        print("4. The agent will need approval before being publicly available")


if __name__ == "__main__":
    asyncio.run(main()) 