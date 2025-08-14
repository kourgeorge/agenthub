import os
import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional
from langchain_core.runnables import RunnableConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_today_str() -> str:
    """Get today's date as a string."""
    return datetime.now().strftime("%Y-%m-%d")

def generate_dates_from_month_and_days(month: Optional[str], travel_days: int) -> Tuple[str, str]:
    """
    Generate start and end dates from month preference and travel days.
    
    Args:
        month: Preferred month (january, february, etc.) or None
        travel_days: Number of travel days
    
    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
    """
    today = datetime.now()
    
    if month:
        # Convert month name to month number
        month_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        target_month = month_map.get(month.lower(), today.month)
        current_year = today.year
        
        # If the target month has passed this year, plan for next year
        if target_month < today.month:
            current_year += 1
        
        # Set start date to the 15th of the target month (middle of month)
        start_date = datetime(current_year, target_month, 15)
        
        # If the start date is in the past, move to next year
        if start_date < today:
            start_date = datetime(current_year + 1, target_month, 15)
    else:
        # No month specified, start 30 days from today
        start_date = today + timedelta(days=30)
    
    # Calculate end date based on travel days
    end_date = start_date + timedelta(days=travel_days - 1)
    
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def parse_date_range(start_date: str, end_date: str) -> Tuple[str, str]:
    """
    Parse and validate date range.
    
    Args:
        start_date: Start date string
        end_date: End date string
    
    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
    """
    try:
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Validate that end date is after start date
        if end <= start:
            raise ValueError("End date must be after start date")
        
        return start_date, end_date
    except ValueError as e:
        logger.error(f"Error parsing dates: {e}")
        # Return default dates if parsing fails
        today = datetime.now()
        start = today + timedelta(days=30)
        end = start + timedelta(days=7)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def calculate_trip_duration(start_date: str, end_date: str) -> int:
    """
    Calculate trip duration in days.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Number of days for the trip
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        duration = (end - start).days + 1  # Include both start and end days
        return max(1, duration)  # Ensure at least 1 day
    except ValueError:
        logger.error("Error calculating trip duration")
        return 7  # Default to 7 days

def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format currency amount.
    
    Args:
        amount: Amount to format
        currency: Currency code
    
    Returns:
        Formatted currency string
    """
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CAD": "C$",
        "AUD": "A$"
    }
    
    symbol = currency_symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"

def get_api_key_for_model(model_name: str, config: RunnableConfig) -> Optional[str]:
    """
    Get the appropriate API key for a given model.
    
    Args:
        model_name: Name of the model
        config: RunnableConfig containing API keys
    
    Returns:
        API key string or None
    """
    if not config:
        return os.getenv("OPENAI_API_KEY")
    
    configurable = config.get("configurable", {})
    
    # Check for model-specific API keys
    if "openai" in model_name.lower():
        return configurable.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    elif "anthropic" in model_name.lower():
        return configurable.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
    else:
        # Default to OpenAI
        return configurable.get("openai_api_key") or os.getenv("OPENAI_API_KEY")

def validate_destination(destination: str) -> bool:
    """
    Basic validation for destination input.
    
    Args:
        destination: Destination string to validate
    
    Returns:
        True if destination is valid, False otherwise
    """
    if not destination or len(destination.strip()) < 2:
        return False
    
    # Check for common invalid inputs
    invalid_inputs = ["", "unknown", "none", "n/a", "tbd"]
    if destination.lower().strip() in invalid_inputs:
        return False
    
    return True

def get_weather_info(destination: str, date: str) -> str:
    """
    Get weather information for a destination and date.
    This is a placeholder function - in a real implementation, 
    you would integrate with a weather API.
    
    Args:
        destination: Destination name
        date: Date in YYYY-MM-DD format
    
    Returns:
        Weather information string
    """
    # This is a placeholder - in a real implementation, you would:
    # 1. Call a weather API (like OpenWeatherMap, WeatherAPI, etc.)
    # 2. Parse the response
    # 3. Return formatted weather information
    
    return f"Weather information for {destination} on {date} would be retrieved from a weather API. Please check local weather forecasts before your trip."

def estimate_budget_range(budget_level: str, trip_duration: int, group_size: int) -> dict:
    """
    Estimate budget ranges for different categories.
    
    Args:
        budget_level: Budget level (budget, moderate, luxury)
        trip_duration: Trip duration in days
        group_size: Number of travelers
    
    Returns:
        Dictionary with budget estimates
    """
    # Base daily costs per person (in USD)
    budget_ranges = {
        "budget": {
            "accommodation": 50,
            "food": 30,
            "activities": 20,
            "transportation": 15
        },
        "moderate": {
            "accommodation": 150,
            "food": 60,
            "activities": 50,
            "transportation": 30
        },
        "luxury": {
            "accommodation": 400,
            "food": 150,
            "activities": 100,
            "transportation": 80
        }
    }
    
    base_costs = budget_ranges.get(budget_level, budget_ranges["moderate"])
    
    # Calculate total costs
    total_costs = {}
    for category, daily_cost in base_costs.items():
        total_costs[category] = daily_cost * trip_duration * group_size
    
    total_costs["total"] = sum(total_costs.values())
    
    return total_costs

def format_trip_summary(destination: str, month: Optional[str], travel_days: int, 
                       trip_type: str, budget_level: str, group_size: int) -> str:
    """
    Format a trip summary.
    
    Args:
        destination: Destination name
        month: Preferred month (optional)
        travel_days: Number of travel days
        trip_type: Type of trip
        budget_level: Budget level
        group_size: Number of travelers
    
    Returns:
        Formatted trip summary string
    """
    summary = f"""
    Trip Summary:
    - Destination: {destination}
    - Travel Period: {month if month else 'Not specified'} ({travel_days} days)
    - Type: {trip_type.title()}
    - Budget: {budget_level.title()}
    - Travelers: {group_size}
    """
    
    return summary.strip()

def get_transportation_tips(destination: str, trip_type: str) -> str:
    """
    Get transportation tips for a destination.
    
    Args:
        destination: Destination name
        trip_type: Type of trip
    
    Returns:
        Transportation tips string
    """
    # This is a placeholder - in a real implementation, you would:
    # 1. Have a database of transportation information for destinations
    # 2. Consider the trip type when providing recommendations
    # 3. Include local transportation options, costs, and tips
    
    tips = f"""
    Transportation Tips for {destination}:
    - Research local public transportation options
    - Consider ride-sharing services for convenience
    - Check if walking is feasible for short distances
    - Look into day passes for public transit
    - Consider renting a car if exploring outside the city
    """
    
    return tips.strip()

def get_packing_list(destination: str, trip_type: str, trip_duration: int, 
                    budget_level: str) -> str:
    """
    Generate a packing list based on trip details.
    
    Args:
        destination: Destination name
        trip_type: Type of trip
        trip_duration: Trip duration in days
        budget_level: Budget level
    
    Returns:
        Packing list string
    """
    # This is a placeholder - in a real implementation, you would:
    # 1. Consider the destination's climate and weather
    # 2. Factor in the trip type and activities
    # 3. Adjust for budget level and duration
    # 4. Include destination-specific items
    
    packing_list = f"""
    Packing List for {destination} ({trip_duration} days):
    
    Essentials:
    - Passport/ID and travel documents
    - Credit cards and cash
    - Phone and charger
    - Camera
    - Comfortable walking shoes
    
    Clothing:
    - {trip_duration} days worth of clothes
    - Weather-appropriate attire
    - Comfortable shoes for activities
    - Formal wear if needed for {trip_type} activities
    
    Toiletries:
    - Personal care items
    - Medications
    - Sunscreen and insect repellent
    
    Electronics:
    - Phone and charger
    - Power bank
    - Universal adapter if needed
    
    Documents:
    - Travel insurance
    - Booking confirmations
    - Emergency contacts
    """
    
    return packing_list.strip() 