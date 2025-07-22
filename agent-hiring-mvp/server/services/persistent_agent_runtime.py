"""Persistent agent runtime service for executing persistent agents with state management."""

import os
import sys
import json
import tempfile
import subprocess
import signal
import logging
import time
import venv
import shutil
import pickle
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from .agent_runtime import AgentRuntimeService, RuntimeResult, RuntimeStatus
from ..database.config import get_engine
from ..models.hiring import Hiring
from sqlalchemy.orm import sessionmaker

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
    """Service for managing and executing persistent agents."""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.join(os.getcwd(), "persistent_agent_runtime")
        self.state_dir = os.path.join(self.base_dir, "states")
        self.agent_runtime = AgentRuntimeService(base_dir)
        
        # Create directories
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.state_dir, exist_ok=True)
        
        # In-memory cache of agent states and instances
        self._agent_states: Dict[str, PersistentAgentState] = {}
        self._agent_instances: Dict[str, Any] = {}  # Store actual agent instances
        
        # Load existing states from disk
        self._load_existing_states()
    
    def _get_state_file_path(self, agent_id: str) -> str:
        """Get the path for storing agent state."""
        return os.path.join(self.state_dir, f"agent_{agent_id}.json")
    
    def _save_agent_state(self, agent_state: PersistentAgentState, hiring_id: Optional[int] = None) -> None:
        """Save agent state to database and disk."""
        # Save to disk (for backward compatibility)
        state_file = self._get_state_file_path(agent_state.agent_id)
        
        # Convert to serializable format (exclude agent_instance)
        serializable_state = {
            'agent_id': agent_state.agent_id,
            'status': agent_state.status.value,
            'config': agent_state.config,
            'state_data': agent_state.state_data,
            'created_at': agent_state.created_at,
            'last_accessed': agent_state.last_accessed,
            'execution_count': agent_state.execution_count
        }
        
        with open(state_file, 'w') as f:
            json.dump(serializable_state, f, indent=2)
        
        # Save to database
        try:
            engine = get_engine()
            Session = sessionmaker(bind=engine)
            with Session() as session:
                # Find the hiring record - prefer hiring_id if provided, otherwise find by agent_id
                if hiring_id:
                    hiring = session.query(Hiring).filter(Hiring.id == hiring_id).first()
                else:
                    hiring = session.query(Hiring).filter(
                        Hiring.agent_id == int(agent_state.agent_id)
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
                else:
                    logger.warning(f"No hiring record found for agent {agent_state.agent_id}, hiring_id {hiring_id}")
                    
        except Exception as e:
            logger.error(f"Failed to save agent state to database: {e}")
        
        logger.info(f"Saved agent state for {agent_state.agent_id}")
    
    def _load_agent_state(self, agent_id: str) -> Optional[PersistentAgentState]:
        """Load agent state from database first, then disk as fallback."""
        # Try to load from database first
        try:
            engine = get_engine()
            Session = sessionmaker(bind=engine)
            with Session() as session:
                hiring = session.query(Hiring).filter(
                    Hiring.agent_id == int(agent_id)
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
        
        # Fallback to disk
        state_file = self._get_state_file_path(agent_id)
        
        if not os.path.exists(state_file):
            return None
        
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Loaded agent state from disk for {agent_id}")
            return PersistentAgentState(
                agent_id=data['agent_id'],
                status=PersistentAgentStatus(data['status']),
                config=data['config'],
                state_data=data.get('state_data'),
                created_at=data.get('created_at'),
                last_accessed=data.get('last_accessed'),
                execution_count=data.get('execution_count', 0),
                agent_instance=None  # Will be recreated if needed
            )
        except Exception as e:
            logger.error(f"Error loading agent state for {agent_id}: {e}")
            return None
    
    def _load_existing_states(self) -> None:
        """Load all existing agent states from disk."""
        for state_file in Path(self.state_dir).glob("agent_*.json"):
            try:
                agent_id = state_file.stem.replace("agent_", "")
                agent_state = self._load_agent_state(agent_id)
                if agent_state:
                    self._agent_states[agent_id] = agent_state
                    logger.info(f"Loaded existing state for agent {agent_id}")
            except Exception as e:
                logger.error(f"Error loading state file {state_file}: {e}")
    
    def _delete_agent_state(self, agent_id: str) -> None:
        """Delete agent state from disk."""
        state_file = self._get_state_file_path(agent_id)
        if os.path.exists(state_file):
            os.remove(state_file)
            logger.info(f"Deleted agent state for {agent_id}")
    
    def _get_agent_config(self, agent_id: int, agent_files: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        """Load an agent class from agent files."""
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
            
            # Create a temporary file with the agent code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(entry_file['file_content'])
                temp_file_path = f.name
            
            try:
                # Load the module
                spec = importlib.util.spec_from_file_location("agent_module", temp_file_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules["agent_module"] = module
                spec.loader.exec_module(module)
                
                # Get the agent class
                agent_class_obj = getattr(module, agent_class, None)
                if agent_class_obj:
                    return agent_class_obj
                else:
                    logger.error(f"Agent class {agent_class} not found in {entry_point}")
                    return None
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"Error loading agent class: {e}")
            return None
    
    def _create_agent_instance(self, agent_id: int, agent_files: List[Dict[str, Any]], 
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
    
    def initialize_agent(self, agent_id: int, init_config: Dict[str, Any], 
                        agent_files: List[Dict[str, Any]], entry_point: Optional[str] = None, 
                        hiring_id: Optional[int] = None) -> RuntimeResult:
        """Initialize a persistent agent using the new inheritance-based design."""
        agent_id_str = str(agent_id)
        
        try:
            # Check if agent is already initialized
            if agent_id_str in self._agent_states:
                existing_state = self._agent_states[agent_id_str]
                if existing_state.status == PersistentAgentStatus.READY:
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
            self._save_agent_state(agent_state, hiring_id)
            
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
                
                if isinstance(init_result, dict) and init_result.get("status") in ["initialized", "already_initialized"]:
                    # Add agent ID to response (platform concern)
                    init_result["agent_id"] = agent_id_str
                    
                    # Update agent state
                    agent_state.status = PersistentAgentStatus.READY
                    agent_state.state_data = init_result
                    agent_state.last_accessed = time.time()
                    self._save_agent_state(agent_state, hiring_id)
                    
                    logger.info(f"Successfully initialized persistent agent {agent_id}")
                    return RuntimeResult(
                        status=RuntimeStatus.COMPLETED,
                        output=json.dumps(init_result)
                    )
                else:
                    # Initialization failed - add agent ID for consistency
                    if isinstance(init_result, dict):
                        init_result["agent_id"] = agent_id_str
                    
                    agent_state.status = PersistentAgentStatus.ERROR
                    self._save_agent_state(agent_state, hiring_id)
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        output=json.dumps(init_result) if isinstance(init_result, dict) else str(init_result)
                    )
                    
            except Exception as e:
                logger.error(f"Error during agent initialization: {e}")
                agent_state.status = PersistentAgentStatus.ERROR
                self._save_agent_state(agent_state, hiring_id)
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
    
    def execute_agent(self, agent_id: int, input_data: Dict[str, Any],
                     agent_files: List[Dict[str, Any]], entry_point: Optional[str] = None) -> RuntimeResult:
        """Execute a persistent agent using the new inheritance-based design."""
        agent_id_str = str(agent_id)
        
        try:
            # Check if agent is initialized
            if agent_id_str not in self._agent_states:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error=f"Agent {agent_id} not initialized. Call initialize_agent first."
                )
            
            agent_state = self._agent_states[agent_id_str]
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
            self._save_agent_state(agent_state)
            
            # Execute the agent
            logger.info(f"Executing persistent agent {agent_id}")
            try:
                result = agent_instance.execute(input_data)
                
                # Add agent ID to response (platform concern)
                if isinstance(result, dict):
                    result["agent_id"] = agent_id_str
                
                # Update state back to ready
                agent_state.status = PersistentAgentStatus.READY
                self._save_agent_state(agent_state)
                
                return RuntimeResult(
                    status=RuntimeStatus.COMPLETED,
                    output=json.dumps(result) if isinstance(result, dict) else str(result)
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
    
    def cleanup_agent(self, agent_id: int, agent_files: List[Dict[str, Any]], 
                     entry_point: Optional[str] = None) -> RuntimeResult:
        """Clean up a persistent agent using the new inheritance-based design."""
        agent_id_str = str(agent_id)
        
        try:
            # Check if agent exists
            if agent_id_str not in self._agent_states:
                return RuntimeResult(
                    status=RuntimeStatus.COMPLETED,
                    output=json.dumps({
                        "status": "not_found",
                        "message": f"Agent {agent_id} not found"
                    })
                )
            
            agent_state = self._agent_states[agent_id_str]
            
            # Get agent instance if available
            agent_instance = self._agent_instances.get(agent_id_str)
            if agent_instance:
                try:
                    # Call cleanup method
                    cleanup_result = agent_instance.cleanup()
                    logger.info(f"Agent {agent_id} cleanup result: {cleanup_result}")
                except Exception as e:
                    logger.error(f"Error during agent cleanup: {e}")
                    cleanup_result = {"status": "error", "error": str(e)}
                
                # Remove instance from memory
                del self._agent_instances[agent_id_str]
            else:
                cleanup_result = {"status": "cleaned_up", "message": "Agent instance not in memory"}
            
            # Add agent ID to response (platform concern)
            if isinstance(cleanup_result, dict):
                cleanup_result["agent_id"] = agent_id_str
            
            # Update state
            agent_state.status = PersistentAgentStatus.CLEANED_UP
            self._save_agent_state(agent_state)
            
            # Remove from memory cache
            if agent_id_str in self._agent_states:
                del self._agent_states[agent_id_str]
            
            # Delete state file
            self._delete_agent_state(agent_id_str)
            
            return RuntimeResult(
                status=RuntimeStatus.COMPLETED,
                output=json.dumps(cleanup_result)
            )
            
        except Exception as e:
            logger.error(f"Error cleaning up persistent agent {agent_id}: {e}")
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"Cleanup error: {e}"
            )
    
    def get_agent_status(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """Get the status of a persistent agent."""
        agent_id_str = str(agent_id)
        
        if agent_id_str not in self._agent_states:
            return None
        
        agent_state = self._agent_states[agent_id_str]
        return {
            "agent_id": agent_id_str,
            "status": agent_state.status.value,
            "created_at": agent_state.created_at,
            "last_accessed": agent_state.last_accessed,
            "execution_count": agent_state.execution_count,
            "has_instance": agent_id_str in self._agent_instances
        }
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all persistent agents."""
        agents = []
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
                    
                    # Delete state file
                    self._delete_agent_state(agent_id)
                    
                    cleaned_count += 1
                except Exception as e:
                    logger.error(f"Error cleaning up expired agent {agent_id}: {e}")
        
        return cleaned_count 