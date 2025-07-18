import os
import aiohttp
import asyncio
import logging
import warnings
from datetime import datetime, timedelta, timezone
from typing import Annotated, List, Literal, Dict, Optional, Any
from langchain_core.tools import BaseTool, StructuredTool, tool, ToolException, InjectedToolArg
from langchain_core.messages import HumanMessage, AIMessage, MessageLikeRepresentation, filter_messages
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model
from tavily import AsyncTavilyClient
from state import Summary, ResearchComplete
from configuration import SearchAPI, Configuration
from prompts import summarize_webpage_prompt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

##########################
# Search Tool Utils
##########################
TAVILY_SEARCH_DESCRIPTION = (
    "A search engine optimized for comprehensive, accurate, and trusted results. "
    "Useful for when you need to answer questions about current events."
)

SERPER_SEARCH_DESCRIPTION = (
    "A Google search API that provides real-time search results from Google. "
    "Useful for finding current information, news, and web content."
)

@tool(description=TAVILY_SEARCH_DESCRIPTION)
async def tavily_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
    config: RunnableConfig = None
) -> str:
    """
    Fetches results from Tavily search API.

    Args:
        queries (List[str]): List of search queries, you can pass in as many queries as you need.
        max_results (int): Maximum number of results to return
        topic (Literal['general', 'news', 'finance']): Topic to filter results by

    Returns:
        str: A formatted string of search results
    """
    try:
        search_results = await tavily_search_async(
            queries,
            max_results=max_results,
            topic=topic,
            include_raw_content=True,
            config=config
        )
        
        # Format the search results and deduplicate results by URL
        formatted_output = f"Search results: \n\n"
        unique_results = {}
        
        for response in search_results:
            for result in response['results']:
                url = result['url']
                if url not in unique_results:
                    unique_results[url] = {**result, "query": response['query']}
        
        configurable = Configuration.from_runnable_config(config)
        max_char_to_include = 50_000  # Keep under input token limits
        
        model_api_key = get_api_key_for_model(configurable.summarization_model, config)
        summarization_model = init_chat_model(
            model=configurable.summarization_model,
            max_tokens=configurable.summarization_model_max_tokens,
            api_key=model_api_key,
            tags=["langsmith:nostream"]
        ).with_structured_output(Summary).with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        
        # Summarize webpages with content
        summarization_tasks = []
        for result in unique_results.values():
            if result.get("raw_content"):
                task = summarize_webpage(summarization_model, result['raw_content'][:max_char_to_include])
                summarization_tasks.append(task)
            else:
                task = asyncio.create_task(asyncio.sleep(0))
                summarization_tasks.append(task)
        
        summaries = await asyncio.gather(*summarization_tasks, return_exceptions=True)
        
        summarized_results = {}
        for url, result, summary in zip(unique_results.keys(), unique_results.values(), summaries):
            if isinstance(summary, Exception):
                summarized_results[url] = {
                    'title': result['title'], 
                    'content': result['content']
                }
            else:
                summarized_results[url] = {
                    'title': result['title'], 
                    'content': result['content'] if summary is None else summary
                }
        
        # Format output
        for i, (url, result) in enumerate(summarized_results.items()):
            formatted_output += f"\n\n--- SOURCE {i+1}: {result['title']} ---\n"
            formatted_output += f"URL: {url}\n\n"
            formatted_output += f"SUMMARY:\n{result['content']}\n\n"
            formatted_output += "\n\n" + "-" * 80 + "\n"
        
        if summarized_results:
            return formatted_output
        else:
            return "No valid search results found. Please try different search queries or use a different search API."
            
    except Exception as e:
        logger.error(f"Error in tavily search: {e}")
        return f"Error performing search: {str(e)}"

@tool(description=SERPER_SEARCH_DESCRIPTION)
async def serper_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    config: RunnableConfig = None
) -> str:
    """
    Fetches results from Serper Google search API.

    Args:
        queries (List[str]): List of search queries, you can pass in as many queries as you need.
        max_results (int): Maximum number of results to return

    Returns:
        str: A formatted string of search results
    """
    try:
        search_results = await serper_search_async(
            queries,
            max_results=max_results,
            config=config
        )
        
        # Format the search results and deduplicate results by URL
        formatted_output = f"Search results: \n\n"
        unique_results = {}
        
        for response in search_results:
            for result in response.get('results', []):
                url = result.get('link', '')
                if url and url not in unique_results:
                    unique_results[url] = {**result, "query": response.get('query', '')}
        
        configurable = Configuration.from_runnable_config(config)
        max_char_to_include = 50_000  # Keep under input token limits
        
        model_api_key = get_api_key_for_model(configurable.summarization_model, config)
        summarization_model = init_chat_model(
            model=configurable.summarization_model,
            max_tokens=configurable.summarization_model_max_tokens,
            api_key=model_api_key,
            tags=["langsmith:nostream"]
        ).with_structured_output(Summary).with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        
        # Summarize webpages with content
        summarization_tasks = []
        for result in unique_results.values():
            if result.get("snippet"):
                task = summarize_webpage(summarization_model, result['snippet'][:max_char_to_include])
                summarization_tasks.append(task)
            else:
                task = asyncio.create_task(asyncio.sleep(0))
                summarization_tasks.append(task)
        
        summaries = await asyncio.gather(*summarization_tasks, return_exceptions=True)
        
        summarized_results = {}
        for url, result, summary in zip(unique_results.keys(), unique_results.values(), summaries):
            if isinstance(summary, Exception):
                summarized_results[url] = {
                    'title': result.get('title', 'No title'), 
                    'content': result.get('snippet', 'No content')
                }
            else:
                summarized_results[url] = {
                    'title': result.get('title', 'No title'), 
                    'content': result.get('snippet', 'No content') if summary is None else summary
                }
        
        # Format output
        for i, (url, result) in enumerate(summarized_results.items()):
            formatted_output += f"\n\n--- SOURCE {i+1}: {result['title']} ---\n"
            formatted_output += f"URL: {url}\n\n"
            formatted_output += f"SUMMARY:\n{result['content']}\n\n"
            formatted_output += "\n\n" + "-" * 80 + "\n"
        
        if summarized_results:
            return formatted_output
        else:
            return "No valid search results found. Please try different search queries or use a different search API."
            
    except Exception as e:
        logger.error(f"Error in serper search: {e}")
        return f"Error performing search: {str(e)}"

async def serper_search_async(search_queries, max_results: int = 5, config: RunnableConfig = None):
    """Async wrapper for Serper search."""
    try:
        serper_api_key = get_serper_api_key(config)
        if not serper_api_key:
            raise ValueError("Serper API key not found")
        
        search_tasks = []
        async with aiohttp.ClientSession() as session:
            for query in search_queries:
                search_tasks.append(
                    serper_search_request(session, query, max_results, serper_api_key)
                )
            
            search_docs = await asyncio.gather(*search_tasks)
            return search_docs
        
    except Exception as e:
        logger.error(f"Error in serper_search_async: {e}")
        return []

async def serper_search_request(session, query: str, max_results: int, api_key: str):
    """Make a single Serper search request."""
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "num": max_results
    }
    
    try:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return {"query": query, "results": data.get("organic", [])}
            else:
                logger.error(f"Serper API error: {response.status}")
                return {"query": query, "results": []}
    except Exception as e:
        logger.error(f"Error in serper_search_request: {e}")
        return {"query": query, "results": []}

async def tavily_search_async(search_queries, max_results: int = 5, topic: Literal["general", "news", "finance"] = "general", include_raw_content: bool = True, config: RunnableConfig = None):
    """Async wrapper for Tavily search."""
    try:
        tavily_async_client = AsyncTavilyClient(api_key=get_tavily_api_key(config))
        search_tasks = []
        
        for query in search_queries:
            search_tasks.append(
                tavily_async_client.search(
                    query,
                    max_results=max_results,
                    include_raw_content=include_raw_content,
                    topic=topic
                )
            )
        
        search_docs = await asyncio.gather(*search_tasks)
        return search_docs
        
    except Exception as e:
        logger.error(f"Error in tavily_search_async: {e}")
        return []

async def summarize_webpage(model: BaseChatModel, webpage_content: str) -> str:
    """Summarize webpage content using the provided model."""
    try:
        summary = await asyncio.wait_for(
            model.ainvoke([HumanMessage(content=summarize_webpage_prompt.format(
                webpage_content=webpage_content, 
                date=get_today_str()
            ))]),
            timeout=60.0
        )
        return f"""<summary>\n{summary.summary}\n</summary>\n\n<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"""
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"Failed to summarize webpage: {str(e)}")
        return webpage_content

##########################
# Search API Tools
##########################
async def get_search_tool(search_api: SearchAPI):
    """Get the appropriate search tool based on the search API configuration."""
    if search_api == SearchAPI.TAVILY:
        return tavily_search
    elif search_api == SearchAPI.SERPER:
        return serper_search
    elif search_api == SearchAPI.OPENAI:
        # OpenAI web search tool would be implemented here
        return None
    elif search_api == SearchAPI.ANTHROPIC:
        # Anthropic web search tool would be implemented here
        return None
    else:
        return None

async def get_all_tools(config: RunnableConfig):
    """Get all available tools for the research agent."""
    configurable = Configuration.from_runnable_config(config)
    tools = []
    
    # Add search tool
    search_tool = await get_search_tool(configurable.search_api)
    if search_tool:
        tools.append(search_tool)
    
    # Add ResearchComplete tool
    tools.append(ResearchComplete)
    
    # Add MCP tools if configured
    if configurable.mcp_config:
        try:
            mcp_tools = await load_mcp_tools(config, set(tool.name for tool in tools))
            tools.extend(mcp_tools)
        except Exception as e:
            logger.warning(f"Failed to load MCP tools: {e}")
    
    return tools

async def load_mcp_tools(config: RunnableConfig, existing_tool_names: set[str]) -> list[BaseTool]:
    """Load MCP tools if configured."""
    # Simplified MCP tool loading - in a full implementation, this would connect to MCP servers
    # For now, return empty list to avoid complexity
    return []

##########################
# Utility Functions
##########################
def get_notes_from_tool_calls(messages: list[MessageLikeRepresentation]):
    """Extract notes from tool call messages."""
    notes = []
    for message in messages:
        if hasattr(message, 'content') and message.content:
            notes.append(str(message.content))
    return notes

def anthropic_websearch_called(response):
    """Check if Anthropic web search was called in the response."""
    # Implementation would check for Anthropic web search tool calls
    return False

def openai_websearch_called(response):
    """Check if OpenAI web search was called in the response."""
    # Implementation would check for OpenAI web search tool calls
    return False

def is_token_limit_exceeded(exception: Exception, model_name: str = None) -> bool:
    """Check if the exception is due to token limit being exceeded."""
    error_str = str(exception).lower()
    
    if model_name and "openai" in model_name.lower():
        return _check_openai_token_limit(exception, error_str)
    elif model_name and "anthropic" in model_name.lower():
        return _check_anthropic_token_limit(exception, error_str)
    elif model_name and "gemini" in model_name.lower():
        return _check_gemini_token_limit(exception, error_str)
    else:
        # Generic check
        token_indicators = [
            "token", "limit", "exceeded", "too long", "context length",
            "maximum", "input", "output", "length"
        ]
        return any(indicator in error_str for indicator in token_indicators)

def _check_openai_token_limit(exception: Exception, error_str: str) -> bool:
    """Check for OpenAI-specific token limit errors."""
    openai_indicators = [
        "context_length_exceeded",
        "maximum_context_length",
        "token_limit",
        "too many tokens",
        "input tokens",
        "output tokens"
    ]
    return any(indicator in error_str for indicator in openai_indicators)

def _check_anthropic_token_limit(exception: Exception, error_str: str) -> bool:
    """Check for Anthropic-specific token limit errors."""
    anthropic_indicators = [
        "input_tokens",
        "output_tokens",
        "token_limit",
        "context_length",
        "maximum_tokens"
    ]
    return any(indicator in error_str for indicator in anthropic_indicators)

def _check_gemini_token_limit(exception: Exception, error_str: str) -> bool:
    """Check for Gemini-specific token limit errors."""
    gemini_indicators = [
        "token_limit",
        "input_tokens",
        "output_tokens",
        "context_length",
        "maximum_tokens"
    ]
    return any(indicator in error_str for indicator in gemini_indicators)

def get_model_token_limit(model_string):
    """Get the token limit for a given model."""
    # Simplified token limits - in practice, these would be more comprehensive
    model_limits = {
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 4096,
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        "gemini-pro": 32768,
        "gemini-flash": 1048576
    }
    
    for model_name, limit in model_limits.items():
        if model_name in model_string.lower():
            return limit
    
    return 8192  # Default fallback

def remove_up_to_last_ai_message(messages: list[MessageLikeRepresentation]) -> list[MessageLikeRepresentation]:
    """Remove messages up to the last AI message."""
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            return messages[i+1:]
    return messages

def get_today_str() -> str:
    """Get today's date as a string."""
    return datetime.now().strftime("%Y-%m-%d")

def get_config_value(value):
    """Get configuration value with fallback."""
    if value is None:
        return ""
    return str(value)

def get_api_key_for_model(model_name: str, config: RunnableConfig):
    """Get the appropriate API key for a given model."""
    if not config:
        return os.getenv("OPENAI_API_KEY")
    
    configurable = config.get("configurable", {})
    
    # Check for model-specific API keys
    if "openai" in model_name.lower():
        return configurable.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    elif "anthropic" in model_name.lower():
        return configurable.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
    elif "tavily" in model_name.lower():
        return configurable.get("tavily_api_key") or os.getenv("TAVILY_API_KEY")
    else:
        # Default to OpenAI
        return configurable.get("openai_api_key") or os.getenv("OPENAI_API_KEY")

def get_tavily_api_key(config: RunnableConfig):
    """Get Tavily API key from config or environment."""
    if not config:
        return os.getenv("TAVILY_API_KEY")
    
    configurable = config.get("configurable", {})
    return configurable.get("tavily_api_key") or os.getenv("TAVILY_API_KEY")

def get_serper_api_key(config: RunnableConfig):
    """Get Serper API key from config or environment."""
    if not config:
        return os.getenv("SERPER_API_KEY")
    
    configurable = config.get("configurable", {})
    return configurable.get("serper_api_key") or os.getenv("SERPER_API_KEY") 