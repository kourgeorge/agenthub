from pydantic import BaseModel, Field
from typing import Any, List, Optional
from langchain_core.runnables import RunnableConfig
import os
from enum import Enum

class BudgetLevel(Enum):
    BUDGET = "budget"
    MODERATE = "moderate"
    LUXURY = "luxury"

class TripType(Enum):
    LEISURE = "leisure"
    BUSINESS = "business"
    ADVENTURE = "adventure"
    CULTURAL = "cultural"
    ROMANTIC = "romantic"
    FAMILY = "family"
    SOLO = "solo"
    GROUP = "group"

class Configuration(BaseModel):
    # General Configuration
    max_structured_output_retries: int = Field(
        default=3,
        description="Maximum number of retries for structured output calls from models"
    )
    
    # Model Configuration
    planning_model: str = Field(
        default="openai:gpt-4o",
        description="Model for trip planning and research"
    )
    planning_model_max_tokens: int = Field(
        default=8000,
        description="Maximum output tokens for planning model"
    )
    final_report_model: str = Field(
        default="openai:gpt-4o",
        description="Model for generating final trip itinerary"
    )
    final_report_model_max_tokens: int = Field(
        default=12000,
        description="Maximum output tokens for final report model"
    )
    
    # Trip Planning Configuration
    max_accommodations_per_budget: int = Field(
        default=5,
        description="Maximum number of accommodation recommendations per budget level"
    )
    max_activities_per_day: int = Field(
        default=4,
        description="Maximum number of activities per day"
    )
    max_restaurants_per_meal: int = Field(
        default=3,
        description="Maximum number of restaurant recommendations per meal"
    )
    include_transportation: bool = Field(
        default=True,
        description="Whether to include transportation recommendations"
    )
    include_weather_info: bool = Field(
        default=True,
        description="Whether to include weather information"
    )
    include_safety_tips: bool = Field(
        default=True,
        description="Whether to include safety tips and local customs"
    )
    
    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create Configuration from RunnableConfig."""
        if config is None:
            return cls()
        
        configurable = config.get("configurable", {})
        return cls(**configurable)
    
    class Config:
        arbitrary_types_allowed = True 