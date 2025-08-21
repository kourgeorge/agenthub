#!/usr/bin/env python3
"""
Deep Research Agent

A comprehensive research agent that conducts deep, multi-source research using web search,
MCP tools, and AI-powered analysis to provide detailed, well-sourced reports on any topic.
"""

import json
import os
import sys
import time
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal
import warnings
from dotenv import load_dotenv

load_dotenv()

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Import the deep research components
from configuration import Configuration
from state import (
    AgentState,
    AgentInputState,
    SupervisorState,
    ResearcherState,
    ClarifyWithUser,
    ResearchQuestion,
    ConductResearch,
    ResearchComplete,
    ResearcherOutputState
)
from prompts import (
    clarify_with_user_instructions,
    transform_messages_into_research_topic_prompt,
    research_system_prompt,
    compress_research_system_prompt,
    compress_research_simple_human_message,
    final_report_generation_prompt,
    lead_researcher_prompt
)
from utils import (
    get_today_str,
    is_token_limit_exceeded,
    get_model_token_limit,
    get_all_tools,
    openai_websearch_called,
    anthropic_websearch_called,
    remove_up_to_last_ai_message,
    get_api_key_for_model,
    get_notes_from_tool_calls
)

# Import LangChain components
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, get_buffer_string, \
    filter_messages
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from langgraph.types import Command

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize a configurable model that we will use throughout the agent
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


class DeepResearchAgent:
    """Comprehensive deep research agent with multi-source research capabilities."""

    def __init__(self, config: Optional[Configuration] = None):
        """Initialize the deep research agent."""
        self.config = config or Configuration()

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

    async def clarify_with_user(self, state: AgentState, config: RunnableConfig) -> Command[
        Literal["write_research_brief", "final_report_generation"]]:
        """Determine if clarification is needed from the user."""
        configurable = Configuration.from_runnable_config(config)
        if not configurable.allow_clarification:
            return Command(goto="write_research_brief")

        messages = state["messages"]
        model_config = {
            "model": configurable.research_model,
            "max_tokens": configurable.research_model_max_tokens,
            "api_key": get_api_key_for_model(configurable.research_model, config),
            "tags": ["langsmith:nostream"]
        }

        model = configurable_model.with_structured_output(ClarifyWithUser).with_retry(
            stop_after_attempt=configurable.max_structured_output_retries
        ).with_config(model_config)

        response = await model.ainvoke([
            HumanMessage(content=clarify_with_user_instructions.format(
                messages=get_buffer_string(messages),
                date=get_today_str()
            ))
        ])

        if response.need_clarification:
            # Instead of going to END, we'll go to final_report_generation with a clarification message
            return Command(goto="final_report_generation", update={
                "messages": [AIMessage(content=response.question)],
                "final_report": f"Clarification needed: {response.question}",
                "research_brief": "Clarification requested",
                "notes": [],
                "search_count": 0
            })
        else:
            # Don't update research_brief here, let write_research_brief handle it
            return Command(goto="write_research_brief", update={"messages": [AIMessage(content=response.verification)]})

    async def write_research_brief(self, state: AgentState, config: RunnableConfig) -> Command[
        Literal["research_supervisor"]]:
        """Transform user messages into a research brief."""
        configurable = Configuration.from_runnable_config(config)
        research_model_config = {
            "model": configurable.research_model,
            "max_tokens": configurable.research_model_max_tokens,
            "api_key": get_api_key_for_model(configurable.research_model, config),
            "tags": ["langsmith:nostream"]
        }

        research_model = configurable_model.with_structured_output(ResearchQuestion).with_retry(
            stop_after_attempt=configurable.max_structured_output_retries
        ).with_config(research_model_config)

        response = await research_model.ainvoke([
            HumanMessage(content=transform_messages_into_research_topic_prompt.format(
                messages=get_buffer_string(state.get("messages", [])),
                date=get_today_str()
            ))
        ])

        return Command(
            goto="research_supervisor",
            update={
                "research_brief": response.research_brief,
                "supervisor_messages": {
                    "type": "override",
                    "value": [
                        SystemMessage(content=lead_researcher_prompt.format(
                            date=get_today_str(),
                            max_concurrent_research_units=configurable.max_concurrent_research_units
                        )),
                        HumanMessage(content=response.research_brief)
                    ]
                }
            }
        )

    async def supervisor(self, state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor_tools"]]:
        """Supervisor node that coordinates research activities."""
        configurable = Configuration.from_runnable_config(config)
        research_model_config = {
            "model": configurable.research_model,
            "max_tokens": configurable.research_model_max_tokens,
            "api_key": get_api_key_for_model(configurable.research_model, config),
            "tags": ["langsmith:nostream"]
        }

        lead_researcher_tools = [ConductResearch, ResearchComplete]
        research_model = configurable_model.bind_tools(lead_researcher_tools).with_retry(
            stop_after_attempt=configurable.max_structured_output_retries
        ).with_config(research_model_config)

        supervisor_messages = state.get("supervisor_messages", [])
        response = await research_model.ainvoke(supervisor_messages)

        return Command(
            goto="supervisor_tools",
            update={
                "supervisor_messages": [response],
                "research_iterations": state.get("research_iterations", 0) + 1
            }
        )

    async def supervisor_tools(self, state: SupervisorState, config: RunnableConfig) -> Command[
        Literal["supervisor", "__end__"]]:
        """Handle supervisor tool calls and coordinate research execution."""
        configurable = Configuration.from_runnable_config(config)
        supervisor_messages = state.get("supervisor_messages", [])
        research_iterations = state.get("research_iterations", 0)
        most_recent_message = supervisor_messages[-1]

        # Debug logging
        logger.info(f"Supervisor tools called - Iteration: {research_iterations}")
        logger.info(f"Search API configured: {configurable.search_api}")
        logger.info(f"Max iterations: {configurable.max_researcher_iterations}")
        
        if most_recent_message.tool_calls:
            logger.info(f"Tool calls found: {[tc['name'] for tc in most_recent_message.tool_calls]}")
        else:
            logger.warning("No tool calls found in supervisor message")

        # Exit Criteria
        exceeded_allowed_iterations = research_iterations >= configurable.max_researcher_iterations
        no_tool_calls = not most_recent_message.tool_calls
        research_complete_tool_call = any(
            tool_call["name"] == "ResearchComplete" for tool_call in most_recent_message.tool_calls
        )

        logger.info(f"Exit criteria check:")
        logger.info(f"  - exceeded_allowed_iterations: {exceeded_allowed_iterations} (iterations: {research_iterations}, max: {configurable.max_researcher_iterations})")
        logger.info(f"  - no_tool_calls: {no_tool_calls}")
        logger.info(f"  - research_complete_tool_call: {research_complete_tool_call}")

        if exceeded_allowed_iterations or no_tool_calls or research_complete_tool_call:
            logger.info("Exit criteria met, ending supervisor execution")
            return Command(
                goto=END,
                update={
                    "notes": get_notes_from_tool_calls(supervisor_messages),
                    "research_brief": state.get("research_brief", "")
                }
            )

        logger.info("Exit criteria not met, proceeding with research execution")

        # Conduct research and gather results
        try:
            all_conduct_research_calls = [
                tool_call for tool_call in most_recent_message.tool_calls
                if tool_call["name"] == "ConductResearch"
            ]
            conduct_research_calls = all_conduct_research_calls[:configurable.max_concurrent_research_units]
            overflow_conduct_research_calls = all_conduct_research_calls[configurable.max_concurrent_research_units:]

            researcher_system_prompt = research_system_prompt.format(
                mcp_prompt=configurable.mcp_prompt or "",
                date=get_today_str()
            )

            coros = [
                self.researcher_subgraph.ainvoke({
                    "researcher_messages": [
                        SystemMessage(content=researcher_system_prompt),
                        HumanMessage(content=tool_call["args"]["research_topic"])
                    ],
                    "research_topic": tool_call["args"]["research_topic"],
                    "search_count": 0  # Initialize search count for each researcher
                }, config)
                for tool_call in conduct_research_calls
            ]

            logger.info(f"Invoking {len(coros)} researcher subgraphs...")
            try:
                tool_results = await asyncio.gather(*coros, return_exceptions=True)
                logger.info(f"Researcher subgraphs completed, got {len(tool_results)} results")
                
                # Check for exceptions in results
                for i, result in enumerate(tool_results):
                    if isinstance(result, Exception):
                        logger.error(f"Researcher subgraph {i} failed with exception: {result}")
                        # Replace exception with a default result
                        tool_results[i] = {
                            "compressed_research": f"Error in researcher subgraph: {str(result)}",
                            "raw_notes": [],
                            "search_count": 0
                        }
            except Exception as e:
                logger.error(f"Error gathering researcher subgraph results: {e}")
                # Create fallback results
                tool_results = [{
                    "compressed_research": f"Error gathering results: {str(e)}",
                    "raw_notes": [],
                    "search_count": 0
                } for _ in conduct_research_calls]

            # Debug: Log the structure of tool_results and conduct_research_calls
            for i, (observation, tool_call) in enumerate(zip(tool_results, conduct_research_calls)):
                if isinstance(observation, dict):
                    logger.info(f"Result {i}: observation keys: {list(observation.keys())}")
                else:
                    logger.info(f"Result {i}: observation is not a dict: {type(observation)}")
                
                if isinstance(tool_call, dict):
                    logger.info(f"Result {i}: tool_call keys: {list(tool_call.keys())}")
                else:
                    logger.info(f"Result {i}: tool_call is not a dict: {type(tool_call)}")

            tool_messages = []
            for observation, tool_call in zip(tool_results, conduct_research_calls):
                try:
                    # Ensure tool_call has the expected structure
                    if not isinstance(tool_call, dict) or "name" not in tool_call:
                        logger.error(f"Invalid tool_call structure: {tool_call}")
                        continue
                    
                    # Ensure observation has the expected structure
                    if not isinstance(observation, dict):
                        logger.error(f"Invalid observation structure: {observation}")
                        compressed_research = "Error: Invalid observation structure"
                    else:
                        compressed_research = observation.get("compressed_research",
                                                "Error synthesizing research report: Maximum retries exceeded")
                    
                    tool_message = ToolMessage(
                        content=compressed_research,
                        name=tool_call["name"],
                        tool_call_id=tool_call.get("id", f"call_{len(tool_messages)}")
                    )
                    tool_messages.append(tool_message)
                except Exception as e:
                    logger.error(f"Error creating ToolMessage: {e}")
                    logger.error(f"observation: {observation}")
                    logger.error(f"tool_call: {tool_call}")
                    # Create a fallback tool message
                    tool_messages.append(ToolMessage(
                        content="Error processing research results",
                        name="ConductResearch",
                        tool_call_id=f"error_call_{len(tool_messages)}"
                    ))

            # Handle overflow research calls
            for overflow_conduct_research_call in overflow_conduct_research_calls:
                tool_messages.append(ToolMessage(
                    content=f"Error: Did not run this research as you have already exceeded the maximum number of concurrent research units. Please try again with {configurable.max_concurrent_research_units} or fewer research units.",
                    name="ConductResearch",
                    tool_call_id=overflow_conduct_research_call["id"]
                ))

            raw_notes_concat = "\n".join([
                "\n".join(observation.get("raw_notes", [])) for observation in tool_results
            ])

            # Aggregate search count from all researcher results
            total_search_count = sum(observation.get("search_count", 0) for observation in tool_results)
            current_search_count = state.get("search_count", 0)
            updated_search_count = current_search_count + total_search_count
            
            logger.info(f"Aggregated search count: {total_search_count} from researchers, total: {updated_search_count}")

            return Command(
                goto="supervisor",
                update={
                    "supervisor_messages": tool_messages,
                    "raw_notes": [raw_notes_concat],
                    "search_count": updated_search_count
                }
            )

        except Exception as e:
            if is_token_limit_exceeded(e, configurable.research_model):
                logger.error(f"Token limit exceeded while reflecting: {e}")
            else:
                logger.error(f"Other error in reflection phase: {e}")

            return Command(
                goto=END,
                update={
                    "notes": get_notes_from_tool_calls(supervisor_messages),
                    "research_brief": state.get("research_brief", ""),
                    "search_count": state.get("search_count", 0)  # Preserve search count on error
                }
            )

    async def researcher(self, state: ResearcherState, config: RunnableConfig) -> Command[Literal["researcher_tools"]]:
        """Individual researcher node that conducts specific research tasks."""
        configurable = Configuration.from_runnable_config(config)
        researcher_messages = state.get("researcher_messages", [])
        tools = await get_all_tools(config)

        logger.info(f"Researcher node called with topic: {state.get('research_topic', 'unknown')}")
        # logger.info(f"Available tools: {[t.name for t in tools]}")

        research_model_config = {
            "model": configurable.research_model,
            "max_tokens": configurable.research_model_max_tokens,
            "api_key": get_api_key_for_model(configurable.research_model, config),
            "tags": ["langsmith:nostream"]
        }

        research_model = configurable_model.bind_tools(tools).with_retry(
            stop_after_attempt=configurable.max_structured_output_retries
        ).with_config(research_model_config)

        response = await research_model.ainvoke(researcher_messages)

        return Command(
            goto="researcher_tools",
            update={
                "researcher_messages": [response],
                "tool_call_iterations": state.get("tool_call_iterations", 0) + 1
            }
        )

    async def researcher_tools(self, state: ResearcherState, config: RunnableConfig) -> Command[
        Literal["researcher", "compress_research"]]:
        """Handle researcher tool calls and determine next steps."""
        configurable = Configuration.from_runnable_config(config)
        researcher_messages = state.get("researcher_messages", [])
        most_recent_message = researcher_messages[-1]

        # Debug logging
        logger.info(f"Researcher tools called - Tool call iteration: {state.get('tool_call_iterations', 0)}")
        logger.info(f"Search API configured: {configurable.search_api}")

        # Early Exit Criteria: No tool calls (or native web search calls) were made by the researcher
        if not most_recent_message.tool_calls and not (openai_websearch_called(most_recent_message) or anthropic_websearch_called(most_recent_message)):
            return Command(goto="compress_research")

        # Otherwise, execute tools and gather results.
        tools = await get_all_tools(config)
        tools_by_name = {}
        for tool in tools:
            if hasattr(tool, "name"):
                tools_by_name[tool.name] = tool
            elif hasattr(tool, "__name__"):
                tools_by_name[tool.__name__] = tool
            else:
                logger.warning(f"Tool without name attribute: {tool}")
                continue
        
        tool_calls = most_recent_message.tool_calls
        
        # Track search operations
        search_count = state.get("search_count", 0)
        for tool_call in tool_calls:
            if tool_call["name"] in ["tavily_search", "serper_search"]:
                search_count += 1
                logger.info(f"Search operation #{search_count} executed: {tool_call['name']}")

        coros = []
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            if tool_name in tools_by_name:
                coros.append(self.execute_tool_safely(tools_by_name[tool_name], tool_call["args"], config))
            else:
                logger.error(f"Tool '{tool_name}' not found in available tools: {list(tools_by_name.keys())}")
                coros.append(asyncio.create_task(asyncio.sleep(0)))  # Placeholder for missing tool
        
        observations = await asyncio.gather(*coros, return_exceptions=True)
        
        # Handle any exceptions in observations
        processed_observations = []
        for i, observation in enumerate(observations):
            if isinstance(observation, Exception):
                logger.error(f"Tool execution {i} failed with exception: {observation}")
                processed_observations.append(f"Error executing tool: {str(observation)}")
            else:
                processed_observations.append(observation)
        
        tool_outputs = [ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        ) for observation, tool_call in zip(processed_observations, tool_calls)]

        # Late Exit Criteria: We have exceeded our max guardrail tool call iterations or the most recent message contains a ResearchComplete tool call
        # These are late exit criteria because we need to add ToolMessages
        if state.get("tool_call_iterations", 0) >= configurable.max_react_tool_calls or any(tool_call["name"] == "ResearchComplete" for tool_call in most_recent_message.tool_calls):
            return Command(
                goto="compress_research",
                update={
                    "researcher_messages": tool_outputs,
                    "search_count": search_count
                }
            )
        return Command(
            goto="researcher",
            update={
                "researcher_messages": tool_outputs,
                "search_count": search_count
            }
        )

    async def execute_tool_safely(self, tool, args, config):
        """Execute a tool safely with error handling."""
        try:
            return await tool.ainvoke(args, config)
        except Exception as e:
            return f"Error executing tool: {str(e)}"

    async def compress_research(self, state: ResearcherState, config: RunnableConfig):
        """Compress and synthesize research findings."""
        configurable = Configuration.from_runnable_config(config)
        synthesis_attempts = 0
        synthesizer_model = configurable_model.with_config({
            "model": configurable.compression_model,
            "max_tokens": configurable.compression_model_max_tokens,
            "api_key": get_api_key_for_model(configurable.compression_model, config),
            "tags": ["langsmith:nostream"]
        })
        researcher_messages = state.get("researcher_messages", [])
        # Update the system prompt to now focus on compression rather than research.
        researcher_messages[0] = SystemMessage(content=compress_research_system_prompt.format(date=get_today_str()))
        researcher_messages.append(HumanMessage(content=compress_research_simple_human_message))
        
        while synthesis_attempts < 3:
            try:
                response = await synthesizer_model.ainvoke(researcher_messages)
                return {
                    "compressed_research": str(response.content),
                    "raw_notes": ["\n".join([str(m.content) for m in filter_messages(researcher_messages, include_types=["tool", "ai"])])],
                    "search_count": state.get("search_count", 0)
                }
            except Exception as e:
                synthesis_attempts += 1
                if is_token_limit_exceeded(e, configurable.research_model):
                    researcher_messages = remove_up_to_last_ai_message(researcher_messages)
                    logger.warning(f"Token limit exceeded while synthesizing: {e}. Pruning the messages to try again.")
                    continue         
                logger.error(f"Error synthesizing research report: {e}")
        
        return {
            "compressed_research": "Error synthesizing research report: Maximum retries exceeded",
            "raw_notes": ["\n".join([str(m.content) for m in filter_messages(researcher_messages, include_types=["tool", "ai"])])],
            "search_count": state.get("search_count", 0)
        }

    async def final_report_generation(self, state: AgentState, config: RunnableConfig):
        """Generate the final comprehensive research report."""
        configurable = Configuration.from_runnable_config(config)
        notes = state.get("notes", [])
        research_brief = state.get("research_brief", "")

        final_report_model_config = {
            "model": configurable.final_report_model,
            "max_tokens": configurable.final_report_model_max_tokens,
            "api_key": get_api_key_for_model(configurable.final_report_model, config),
            "tags": ["langsmith:nostream"]
        }

        final_report_model = configurable_model.with_retry(
            stop_after_attempt=configurable.max_structured_output_retries
        ).with_config(final_report_model_config)

        try:
            final_report = await final_report_model.ainvoke([
                HumanMessage(content=final_report_generation_prompt.format(
                    research_brief=research_brief,
                    notes="\n".join(notes),
                    date=get_today_str()
                ))
            ])

            return {
                "final_report": final_report.content,
                "research_brief": research_brief,
                "notes": notes,
                "search_count": state.get("search_count", 0)
            }

        except Exception as e:
            logger.error(f"Error generating final report: {e}")
            return {
                "final_report": f"Error generating final report: {str(e)}",
                "research_brief": research_brief,
                "notes": notes,
                "search_count": state.get("search_count", 0)
            }

    def build_graphs(self):
        """Build the research graphs."""
        # Build supervisor subgraph
        supervisor_builder = StateGraph(SupervisorState, config_schema=Configuration)
        supervisor_builder.add_node("supervisor", self.supervisor)
        supervisor_builder.add_node("supervisor_tools", self.supervisor_tools)
        supervisor_builder.add_edge(START, "supervisor")
        self.supervisor_subgraph = supervisor_builder.compile()

        # Build researcher subgraph
        researcher_builder = StateGraph(ResearcherState, output=ResearcherOutputState, config_schema=Configuration)
        researcher_builder.add_node("researcher", self.researcher)
        researcher_builder.add_node("researcher_tools", self.researcher_tools)
        researcher_builder.add_node("compress_research", self.compress_research)
        researcher_builder.add_edge(START, "researcher")
        researcher_builder.add_edge("compress_research", END)
        self.researcher_subgraph = researcher_builder.compile()

        # Build main graph
        main_builder = StateGraph(AgentState, input=AgentInputState, config_schema=Configuration)
        main_builder.add_node("clarify_with_user", self.clarify_with_user)
        main_builder.add_node("write_research_brief", self.write_research_brief)
        main_builder.add_node("research_supervisor", self.supervisor_subgraph)
        main_builder.add_node("final_report_generation", self.final_report_generation)
        main_builder.add_edge(START, "clarify_with_user")
        main_builder.add_edge("clarify_with_user", "write_research_brief")
        main_builder.add_edge("clarify_with_user", "final_report_generation")
        main_builder.add_edge("write_research_brief", "research_supervisor")
        main_builder.add_edge("research_supervisor", "final_report_generation")
        main_builder.add_edge("final_report_generation", END)

        self.main_graph = main_builder.compile()


async def _main_async(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async main function for the Deep Research Agent.
    
    Args:
        input_data: Dictionary containing:
            - research_query: The research question or topic to investigate
            - research_depth: Level of research depth (shallow, moderate, deep, comprehensive)
            - max_iterations: Maximum number of research iterations
            - max_concurrent_research: Maximum concurrent research units
            - search_api: Search API to use (tavily, serper, openai, anthropic, none)
            - include_sources: Whether to include source citations
            - research_model: Model for conducting research
            - compression_model: Model for compressing findings
            - final_report_model: Model for final report generation
            - allow_clarification: Whether to ask clarifying questions
            - mcp_config: MCP server configuration (optional)
    
    Returns:
        Dictionary containing comprehensive research report and findings
    """

    # Initialize agent
    agent = DeepResearchAgent()

    # Extract and validate parameters
    research_query = input_data.get('research_query', '').strip()
    if not research_query:
        return {'error': 'Research query is required'}

    # Build configuration from input
    config_data = {
        'research_model': input_data.get('research_model', 'openai:gpt-4o'),
        'research_model_max_tokens': int(input_data.get('research_model_max_tokens', 10000)),
        'compression_model': input_data.get('compression_model', 'openai:gpt-4o-mini'),
        'compression_model_max_tokens': int(input_data.get('compression_model_max_tokens', 8192)),
        'final_report_model': input_data.get('final_report_model', 'openai:gpt-4o'),
        'final_report_model_max_tokens': int(input_data.get('final_report_model_max_tokens', 10000)),
        'max_researcher_iterations': int(input_data.get('max_iterations', 3)),
        'max_concurrent_research_units': int(input_data.get('max_concurrent_research', 5)),
        'max_react_tool_calls': int(input_data.get('max_tool_calls', 5)),
        'allow_clarification': agent.ensure_boolean(input_data.get('allow_clarification', False)),
        'search_api': input_data.get('search_api', 'serper'),
        'max_structured_output_retries': int(input_data.get('max_retries', 3))
    }

    # Handle MCP configuration if provided
    mcp_config = input_data.get('mcp_config')
    if mcp_config:
        config_data['mcp_config'] = mcp_config

    # Create configuration object
    config = Configuration(**config_data)
    agent.config = config

    # Build the research graphs
    agent.build_graphs()

    logger.info(f"Starting deep research on: {research_query}")

    try:
        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=research_query)],
            "supervisor_messages": [],
            "research_brief": "",
            "raw_notes": [],
            "notes": [],
            "final_report": "",
            "search_count": 0  # Track number of search operations
        }

        # Create runnable config
        runnable_config = RunnableConfig(
            configurable=config_data,
            metadata=context.get('metadata', {}),
            tags=["deep_research_agent"]
        )

        # Execute the research
        start_time = time.time()
        result = await agent.main_graph.ainvoke(initial_state, runnable_config)
        execution_time = time.time() - start_time

        # Extract final report and notes
        final_report = result.get('final_report', '')
        research_brief = result.get('research_brief', '')
        notes = result.get('notes', [])
        search_count = result.get('search_count', 0)

        # Prepare response
        response = {
            'status': 'success',
            'research_query': research_query,
            'research_brief': research_brief,
            'final_report': final_report,
            'execution_time': execution_time,
            'research_iterations': result.get('research_iterations', 0),
            'search_operations_count': search_count,
            'notes_count': len(notes),
            'generated_at': datetime.now().isoformat()
        }

        # Include source information if requested
        if agent.ensure_boolean(input_data.get('include_sources', True)):
            response['sources'] = notes

        logger.info(f"Research completed in {execution_time:.2f} seconds")
        return response

    except Exception as e:
        logger.error(f"Error in deep research: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'research_query': research_query
        }


def execute(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function for the Deep Research Agent.
    
    This is a synchronous wrapper around the async implementation.
    
    Args:
        input_data: Dictionary containing research parameters
        context: Dictionary containing execution context
    
    Returns:
        Dictionary containing comprehensive research report and findings
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
            'research_query': input_data.get('research_query', 'Unknown')
        }


if __name__ == "__main__":
    # Test the agent
    test_input = {
        'research_query': 'Who is George Kour?',
        'research_depth': 'moderate',
        'max_iterations': 2,
        'max_concurrent_research': 3,
        'search_api': 'serper',
        'include_sources': True,
        'max_concurrent_research_units': 3,
    }

    result = execute(test_input, {})
    print(json.dumps(result, indent=2))
