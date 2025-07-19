from typing import Annotated, Optional, List
from pydantic import BaseModel, Field
import operator
from langgraph.graph import MessagesState
from langchain_core.messages import MessageLikeRepresentation
from typing_extensions import TypedDict

###################
# Structured Outputs
###################

class TripPreferences(BaseModel):
    """Extracted trip preferences from user input."""
    destination: str = Field(
        description="The travel destination (city, country, or region)"
    )
    start_date: str = Field(
        description="Start date of the trip in YYYY-MM-DD format"
    )
    end_date: str = Field(
        description="End date of the trip in YYYY-MM-DD format"
    )
    budget_level: str = Field(
        description="Budget level: budget, moderate, or luxury"
    )
    trip_type: str = Field(
        description="Type of trip: leisure, business, adventure, cultural, romantic, family, solo, or group"
    )
    preferences: str = Field(
        description="User preferences and interests (e.g., art, food, nature, history)"
    )
    group_size: int = Field(
        description="Number of travelers",
        default=1
    )

class Destination(BaseModel):
    """Destination information and research."""
    description: str = Field(
        description="Comprehensive description of the destination"
    )
    best_time_to_visit: str = Field(
        description="Best time of year to visit this destination"
    )
    weather_info: str = Field(
        description="Typical weather conditions and climate information"
    )
    local_customs: str = Field(
        description="Important local customs, etiquette, and cultural information"
    )
    safety_tips: str = Field(
        description="Safety tips and important information for travelers"
    )

class AccommodationRecommendation(BaseModel):
    """Individual accommodation recommendation."""
    name: str = Field(description="Name of the accommodation")
    type: str = Field(description="Type of accommodation (hotel, hostel, apartment, etc.)")
    price_range: str = Field(description="Price range and budget category")
    location: str = Field(description="Location and neighborhood")
    amenities: str = Field(description="Key amenities and features")
    pros: str = Field(description="Positive aspects of this accommodation")
    cons: str = Field(description="Negative aspects or limitations")
    booking_tips: str = Field(description="Tips for booking this accommodation")

class Accommodation(BaseModel):
    """Accommodation recommendations."""
    recommendations: List[AccommodationRecommendation] = Field(
        description="List of accommodation recommendations with details"
    )
    tips: str = Field(
        description="Tips for booking accommodations in this destination"
    )

class ActivityRecommendation(BaseModel):
    """Individual activity recommendation."""
    name: str = Field(description="Name of the activity or attraction")
    type: str = Field(description="Type of activity (museum, park, tour, etc.)")
    description: str = Field(description="Description and highlights")
    cost: str = Field(description="Cost and budget category")
    duration: str = Field(description="Duration and time required")
    location: str = Field(description="Location and accessibility")
    best_time: str = Field(description="Best time to visit")
    booking_tips: str = Field(description="Booking requirements and tips")

class Activity(BaseModel):
    """Activity and attraction recommendations."""
    recommendations: List[ActivityRecommendation] = Field(
        description="List of activity and attraction recommendations"
    )
    tips: str = Field(
        description="Tips for activities and attractions in this destination"
    )

class RestaurantRecommendation(BaseModel):
    """Individual restaurant recommendation."""
    name: str = Field(description="Restaurant name")
    cuisine: str = Field(description="Cuisine type")
    price_range: str = Field(description="Price range and budget category")
    location: str = Field(description="Location and neighborhood")
    specialties: str = Field(description="Specialties and must-try dishes")
    atmosphere: str = Field(description="Atmosphere and dining experience")
    reservation_tips: str = Field(description="Reservation requirements and tips")

class Restaurant(BaseModel):
    """Restaurant and dining recommendations."""
    recommendations: List[RestaurantRecommendation] = Field(
        description="List of restaurant and dining recommendations"
    )
    tips: str = Field(
        description="Tips for dining in this destination"
    )

class DailyPlanItem(BaseModel):
    """Individual day plan item."""
    day: int = Field(description="Day number (1, 2, 3, etc.)")
    date: str = Field(description="Actual date in YYYY-MM-DD format")
    morning: str = Field(description="Morning activities and timing")
    lunch: str = Field(description="Lunch recommendations")
    afternoon: str = Field(description="Afternoon activities and timing")
    dinner: str = Field(description="Dinner recommendations")
    evening: str = Field(description="Evening activities (if any)")
    transportation: str = Field(description="Transportation between activities")
    estimated_cost: str = Field(description="Estimated costs for the day")
    tips: str = Field(description="Tips and notes for the day")

class DayPlan(BaseModel):
    """Day-by-day trip plan."""
    daily_plans: List[DailyPlanItem] = Field(
        description="Detailed day-by-day itinerary with activities, meals, and logistics"
    )

class TripPlan(BaseModel):
    """Complete trip plan."""
    itinerary: str = Field(
        description="Complete trip itinerary"
    )
    summary: str = Field(
        description="Summary of the trip plan"
    )

###################
# State Definitions
###################

def override_reducer(current_value, new_value):
    if isinstance(new_value, dict) and new_value.get("type") == "override":
        return new_value.get("value", new_value)
    else:
        return operator.add(current_value, new_value)

class AgentInputState(MessagesState):
    """InputState is only 'messages'"""

class AgentState(MessagesState):
    user_input: str
    planner_messages: Annotated[list[MessageLikeRepresentation], override_reducer]
    destination: str
    start_date: str
    end_date: str
    trip_duration: int
    budget_level: str
    trip_type: str
    preferences: str
    group_size: int
    destination_info: str
    accommodations: List[dict] = []
    activities: List[dict] = []
    restaurants: List[dict] = []
    day_plans: List[dict] = []

class PlannerState(TypedDict):
    planner_messages: Annotated[list[MessageLikeRepresentation], override_reducer]
    destination: str
    start_date: str
    end_date: str
    trip_duration: int
    budget_level: str
    trip_type: str
    preferences: str
    group_size: int
    destination_info: str
    accommodations: List[dict]
    activities: List[dict]
    restaurants: List[dict]
    day_plans: List[dict]

class ResearchState(TypedDict):
    research_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    research_topic: str
    research_results: str 