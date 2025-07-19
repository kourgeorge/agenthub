# Trip Planner Agent

A comprehensive trip planning agent that creates detailed travel itineraries including activities, accommodations, dining recommendations, and day-by-day plans based on user preferences. **Now with real-time web search capabilities for up-to-date information!**

## Features

### 🎯 **Comprehensive Trip Planning**
- **Destination Research**: Detailed information about destinations including weather, local customs, and safety tips
- **Accommodation Recommendations**: Hotel, hostel, and apartment suggestions based on budget and preferences
- **Activity Planning**: Curated activities and attractions matching trip type and interests
- **Dining Recommendations**: Restaurant suggestions with cuisine types and specialties
- **Day-by-Day Itineraries**: Detailed daily schedules with timing and logistics

### 🌐 **Real-Time Web Search**
- **Live Information**: Search the internet for current travel information
- **Website Crawling**: Extract content from travel websites and guides
- **Multiple Sources**: Combine information from various web sources
- **Up-to-Date Data**: Get the latest prices, opening hours, and recommendations
- **Source Attribution**: Track and cite information sources

### 💰 **Budget-Aware Planning**
- **Budget Levels**: Support for budget, moderate, and luxury travel styles
- **Cost Estimates**: Detailed cost breakdowns for accommodations, activities, and dining
- **Budget Optimization**: Recommendations that fit within specified budget constraints

### 🎨 **Personalized Recommendations**
- **Trip Types**: Support for leisure, business, adventure, cultural, romantic, family, solo, and group trips
- **User Preferences**: Customized recommendations based on interests (art, food, nature, history, etc.)
- **Group Size**: Tailored planning for different group sizes
- **Special Requirements**: Accommodation for accessibility needs and special requests

### 📅 **Smart Scheduling**
- **Date Range Support**: Flexible date planning with automatic duration calculation
- **Optimal Timing**: Recommendations for best times to visit attractions
- **Realistic Scheduling**: Balanced itineraries with appropriate rest time
- **Transportation Integration**: Logistics and transportation recommendations

## Web Search Capabilities

The Trip Planner Agent now includes powerful web search functionality:

### **Search Tools**
- **Serper Search**: Real-time Google search results for current information
- **Website Crawling**: Extract content from specific URLs
- **Content Parsing**: Intelligent extraction of relevant information
- **Source Tracking**: Keep track of information sources

### **What Gets Searched**
- **Destination Information**: Current weather, local customs, safety tips
- **Accommodations**: Real hotel listings and availability
- **Activities**: Current attractions and opening hours
- **Restaurants**: Latest dining recommendations and reviews
- **Travel Updates**: Recent changes and current conditions

### **Information Sources**
- Travel websites and blogs
- Official tourism websites
- Review platforms
- News articles
- Government travel advisories

## Setup

### **Required Environment Variables**
```bash
# Required for AI functionality
export OPENAI_API_KEY="your-openai-api-key"

# Optional for web search (highly recommended)
export SERPER_API_KEY="your-serper-api-key"
```

### **Getting API Keys**

#### **OpenAI API Key**
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Create an account or sign in
3. Go to API Keys section
4. Create a new API key
5. Copy and set as environment variable

#### **Serper API Key (for Web Search)**
1. Visit [Serper](https://serper.dev/)
2. Sign up for a free account
3. Get your API key from the dashboard
4. Copy and set as environment variable

### **Installation**
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export OPENAI_API_KEY="your-openai-api-key"
export SERPER_API_KEY="your-serper-api-key"  # Optional but recommended

# Test the web search functionality
python example_web_search.py
```

## Usage

### **Basic Usage (AI Only)**
```python
from trip_planner_agent import main

# Plan a trip to Paris (uses AI knowledge only)
result = main({
    "destination": "Paris, France",
    "start_date": "2024-06-15",
    "end_date": "2024-06-22",
    "budget_level": "moderate",
    "trip_type": "leisure",
    "preferences": "art, food, culture, walking",
    "group_size": 2
}, {})
```

### **Advanced Usage (With Web Search)**
```python
from trip_planner_agent import main

# Plan a trip with real-time web search
result = main({
    "destination": "Tokyo, Japan",
    "start_date": "2024-07-10",
    "end_date": "2024-07-15",
    "budget_level": "luxury",
    "trip_type": "adventure",
    "preferences": "technology, food, nightlife, shopping",
    "group_size": 1,
    "special_requirements": "accessible transportation",
    "planning_model": "openai:gpt-4o",
    "final_report_model": "openai:gpt-4o"
}, {})
```

### **Web Search Demo**
```bash
# Run the web search demonstration
python example_web_search.py
```

This will show you:
- How web search works for different types of information
- Examples of real-time data extraction
- Website crawling capabilities
- Full trip planning with web search integration

## Input Parameters

### Required Parameters
- **`destination`** (string): The travel destination (city, country, or region)
- **`start_date`** (string): Start date in YYYY-MM-DD format
- **`end_date`** (string): End date in YYYY-MM-DD format

### Optional Parameters
- **`budget_level`** (string): "budget", "moderate", or "luxury" (default: "moderate")
- **`trip_type`** (string): "leisure", "business", "adventure", "cultural", "romantic", "family", "solo", or "group" (default: "leisure")
- **`preferences`** (string): User interests and preferences (e.g., "art, food, nature, history")
- **`group_size`** (integer): Number of travelers (default: 2)
- **`special_requirements`** (string): Any special requirements or accessibility needs

### Advanced Configuration
- **`planning_model`** (string): Model for trip planning (default: "openai:gpt-4o")
- **`final_report_model`** (string): Model for final itinerary (default: "openai:gpt-4o")
- **`include_transportation`** (boolean): Include transportation recommendations (default: true)
- **`include_weather_info`** (boolean): Include weather information (default: true)
- **`include_safety_tips`** (boolean): Include safety tips (default: true)

## Output Structure

The agent returns a comprehensive trip plan with web search information:

```json
{
  "status": "success",
  "destination": "Paris, France",
  "trip_itinerary": "Comprehensive trip itinerary in markdown format...",
  "start_date": "2024-06-15",
  "end_date": "2024-06-22",
  "trip_duration": 7,
  "budget_level": "moderate",
  "trip_type": "leisure",
  "preferences": "art, food, culture, walking",
  "accommodations": [
    {
      "name": "Hotel Example",
      "type": "hotel",
      "price_range": "$150-200/night",
      "location": "Central Paris",
      "amenities": "WiFi, breakfast, concierge",
      "pros": "Great location, excellent service",
      "cons": "Small rooms",
      "booking_tips": "Book 3 months in advance",
      "source_url": "https://example.com/hotel"
    }
  ],
  "activities": [...],
  "restaurants": [...],
  "day_plans": [...],
  "destination_info": "Comprehensive destination information...",
  "web_sources": [
    "https://www.lonelyplanet.com/paris",
    "https://www.tripadvisor.com/paris",
    "https://en.wikipedia.org/wiki/Paris"
  ],
  "execution_time": 12.5,
  "generated_at": "2024-01-15T10:30:00"
}
```

## Trip Planning Process

The agent follows a structured 7-step planning process with web search integration:

1. **Trip Analysis** → Extracts and validates trip requirements from user input
2. **Destination Research** → Searches web for current destination information
3. **Accommodation Research** → Searches for real accommodation options
4. **Activity Research** → Finds current activities and attractions
5. **Restaurant Research** → Discovers dining options with recent reviews
6. **Day Planning** → Creates detailed day-by-day itineraries with timing and logistics
7. **Final Itinerary** → Generates a comprehensive trip guide with all recommendations

## Web Search Features

### **Intelligent Information Extraction**
- **Pattern Recognition**: Automatically extracts hotel names, prices, and amenities
- **Content Categorization**: Organizes information by type (weather, customs, safety)
- **Source Validation**: Prioritizes information from reliable sources
- **Content Summarization**: Condenses long articles into relevant snippets

### **Real-Time Data**
- **Current Prices**: Latest accommodation and activity costs
- **Opening Hours**: Current operating schedules
- **Weather Updates**: Recent weather information
- **Travel Alerts**: Latest safety and security information

### **Multi-Source Aggregation**
- **Diverse Sources**: Combines information from multiple websites
- **Cross-Validation**: Verifies information across different sources
- **Comprehensive Coverage**: Ensures all aspects of travel are covered
- **Source Attribution**: Tracks where each piece of information comes from

## Examples

### Example 1: Paris Leisure Trip (With Web Search)
```python
{
  "destination": "Paris, France",
  "start_date": "2024-06-15",
  "end_date": "2024-06-22",
  "budget_level": "moderate",
  "trip_type": "leisure",
  "preferences": "art, food, culture, walking",
  "group_size": 2
}
```

### Example 2: Tokyo Adventure Trip (With Web Search)
```python
{
  "destination": "Tokyo, Japan",
  "start_date": "2024-07-10",
  "end_date": "2024-07-15",
  "budget_level": "luxury",
  "trip_type": "adventure",
  "preferences": "technology, food, nightlife, shopping",
  "group_size": 1
}
```

### Example 3: New York Business Trip (With Web Search)
```python
{
  "destination": "New York City, USA",
  "start_date": "2024-08-20",
  "end_date": "2024-08-23",
  "budget_level": "budget",
  "trip_type": "business",
  "preferences": "business, networking, quick meals",
  "group_size": 1,
  "special_requirements": "accessible accommodations"
}
```

## Architecture

The Trip Planner Agent uses LangGraph with web search integration:

- **State Management**: Uses TypedDict and Pydantic models for type-safe state management
- **Web Search Integration**: Real-time information gathering from multiple sources
- **Modular Design**: Each planning step is a separate node in the graph
- **Error Handling**: Robust error handling with fallbacks and retries
- **Configurable Models**: Support for different LLM providers and models
- **Structured Output**: Uses Pydantic models for consistent, validated outputs
- **Source Tracking**: Maintains references to information sources

## Contributing

To contribute to the Trip Planner Agent:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 