from pydantic import BaseModel, Field
from typing import Any, List, Optional
from langchain_core.runnables import RunnableConfig
import os
from enum import Enum

class SearchAPI(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    TAVILY = "tavily"
    SERPER = "serper"
    NONE = "none"

class MCPConfig(BaseModel):
    url: Optional[str] = Field(
        default=None,
        description="The URL of the MCP server"
    )
    tools: Optional[List[str]] = Field(
        default=None,
        description="The tools to make available to the LLM"
    )
    auth_required: Optional[bool] = Field(
        default=False,
        description="Whether the MCP server requires authentication"
    )

class Configuration(BaseModel):
    # General Configuration
    max_structured_output_retries: int = Field(
        default=3,
        description="Maximum number of retries for structured output calls from models"
    )
    allow_clarification: bool = Field(
        default=True,
        description="Whether to allow the researcher to ask the user clarifying questions before starting research"
    )
    max_concurrent_research_units: int = Field(
        default=5,
        description="Maximum number of research units to run concurrently. This will allow the researcher to use multiple sub-agents to conduct research. Note: with more concurrency, you may run into rate limits."
    )
    
    # Research Configuration
    search_api: SearchAPI = Field(
        default=SearchAPI.TAVILY,
        description="Search API to use for research. Options: tavily, serper, openai, anthropic, none. NOTE: Make sure your Researcher Model supports the selected search API."
    )
    max_researcher_iterations: int = Field(
        default=3,
        description="Maximum number of research iterations for the Research Supervisor. This is the number of times the Research Supervisor will reflect on the research and ask follow-up questions."
    )
    max_react_tool_calls: int = Field(
        default=5,
        description="Maximum number of tool calling iterations to make in a single researcher step."
    )
    
    # Model Configuration
    summarization_model: str = Field(
        default="openai:gpt-4o-mini",
        description="Model for summarizing research results from search results"
    )
    summarization_model_max_tokens: int = Field(
        default=8192,
        description="Maximum output tokens for summarization model"
    )
    research_model: str = Field(
        default="openai:gpt-4o",
        description="Model for conducting research. NOTE: Make sure your Researcher Model supports the selected search API."
    )
    research_model_max_tokens: int = Field(
        default=10000,
        description="Maximum output tokens for research model"
    )
    compression_model: str = Field(
        default="openai:gpt-4o-mini",
        description="Model for compressing research findings from sub-agents. NOTE: Make sure your Compression Model supports the selected search API."
    )
    compression_model_max_tokens: int = Field(
        default=8192,
        description="Maximum output tokens for compression model"
    )
    final_report_model: str = Field(
        default="openai:gpt-4o",
        description="Model for writing the final report from all research findings"
    )
    final_report_model_max_tokens: int = Field(
        default=10000,
        description="Maximum output tokens for final report model"
    )
    
    # MCP server configuration
    mcp_config: Optional[MCPConfig] = Field(
        default=None,
        description="MCP server configuration"
    )
    mcp_prompt: Optional[str] = Field(
        default=None,
        description="Additional prompt to include for MCP tools"
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