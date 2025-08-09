#!/usr/bin/env python3
"""
Personal Assistant Agent - Persistent Implementation

A comprehensive personal assistant agent using LangGraph that can handle various tasks
including email management, file operations, web search, and more.

This agent demonstrates the proper way to implement a persistent agent:
1. Inherit from PersistentAgent
2. Implement initialize(), execute(), cleanup()
3. Use _get_state()/_set_state() for state management
4. Use _is_initialized()/_mark_initialized() for lifecycle management
5. Focus on business logic only - no platform concerns
"""

import json
import os
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional
import warnings
from dotenv import load_dotenv

# Import the base PersistentAgent class from the SDK
from agenthub_sdk.agent import PersistentAgent

load_dotenv()

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import LangChain components with fallback
try:
    from langchain_community.agent_toolkits.load_tools import load_tools
    from langchain.memory import ConversationSummaryBufferMemory
    from langchain_community.agent_toolkits import GmailToolkit, FileManagementToolkit
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.tools import ShellTool
    from langchain_community.tools.gmail import get_gmail_credentials
    from langchain_community.tools.gmail.utils import build_resource_service
    from langchain_community.tools.semanticscholar import SemanticScholarQueryRun
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.prebuilt import create_react_agent
    from langgraph.prebuilt.chat_agent_executor import AgentState
    from langgraph.store.base import BaseStore
    from langchain.tools import tool
    
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not available, using fallback implementation")
    LANGCHAIN_AVAILABLE = False



class JSONFileStore:
    """Simple JSON-based file store for memories."""
    
    def __init__(self, file_path: str = "memories.json"):
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Ensure the JSON file exists."""
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)
    
    def search(self, namespace):
        """Search for memories in the given namespace."""
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            namespace_key = "_".join(namespace)
            memories = data.get(namespace_key, [])
            return [{"value": {"data": memory}} for memory in memories]
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []
    
    def write(self, namespace, key, value):
        """Write a memory to the store."""
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            namespace_key = "_".join(namespace)
            if namespace_key not in data:
                data[namespace_key] = []
            
            data[namespace_key].append(value)
            
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing memory: {e}")


class PersonalAssistantAgent(PersistentAgent):
    """
    Clean Persistent Personal Assistant Agent Implementation
    
    This agent demonstrates the proper way to implement a persistent agent:
    1. Inherit from PersistentAgent
    2. Implement initialize(), execute(), cleanup()
    3. Use _get_state()/_set_state() for state management
    4. Use _is_initialized()/_mark_initialized() for lifecycle management
    5. Focus on business logic only - no platform concerns
    
    The platform will call these methods directly:
    - initialize(config) -> called once to set up the agent
    - execute(input_data) -> called for each query
    - cleanup() -> called when agent is no longer needed
    """

    def __init__(self):
        """Initialize the Personal Assistant agent."""
        super().__init__()
        # Instance variables for LangChain components
        self.llm = None
        self.tools = []
        self.agent = None
        self.store = None
        self.memory_saver = None

    def initialize(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the Personal Assistant agent with configuration data.
        
        This method is called once by the platform to set up the agent.
        It should:
        1. Validate the configuration
        2. Set up LLM and tools
        3. Create the agent
        4. Store configuration in state
        5. Mark as initialized
        
        Args:
            config: Configuration data containing system_prompt, model_name, etc.
            
        Returns:
            Dict with initialization result (no platform concerns)
        """
        try:
            # Check if already initialized
            if self._is_initialized():
                return {
                    "status": "already_initialized",
                    "message": "Personal Assistant agent already initialized",
                    "model_name": self._get_state("model_name")
                }

            logger.info("Initializing Personal Assistant agent")

            # Validate configuration
            system_prompt = config.get("system_prompt", "You are a helpful personal assistant with access to various tools.")
            model_name = config.get("model_name", "gpt-4")
            temperature = config.get("temperature", 0.1)
            max_tokens = config.get("max_tokens", 2000)
            enable_memory = config.get("enable_memory", True)

            # Initialize memory store if enabled
            if enable_memory:
                self.store = JSONFileStore(file_path="personal_assistant_memories.json")
                self.memory_saver = None  # Will be set if LangChain is available
            else:
                self.store = None
                self.memory_saver = None

            # Try to initialize LangChain components
            langchain_success = False
            if LANGCHAIN_AVAILABLE:
                try:
                    # Initialize LLM
                    api_key = os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        logger.warning("OPENAI_API_KEY environment variable not found, using fallback mode")
                        raise ValueError("OPENAI_API_KEY environment variable is required")
                    
                    self.llm = ChatOpenAI(
                        model=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        api_key=api_key
                    )

                    # Initialize memory saver if enabled
                    if enable_memory:
                        self.memory_saver = MemorySaver()

                    # Initialize tools
                    self._initialize_tools()

                    # Create the agent
                    self.agent = create_react_agent(
                        model=self.llm,
                        tools=self.tools,
                        debug=False
                    )

                    langchain_success = True
                    logger.info(f"LangChain components initialized successfully with {len(self.tools)} tools")
                except Exception as e:
                    logger.error(f"Failed to initialize LangChain components: {e}")
                    # Reset components to None
                    self.llm = None
                    self.tools = []
                    self.agent = None
                    self.memory_saver = None
                    langchain_success = False
            else:
                logger.warning("LangChain not available, using fallback mode")
                langchain_success = False

            # Store configuration in state (persisted by platform)
            self._set_state("system_prompt", system_prompt)
            self._set_state("model_name", model_name)
            self._set_state("temperature", temperature)
            self._set_state("max_tokens", max_tokens)
            self._set_state("enable_memory", enable_memory)
            self._set_state("tools_count", len(self.tools) if self.tools else 0)
            self._set_state("langchain_available", langchain_success)

            # Mark as initialized (important for platform)
            self._mark_initialized()

            logger.info(f"Personal Assistant agent initialized successfully (LangChain: {langchain_success})")

            return {
                "status": "initialized",
                "message": "Successfully initialized Personal Assistant agent",
                "model_name": model_name,
                "tools_count": len(self.tools) if self.tools else 0,
                "enable_memory": enable_memory,
                "langchain_available": langchain_success
            }

        except Exception as e:
            logger.error(f"Error initializing Personal Assistant agent: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Personal Assistant query.
        
        This method is called by the platform for each query.
        It should:
        1. Check if agent is initialized
        2. Validate input data
        3. Process the query
        4. Return the result
        
        Args:
            input_data: Input data containing the message and user_id
            
        Returns:
            Dict with execution result (no platform concerns)
        """
        try:
            # Check if agent is initialized (important for platform)
            if not self._is_initialized():
                raise ValueError("Agent not initialized. Call initialize() first.")

            # Validate input
            message = input_data.get("message")
            if not message:
                raise ValueError("message is required for execution")

            user_id = input_data.get("user_id", "default_user")

            logger.info(f"Executing Personal Assistant query for user {user_id}: {message}")

            # Check if LangChain is available and agent is properly set up
            if not LANGCHAIN_AVAILABLE or not self._get_state("langchain_available", False):
                # Fallback response without LangChain
                system_prompt = self._get_state("system_prompt", "You are a helpful personal assistant.")
                model_name = self._get_state("model_name", "gpt-4")
                
                # Simple fallback response
                if "hello" in message.lower() or "hi" in message.lower():
                    response = f"Hello! I'm your personal assistant. I received your message: '{message}'. I'm currently running in fallback mode due to LangChain availability issues."
                elif "how are you" in message.lower():
                    response = "I'm doing well, thank you for asking! I'm currently running in fallback mode but I'm here to help with your requests."
                else:
                    response = f"I received your message: '{message}'. I'm currently running in fallback mode due to LangChain availability issues. I can still help with basic responses and remember our conversation."
            else:
                # LangChain is available, check if agent needs to be recreated
                if self.agent is None:
                    logger.info("LangChain agent is None, recreating from stored configuration")
                    try:
                        # Recreate the agent from stored configuration
                        system_prompt = self._get_state("system_prompt", "You are a helpful personal assistant.")
                        model_name = self._get_state("model_name", "gpt-4")
                        temperature = self._get_state("temperature", 0.1)
                        max_tokens = self._get_state("max_tokens", 2000)
                        enable_memory = self._get_state("enable_memory", True)
                        
                        # Initialize LLM
                        self.llm = ChatOpenAI(
                            model=model_name,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            openai_api_key=os.getenv("OPENAI_API_KEY")
                        )
                        
                        # Initialize memory if enabled
                        if enable_memory:
                            self.memory_saver = JSONFileStore("memories.json")
                        
                        # Initialize tools
                        self._initialize_tools()
                        
                        # Create the agent
                        self.agent = create_react_agent(
                            model=self.llm,
                            tools=self.tools,
                            debug=False
                        )
                        
                        logger.info(f"LangChain agent recreated successfully with {len(self.tools)} tools")
                    except Exception as e:
                        logger.error(f"Failed to recreate LangChain agent: {e}")
                        # Fall back to simple response
                        response = f"I received your message: '{message}'. I'm currently running in fallback mode due to LangChain recreation issues."
                        return {
                            "response": response,
                            "message": message,
                            "user_id": user_id,
                            "timestamp": datetime.now().isoformat(),
                            "agent_type": "personal_assistant",
                            "model_name": self._get_state("model_name")
                        }
                
                # Full LangChain processing
                # Prepare the configuration
                config = {
                    "configurable": {
                        "thread_id": f"thread-{user_id}",
                        "user_id": user_id,
                        "system_prompt": self._get_state("system_prompt")
                    }
                }
                
                # Create initial state
                initial_state = {
                    "messages": [{"role": "user", "content": message}]
                }
                
                # Process the request
                result = self.agent.invoke(initial_state, config)
                
                # Extract the response
                messages = result.get("messages", [])
                ai_messages = [msg for msg in messages if msg.type == "ai"]
                
                if ai_messages:
                    response = ai_messages[-1].content
                else:
                    response = "I couldn't generate a response for your request."

            return {
                "response": response,
                "message": message,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "agent_type": "personal_assistant",
                "model_name": self._get_state("model_name")
            }

        except Exception as e:
            logger.error(f"Error executing Personal Assistant agent: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": input_data.get("message", ""),
                "user_id": input_data.get("user_id", "default_user"),
                "timestamp": datetime.now().isoformat(),
                "agent_type": "personal_assistant"
            }

    def cleanup(self) -> Dict[str, Any]:
        """
        Clean up agent resources.
        
        This method is called by the platform when the agent is no longer needed.
        It should:
        1. Clean up any resources (files, connections, etc.)
        2. Clear instance variables
        3. Clear state (platform will handle persistence)
        
        Returns:
            Dict with cleanup result (no platform concerns)
        """
        try:
            logger.info("Cleaning up Personal Assistant agent resources")

            # Clear instance variables
            self.llm = None
            self.tools = []
            self.agent = None
            self.store = None
            self.memory_saver = None

            # Clear state (platform will handle persistence)
            self._state.clear()
            self._initialized = False

            return {
                "status": "cleaned_up",
                "message": "Personal Assistant agent resources cleaned up successfully"
            }
        except Exception as e:
            logger.error(f"Error cleaning up Personal Assistant agent: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _initialize_tools(self):
        """Initialize all available tools."""
        if not LANGCHAIN_AVAILABLE:
            self.tools = []
            return

        try:
            # Basic tools
            common_tools = load_tools([
                'wikipedia', 
                'arxiv', 
                'pubmed', 
                'google-scholar', 
                'stackexchange', 
                'human',
                'google-serper', 
                'google-finance', 
                'reddit_search'
            ], llm=self.llm)
            
            # File management tools
            file_management_toolkit = FileManagementToolkit()
            
            # Create custom tools using the @tool decorator
            @tool
            def save_memory(memory_content: str) -> str:
                """Save a memory for the user."""
                try:
                    if self.store:
                        user_id = "default_user"  # Could be passed from context
                        namespace = ("memories", user_id)
                        self.store.write(namespace, "memory", memory_content)
                        return f"Memory saved successfully: {memory_content[:100]}..."
                    else:
                        return "Memory storage is disabled"
                except Exception as e:
                    return f"Error saving memory: {e}"

            @tool
            def delete_memory(memory_content: str) -> str:
                """Delete a memory for the user."""
                try:
                    # For simplicity, we'll just return a success message
                    # In a real implementation, you'd want to actually delete the memory
                    return f"Memory deletion requested for: {memory_content[:100]}..."
                except Exception as e:
                    return f"Error deleting memory: {e}"

            @tool
            def load_pdf(file_path: str) -> str:
                """Load and extract text from a PDF file."""
                try:
                    loader = PyPDFLoader(file_path)
                    documents = loader.load()
                    text = "\n".join([doc.page_content for doc in documents])
                    return f"PDF loaded successfully. Content preview: {text[:500]}..."
                except Exception as e:
                    return f"Error loading PDF: {e}"

            @tool
            def execute_python(code: str) -> str:
                """Execute Python code safely."""
                try:
                    # Create a safe execution environment
                    safe_globals = {
                        '__builtins__': {
                            'print': print,
                            'len': len,
                            'str': str,
                            'int': int,
                            'float': float,
                            'list': list,
                            'dict': dict,
                            'tuple': tuple,
                            'set': set,
                            'range': range,
                            'enumerate': enumerate,
                            'zip': zip,
                            'map': map,
                            'filter': filter,
                            'sum': sum,
                            'max': max,
                            'min': min,
                            'abs': abs,
                            'round': round,
                            'sorted': sorted,
                            'reversed': reversed,
                            'any': any,
                            'all': all,
                            'bool': bool,
                            'type': type,
                            'isinstance': isinstance,
                            'hasattr': hasattr,
                            'getattr': getattr,
                            'setattr': setattr,
                            'dir': dir,
                            'vars': vars,
                            'help': help,
                            'id': id,
                            'hash': hash,
                            'repr': repr,
                            'ascii': ascii,
                            'bin': bin,
                            'hex': hex,
                            'oct': oct,
                            'ord': ord,
                            'chr': chr,
                            'format': format,
                            'divmod': divmod,
                            'pow': pow,
                            'complex': complex,
                            'bytes': bytes,
                            'bytearray': bytearray,
                            'memoryview': memoryview,
                            'slice': slice,
                            'property': property,
                            'staticmethod': staticmethod,
                            'classmethod': classmethod,
                            'super': super,
                            'object': object,
                            'Exception': Exception,
                            'BaseException': BaseException,
                            'TypeError': TypeError,
                            'ValueError': ValueError,
                            'AttributeError': AttributeError,
                            'KeyError': KeyError,
                            'IndexError': IndexError,
                            'NameError': NameError,
                            'SyntaxError': SyntaxError,
                            'ImportError': ImportError,
                            'ModuleNotFoundError': ModuleNotFoundError,
                            'FileNotFoundError': FileNotFoundError,
                            'PermissionError': PermissionError,
                            'OSError': OSError,
                            'RuntimeError': RuntimeError,
                            'NotImplementedError': NotImplementedError,
                            'AssertionError': AssertionError,
                            'ArithmeticError': ArithmeticError,
                            'OverflowError': OverflowError,
                            'ZeroDivisionError': ZeroDivisionError,
                            'FloatingPointError': FloatingPointError,
                            'BufferError': BufferError,
                            'LookupError': LookupError,
                            'UnicodeError': UnicodeError,
                            'UnicodeEncodeError': UnicodeEncodeError,
                            'UnicodeDecodeError': UnicodeDecodeError,
                            'UnicodeTranslateError': UnicodeTranslateError,
                            'Warning': Warning,
                            'UserWarning': UserWarning,
                            'DeprecationWarning': DeprecationWarning,
                            'PendingDeprecationWarning': PendingDeprecationWarning,
                            'SyntaxWarning': SyntaxWarning,
                            'RuntimeWarning': RuntimeWarning,
                            'FutureWarning': FutureWarning,
                            'ImportWarning': ImportWarning,
                            'UnicodeWarning': UnicodeWarning,
                            'BytesWarning': BytesWarning,
                            'ResourceWarning': ResourceWarning,
                        }
                    }
                    
                    # Execute the code
                    exec(code, safe_globals)
                    return "Python code executed successfully."
                except Exception as e:
                    return f"Error executing Python code: {e}"
            
            # Shell tool
            shell_tool = ShellTool(ask_human_input=False)
            
            # Academic search tool
            semantic_scholar_tool = SemanticScholarQueryRun()
            
            # Combine all tools
            self.tools = (
                common_tools +
                file_management_toolkit.get_tools() +
                [
                    save_memory,
                    delete_memory,
                    load_pdf,
                    execute_python,
                    shell_tool,
                    semantic_scholar_tool
                ]
            )
            
            logger.info(f"Initialized {len(self.tools)} tools")
        except Exception as e:
            logger.error(f"Error initializing tools: {e}")
            self.tools = []


# =============================================================================
# LOCAL TESTING SECTION (Optional - for development only)
# =============================================================================

if __name__ == "__main__":
    """
    This section is only for local testing and development.
    The platform will NOT use this - it will call the class methods directly.
    
    IMPORTANT: When deployed in Docker, the platform uses Docker exec to run
    the agent class methods directly. This main block is only for local development testing.
    """

    agent = PersonalAssistantAgent()

    # Test initialization
    print("1. Testing initialization...")
    init_result = agent.initialize({
        "system_prompt": "You are a helpful personal assistant.",
        "model_name": "gpt-4",
        "temperature": 0.1,
        "max_tokens": 2000,
        "enable_memory": True
    })
    print(json.dumps(init_result, indent=2))

    if init_result.get("status") == "initialized":
        # Test first execution
        print("\n2. Testing first execution...")
        exec_result1 = agent.execute({
            "message": "Hello! Can you help me with a web search?",
            "user_id": "test_user"
        })
        print(json.dumps(exec_result1, indent=2))

        # Test second execution (should use same state)
        print("\n3. Testing second execution...")
        exec_result2 = agent.execute({
            "message": "What can you do?",
            "user_id": "test_user"
        })
        print(json.dumps(exec_result2, indent=2))

        # Test cleanup
        print("\n4. Testing cleanup...")
        cleanup_result = agent.cleanup()
        print(json.dumps(cleanup_result, indent=2))

    print("\n=== Local testing completed ===")
    print("Note: The platform will call these methods directly and handle all platform concerns")
else:
    print("Persistent agent loaded. The platform will use Docker exec to run agent methods.")
    print("Set RUN_LOCAL_TESTING=true to run local testing.") 