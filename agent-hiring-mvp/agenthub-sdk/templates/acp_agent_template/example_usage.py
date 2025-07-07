#!/usr/bin/env python3
"""
Example: How to customize the ACP Agent Template

This example shows how to extend the basic template to create
a specialized agent with custom functionality.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from acp_agent_template import ACPAgentTemplate


class WeatherAgent(ACPAgentTemplate):
    """
    Example: Weather Agent
    
    This agent demonstrates how to extend the template to create
    a specialized agent that provides weather information.
    """
    
    def __init__(self):
        super().__init__(
            name="Weather Agent",
            version="1.0.0",
            description="An agent that provides weather information and forecasts"
        )
        
        # Mock weather data (in real implementation, use weather API)
        self.weather_data = {
            "new york": {"temp": 22, "condition": "sunny", "humidity": 60},
            "london": {"temp": 15, "condition": "cloudy", "humidity": 80},
            "tokyo": {"temp": 28, "condition": "rainy", "humidity": 85},
            "paris": {"temp": 18, "condition": "partly cloudy", "humidity": 70}
        }
        
        logger.info("Weather Agent initialized with mock data")
    
    async def process_chat_message(self, message: str, session: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process chat messages with weather-specific logic.
        """
        message_lower = message.lower()
        
        # Check if this is a weather request
        if any(keyword in message_lower for keyword in ["weather", "temperature", "forecast", "temp"]):
            return await self.handle_weather_request(message, session, context)
        
        # Check for location-specific queries
        for city in self.weather_data.keys():
            if city in message_lower:
                return await self.get_weather_for_city(city, session)
        
        # Default responses
        if "hello" in message_lower:
            return self.create_response("Hello! I'm a weather agent. Ask me about the weather in any city!")
        elif "help" in message_lower:
            return self.create_response("I can help you with weather information. Try asking 'What's the weather in New York?' or 'Tell me about the temperature in London'.")
        elif "capabilities" in message_lower:
            return self.create_response("I can provide weather information, temperature data, and forecasts for major cities worldwide.")
        else:
            return self.create_response(f"I didn't understand '{message}'. Try asking about the weather in a city!")
    
    async def handle_weather_request(self, message: str, session: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle weather-specific requests."""
        message_lower = message.lower()
        
        # Extract city name (simple implementation)
        for city in self.weather_data.keys():
            if city in message_lower:
                return await self.get_weather_for_city(city, session)
        
        # General weather request without specific city
        return self.create_response(
            "I can provide weather information for major cities. "
            "Try asking about New York, London, Tokyo, or Paris!"
        )
    
    async def get_weather_for_city(self, city: str, session: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather information for a specific city."""
        city_lower = city.lower()
        
        if city_lower in self.weather_data:
            weather = self.weather_data[city_lower]
            response = (
                f"🌤️ Weather in {city.title()}:\n"
                f"Temperature: {weather['temp']}°C\n"
                f"Condition: {weather['condition']}\n"
                f"Humidity: {weather['humidity']}%"
            )
            
            # Add to session context
            session['context']['last_weather_city'] = city
            
            return self.create_response(response, extra_data={
                "city": city,
                "weather": weather,
                "type": "weather_info"
            })
        else:
            return self.create_response(f"Sorry, I don't have weather data for {city}. Try New York, London, Tokyo, or Paris.")
    
    def create_response(self, text: str, extra_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a standardized response."""
        response = {
            "agent": self.name,
            "version": self.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response": text,
            "processed": True,
            "message_id": f"msg_{self.message_count + 1}",
            "processing_time_ms": 25
        }
        
        if extra_data:
            response.update(extra_data)
        
        return response
    
    async def create_app(self):
        """Extend the base app with custom endpoints."""
        app = await super().create_app()
        
        # Add custom endpoints
        app.router.add_get('/weather', self.get_all_weather)
        app.router.add_get('/weather/{city}', self.get_city_weather)
        app.router.add_post('/weather/update', self.update_weather_data)
        
        return app
    
    async def get_all_weather(self, request):
        """Custom endpoint: Get weather for all cities."""
        return web.json_response({
            "cities": self.weather_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def get_city_weather(self, request):
        """Custom endpoint: Get weather for specific city."""
        city = request.match_info['city'].lower()
        
        if city in self.weather_data:
            return web.json_response({
                "city": city,
                "weather": self.weather_data[city],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        else:
            return web.json_response({
                "error": f"Weather data not available for {city}",
                "available_cities": list(self.weather_data.keys())
            }, status=404)
    
    async def update_weather_data(self, request):
        """Custom endpoint: Update weather data."""
        try:
            data = await request.json()
            city = data.get('city', '').lower()
            weather_info = data.get('weather', {})
            
            if city and weather_info:
                self.weather_data[city] = weather_info
                return web.json_response({
                    "message": f"Weather data updated for {city}",
                    "city": city,
                    "weather": weather_info
                })
            else:
                return web.json_response({
                    "error": "Invalid data format. Expected 'city' and 'weather' fields."
                }, status=400)
        except Exception as e:
            return web.json_response({
                "error": f"Failed to update weather data: {str(e)}"
            }, status=500)


class CalculatorAgent(ACPAgentTemplate):
    """
    Example: Calculator Agent
    
    This agent demonstrates how to create a specialized agent
    that performs mathematical calculations.
    """
    
    def __init__(self):
        super().__init__(
            name="Calculator Agent",
            version="1.0.0",
            description="An agent that performs mathematical calculations"
        )
        
        # Import math functions safely
        import math
        self.math_functions = {
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'sqrt': math.sqrt,
            'log': math.log,
            'exp': math.exp,
            'pi': math.pi,
            'e': math.e
        }
    
    async def process_chat_message(self, message: str, session: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process messages with calculation logic."""
        message_lower = message.lower()
        
        # Check for calculation keywords
        if any(keyword in message_lower for keyword in ["calculate", "compute", "solve", "+", "-", "*", "/", "="]):
            return await self.handle_calculation(message, session, context)
        
        # Default responses
        if "hello" in message_lower:
            return self.create_response("Hello! I'm a calculator agent. I can help you with mathematical calculations!")
        elif "help" in message_lower:
            return self.create_response("I can perform calculations like: 2+2, sqrt(16), sin(pi/2), etc. Just ask me to calculate something!")
        else:
            return self.create_response(f"I can help with calculations. Try asking me to calculate something like '2+2' or 'sqrt(16)'")
    
    async def handle_calculation(self, message: str, session: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle calculation requests."""
        try:
            # Extract mathematical expression (simplified)
            expression = message.lower()
            
            # Remove common words
            for word in ["calculate", "compute", "solve", "what", "is", "equals", "="]:
                expression = expression.replace(word, "")
            
            expression = expression.strip()
            
            # Simple calculation (be careful with eval in production!)
            # In a real implementation, use a proper math parser
            if expression:
                # Replace common math functions
                for func_name in self.math_functions:
                    if func_name in expression:
                        expression = expression.replace(func_name, f"self.math_functions['{func_name}']")
                
                # Very basic evaluation (unsafe - for demo only)
                # In production, use a proper math expression parser
                result = eval(expression, {"__builtins__": {}}, {"self": self})
                
                return self.create_response(
                    f"📊 Calculation Result: {result}",
                    extra_data={
                        "expression": message,
                        "result": result,
                        "type": "calculation"
                    }
                )
            else:
                return self.create_response("I couldn't find a mathematical expression to calculate. Try something like '2+2' or 'sqrt(16)'")
        
        except Exception as e:
            return self.create_response(f"Sorry, I couldn't calculate that. Error: {str(e)}")
    
    def create_response(self, text: str, extra_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a standardized response."""
        response = {
            "agent": self.name,
            "version": self.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response": text,
            "processed": True,
            "message_id": f"msg_{self.message_count + 1}",
            "processing_time_ms": 15
        }
        
        if extra_data:
            response.update(extra_data)
        
        return response


async def main():
    """
    Example of how to run custom agents.
    
    Uncomment the agent you want to test.
    """
    
    # Create your custom agent
    # agent = WeatherAgent()
    agent = CalculatorAgent()
    
    # Create and run the app
    app = await agent.create_app()
    
    # Start the server
    from aiohttp import web
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", 8001)
    await site.start()
    
    print(f"🚀 {agent.name} is running on http://localhost:8001")
    print("Try these endpoints:")
    print("  GET  /health - Health check")
    print("  GET  /info - Agent information")
    print("  POST /chat - Chat interface")
    print("  GET  /sessions - List sessions")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 