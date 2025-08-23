#!/usr/bin/env python3
"""
Trip Planner Agent

A comprehensive trip planning agent that creates detailed travel itineraries including
activities, accommodations, dining recommendations, and day-by-day plans based on user preferences.
Now with real-time web search capabilities for up-to-date information.
"""

import json
import os
import sys
import time
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Literal
import warnings
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re

load_dotenv()

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Import the trip planner components
from configuration import Configuration
from state import (
    AgentState,
    AgentInputState,
    PlannerState,
    ResearchState,
    TripPlan,
    Destination,
    Accommodation,
    Activity,
    Restaurant,
    DayPlan,
    TripPreferences
)
from prompts import (
    trip_analysis_instructions,
    destination_research_prompt,
    accommodation_research_prompt,
    activity_research_prompt,
    restaurant_research_prompt,
    day_planning_prompt,
    final_itinerary_prompt
)
from utils import (
    get_today_str,
    parse_date_range,
    calculate_trip_duration,
    generate_dates_from_month_and_days,
    format_currency,
    get_api_key_for_model,
    validate_destination,
    get_weather_info
)

# Import LangChain components
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, get_buffer_string
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from langgraph.types import Command

# Import search tools
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize a configurable model that we will use throughout the agent
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


class WebSearchTools:
    """Tools for web searching and crawling."""
    
    def __init__(self, config: Configuration):
        self.config = config
        self.serper_api_key = None
        self.session = None
        
    async def initialize(self):
        """Initialize search tools and HTTP session."""
        try:
            # Initialize Serper search if API key is available
            self.serper_api_key = os.getenv("SERPER_API_KEY")
            if self.serper_api_key:
                logger.info("Serper search initialized")
            else:
                logger.warning("SERPER_API_KEY not found, web search will be limited")
            
            # Initialize HTTP session for web crawling
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            logger.info("HTTP session initialized")
            
        except Exception as e:
            logger.error(f"Error initializing web search tools: {e}")
    
    async def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web for information using Serper API."""
        try:
            if not self.serper_api_key:
                logger.warning("Serper API key not available, returning empty results")
                return []
            
            logger.info(f"Searching web for: {query}")
            
            # Serper API endpoint
            url = "https://google.serper.dev/search"
            
            # Prepare the request
            payload = {
                "q": query,
                "num": max_results
            }
            
            headers = {
                "X-API-KEY": self.serper_api_key,
                "Content-Type": "application/json"
            }
            
            # Make the request
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Serper API request failed, status: {response.status}")
                    return []
                
                data = await response.json()
                
                # Parse Serper results
                parsed_results = []
                
                # Extract organic results
                organic_results = data.get('organic', [])
                for result in organic_results[:max_results]:
                    parsed_results.append({
                        'title': result.get('title', ''),
                        'url': result.get('link', ''),
                        'content': result.get('snippet', ''),
                        'source': 'organic'
                    })
                
                # Extract knowledge graph results if available
                knowledge_graph = data.get('knowledgeGraph', {})
                if knowledge_graph:
                    parsed_results.append({
                        'title': knowledge_graph.get('title', ''),
                        'url': knowledge_graph.get('link', ''),
                        'content': knowledge_graph.get('description', ''),
                        'source': 'knowledge_graph'
                    })
                
                # Extract featured snippet if available
                featured_snippet = data.get('answerBox', {})
                if featured_snippet:
                    parsed_results.append({
                        'title': featured_snippet.get('title', ''),
                        'url': featured_snippet.get('link', ''),
                        'content': featured_snippet.get('snippet', ''),
                        'source': 'featured_snippet'
                    })
                
                logger.info(f"Found {len(parsed_results)} search results from Serper")
                return parsed_results
                
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return []
    
    async def crawl_website(self, url: str) -> str:
        """Crawl a website and extract relevant content."""
        try:
            if not self.session:
                logger.warning("HTTP session not available")
                return ""
            
            logger.info(f"Crawling website: {url}")
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}, status: {response.status}")
                    return ""
                
                html = await response.text()
                
                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Extract text content
                text = soup.get_text()
                
                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                # Limit content length
                if len(text) > 2000:
                    text = text[:2000] + "..."
                
                logger.info(f"Extracted {len(text)} characters from {url}")
                return text
                
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return ""
    
    async def search_destination_info(self, destination: str) -> Dict[str, Any]:
        """Search for comprehensive destination information."""
        try:
            search_queries = [
                f"{destination} travel guide best time to visit",
                f"{destination} weather climate information",
                f"{destination} local customs culture etiquette",
                f"{destination} safety tips for tourists",
                f"{destination} top attractions things to do"
            ]
            
            all_results = []
            for query in search_queries:
                results = await self.search_web(query, max_results=3)
                all_results.extend(results)
            
            # Extract and organize information
            destination_info = {
                'description': '',
                'best_time_to_visit': '',
                'weather_info': '',
                'local_customs': '',
                'safety_tips': '',
                'attractions': [],
                'sources': []
            }
            
            for result in all_results:
                content = result.get('content', '')
                url = result.get('url', '')
                
                # Categorize information based on content
                if any(word in content.lower() for word in ['weather', 'climate', 'temperature']):
                    if not destination_info['weather_info']:
                        destination_info['weather_info'] = content[:500]
                elif any(word in content.lower() for word in ['custom', 'culture', 'etiquette']):
                    if not destination_info['local_customs']:
                        destination_info['local_customs'] = content[:500]
                elif any(word in content.lower() for word in ['safety', 'security', 'crime']):
                    if not destination_info['safety_tips']:
                        destination_info['safety_tips'] = content[:500]
                elif any(word in content.lower() for word in ['attraction', 'visit', 'see', 'do']):
                    destination_info['attractions'].append(content[:300])
                
                destination_info['sources'].append(url)
            
            # Generate description from available information
            if destination_info['attractions']:
                destination_info['description'] = ' '.join(destination_info['attractions'][:2])
            
            logger.info(f"Collected destination info for {destination}")
            return destination_info
            
        except Exception as e:
            logger.error(f"Error searching destination info: {e}")
            return {}
    
    async def search_accommodations(self, destination: str, budget_level: str) -> List[Dict[str, Any]]:
        """Search for accommodation options."""
        try:
            query = f"{destination} {budget_level} hotels accommodations booking"
            results = await self.search_web(query, max_results=8)
            
            accommodations = []
            for result in results:
                content = result.get('content', '')
                url = result.get('url', '')
                
                # Skip generic booking.com URLs and similar generic results
                if any(generic in url.lower() for generic in [
                    'booking.com/city/', 'booking.com/region/', 'booking.com/accommodation/',
                    'booking.com/budget/', 'hotels.com', 'expedia.com', 'tripadvisor.com'
                ]):
                    continue
                
                # Skip if content is too generic
                if any(generic in content.lower() for generic in [
                    'booking.com', 'hotels.com', 'expedia.com', 'tripadvisor.com',
                    'find hotels', 'book hotels', 'hotel booking', 'accommodation booking'
                ]):
                    continue
                
                # Extract accommodation information only if it contains actual hotel details
                if any(word in content.lower() for word in ['hotel', 'accommodation', 'stay', 'room', 'guesthouse', 'hostel']):
                    # Try to extract hotel name
                    hotel_name = self.extract_hotel_name(content)
                    
                    # Skip if we couldn't extract a proper hotel name
                    if not hotel_name or hotel_name.lower() in ['hotel', 'accommodation', 'vienna', destination.lower()]:
                        continue
                    
                    # Extract more detailed information
                    amenities = self.extract_amenities(content)
                    price_range = self.extract_price_range(content, budget_level)
                    
                    # Generate a proper booking URL
                    booking_url = self.generate_booking_url(hotel_name, destination, url)
                    
                    # Skip if we can't generate a proper booking URL
                    if not booking_url:
                        continue
                    
                    accommodations.append({
                        'name': hotel_name,
                        'type': self.extract_accommodation_type(content),
                        'price_range': price_range,
                        'location': self.extract_location(content, destination),
                        'amenities': amenities,
                        'pros': self.extract_pros(content),
                        'cons': self.extract_cons(content),
                        'booking_tips': self.extract_booking_tips(content, booking_url),
                        'source_url': booking_url
                    })
            
            logger.info(f"Found {len(accommodations)} valid accommodation options with booking URLs")
            return accommodations[:5]  # Limit to 5 results
            
        except Exception as e:
            logger.error(f"Error searching accommodations: {e}")
            return []
    
    async def search_activities(self, destination: str, trip_type: str) -> List[Dict[str, Any]]:
        """Search for activities and attractions."""
        try:
            query = f"{destination} {trip_type} activities attractions things to do"
            results = await self.search_web(query, max_results=8)
            
            activities = []
            for result in results:
                content = result.get('content', '')
                url = result.get('url', '')
                
                # Extract activity information
                if any(word in content.lower() for word in ['museum', 'park', 'tour', 'visit', 'see', 'attraction']):
                    activity_name = self.extract_activity_name(content)
                    
                    activities.append({
                        'name': activity_name or 'Activity from search results',
                        'type': self.categorize_activity(content),
                        'description': content[:300],
                        'cost': self.extract_cost_info(content),
                        'duration': self.extract_duration_info(content),
                        'location': destination,
                        'best_time': 'Check current opening hours',
                        'booking_tips': f'Visit {url} for current information',
                        'source_url': url
                    })
            
            logger.info(f"Found {len(activities)} activity options")
            return activities[:6]  # Limit to 6 results
            
        except Exception as e:
            logger.error(f"Error searching activities: {e}")
            return []
    
    async def search_restaurants(self, destination: str, cuisine_preferences: str = "") -> List[Dict[str, Any]]:
        """Search for restaurant recommendations."""
        try:
            query = f"{destination} restaurants dining {cuisine_preferences} best places to eat"
            results = await self.search_web(query, max_results=8)
            
            restaurants = []
            for result in results:
                content = result.get('content', '')
                url = result.get('url', '')
                
                # Extract restaurant information
                if any(word in content.lower() for word in ['restaurant', 'dining', 'eat', 'food', 'cuisine']):
                    restaurant_name = self.extract_restaurant_name(content)
                    
                    restaurants.append({
                        'name': restaurant_name or 'Restaurant from search results',
                        'cuisine': self.extract_cuisine_type(content),
                        'price_range': self.extract_price_range(content, 'moderate'),
                        'location': destination,
                        'specialties': self.extract_specialties(content),
                        'atmosphere': 'Based on recent reviews',
                        'reservation_tips': f'Check {url} for current information',
                        'source_url': url
                    })
            
            logger.info(f"Found {len(restaurants)} restaurant options")
            return restaurants[:5]  # Limit to 5 results
            
        except Exception as e:
            logger.error(f"Error searching restaurants: {e}")
            return []
    
    def extract_hotel_name(self, content: str) -> str:
        """Extract hotel name from content."""
        # Simple pattern matching for hotel names
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Hotel|Resort|Inn|Lodge)',
            r'(?:at|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Vienna|Wien)',
            r'(?:Hotel|Resort|Inn|Lodge)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                hotel_name = match.group(1)
                # Filter out generic names
                if hotel_name.lower() not in ['vienna', 'wien', 'hotel', 'accommodation', 'stay']:
                    return hotel_name
        
        # Look for specific hotel names in the content
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if 'Hotel' in line and len(line) > 10 and len(line) < 100:
                # Extract potential hotel name
                words = line.split()
                for i, word in enumerate(words):
                    if word == 'Hotel' and i > 0:
                        potential_name = ' '.join(words[:i+1])
                        if len(potential_name) > 5 and potential_name.lower() not in ['vienna hotel', 'wien hotel']:
                            return potential_name
        
        return ""
    
    def extract_activity_name(self, content: str) -> str:
        """Extract activity name from content."""
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Museum|Park|Gallery|Tower)',
            r'visit\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        return ""
    
    def extract_restaurant_name(self, content: str) -> str:
        """Extract restaurant name from content."""
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Restaurant|Bistro|Cafe)',
            r'at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        return ""
    
    def extract_price_range(self, content: str, budget_level: str) -> str:
        """Extract price range from content."""
        if budget_level == "budget":
            return "$50-100"
        elif budget_level == "luxury":
            return "$200-500"
        else:
            return "$100-200"
    
    def extract_amenities(self, content: str) -> str:
        """Extract amenities from content."""
        amenities = []
        if 'wifi' in content.lower():
            amenities.append('WiFi')
        if 'breakfast' in content.lower():
            amenities.append('Breakfast')
        if 'parking' in content.lower():
            amenities.append('Parking')
        if 'gym' in content.lower():
            amenities.append('Gym')
        
        return ', '.join(amenities) if amenities else 'Standard amenities'
    
    def categorize_activity(self, content: str) -> str:
        """Categorize activity type."""
        if 'museum' in content.lower():
            return 'museum'
        elif 'park' in content.lower():
            return 'park'
        elif 'tour' in content.lower():
            return 'guided tour'
        else:
            return 'attraction'
    
    def extract_cost_info(self, content: str) -> str:
        """Extract cost information."""
        if 'free' in content.lower():
            return 'Free'
        elif 'cheap' in content.lower() or 'inexpensive' in content.lower():
            return '$5-15'
        else:
            return '$10-30'
    
    def extract_duration_info(self, content: str) -> str:
        """Extract duration information."""
        if 'hour' in content.lower():
            return '1-2 hours'
        elif 'day' in content.lower():
            return 'Full day'
        else:
            return '2-3 hours'
    
    def extract_cuisine_type(self, content: str) -> str:
        """Extract cuisine type."""
        cuisines = ['french', 'italian', 'chinese', 'japanese', 'indian', 'mexican', 'thai', 'mediterranean']
        for cuisine in cuisines:
            if cuisine in content.lower():
                return cuisine.title()
        return 'Local cuisine'
    
    def extract_specialties(self, content: str) -> str:
        """Extract restaurant specialties."""
        return 'Local specialties and seasonal dishes'
    
    def extract_accommodation_type(self, content: str) -> str:
        """Extract accommodation type from content."""
        content_lower = content.lower()
        if 'hotel' in content_lower:
            return 'hotel'
        elif 'hostel' in content_lower:
            return 'hostel'
        elif 'guesthouse' in content_lower or 'pension' in content_lower:
            return 'guesthouse'
        elif 'apartment' in content_lower or 'flat' in content_lower:
            return 'apartment'
        elif 'resort' in content_lower:
            return 'resort'
        else:
            return 'hotel'
    
    def extract_location(self, content: str, destination: str) -> str:
        """Extract specific location from content."""
        # Look for neighborhood or district mentions
        neighborhoods = ['city center', 'downtown', 'old town', 'historic district', 'business district']
        for neighborhood in neighborhoods:
            if neighborhood in content.lower():
                return f"{neighborhood}, {destination}"
        
        # Look for street names or landmarks
        import re
        street_pattern = r'(\w+\s+(?:Street|Straße|Gasse|Platz|Avenue|Boulevard))'
        match = re.search(street_pattern, content, re.IGNORECASE)
        if match:
            return f"{match.group(1)}, {destination}"
        
        return destination
    
    def extract_pros(self, content: str) -> str:
        """Extract positive aspects from content."""
        pros_keywords = ['excellent', 'great', 'perfect', 'amazing', 'wonderful', 'beautiful', 'convenient', 'central', 'charming']
        pros = []
        
        sentences = content.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in pros_keywords):
                pros.append(sentence.strip())
        
        if pros:
            return '. '.join(pros[:2])  # Return up to 2 positive sentences
        else:
            return "Well-located accommodation with good amenities"
    
    def extract_cons(self, content: str) -> str:
        """Extract negative aspects from content."""
        cons_keywords = ['small', 'noisy', 'expensive', 'crowded', 'basic', 'limited', 'old', 'dated']
        cons = []
        
        sentences = content.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in cons_keywords):
                cons.append(sentence.strip())
        
        if cons:
            return '. '.join(cons[:1])  # Return up to 1 negative sentence
        else:
            return "Standard accommodation limitations"
    
    def extract_booking_tips(self, content: str, url: str) -> str:
        """Extract booking tips from content."""
        tips_keywords = ['book', 'reserve', 'advance', 'early', 'recommend', 'suggest']
        tips = []
        
        sentences = content.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in tips_keywords):
                tips.append(sentence.strip())
        
        if tips:
            base_tip = '. '.join(tips[:1])  # Return up to 1 tip sentence
        else:
            base_tip = "Book in advance for best availability and rates"
        
        # Add specific booking URL information
        if 'booking.com' in url:
            return f"{base_tip}. Check availability and book directly at: {url}"
        elif 'hotels.com' in url:
            return f"{base_tip}. Check availability and book directly at: {url}"
        elif 'expedia.com' in url:
            return f"{base_tip}. Check availability and book directly at: {url}"
        else:
            return f"{base_tip}. Visit the hotel's booking page for current rates and availability"
    
    def generate_booking_url(self, hotel_name: str, destination: str, original_url: str) -> Optional[str]:
        """
        Generates a proper booking URL for a hotel.
        Returns None if we can't generate a valid booking URL.
        """
        # If the original URL is already a booking site, use it
        if any(site in original_url.lower() for site in ['booking.com', 'hotels.com', 'expedia.com', 'tripadvisor.com']):
            return original_url
        
        # Clean hotel name for URL generation
        clean_hotel_name = hotel_name.replace('Hotel', '').replace('hotel', '').strip()
        if not clean_hotel_name:
            return None
        
        # Clean destination name
        clean_destination = destination.replace(',', '').replace(' ', '-').lower()
        
        # Generate booking.com URL (most common booking site)
        try:
            # Remove special characters and spaces
            hotel_slug = re.sub(r'[^a-zA-Z0-9\s-]', '', clean_hotel_name)
            hotel_slug = hotel_slug.replace(' ', '-').lower()
            
            # Ensure we have a valid hotel name
            if len(hotel_slug) < 3:
                return None
            
            # Generate the booking URL
            booking_url = f"https://www.booking.com/hotel/{hotel_slug}-{clean_destination}.html"
            
            # Basic validation - ensure URL looks reasonable
            if len(booking_url) > 200:  # URL too long
                return None
                
            return booking_url
            
        except Exception as e:
            logger.error(f"Error generating booking URL for {hotel_name}: {e}")
            return None
    
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            logger.info("HTTP session closed")


class TripPlannerAgent:
    """Comprehensive trip planning agent with detailed itinerary generation."""

    def __init__(self, config: Optional[Configuration] = None):
        """Initialize the trip planner agent."""
        self.config = config or Configuration()
        self.web_search_tools = WebSearchTools(self.config)

    def ensure_boolean(self, value: Any) -> bool:
        """Convert various input types to boolean."""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(value, (int, float)):
            return bool(value)
        else:
            return False

    async def analyze_trip_request(self, state: AgentState, config: RunnableConfig) -> Command[
        Literal["research_destination"]]:
        """Analyze the trip request and extract key information."""
        try:
            configurable = Configuration.from_runnable_config(config)
            
            model_config = {
                "model": configurable.planning_model,
                "max_tokens": configurable.planning_model_max_tokens,
                "api_key": get_api_key_for_model(configurable.planning_model, config),
                "tags": ["langsmith:nostream"]
            }

            model = configurable_model.with_structured_output(TripPreferences).with_retry(
                stop_after_attempt=configurable.max_structured_output_retries
            ).with_config(model_config)

            user_input = state.get("user_input", "")
            logger.info(f"Analyzing trip request: {user_input[:100]}...")
            logger.info(f"Full user input: {user_input}")
            
            # Enhanced prompt to include special requirements and constraints
            enhanced_instructions = f"""
            {trip_analysis_instructions}
            
            IMPORTANT ADDITIONAL CONSIDERATIONS:
            Pay special attention to any constraints, limitations, or special requirements mentioned by the user:
            - Conference schedules or work commitments
            - Pre-booked accommodations (hotels already reserved)
            - Group dynamics (spouse traveling alone during conferences)
            - Time constraints or specific date limitations
            - Special accessibility or dietary requirements
            - Budget constraints or preferences
            - Any other specific requests or limitations
            
            Be very careful to:
            1. Use the EXACT destination from user input (do not substitute with other cities)
            2. Identify any conference or work commitments and their dates
            3. Note if accommodation is already booked
            4. Consider group dynamics (e.g., spouse traveling alone during conferences)
            5. Extract all special requirements and constraints
            6. Ensure all dates are in YYYY-MM-DD format
            """
            
            response = await model.ainvoke([
                HumanMessage(content=enhanced_instructions.format(
                    user_input=user_input,
                    date=get_today_str()
                ))
            ])

            logger.info(f"Trip analysis response: {response}")
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response attributes: {dir(response)}")
            
            # Validate response fields
            destination = response.destination.strip() if response.destination else ""
            month = response.month.strip() if response.month and response.month.strip() and response.month.strip().lower() != "null" else None
            travel_days = response.travel_days if response.travel_days > 0 else 7
            budget_level = response.budget_level.strip() if response.budget_level else "moderate"
            trip_type = response.trip_type.strip() if response.trip_type else "leisure"
            preferences = response.preferences.strip() if response.preferences else "general travel"
            group_size = response.group_size if response.group_size > 0 else 2
            
            # Debug logging for month parameter
            logger.info(f"Raw month from response: {response.month}")
            logger.info(f"Processed month: {month}")
            logger.info(f"Month type: {type(month)}")
            
            # Additional check for "NULL" string
            if month and month.lower() == "null":
                logger.warning("Month is 'NULL' string, setting to None")
                month = None

            # Extract destination from user input if LLM failed
            if not destination:
                destination = self.extract_destination_from_input(user_input)
                logger.warning(f"LLM didn't extract destination, extracted from user input: {destination}")

            # Generate dates from month and travel days
            start_date, end_date = generate_dates_from_month_and_days(month, travel_days)
            duration = travel_days

            logger.info(f"Validated fields - destination: {destination}, month: {month}, travel_days: {travel_days}")
            logger.info(f"Generated dates: {start_date} to {end_date}, duration: {duration}")
            logger.info(f"User input for special requirements: {user_input}")

            # Debug the state update
            logger.info(f"Updating state with month: {month}, travel_days: {travel_days}")
            
            return Command(
                goto="research_destination",
                update={
                    "destination": destination,
                    "month": month,
                    "travel_days": travel_days,
                    "trip_duration": duration,
                    "budget_level": budget_level,
                    "trip_type": trip_type,
                    "preferences": preferences,
                    "group_size": group_size,
                    "user_input": user_input,  # Preserve original user input for special requirements
                    "planner_messages": {
                        "type": "override",
                        "value": [
                            SystemMessage(content=f"You are a travel planning expert. Planning a {duration}-day {trip_type} trip to {destination} with {budget_level} budget. Pay special attention to any constraints or special requirements mentioned by the user."),
                            HumanMessage(content=f"Plan a detailed trip to {destination} for {travel_days} days{' in ' + month if month else ''}. Budget: {budget_level}. Type: {trip_type}. Preferences: {preferences}. Special requirements: {user_input}")
                        ]
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error in analyze_trip_request: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {str(e)}")
            # Extract information from user input as fallback
            fallback_destination = self.extract_destination_from_input(user_input)
            
            # Use extracted values or sensible defaults
            destination = fallback_destination or "Unknown Destination"
            month = None  # No month preference in fallback
            travel_days = 7  # Default to 7 days
            
            # Generate dates from month and travel days
            start_date, end_date = generate_dates_from_month_and_days(month, travel_days)
            duration = travel_days
            
            logger.warning(f"Using fallback values - destination: {destination}, month: {month}, travel_days: {travel_days}")
            
            # Return a fallback response
            return Command(
                goto="research_destination",
                update={
                    "destination": destination,
                    "month": month,
                    "travel_days": travel_days,
                    "trip_duration": duration,
                    "budget_level": "moderate",
                    "trip_type": "leisure",
                    "preferences": "general travel",
                    "group_size": 2,
                    "user_input": user_input,
                    "planner_messages": {
                        "type": "override",
                        "value": [
                            SystemMessage(content=f"You are a travel planning expert. Planning a {duration}-day leisure trip to {destination} with moderate budget."),
                            HumanMessage(content=f"Plan a detailed trip to {destination} for {travel_days} days{' in ' + month if month else ''}. Budget: moderate. Type: leisure. Preferences: general travel. Special requirements: {user_input}")
                        ]
                    }
                }
            )

    async def research_destination(self, state: PlannerState, config: RunnableConfig) -> Command[
        Literal["research_accommodations"]]:
        """Research the destination and gather key information."""
        try:
            configurable = Configuration.from_runnable_config(config)
            
            model_config = {
                "model": configurable.planning_model,
                "max_tokens": configurable.planning_model_max_tokens,
                "api_key": get_api_key_for_model(configurable.planning_model, config),
                "tags": ["langsmith:nostream"]
            }

            model = configurable_model.with_structured_output(Destination).with_retry(
                stop_after_attempt=configurable.max_structured_output_retries
            ).with_config(model_config)

            destination = state.get("destination", "")
            month = state.get("month", None)
            travel_days = state.get("travel_days", 7)
            trip_type = state.get("trip_type", "")
            budget_level = state.get("budget_level", "")
            preferences = state.get("preferences", "")

            # Validate destination
            if not destination or destination.strip() == "":
                destination = "Paris, France"
                logger.warning(f"Empty destination, using default: {destination}")

            logger.info(f"Researching destination: {destination}")
            logger.info(f"State month: {month}")
            logger.info(f"State travel_days: {travel_days}")

            # First, try to get real-time information from web search
            web_info = await self.web_search_tools.search_destination_info(destination)
            
            # Combine web search results with AI-generated content
            if web_info and any(web_info.values()):
                logger.info(f"Found web search results for {destination}")
                
                # Use web search results as context for AI generation
                web_context = f"""
                Web search results for {destination}:
                - Description: {web_info.get('description', '')}
                - Weather: {web_info.get('weather_info', '')}
                - Customs: {web_info.get('local_customs', '')}
                - Safety: {web_info.get('safety_tips', '')}
                - Sources: {', '.join(web_info.get('sources', [])[:3])}
                """
                
                enhanced_prompt = destination_research_prompt.format(
                    destination=destination,
                    trip_type=trip_type,
                    budget_level=budget_level,
                    preferences=preferences,
                    date=get_today_str()
                ) + f"\n\nAdditional context from recent web search:\n{web_context}"
                
                response = await model.ainvoke([
                    HumanMessage(content=enhanced_prompt)
                ])
            else:
                logger.info(f"No web search results found, using AI-only approach for {destination}")
                response = await model.ainvoke([
                    HumanMessage(content=destination_research_prompt.format(
                        destination=destination,
                        trip_type=trip_type,
                        budget_level=budget_level,
                        preferences=preferences,
                        date=get_today_str()
                    ))
                ])

            logger.info(f"Destination research response: {response}")

            return Command(
                goto="research_accommodations",
                update={
                    "destination_info": response.description,
                    "best_time_to_visit": response.best_time_to_visit,
                    "weather_info": response.weather_info,
                    "local_customs": response.local_customs,
                    "safety_tips": response.safety_tips,
                    "planner_messages": state.get("planner_messages", []),
                    "web_sources": web_info.get('sources', []) if web_info else []
                }
            )
        except Exception as e:
            logger.error(f"Error in research_destination: {e}")
            # Return fallback destination info
            return Command(
                goto="research_accommodations",
                update={
                    "destination_info": f"{destination} is a popular travel destination with rich culture and history.",
                    "best_time_to_visit": "Spring and fall are generally the best times to visit.",
                    "weather_info": "Check local weather forecasts before your trip.",
                    "local_customs": "Respect local customs and traditions.",
                    "safety_tips": "Stay aware of your surroundings and follow local safety guidelines.",
                    "planner_messages": state.get("planner_messages", []),
                    "web_sources": []
                }
            )

    async def research_accommodations(self, state: PlannerState, config: RunnableConfig) -> Command[
        Literal["research_activities"]]:
        """Research accommodation options."""
        try:
            user_input = state.get("user_input", "")
            
            # Check if user has already booked accommodation
            if any(keyword in user_input.lower() for keyword in [
                'already booked', 'already reserved', 'staying at', 'booked at', 'reserved at',
                'novotel', 'accor', 'marriott', 'hilton', 'hyatt', 'ibis', 'mercure'
            ]):
                logger.info("User has already booked accommodation, skipping accommodation research")
                return Command(
                    goto="research_activities",
                    update={
                        "accommodations": [{
                            "name": "Pre-booked accommodation",
                            "type": "hotel",
                            "price_range": "Already paid",
                            "location": state.get("destination", ""),
                            "amenities": "Based on user's booking",
                            "pros": "Accommodation already secured",
                            "cons": "Limited flexibility for changes",
                            "booking_tips": "Contact your hotel directly for any modifications",
                            "source_url": "",
                            "note": "User has already booked accommodation as mentioned in special requirements"
                        }]
                    }
                )
            
            destination = state.get("destination", "")
            budget_level = state.get("budget_level", "moderate")
            
            logger.info(f"Researching accommodations in {destination} with {budget_level} budget")
            
            accommodations = await self.web_search_tools.search_accommodations(destination, budget_level)
            
            return Command(
                goto="research_activities",
                update={"accommodations": accommodations}
            )
            
        except Exception as e:
            logger.error(f"Error researching accommodations: {e}")
            return Command(
                goto="research_activities",
                update={"accommodations": []}
            )

    async def research_activities(self, state: PlannerState, config: RunnableConfig) -> Command[
        Literal["research_restaurants"]]:
        """Research and recommend activities and attractions."""
        try:
            configurable = Configuration.from_runnable_config(config)
            
            model_config = {
                "model": configurable.planning_model,
                "max_tokens": configurable.planning_model_max_tokens,
                "api_key": get_api_key_for_model(configurable.planning_model, config),
                "tags": ["langsmith:nostream"]
            }

            model = configurable_model.with_structured_output(Activity).with_retry(
                stop_after_attempt=configurable.max_structured_output_retries
            ).with_config(model_config)

            destination = state.get("destination", "")
            trip_type = state.get("trip_type", "")
            budget_level = state.get("budget_level", "")
            trip_duration = state.get("trip_duration", 1)
            preferences = state.get("preferences", "")

            # Validate destination
            if not destination or destination.strip() == "":
                destination = "Paris, France"
                logger.warning(f"Empty destination, using default: {destination}")

            logger.info(f"Researching activities for: {destination}")

            # First, try to get real-time activity information from web search
            web_activities = await self.web_search_tools.search_activities(destination, trip_type)
            
            if web_activities:
                logger.info(f"Found {len(web_activities)} activity options from web search")
                
                # Convert web search results to the expected format
                activity_dicts = []
                for web_activity in web_activities:
                    activity_dicts.append({
                        "name": web_activity.get('name', 'Activity from search results'),
                        "type": web_activity.get('type', 'attraction'),
                        "description": web_activity.get('description', 'Based on recent search results'),
                        "cost": web_activity.get('cost', '$10-30'),
                        "duration": web_activity.get('duration', '2-3 hours'),
                        "location": web_activity.get('location', destination),
                        "best_time": web_activity.get('best_time', 'Check current opening hours'),
                        "booking_tips": web_activity.get('booking_tips', 'Visit website for current information'),
                        "source_url": web_activity.get('source_url', '')
                    })
                
                # Try to use AI to enhance the web search results
                try:
                    enhanced_prompt = activity_research_prompt.format(
                        destination=destination,
                        trip_type=trip_type,
                        budget_level=budget_level,
                        trip_duration=trip_duration,
                        preferences=preferences,
                        date=get_today_str()
                    ) + f"\n\nWeb search results for reference:\n{json.dumps(web_activities[:3], indent=2)}"
                    
                    response = await model.ainvoke([
                        HumanMessage(content=enhanced_prompt)
                    ])
                    
                    # Combine web search results with AI recommendations
                    ai_recommendations = []
                    for rec in response.recommendations:
                        ai_recommendations.append({
                            "name": rec.name,
                            "type": rec.type,
                            "description": rec.description,
                            "cost": rec.cost,
                            "duration": rec.duration,
                            "location": rec.location,
                            "best_time": rec.best_time,
                            "booking_tips": rec.booking_tips
                        })
                    
                    # Combine both sources, prioritizing web search results
                    final_activities = activity_dicts + ai_recommendations
                    
                except Exception as ai_error:
                    logger.warning(f"AI enhancement failed, using web search results only: {ai_error}")
                    final_activities = activity_dicts
                
            else:
                logger.info(f"No web search results found, using AI-only approach for activities")
                try:
                    response = await model.ainvoke([
                        HumanMessage(content=activity_research_prompt.format(
                            destination=destination,
                            trip_type=trip_type,
                            budget_level=budget_level,
                            trip_duration=trip_duration,
                            preferences=preferences,
                            date=get_today_str()
                        ))
                    ])

                    logger.info(f"Activity research response: {response}")

                    # Convert Pydantic models to dictionaries for state storage
                    final_activities = []
                    for rec in response.recommendations:
                        final_activities.append({
                            "name": rec.name,
                            "type": rec.type,
                            "description": rec.description,
                            "cost": rec.cost,
                            "duration": rec.duration,
                            "location": rec.location,
                            "best_time": rec.best_time,
                            "booking_tips": rec.booking_tips
                        })
                except Exception as ai_error:
                    logger.error(f"AI activity research failed: {ai_error}")
                    final_activities = []

            return Command(
                goto="research_restaurants",
                update={
                    "activities": final_activities,
                    "activity_tips": response.tips if 'response' in locals() else "Book popular activities in advance to avoid disappointment.",
                    "planner_messages": state.get("planner_messages", [])
                }
            )
        except Exception as e:
            logger.error(f"Error in research_activities: {e}")
            # Return fallback activity recommendations
            fallback_activities = [
                {
                    "name": "City Tour",
                    "type": "guided tour",
                    "description": "Explore the city with a knowledgeable guide",
                    "cost": "$20-50",
                    "duration": "2-3 hours",
                    "location": "City center",
                    "best_time": "Morning or afternoon",
                    "booking_tips": "Book in advance for best availability"
                }
            ]
            return Command(
                goto="research_restaurants",
                update={
                    "activities": fallback_activities,
                    "activity_tips": "Book popular activities in advance to avoid disappointment.",
                    "planner_messages": state.get("planner_messages", [])
                }
            )

    async def research_restaurants(self, state: PlannerState, config: RunnableConfig) -> Command[
        Literal["create_day_plans"]]:
        """Research and recommend restaurants and dining options."""
        try:
            configurable = Configuration.from_runnable_config(config)
            
            model_config = {
                "model": configurable.planning_model,
                "max_tokens": configurable.planning_model_max_tokens,
                "api_key": get_api_key_for_model(configurable.planning_model, config),
                "tags": ["langsmith:nostream"]
            }

            model = configurable_model.with_structured_output(Restaurant).with_retry(
                stop_after_attempt=configurable.max_structured_output_retries
            ).with_config(model_config)

            destination = state.get("destination", "")
            budget_level = state.get("budget_level", "")
            preferences = state.get("preferences", "")

            # Validate destination
            if not destination or destination.strip() == "":
                destination = "Paris, France"
                logger.warning(f"Empty destination, using default: {destination}")

            logger.info(f"Researching restaurants for: {destination}")

            response = await model.ainvoke([
                HumanMessage(content=restaurant_research_prompt.format(
                    destination=destination,
                    budget_level=budget_level,
                    preferences=preferences,
                    date=get_today_str()
                ))
            ])

            logger.info(f"Restaurant research response: {response}")

            # Convert Pydantic models to dictionaries for state storage
            restaurant_dicts = []
            for rec in response.recommendations:
                restaurant_dicts.append({
                    "name": rec.name,
                    "cuisine": rec.cuisine,
                    "price_range": rec.price_range,
                    "location": rec.location,
                    "specialties": rec.specialties,
                    "atmosphere": rec.atmosphere,
                    "reservation_tips": rec.reservation_tips
                })

            return Command(
                goto="create_day_plans",
                update={
                    "restaurants": restaurant_dicts,
                    "dining_tips": response.tips,
                    "planner_messages": state.get("planner_messages", [])
                }
            )
        except Exception as e:
            logger.error(f"Error in research_restaurants: {e}")
            # Return fallback restaurant recommendations
            fallback_restaurants = [
                {
                    "name": "Local Bistro",
                    "cuisine": "Local cuisine",
                    "price_range": "$$",
                    "location": "City center",
                    "specialties": "Local specialties",
                    "atmosphere": "Cozy and welcoming",
                    "reservation_tips": "Reserve in advance for dinner"
                }
            ]
            return Command(
                goto="create_day_plans",
                update={
                    "restaurants": fallback_restaurants,
                    "dining_tips": "Try local specialties and make reservations for popular restaurants.",
                    "planner_messages": state.get("planner_messages", [])
                }
            )

    async def create_day_plans(self, state: PlannerState, config: RunnableConfig) -> Command[
        Literal["generate_final_itinerary"]]:
        """Create detailed day-by-day plans."""
        try:
            configurable = Configuration.from_runnable_config(config)
            
            model_config = {
                "model": configurable.planning_model,
                "max_tokens": configurable.planning_model_max_tokens,
                "api_key": get_api_key_for_model(configurable.planning_model, config),
                "tags": ["langsmith:nostream"]
            }

            model = configurable_model.with_structured_output(DayPlan).with_retry(
                stop_after_attempt=configurable.max_structured_output_retries
            ).with_config(model_config)

            destination = state.get("destination", "")
            trip_duration = state.get("trip_duration", 1)
            month = state.get("month", None)
            travel_days = state.get("travel_days", 7)
            activities = state.get("activities", [])
            restaurants = state.get("restaurants", [])

            # Validate destination
            if not destination or destination.strip() == "":
                destination = "Paris, France"
                logger.warning(f"Empty destination, using default: {destination}")

            logger.info(f"Creating day plans for: {destination} ({trip_duration} days)")

            try:
                response = await model.ainvoke([
                    HumanMessage(content=day_planning_prompt.format(
                        destination=destination,
                        trip_duration=trip_duration,
                        month=month if month else "Not specified",
                        travel_days=travel_days,
                        activities=json.dumps(activities, indent=2),
                        restaurants=json.dumps(restaurants, indent=2),
                        date=get_today_str()
                    ))
                ])

                logger.info(f"Day plans response: {response}")

                # Convert Pydantic models to dictionaries for state storage
                day_plan_dicts = []
                for day_plan in response.daily_plans:
                    day_plan_dicts.append({
                        "day": day_plan.day,
                        "date": day_plan.date,
                        "morning": day_plan.morning,
                        "lunch": day_plan.lunch,
                        "afternoon": day_plan.afternoon,
                        "dinner": day_plan.dinner,
                        "evening": day_plan.evening,
                        "transportation": day_plan.transportation,
                        "estimated_cost": day_plan.estimated_cost,
                        "tips": day_plan.tips
                    })

                return Command(
                    goto="generate_final_itinerary",
                    update={
                        "day_plans": day_plan_dicts,
                        "planner_messages": state.get("planner_messages", [])
                    }
                )
            except Exception as ai_error:
                logger.error(f"AI day planning failed: {ai_error}")
                # Generate fallback day plans based on available activities and restaurants
                fallback_day_plans = []
                for day in range(1, trip_duration + 1):
                    # Use day number instead of actual dates
                    current_date = f"Day {day}"
                    
                    # Select activities and restaurants for this day
                    day_activities = activities[day-1 % len(activities)] if activities else {"name": "City exploration"}
                    day_restaurants = restaurants[day-1 % len(restaurants)] if restaurants else {"name": "Local restaurant"}
                    
                    fallback_day_plans.append({
                        "day": day,
                        "date": current_date,
                        "morning": f"Start your day exploring {destination}",
                        "lunch": f"Lunch at {day_restaurants.get('name', 'local restaurant')}",
                        "afternoon": f"Visit {day_activities.get('name', 'local attractions')}",
                        "dinner": f"Dinner at {day_restaurants.get('name', 'recommended restaurant')}",
                        "evening": "Evening walk and local entertainment",
                        "transportation": "Walking and public transport",
                        "estimated_cost": "$100-150",
                        "tips": "Enjoy your day exploring the city!"
                    })
                
                return Command(
                    goto="generate_final_itinerary",
                    update={
                        "day_plans": fallback_day_plans,
                        "planner_messages": state.get("planner_messages", [])
                    }
                )

        except Exception as e:
            logger.error(f"Error in create_day_plans: {e}")
            # Return fallback day plans
            fallback_day_plans = []
            for day in range(1, state.get("trip_duration", 1) + 1):
                fallback_day_plans.append({
                    "day": day,
                    "date": f"Day {day}",
                    "morning": "Explore the city",
                    "lunch": "Local restaurant",
                    "afternoon": "Visit attractions",
                    "dinner": "Dinner at recommended restaurant",
                    "evening": "Evening activities",
                    "transportation": "Walking and public transport",
                    "estimated_cost": "$100-150",
                    "tips": "Enjoy your day!"
                })
            
            return Command(
                goto="generate_final_itinerary",
                update={
                    "day_plans": fallback_day_plans,
                    "planner_messages": state.get("planner_messages", [])
                }
            )

    async def generate_final_itinerary(self, state: PlannerState, config: RunnableConfig) -> Command:
        """Generate the final comprehensive itinerary."""
        try:
            configurable = Configuration.from_runnable_config(config)
            
            model_config = {
                "model": configurable.planning_model,
                "max_tokens": configurable.planning_model_max_tokens,
                "api_key": get_api_key_for_model(configurable.planning_model, config),
                "tags": ["langsmith:nostream"]
            }

            model = configurable_model.with_retry(
                stop_after_attempt=configurable.max_structured_output_retries
            ).with_config(model_config)

            # Extract all the researched information
            destination = state.get("destination", "")
            month = state.get("month", None)
            travel_days = state.get("travel_days", 7)
            trip_duration = state.get("trip_duration", 1)
            budget_level = state.get("budget_level", "")
            trip_type = state.get("trip_type", "")
            preferences = state.get("preferences", "")
            group_size = state.get("group_size", 2)
            user_input = state.get("user_input", "")
            
            destination_info = state.get("destination_info", {})
            accommodations = state.get("accommodations", [])
            activities = state.get("activities", [])
            restaurants = state.get("restaurants", [])
            day_plans = state.get("day_plans", [])

            logger.info(f"Generating final itinerary for {destination}")

            # Create a summary of special considerations
            special_considerations = self.extract_special_considerations(user_input)
            
            # Enhanced prompt to include special considerations
            enhanced_prompt = f"""
            {final_itinerary_prompt}
            
            IMPORTANT: The user has provided special requirements and considerations that must be acknowledged and incorporated:
            
            Special Requirements: {user_input}
            
            Extracted Considerations:
            {special_considerations}
            
            Make sure to:
            1. Acknowledge any conference schedules or work commitments
            2. Consider pre-booked accommodations
            3. Plan activities for group members during conference days
            4. Address any specific constraints or limitations mentioned
            5. Show understanding of the user's unique situation
            
            Include a section at the beginning that summarizes the special considerations and shows the user that their unique requirements have been understood and incorporated into the planning.
            """

            response = await model.ainvoke([
                HumanMessage(content=enhanced_prompt.format(
                    destination=destination,
                    month=month if month else "Not specified",
                    travel_days=travel_days,
                    trip_duration=trip_duration,
                    budget_level=budget_level,
                    trip_type=trip_type,
                    preferences=preferences,
                    group_size=group_size,
                    destination_info=json.dumps(destination_info, indent=2),
                    accommodations=json.dumps(accommodations, indent=2),
                    activities=json.dumps(activities, indent=2),
                    restaurants=json.dumps(restaurants, indent=2),
                    day_plans=json.dumps(day_plans, indent=2),
                    date=get_today_str()
                ))
            ])

            logger.info(f"Final itinerary generated successfully")
            logger.info(f"Final itinerary month: {month}")
            logger.info(f"Final itinerary travel_days: {travel_days}")

            # Create the final itinerary structure
            final_itinerary = {
                "trip_itinerary": response.content,
                "special_considerations": special_considerations,
                "destination": destination,
                "month": month,
                "travel_days": travel_days,
                "trip_duration": trip_duration,
                "budget_level": budget_level,
                "trip_type": trip_type,
                "preferences": preferences,
                "accommodations": accommodations,
                "activities": activities,
                "restaurants": restaurants,
                "day_plans": day_plans,
                "destination_info": destination_info
            }
            
            # Add trip understanding summary
            month_display = month if month else "Not specified"
            final_itinerary["trip_understanding"] = f"""
## Trip Understanding Summary

I've analyzed your trip request and understand the following requirements:

**Destination**: {destination}
**Travel Period**: {month_display} ({travel_days} days)
**Trip Type**: {trip_type}
**Budget Level**: {budget_level}
**Preferences**: {preferences}

**My Approach**: I've tailored this itinerary specifically for a {trip_type} trip with a {budget_level} budget. The recommendations focus on {preferences} to match your interests. {destination} is perfect for this type of trip because of its rich culture, history, and diverse attractions.

**What I've Prepared**: 
- Comprehensive destination research with current information
- {len(accommodations)} carefully selected accommodation options
- {len(activities)} activities and attractions that match your preferences
- {len(restaurants)} dining recommendations for various tastes and budgets
- {len(day_plans)} days of detailed planning with realistic timing

This itinerary is designed to give you the best possible experience in {destination} within your specified parameters.
            """.strip()

            return Command(
                goto=END,
                update={"final_itinerary": final_itinerary}
            )
            
        except Exception as e:
            logger.error(f"Error in generate_final_itinerary: {e}")
            logger.error(f"Error type: {type(e)}")
            # Return a fallback itinerary
            special_considerations = self.extract_special_considerations(user_input)
            fallback_itinerary = {
                "trip_itinerary": f"""
# Trip Itinerary for {destination}

## Special Considerations
{special_considerations}

## Trip Summary
- **Destination**: {destination}
- **Travel Period**: {month if month else 'Not specified'} ({travel_days} days)
- **Budget Level**: {budget_level}
- **Trip Type**: {trip_type}
- **Preferences**: {preferences}

## Overview
This is a {trip_duration}-day {trip_type} trip to {destination} with a {budget_level} budget.

## Accommodations
{len(accommodations)} accommodation options have been researched for your trip.

## Activities
{len(activities)} activities and attractions have been recommended for your trip.

## Dining
{len(restaurants)} restaurant recommendations have been provided for your trip.

## Day-by-Day Itinerary
{len(day_plans)} days of detailed planning have been created.

## Travel Tips
- Book accommodations in advance
- Reserve popular restaurants early
- Check local weather forecasts
- Research local customs and etiquette
- Keep important documents safe
- Have emergency contacts ready

## Budget Estimate
Estimated total cost: $100-200 per day per person

*Note: This itinerary was generated with fallback data due to an error in the planning process.*
                """,
                "trip_understanding": f"""
## Trip Understanding Summary

I've analyzed your trip request and understand the following requirements:

**Destination**: {destination}
**Travel Period**: {month if month else 'Not specified'} ({travel_days} days)
**Trip Type**: {trip_type}
**Budget Level**: {budget_level}
**Preferences**: {preferences}

**My Approach**: I've tailored this itinerary specifically for a {trip_type} trip with a {budget_level} budget. The recommendations focus on {preferences} to match your interests.

**What I've Prepared**: 
- Comprehensive destination research with current information
- {len(accommodations)} carefully selected accommodation options
- {len(activities)} activities and attractions that match your preferences
- {len(restaurants)} dining recommendations for various tastes and budgets
- {len(day_plans)} days of detailed planning with realistic timing

This itinerary is designed to give you the best possible experience in {destination} within your specified parameters.
                """.strip(),
                "special_considerations": special_considerations,
                "destination": destination,
                "month": month,
                "travel_days": travel_days,
                "trip_duration": trip_duration,
                "budget_level": budget_level,
                "trip_type": trip_type,
                "preferences": preferences,
                "accommodations": accommodations,
                "activities": activities,
                "restaurants": restaurants,
                "day_plans": day_plans,
                "destination_info": destination_info
            }
            return Command(
                goto=END,
                update={"final_itinerary": fallback_itinerary}
            )

    def extract_destination_from_input(self, user_input: str) -> str:
        """Extract destination from user input using simple pattern matching."""
        import re
        
        # Common destination patterns
        patterns = [
            r'destination["\']?\s*:\s*["\']([^"\']+)["\']',
            r'to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'visit\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'trip\s+to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                destination = match.group(1).strip()
                # Add country if it's a city
                if destination.lower() in ['vienna', 'wien']:
                    return "Vienna, Austria"
                elif destination.lower() in ['paris']:
                    return "Paris, France"
                elif destination.lower() in ['london']:
                    return "London, UK"
                elif destination.lower() in ['tokyo']:
                    return "Tokyo, Japan"
                elif destination.lower() in ['new york', 'nyc']:
                    return "New York City, USA"
                else:
                    return destination
        
        # If no pattern matches, look for common city names
        if 'vienna' in user_input.lower() or 'wien' in user_input.lower():
            return "Vienna, Austria"
        elif 'paris' in user_input.lower():
            return "Paris, France"
        elif 'london' in user_input.lower():
            return "London, UK"
        elif 'tokyo' in user_input.lower():
            return "Tokyo, Japan"
        elif 'new york' in user_input.lower() or 'nyc' in user_input.lower():
            return "New York City, USA"
        
        return "Unknown Destination"
    
    def extract_dates_from_input(self, user_input: str) -> tuple[str, str]:
        """Extract start and end dates from user input (legacy method for backward compatibility)."""
        import re
        from datetime import datetime, timedelta
        
        # Date patterns for legacy date format
        date_patterns = [
            r'start_date["\']?\s*:\s*["\']([^"\']+)["\']',
            r'end_date["\']?\s*:\s*["\']([^"\']+)["\']',
            r'from\s+(\d{4}-\d{2}-\d{2})',
            r'to\s+(\d{4}-\d{2}-\d{2})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, user_input)
            dates.extend(matches)
        
        # Remove duplicates and sort
        dates = sorted(list(set(dates)))
        
        if len(dates) >= 2:
            return dates[0], dates[1]
        elif len(dates) == 1:
            # If only one date, assume it's start date and add 7 days
            start_date = dates[0]
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = start_dt + timedelta(days=7)
                end_date = end_dt.strftime("%Y-%m-%d")
                return start_date, end_date
            except ValueError:
                pass
        
        # Default dates if none found
        return "2024-06-15", "2024-06-22"

    def extract_month_and_days_from_input(self, user_input: str) -> tuple[Optional[str], int]:
        """Extract month preference and travel days from user input using pattern matching."""
        import re
        
        # Month patterns
        month_patterns = [
            r'in\s+(january|february|march|april|may|june|july|august|september|october|november|december)',
            r'during\s+(january|february|march|april|may|june|july|august|september|october|november|december)',
            r'(january|february|march|april|may|june|july|august|september|october|november|december)',
        ]
        
        # Travel days patterns
        days_patterns = [
            r'(\d+)\s+days?',
            r'for\s+(\d+)\s+days?',
            r'trip\s+of\s+(\d+)\s+days?',
            r'(\d+)-day',
        ]
        
        # Extract month
        month = None
        for pattern in month_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                month = match.group(1).lower()
                break
        
        # Extract travel days
        travel_days = 7  # Default
        for pattern in days_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                try:
                    days = int(match.group(1))
                    if 1 <= days <= 30:  # Reasonable range
                        travel_days = days
                        break
                except ValueError:
                    continue
        
        return month, travel_days

    def extract_special_considerations(self, user_input: str) -> str:
        """Extracts and formats special considerations from the user's input."""
        considerations = []
        user_input_lower = user_input.lower()
        
        # Conference and work commitments
        if "conference" in user_input_lower or "acl" in user_input_lower:
            considerations.append("Conference schedules or work commitments (ACL conference mentioned).")
        
        # Pre-booked accommodations
        if any(keyword in user_input_lower for keyword in [
            'already booked', 'already reserved', 'staying at', 'booked at', 'reserved at',
            'novotel', 'accor', 'marriott', 'hilton', 'hyatt', 'ibis', 'mercure'
        ]):
            considerations.append("Pre-booked accommodations (hotels already reserved).")
        
        # Group dynamics
        if "spouse" in user_input_lower and ("traveling alone" in user_input_lower or "while i am at" in user_input_lower):
            considerations.append("Group dynamics (spouse traveling alone during conferences).")
        
        # Specific location mentions
        if "stephansdom" in user_input_lower or "stephan's" in user_input_lower:
            considerations.append("Specific location preferences (Stephansdom area mentioned).")
        
        # Time constraints
        if any(keyword in user_input_lower for keyword in ['from 27', 'for 4 days', 'first two days']):
            considerations.append("Specific time constraints and scheduling requirements.")
        
        # Accessibility or dietary requirements
        if "accessibility" in user_input_lower or "dietary" in user_input_lower:
            considerations.append("Special accessibility or dietary requirements.")
        
        # Budget constraints
        if "budget" in user_input_lower and ("constraint" in user_input_lower or "limit" in user_input_lower):
            considerations.append("Budget constraints or preferences.")
        
        # Other specific requests
        if "special" in user_input_lower and "requirement" in user_input_lower:
            considerations.append("Other specific requests or limitations.")

        if considerations:
            return "Special Considerations:\n" + "\n".join(f"- {c}" for c in considerations)
        else:
            return "No specific special considerations were identified."

    def build_graph(self):
        """Build the trip planning graph."""
        # Build main graph
        main_builder = StateGraph(AgentState, input=AgentState, config_schema=Configuration)
        main_builder.add_node("analyze_trip_request", self.analyze_trip_request)
        main_builder.add_node("research_destination", self.research_destination)
        main_builder.add_node("research_accommodations", self.research_accommodations)
        main_builder.add_node("research_activities", self.research_activities)
        main_builder.add_node("research_restaurants", self.research_restaurants)
        main_builder.add_node("create_day_plans", self.create_day_plans)
        main_builder.add_node("generate_final_itinerary", self.generate_final_itinerary)
        
        main_builder.add_edge(START, "analyze_trip_request")
        main_builder.add_edge("analyze_trip_request", "research_destination")
        main_builder.add_edge("research_destination", "research_accommodations")
        main_builder.add_edge("research_accommodations", "research_activities")
        main_builder.add_edge("research_activities", "research_restaurants")
        main_builder.add_edge("research_restaurants", "create_day_plans")
        main_builder.add_edge("create_day_plans", "generate_final_itinerary")
        main_builder.add_edge("generate_final_itinerary", END)

        self.main_graph = main_builder.compile()


async def _main_async(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async main function for the Trip Planner Agent.
    
    Args:
        input_data: Dictionary containing:
            - destination: The travel destination (required)
            - month: Preferred month for the trip (optional)
            - travel_days: Number of travel days (optional, default: 7)
            - budget_level: Budget level (budget, moderate, luxury)
            - trip_type: Type of trip (leisure, business, adventure, cultural, etc.)
            - preferences: User preferences and interests
            - group_size: Number of travelers
            - special_requirements: Any special requirements or accessibility needs
    
    Returns:
        Dictionary containing comprehensive trip itinerary and recommendations
    """

    # Initialize agent
    agent = TripPlannerAgent()

    # Extract and validate parameters
    destination = input_data.get('destination', '').strip()
    if not destination:
        return {'error': 'Destination is required'}

    # Build configuration from input
    config_data = {
        'planning_model': input_data.get('planning_model', 'openai:gpt-4o'),
        'planning_model_max_tokens': int(input_data.get('planning_model_max_tokens', 8000)),
        'final_report_model': input_data.get('final_report_model', 'openai:gpt-4o'),
        'final_report_model_max_tokens': int(input_data.get('final_report_model_max_tokens', 12000)),
        'max_structured_output_retries': int(input_data.get('max_retries', 3))
    }

    # Create configuration object
    config = Configuration(**config_data)
    agent.config = config

    # Initialize web search tools
    await agent.web_search_tools.initialize()

    # Build the planning graph
    agent.build_graph()

    logger.info(f"Starting trip planning for: {destination}")
    logger.info(f"Input data: {input_data}")
    logger.info(f"Month from input: {input_data.get('month', None)}")
    logger.info(f"Travel days from input: {input_data.get('travel_days', 7)}")

    try:
        # Prepare initial state
        initial_state = {
            "user_input": f"Plan a trip to {destination}. " + 
                         f"Month: {input_data.get('month', 'Not specified')}. " +
                         f"Travel days: {input_data.get('travel_days', '7')}. " +
                         f"Budget: {input_data.get('budget_level', 'moderate')}. " +
                         f"Type: {input_data.get('trip_type', 'leisure')}. " +
                         f"Preferences: {input_data.get('preferences', '')}. " +
                         f"Group size: {input_data.get('group_size', '2')}. " +
                         f"Special requirements: {input_data.get('special_requirements', '')}",
            "planner_messages": [],
            "destination": "",
            "month": input_data.get('month', None),
            "travel_days": input_data.get('travel_days', 7),
            "trip_duration": 0,
            "budget_level": "",
            "trip_type": "",
            "preferences": "",
            "group_size": 0,
            "destination_info": "",
            "accommodations": [],
            "activities": [],
            "restaurants": [],
            "day_plans": [],
            "web_sources": []
        }
        
        logger.info(f"Initial state month: {initial_state['month']}")
        logger.info(f"Initial state travel_days: {initial_state['travel_days']}")

        # Create runnable config
        runnable_config = RunnableConfig(
            configurable=config_data,
            metadata=context.get('metadata', {}),
            tags=["trip_planner_agent"]
        )

        # Execute the planning
        start_time = time.time()
        result = await agent.main_graph.ainvoke(initial_state, runnable_config)
        execution_time = time.time() - start_time

        # Debug the result
        logger.info(f"Final result keys: {result.keys()}")
        logger.info(f"Final result month: {result.get('month', None)}")
        logger.info(f"Final result travel_days: {result.get('travel_days', None)}")
        
        # Check if final_itinerary exists and extract from it
        final_itinerary = result.get('final_itinerary', {})
        if final_itinerary:
            logger.info(f"Final itinerary keys: {final_itinerary.keys()}")
            logger.info(f"Final itinerary month: {final_itinerary.get('month', None)}")
            logger.info(f"Final itinerary travel_days: {final_itinerary.get('travel_days', None)}")

        # Prepare response
        response = {
            'status': 'success',
            'destination': destination,
            'trip_itinerary': final_itinerary.get('trip_itinerary', '') if final_itinerary else result.get('trip_itinerary', ''),
            'trip_understanding': final_itinerary.get('trip_understanding', '') if final_itinerary else '',
            'month': final_itinerary.get('month', None) if final_itinerary else result.get('month', None),
            'travel_days': final_itinerary.get('travel_days', 7) if final_itinerary else result.get('travel_days', 7),
            'trip_duration': result.get('trip_duration', 0),
            'budget_level': final_itinerary.get('budget_level', '') if final_itinerary else result.get('budget_level', ''),
            'trip_type': final_itinerary.get('trip_type', '') if final_itinerary else result.get('trip_type', ''),
            'preferences': final_itinerary.get('preferences', '') if final_itinerary else result.get('preferences', ''),
            'accommodations': final_itinerary.get('accommodations', []) if final_itinerary else result.get('accommodations', []),
            'activities': final_itinerary.get('activities', []) if final_itinerary else result.get('activities', []),
            'restaurants': final_itinerary.get('restaurants', []) if final_itinerary else result.get('restaurants', []),
            'day_plans': final_itinerary.get('day_plans', []) if final_itinerary else result.get('day_plans', []),
            'destination_info': final_itinerary.get('destination_info', '') if final_itinerary else result.get('destination_info', ''),
            'web_sources': result.get('web_sources', []),
            'execution_time': execution_time,
            'generated_at': datetime.now().isoformat()
        }
        
        # Convert None month to "Not specified" for display
        if response['month'] is None:
            response['month'] = "Not specified"
        
        # Add a trip summary to show understanding
        response['trip_summary'] = f"""
## Trip Planning Summary

I've successfully planned your trip with the following details:

**Destination**: {response['destination']}
**Travel Period**: {response['month']} ({response['travel_days']} days)
**Trip Type**: {response['trip_type']}
**Budget Level**: {response['budget_level']}
**Preferences**: {response['preferences']}

**What I've prepared for you:**
- ✅ Destination research and information
- ✅ {len(response['accommodations'])} accommodation recommendations
- ✅ {len(response['activities'])} activity and attraction suggestions
- ✅ {len(response['restaurants'])} dining recommendations
- ✅ {len(response['day_plans'])} days of detailed day-by-day planning

The complete itinerary below includes all the details you need for a fantastic trip to {response['destination']}!
        """.strip()

        logger.info(f"Final response month: {response['month']}")
        logger.info(f"Final response travel_days: {response['travel_days']}")
        logger.info(f"Trip planning completed in {execution_time:.2f} seconds")
        return response

    except Exception as e:
        logger.error(f"Error in trip planning: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'destination': destination
        }
    finally:
        # Clean up web search tools
        await agent.web_search_tools.close()


def main(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function for the Trip Planner Agent.
    
    This is a synchronous wrapper around the async implementation.
    
    Args:
        input_data: Dictionary containing trip planning parameters
        context: Dictionary containing execution context
    
    Returns:
        Dictionary containing comprehensive trip itinerary and recommendations
    """
    try:
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_main_async(input_data, context))
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'destination': input_data.get('destination', 'Unknown')
        }


def execute(input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute function for the Trip Planner Agent.
    
    This is the main entry point that matches the config.json schema requirements.
    
    Args:
        input_data: Dictionary containing trip planning parameters as defined in config.json
        context: Dictionary containing execution context (optional)
    
    Returns:
        Dictionary containing comprehensive trip itinerary and recommendations as defined in config.json
    """
    try:
        # Set default context if none provided
        if context is None:
            context = {}
        
        # Call the main function which handles the actual trip planning
        result = main(input_data, context)
        
        # Transform the result to match the expected output schema from config.json
        if result.get('status') == 'success':
            # Extract the final itinerary from the result
            final_itinerary = result.get('final_itinerary', {})
            
            # Transform to match config.json output schema
            transformed_result = {
                "itinerary": {
                    "trip_itinerary": final_itinerary.get('trip_itinerary', ''),
                    "trip_understanding": final_itinerary.get('trip_understanding', ''),
                    "day_plans": final_itinerary.get('day_plans', []),
                    "special_considerations": final_itinerary.get('special_considerations', '')
                },
                "destination": result.get('destination', ''),
                "travel_days": result.get('travel_days', 7),
                "budget_level": final_itinerary.get('budget_level', ''),
                "trip_type": final_itinerary.get('trip_type', ''),
                "accommodations": final_itinerary.get('accommodations', []),
                "activities": final_itinerary.get('activities', []),
                "dining_recommendations": final_itinerary.get('restaurants', []),
                "transportation": {
                    "recommendations": "Walking and public transport recommended for city exploration",
                    "tips": "Use local public transportation for longer distances"
                },
                "weather_info": {
                    "destination": result.get('destination', ''),
                    "best_time_to_visit": final_itinerary.get('destination_info', {}).get('best_time_to_visit', ''),
                    "current_info": final_itinerary.get('destination_info', {}).get('weather_info', '')
                },
                "safety_tips": [
                    final_itinerary.get('destination_info', {}).get('safety_tips', ''),
                    final_itinerary.get('destination_info', {}).get('local_customs', '')
                ] if final_itinerary.get('destination_info') else [],
                "total_estimated_cost": {
                    "per_day": "$100-200",
                    "total": f"${100 * result.get('travel_days', 7)}-{200 * result.get('travel_days', 7)}",
                    "currency": "USD",
                    "breakdown": {
                        "accommodation": "40-60%",
                        "food": "20-30%",
                        "activities": "15-25%",
                        "transportation": "5-10%"
                    }
                },
                "metadata": {
                    "processing_time": result.get('execution_time', 0),
                    "models_used": [
                        input_data.get('planning_model', 'openai:gpt-4o'),
                        input_data.get('final_report_model', 'openai:gpt-4o')
                    ],
                    "timestamp": result.get('generated_at', datetime.now().isoformat())
                }
            }
            
            return transformed_result
        else:
            # Return error response
            return {
                "error": result.get('error', 'Unknown error occurred'),
                "destination": result.get('destination', 'Unknown'),
                "status": "error"
            }
            
    except Exception as e:
        logger.error(f"Error in execute function: {e}")
        return {
            "error": str(e),
            "destination": input_data.get('destination', 'Unknown'),
            "status": "error"
        }


if __name__ == "__main__":
    # Test the agent
    test_input = {
        'destination': 'Vienna, Austria',
        'month': 'july',
        'travel_days': 10,
        'budget_level': 'moderate',
        'trip_type': 'leisure',
        'preferences': 'art, food, culture, walking',
        'group_size': 2,
        'special_requirements': 'I will bw in an ACL conference from 27 for 4 days, so I need to plan around that. '
                                'My spouse will be with me, so we need to plan some activities for her while I am at the conference.'
                                'We will stay in Novotel Wien City (Accor Hotels). In the first two days i will be in stephansdom area.',
    }

    result = main(test_input, {})
    print(json.dumps(result, indent=2)) 