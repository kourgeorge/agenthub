"""Persistent agent runtime service for executing persistent agents with state management."""

import json
import logging
import time
import importlib.util
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .base_runtime import RuntimeResult, RuntimeStatus
from ..database.config import get_engine
from ..models.hiring import Hiring
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class PersistentAgentStatus(str, Enum):
    """Persistent agent status."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    EXECUTING = "executing"
    ERROR = "error"
    CLEANED_UP = "cleaned_up"


@dataclass
class PersistentAgentState:
    """State of a persistent agent."""
    agent_id: str
    status: PersistentAgentStatus
    config: Dict[str, Any]
    state_data: Optional[Dict[str, Any]] = None
    created_at: Optional[float] = None
    last_accessed: Optional[float] = None
    execution_count: int = 0
    agent_instance: Optional[Any] = None  # Store the actual agent instance


class PersistentAgentRuntimeService:
    """Service for managing and executing persistent agents with database-only storage."""
    
    def __init__(self):
        # In-memory cache of agent states and instances
        self._agent_states: Dict[str, PersistentAgentState] = {}
        self._agent_instances: Dict[str, Any] = {}  # Store actual agent instances
        
        # Load existing states from database
        self._load_existing_states()
        logger.info("PersistentAgentRuntimeService initialized and loaded existing states")
    
    def _save_agent_state(self, agent_state: PersistentAgentState, hiring_id: Optional[int] = None) -> bool:
        """Save agent state to database only. Returns True if successful, False otherwise."""
        try:
            engine = get_engine()
            Session = sessionmaker(bind=engine)
            with Session() as session:
                try:
                    # Find the hiring record - prefer hiring_id if provided, otherwise find by agent_id
                    if hiring_id:
                        hiring = session.query(Hiring).filter(Hiring.id == hiring_id).first()
                    else:
                        hiring = session.query(Hiring).filter(
                            Hiring.agent_id == agent_state.agent_id
                        ).first()
                    
                    if hiring:
                        # Update the state in the database
                        hiring.state = {
                            'status': agent_state.status.value,
                            'config': agent_state.config,
                            'state_data': agent_state.state_data,
                            'created_at': agent_state.created_at,
                            'last_accessed': agent_state.last_accessed,
                            'execution_count': agent_state.execution_count
                        }
                        session.commit()
                        logger.info(f"Saved agent state to database for agent {agent_state.agent_id}, hiring {hiring.id}")
                        return True
                    else:
                        logger.warning(f"No hiring record found for agent {agent_state.agent_id}, hiring_id {hiring_id}")
                        return False
                        
                except SQLAlchemyError as e:
                    session.rollback()
                    logger.error(f"Database error saving agent state: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to save agent state to database: {e}")
            return False
    
    def _load_agent_state(self, agent_id: str) -> Optional[PersistentAgentState]:
        """Load agent state from database only."""
        try:
            engine = get_engine()
            Session = sessionmaker(bind=engine)
            with Session() as session:
                hiring = session.query(Hiring).filter(
                    Hiring.agent_id == agent_id
                ).first()
                
                if hiring and hiring.state:
                    data = hiring.state
                    logger.info(f"Loaded agent state from database for {agent_id}")
                    return PersistentAgentState(
                        agent_id=agent_id,
                        status=PersistentAgentStatus(data['status']),
                        config=data['config'],
                        state_data=data.get('state_data'),
                        created_at=data.get('created_at'),
                        last_accessed=data.get('last_accessed'),
                        execution_count=data.get('execution_count', 0),
                        agent_instance=None  # Will be recreated if needed
                    )
        except Exception as e:
            logger.error(f"Failed to load agent state from database: {e}")
        
        return None
    
    def _load_existing_states(self) -> None:
        """Load all existing agent states from database."""
        try:
            engine = get_engine()
            Session = sessionmaker(bind=engine)
            with Session() as session:
                # Query database for all active hirings with state
                hirings = session.query(Hiring).filter(
                    Hiring.state.isnot(None)  # Has state data
                ).all()
                
                for hiring in hirings:
                    agent_id_str = str(hiring.agent_id)
                    
                    # Skip if already loaded in memory
                    if agent_id_str in self._agent_states:
                        continue
                    
                    # Create agent state directly from hiring data (no additional database calls)
                    if hiring.state:
                        try:
                            data = hiring.state
                            agent_state = PersistentAgentState(
                                agent_id=agent_id_str,
                                status=PersistentAgentStatus(data['status']),
                                config=data['config'],
                                state_data=data.get('state_data'),
                                created_at=data.get('created_at'),
                                last_accessed=data.get('last_accessed'),
                                execution_count=data.get('execution_count', 0),
                                agent_instance=None  # Will be recreated if needed
                            )
                            
                            self._agent_states[agent_id_str] = agent_state
                            logger.info(f"Loaded existing state for agent {hiring.agent_id} from database")
                            
                        except Exception as e:
                            logger.error(f"Error processing state data for agent {hiring.agent_id}: {e}")
                            continue
        except Exception as e:
            logger.error(f"Error loading existing states from database: {e}")
    
    def _delete_agent_state(self, agent_id: str) -> bool:
        """Delete agent state from database only. Returns True if successful."""
        try:
            engine = get_engine()
            Session = sessionmaker(bind=engine)
            with Session() as session:
                try:
                    hiring = session.query(Hiring).filter(
                        Hiring.agent_id == agent_id
                    ).first()
                    
                    if hiring and hiring.state:
                        # Clear the state but keep the hiring record
                        hiring.state = None
                        session.commit()
                        logger.info(f"Deleted agent state from database for {agent_id}")
                        return True
                    else:
                        logger.info(f"No state found to delete for agent {agent_id}")
                        return True
                        
                except SQLAlchemyError as e:
                    session.rollback()
                    logger.error(f"Database error deleting agent state: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete agent state from database: {e}")
            return False
    
    def _get_agent_config(self, agent_id: str, agent_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract agent configuration from agent files."""
        for file_data in agent_files:
            if file_data.get('file_path') == 'config.json':
                try:
                    return json.loads(file_data['file_content'])
                except Exception as e:
                    logger.error(f"Error parsing config.json: {e}")
                    return {}
        return {}
    
    def _load_agent_class(self, agent_files: List[Dict[str, Any]], entry_point: str, agent_class: str) -> Optional[Any]:
        """Load an agent class from agent files using in-memory execution."""
        try:
            # Find the entry point file
            entry_file = None
            for file_data in agent_files:
                if file_data.get('file_path') == entry_point:
                    entry_file = file_data
                    break
            
            if not entry_file:
                logger.error(f"Entry point file {entry_point} not found in agent files")
                return None
            
            # Execute code in memory instead of creating temporary files
            try:
                # Create a new module namespace
                module_name = f"agent_module_{int(time.time())}"
                module = importlib.util.module_from_spec(
                    importlib.util.spec_from_loader(module_name, loader=None)
                )
                
                # Execute the code in the module namespace
                exec(entry_file['file_content'], module.__dict__)
                
                # Get the agent class
                agent_class_obj = getattr(module, agent_class, None)
                if agent_class_obj:
                    return agent_class_obj
                else:
                    logger.error(f"Agent class {agent_class} not found in {entry_point}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error executing agent code in memory: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading agent class: {e}")
            return None
    
    def _create_agent_instance(self, agent_id: str, agent_files: List[Dict[str, Any]], 
                              entry_point: str, agent_class: str) -> Optional[Any]:
        """Create an instance of the agent class."""
        try:
            agent_class_obj = self._load_agent_class(agent_files, entry_point, agent_class)
            if agent_class_obj:
                # Create instance (no need to set agent ID - platform handles this)
                instance = agent_class_obj()
                return instance
            return None
        except Exception as e:
            logger.error(f"Error creating agent instance: {e}")
            return None
    
    async def initialize_agent(self, agent_id: str, init_config: Dict[str, Any], 
                        agent_files: List[Dict[str, Any]], entry_point: Optional[str] = None, 
                        hiring_id: Optional[int] = None) -> RuntimeResult:
        """Initialize a persistent agent using database-only storage."""
        agent_id_str = str(agent_id)
        
        try:
            # Check if agent is already initialized - check database first, then memory cache
            agent_state = self._agent_states.get(agent_id_str)
            if not agent_state:
                # Not in memory cache, try to load from database
                agent_state = self._load_agent_state(agent_id_str)
                if agent_state:
                    # Update memory cache for performance
                    self._agent_states[agent_id_str] = agent_state
            
            if agent_state and agent_state.status == PersistentAgentStatus.READY:
                return RuntimeResult(
                    status=RuntimeStatus.COMPLETED,
                    output=json.dumps({
                        "status": "already_initialized",
                        "message": f"Agent {agent_id} already initialized",
                        "agent_id": agent_id_str
                    })
                )
            
            # Get agent configuration
            agent_config = self._get_agent_config(agent_id, agent_files)
            agent_class = agent_config.get("agent_class")
            
            if not agent_class:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error="Agent class not specified in config.json"
                )
            
            # Create new agent state
            agent_state = PersistentAgentState(
                agent_id=agent_id_str,
                status=PersistentAgentStatus.INITIALIZING,
                config=init_config,
                created_at=time.time(),
                last_accessed=time.time()
            )
            
            self._agent_states[agent_id_str] = agent_state
            
            # Save to database first
            if not self._save_agent_state(agent_state, hiring_id):
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error=f"Failed to save agent state to database for {agent_id}"
                )
            
            # Create agent instance
            agent_instance = self._create_agent_instance(agent_id, agent_files, entry_point, agent_class)
            if not agent_instance:
                agent_state.status = PersistentAgentStatus.ERROR
                self._save_agent_state(agent_state, hiring_id)
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error=f"Failed to create agent instance for {agent_id}"
                )
            
            # Store the instance
            self._agent_instances[agent_id_str] = agent_instance
            
            # Initialize the agent
            logger.info(f"Initializing persistent agent {agent_id}")
            try:
                init_result = agent_instance.initialize(init_config)
                
                # Check if initialization was successful
                is_successful = False
                if isinstance(init_result, dict):
                    status = init_result.get("status", "")
                    error = init_result.get("error", "")
                    
                    # Check for explicit success statuses
                    if status in ["initialized", "already_initialized"]:
                        is_successful = True
                    # Check for explicit error indicators
                    elif status == "error" or error or "Error code:" in str(init_result):
                        is_successful = False
                    # If no clear status, check if there's any error content
                    elif any(error_indicator in str(init_result).lower() for error_indicator in 
                           ["error", "failed", "quota", "insufficient", "429", "500", "400"]):
                        is_successful = False
                    else:
                        # Default to success if no clear error indicators
                        is_successful = True
                else:
                    # Non-dict result, treat as success unless it contains error indicators
                    result_str = str(init_result).lower()
                    if any(error_indicator in result_str for error_indicator in 
                           ["error", "failed", "quota", "insufficient", "429", "500", "400"]):
                        is_successful = False
                    else:
                        is_successful = True
                
                if is_successful:
                    # Add agent ID to response (platform concern)
                    if isinstance(init_result, dict):
                        init_result["agent_id"] = agent_id_str
                    
                    # Update agent state to READY
                    agent_state.status = PersistentAgentStatus.READY
                    agent_state.state_data = init_result
                    agent_state.last_accessed = time.time()
                    
                    if self._save_agent_state(agent_state, hiring_id):
                        logger.info(f"Successfully initialized persistent agent {agent_id}")
                        return RuntimeResult(
                            status=RuntimeStatus.COMPLETED,
                            output=json.dumps(init_result) if isinstance(init_result, dict) else str(init_result)
                        )
                    else:
                        # Failed to save state
                        agent_state.status = PersistentAgentStatus.ERROR
                        self._save_agent_state(agent_state, hiring_id)
                        return RuntimeResult(
                            status=RuntimeStatus.FAILED,
                            error=f"Failed to save agent state after successful initialization for {agent_id}"
                        )
                else:
                    # Initialization failed - add agent ID for consistency
                    if isinstance(init_result, dict):
                        init_result["agent_id"] = agent_id_str
                    
                    # Mark agent as ERROR and clean up
                    agent_state.status = PersistentAgentStatus.ERROR
                    self._save_agent_state(agent_state, hiring_id)
                    
                    # Remove failed instance from memory
                    if agent_id_str in self._agent_instances:
                        del self._agent_instances[agent_id_str]
                    
                    logger.error(f"Agent initialization failed for {agent_id}: {init_result}")
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        output=json.dumps(init_result) if isinstance(init_result, dict) else str(init_result)
                    )
                    
            except Exception as e:
                logger.error(f"Error during agent initialization: {e}")
                agent_state.status = PersistentAgentStatus.ERROR
                self._save_agent_state(agent_state, hiring_id)
                
                # Remove failed instance from memory
                if agent_id_str in self._agent_instances:
                    del self._agent_instances[agent_id_str]
                
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error=f"Initialization error: {e}"
                )
                
        except Exception as e:
            logger.error(f"Error initializing persistent agent {agent_id}: {e}")
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"Initialization error: {e}"
            )
    
    async def execute_agent(self, agent_id: str, input_data: Dict[str, Any],
                     agent_files: List[Dict[str, Any]], entry_point: Optional[str] = None) -> RuntimeResult:
        """Execute a persistent agent using database-only storage."""
        agent_id_str = str(agent_id)
        
        try:
            # Check if agent is initialized - read from database first, then memory cache
            agent_state = self._agent_states.get(agent_id_str)
            if not agent_state:
                # Not in memory cache, try to load from database
                agent_state = self._load_agent_state(agent_id_str)
                if agent_state:
                    # Update memory cache for performance
                    self._agent_states[agent_id_str] = agent_state
                else:
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        error=f"Agent {agent_id} not initialized. Call initialize_agent first."
                    )
            
            if agent_state.status != PersistentAgentStatus.READY:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error=f"Agent {agent_id} is not ready (status: {agent_state.status})"
                )
            
            # Get or create agent instance
            agent_instance = self._agent_instances.get(agent_id_str)
            if not agent_instance:
                # Recreate instance if not in memory
                agent_config = self._get_agent_config(agent_id, agent_files)
                agent_class = agent_config.get("agent_class")
                if agent_class:
                    agent_instance = self._create_agent_instance(agent_id, agent_files, entry_point, agent_class)
                    if agent_instance:
                        self._agent_instances[agent_id_str] = agent_instance
                    else:
                        return RuntimeResult(
                            status=RuntimeStatus.FAILED,
                            error=f"Failed to recreate agent instance for {agent_id}"
                        )
                else:
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        error=f"Agent class not found for {agent_id}"
                    )
            
            # Update state
            agent_state.status = PersistentAgentStatus.EXECUTING
            agent_state.last_accessed = time.time()
            agent_state.execution_count += 1
            
            if not self._save_agent_state(agent_state):
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error=f"Failed to save agent state before execution for {agent_id}"
                )
            
            # Execute the agent
            logger.info(f"Executing persistent agent {agent_id}")
            try:
                # Check if the agent's execute method is async
                if hasattr(agent_instance.execute, '__await__'):
                    result = await agent_instance.execute(input_data)
                else:
                    result = agent_instance.execute(input_data)
                
                # Add agent ID to response (platform concern)
                if isinstance(result, dict):
                    result["agent_id"] = agent_id_str
                
                # Update state back to ready
                agent_state.status = PersistentAgentStatus.READY
                if self._save_agent_state(agent_state):
                    return RuntimeResult(
                        status=RuntimeStatus.COMPLETED,
                        output=json.dumps(result) if isinstance(result, dict) else str(result)
                    )
                else:
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        error=f"Failed to save agent state after execution for {agent_id}"
                    )
                
            except Exception as e:
                logger.error(f"Error during agent execution: {e}")
                agent_state.status = PersistentAgentStatus.ERROR
                self._save_agent_state(agent_state)
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error=f"Execution error: {e}"
                )
                
        except Exception as e:
            logger.error(f"Error executing persistent agent {agent_id}: {e}")
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"Execution error: {e}"
            )
    
    def cleanup_agent(self, agent_id: str, agent_files: List[Dict[str, Any]], 
                     entry_point: Optional[str] = None) -> RuntimeResult:
        """Clean up a persistent agent using database-only storage."""
        agent_id_str = str(agent_id)
        
        try:
            # Check if agent exists - check database first, then memory cache
            agent_state = self._agent_states.get(agent_id_str)
            if not agent_state:
                # Not in memory cache, try to load from database
                agent_state = self._load_agent_state(agent_id_str)
                if not agent_state:
                    return RuntimeResult(
                        status=RuntimeStatus.COMPLETED,
                        output=json.dumps({
                            "status": "not_found",
                            "message": f"Agent {agent_id} not found"
                        })
                    )
                else:
                    # Update memory cache for performance
                    self._agent_states[agent_id_str] = agent_state
            
            # Get agent instance if available
            agent_instance = self._agent_instances.get(agent_id_str)
            if agent_instance:
                try:
                    # Call cleanup on the agent instance
                    cleanup_result = agent_instance.cleanup()
                    logger.info(f"Agent {agent_id} cleanup completed: {cleanup_result}")
                except Exception as e:
                    logger.warning(f"Error during agent cleanup: {e}")
                    cleanup_result = {"status": "error", "error": str(e)}
            else:
                cleanup_result = {"status": "no_instance", "message": "No agent instance to cleanup"}
            
            # Update state to cleaned up
            agent_state.status = PersistentAgentStatus.CLEANED_UP
            agent_state.last_accessed = time.time()
            
            if self._save_agent_state(agent_state):
                # Remove from memory cache
                if agent_id_str in self._agent_states:
                    del self._agent_states[agent_id_str]
                if agent_id_str in self._agent_instances:
                    del self._agent_instances[agent_id_str]
                
                # Delete from database
                if self._delete_agent_state(agent_id_str):
                    return RuntimeResult(
                        status=RuntimeStatus.COMPLETED,
                        output=json.dumps({
                            "status": "cleaned_up",
                            "message": f"Agent {agent_id} cleaned up successfully",
                            "cleanup_result": cleanup_result
                        })
                    )
                else:
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        error=f"Failed to delete agent state from database for {agent_id}"
                    )
            else:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error=f"Failed to save agent state during cleanup for {agent_id}"
                )
                
        except Exception as e:
            logger.error(f"Error cleaning up persistent agent {agent_id}: {e}")
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"Cleanup error: {e}"
            )
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a persistent agent."""
        agent_id_str = str(agent_id)
        
        # Check memory cache first
        agent_state = self._agent_states.get(agent_id_str)
        if not agent_state:
            # Not in memory cache, try to load from database
            agent_state = self._load_agent_state(agent_id_str)
            if agent_state:
                # Update memory cache for performance
                self._agent_states[agent_id_str] = agent_state
            else:
                return None
        
        return {
            "agent_id": agent_id_str,
            "status": agent_state.status.value,
            "created_at": agent_state.created_at,
            "last_accessed": agent_state.last_accessed,
            "execution_count": agent_state.execution_count,
            "has_instance": agent_id_str in self._agent_instances
        }
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all persistent agents from database."""
        agents = []
        
        # First, ensure we have all agents from database loaded in memory
        try:
            engine = get_engine()
            Session = sessionmaker(bind=engine)
            with Session() as session:
                # Query database for all active hirings with state
                hirings = session.query(Hiring).filter(
                    Hiring.state.isnot(None)  # Has state data
                ).all()
                
                for hiring in hirings:
                    agent_id_str = str(hiring.agent_id)
                    if agent_id_str not in self._agent_states:
                        # Create agent state directly from hiring data (no additional database calls)
                        if hiring.state:
                            try:
                                data = hiring.state
                                agent_state = PersistentAgentState(
                                    agent_id=agent_id_str,
                                    status=PersistentAgentStatus(data['status']),
                                    config=data['config'],
                                    state_data=data.get('state_data'),
                                    created_at=data.get('created_at'),
                                    last_accessed=data.get('last_accessed'),
                                    execution_count=data.get('execution_count', 0),
                                    agent_instance=None  # Will be recreated if needed
                                )
                                
                                self._agent_states[agent_id_str] = agent_state
                                
                            except Exception as e:
                                logger.error(f"Error processing state data for agent {hiring.agent_id}: {e}")
                                continue
        except Exception as e:
            logger.error(f"Error loading agents from database: {e}")
        
        # Now list all agents from memory cache (which now includes database data)
        for agent_id, agent_state in self._agent_states.items():
            agents.append({
                "agent_id": agent_id,
                "status": agent_state.status.value,
                "created_at": agent_state.created_at,
                "last_accessed": agent_state.last_accessed,
                "execution_count": agent_state.execution_count,
                "has_instance": agent_id in self._agent_instances
            })
        return agents
    
    def cleanup_expired_agents(self, max_age_hours: int = 24) -> int:
        """Clean up agents that haven't been accessed for a specified time."""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        
        for agent_id, agent_state in list(self._agent_states.items()):
            if agent_state.last_accessed and (current_time - agent_state.last_accessed) > max_age_seconds:
                logger.info(f"Cleaning up expired agent {agent_id}")
                try:
                    # Remove instance from memory
                    if agent_id in self._agent_instances:
                        del self._agent_instances[agent_id]
                    
                    # Remove from state cache
                    del self._agent_states[agent_id]
                    
                    # Delete from database
                    if self._delete_agent_state(agent_id):
                        cleaned_count += 1
                    else:
                        logger.error(f"Failed to delete expired agent {agent_id} from database")
                        
                except Exception as e:
                    logger.error(f"Error cleaning up expired agent {agent_id}: {e}")
        
        return cleaned_count 

 