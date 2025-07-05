#!/usr/bin/env python3
"""
Debug script to test the execution service directly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from server.services.execution_service import ExecutionService
from server.database.config import get_session_dependency
from server.models.execution import Execution

def test_execution_service():
    """Test the execution service directly."""
    print("🔍 DEBUGGING EXECUTION SERVICE")
    
    # Get a database session
    session = next(get_session_dependency())
    
    try:
        # Create execution service
        execution_service = ExecutionService(session)
        
        # Get all executions
        executions = session.query(Execution).all()
        print(f"Found {len(executions)} executions")
        
        for execution in executions:
            print(f"Execution ID: {execution.id}")
            print(f"  Execution UUID: {execution.execution_id}")
            print(f"  Status: {execution.status}")
            print(f"  Agent ID: {execution.agent_id}")
            print(f"  Created: {execution.created_at}")
            print()
        
        # Try to execute the first pending execution
        pending_executions = [e for e in executions if e.status == 'pending']
        if pending_executions:
            execution = pending_executions[0]
            print(f"Executing: {execution.execution_id}")
            
            result = execution_service.execute_agent(execution.execution_id)
            print(f"Result: {result}")
        else:
            print("No pending executions found")
            
    finally:
        session.close()

if __name__ == "__main__":
    test_execution_service() 