"""Agent runtime service for executing agent code securely."""

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
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RuntimeStatus(str, Enum):
    """Runtime execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SECURITY_VIOLATION = "security_violation"


@dataclass
class RuntimeResult:
    """Result of agent runtime execution."""
    status: RuntimeStatus
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    exit_code: Optional[int] = None
    security_violations: Optional[List[str]] = None
    container_logs: Optional[str] = None


class AgentRuntimeService:
    """Service for securely executing agent code."""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.join(os.getcwd(), "agent_runtime")
        self.max_execution_time = 120  # seconds (increased for virtual environment setup)
        self.max_output_size = 1024 * 1024  # 1MB
        self.allowed_extensions = {'.py', '.js', '.sh', '.txt', '.json', '.yaml', '.yml'}
        self.forbidden_commands = {
            'rm', 'del', 'format', 'mkfs', 'dd', 'shutdown', 'reboot',
            'sudo', 'su', 'chmod', 'chown', 'mount', 'umount'
        }
        
        # Create runtime directory
        os.makedirs(self.base_dir, exist_ok=True)
    
    def execute_agent(self, agent_id: str, input_data: Dict[str, Any], 
                     agent_code: Optional[str] = None, agent_file_path: Optional[str] = None,
                     agent_files: Optional[List[Dict[str, Any]]] = None, 
                     entry_point: Optional[str] = None) -> RuntimeResult:
        """Execute an agent with the given input data."""
        start_time = time.time()
        
        try:
            # Create temporary execution directory
            with tempfile.TemporaryDirectory(dir=self.base_dir) as temp_dir:
                logger.info(f"Executing agent {agent_id} in {temp_dir}")
                
                # Prepare agent files
                if agent_files:
                    # Use new multi-file approach
                    agent_file = self._prepare_agent_files(temp_dir, agent_files, entry_point)
                elif agent_code:
                    # Legacy single-file approach
                    agent_file = self._prepare_agent_code(temp_dir, agent_code, entry_point)
                elif agent_file_path:
                    agent_file = self._copy_agent_file(temp_dir, agent_file_path)
                else:
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        error="No agent code or files provided"
                    )
                
                # Check for requirements.txt and create virtual environment if needed
                python_executable = self._setup_virtual_environment(temp_dir)
                
                # Prepare input data
                input_file = self._prepare_input_data(temp_dir, input_data)
                
                # Execute the agent
                result = self._run_agent_safely(temp_dir, agent_file, input_file, python_executable)
                
                # Calculate execution time
                execution_time = time.time() - start_time
                result.execution_time = execution_time
                
                logger.info(f"Agent {agent_id} execution completed in {execution_time:.2f}s")
                return result
                
        except Exception as e:
            logger.error(f"Error executing agent {agent_id}: {str(e)}")
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"Runtime error: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def _setup_virtual_environment(self, temp_dir: str) -> str:
        """Set up a virtual environment and install requirements if needed."""
        requirements_file = os.path.join(temp_dir, "requirements.txt")
        
        # Check if requirements.txt exists
        if not os.path.exists(requirements_file):
            logger.info("No requirements.txt found, using system Python")
            return sys.executable
        
        logger.info("Requirements.txt found, creating virtual environment")
        
        # Create virtual environment
        venv_dir = os.path.join(temp_dir, "venv")
        venv.create(venv_dir, with_pip=True)
        
        # Determine pip executable
        if os.name == 'nt':  # Windows
            pip_executable = os.path.join(venv_dir, "Scripts", "pip")
            python_executable = os.path.join(venv_dir, "Scripts", "python")
        else:  # Unix/Linux/macOS
            pip_executable = os.path.join(venv_dir, "bin", "pip")
            python_executable = os.path.join(venv_dir, "bin", "python")
        
        # Install requirements
        try:
            logger.info("Installing requirements in virtual environment")
            
            # Upgrade pip first
            logger.info("Upgrading pip...")
            subprocess.run([
                pip_executable, "install", "--upgrade", "pip"
            ], cwd=temp_dir, check=True, capture_output=True, timeout=60)
            logger.info("Pip upgrade completed")
            
            # Install requirements
            logger.info("Installing requirements from requirements.txt...")
            result = subprocess.run([
                pip_executable, "install", "-r", "requirements.txt"
            ], cwd=temp_dir, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                logger.warning(f"Failed to install some requirements: {result.stderr}")
                logger.warning(f"Pip output: {result.stdout}")
                # Continue anyway - some packages might be optional
            
            logger.info("Virtual environment setup completed")
            return python_executable
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout installing requirements")
            raise RuntimeError("Timeout installing requirements")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install requirements: {e}")
            raise RuntimeError(f"Failed to install requirements: {e}")
    
    def _prepare_agent_files(self, temp_dir: str, agent_files: List[Dict[str, Any]], entry_point: Optional[str] = None) -> str:
        """Prepare all agent files in temporary directory."""
        main_file_path: Optional[str] = None
        
        for file_data in agent_files:
            # Create directory structure if needed
            file_path = os.path.join(temp_dir, file_data['file_path'])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write file content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_data['file_content'])
            
            # Track main file based on entry point or is_main_file flag
            if entry_point:
                # Use entry point to determine main file
                entry_file = entry_point.split(':')[0]
                if file_data['file_path'] == entry_file:
                    main_file_path = file_path
            elif file_data.get('is_main_file') == 'Y':
                main_file_path = file_path
        
        if not main_file_path:
            # Fallback to first Python file
            python_files = [f for f in agent_files if f.get('file_type') == '.py']
            if python_files:
                main_file_path = os.path.join(temp_dir, python_files[0]['file_path'])
            else:
                raise ValueError("No main file or Python files found")
        
        # Create the main execution wrapper
        wrapper_file = os.path.join(temp_dir, "agent.py")
        wrapped_code = self._wrap_agent_code(entry_point)
        
        with open(wrapper_file, 'w') as f:
            f.write(wrapped_code)
        
        return wrapper_file
    
    def _prepare_agent_code(self, temp_dir: str, agent_code: Optional[str], entry_point: Optional[str] = None) -> str:
        """Prepare agent code in temporary directory (legacy method)."""
        if agent_code is None:
            raise ValueError("Agent code cannot be None")
            
        # Use entry point to determine file name
        if entry_point:
            entry_file = entry_point.split(':')[0]
        else:
            entry_file = "agent_code.py"
            
        # Write the agent code to a separate file
        agent_code_file = os.path.join(temp_dir, entry_file)
        with open(agent_code_file, 'w') as f:
            f.write(agent_code)
        
        # Create the main execution file
        agent_file = os.path.join(temp_dir, "agent.py")
        wrapped_code = self._wrap_agent_code(entry_point)
        
        with open(agent_file, 'w') as f:
            f.write(wrapped_code)
        
        return agent_file
    
    def _copy_agent_file(self, temp_dir: str, agent_file_path: str) -> str:
        """Copy agent file to temporary directory."""
        if not os.path.exists(agent_file_path):
            raise FileNotFoundError(f"Agent file not found: {agent_file_path}")
        
        # Validate file extension
        file_ext = Path(agent_file_path).suffix.lower()
        if file_ext not in self.allowed_extensions:
            raise ValueError(f"Unsupported file extension: {file_ext}")
        
        # Copy file to temp directory
        dest_file = os.path.join(temp_dir, f"agent{file_ext}")
        with open(agent_file_path, 'r') as src, open(dest_file, 'w') as dst:
            dst.write(src.read())
        
        return dest_file
    
    def _wrap_agent_code(self, entry_point: Optional[str] = None) -> str:
        """Wrap agent code in a safe execution environment."""
        # Parse entry point to get file and function name
        if entry_point:
            if ':' in entry_point:
                file_name, function_name = entry_point.split(':', 1)
            else:
                file_name = entry_point
                function_name = 'main'
            # Ensure module name matches the actual file name (without .py extension)
            module_name = file_name.replace('.py', '')
        else:
            # Fallback to legacy agent_code.py
            module_name = 'agent_code'
            function_name = 'main'
        
        # Create a simpler wrapper that imports the agent code
        wrapper = f'''#!/usr/bin/env python3
"""
Safe agent execution wrapper.
This wrapper provides a controlled environment for agent execution.
"""

import sys
import json
import os
import signal
import time
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

def safe_execute():
    """Safely execute the agent code."""
    try:
        # Read input data
        input_file = "input.json"
        if os.path.exists(input_file):
            with open(input_file, 'r') as f:
                input_data = json.load(f)
        else:
            input_data = {{}}
        
        # Capture stdout and stderr for debugging
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        agent_result = None
        
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Import and execute agent code
            import {module_name}
            if hasattr({module_name}, '{function_name}'):
                # Call the specified function with proper parameters
                agent_result = {module_name}.{function_name}(input_data, {{}})
            else:
                raise Exception(f"Agent code does not have a {{function_name}}() function")
        
        # Get captured output for debugging
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        
        # Use the actual agent result, not the captured output
        if agent_result:
            # Write the actual agent result to output.json
            output_data = {{
                'status': 'success',
                'output': agent_result,  # Store the actual result as dict, not JSON string
            }}
            if stderr_output and stderr_output.strip():
                output_data['error'] = stderr_output
        else:
            # Fallback if no result returned
            fallback_output = stdout_output.strip() if stdout_output else ''
            if not fallback_output:
                fallback_output = '{{"status": "success", "response": "No result returned"}}'
            output_data = {{
                'status': 'success',
                'output': fallback_output,
            }}
            if stderr_output and stderr_output.strip():
                output_data['error'] = stderr_output
        
        with open('output.json', 'w') as f:
            json.dump(output_data, f)
            
    except Exception as e:
        result = {{
            'status': 'error',
            'error': str(e)
        }}
        with open('output.json', 'w') as f:
            json.dump(result, f)

if __name__ == "__main__":
    # Set up timeout handler (cross-platform)
    def timeout_handler(signum, frame):
        raise TimeoutError("Execution timeout")
    
    # Use signal timeout only on Unix systems
    timeout_set = False
    try:
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(120)  # 120 second timeout (increased for virtual environment setup)
            timeout_set = True
    except (AttributeError, OSError):
        # Windows doesn't support SIGALRM
        pass
    
    try:
        safe_execute()
    except Exception as e:
        result = {{
            'status': 'error',
            'error': str(e)
        }}
        with open('output.json', 'w') as f:
            json.dump(result, f)
    finally:
        if timeout_set:
            try:
                signal.alarm(0)  # Cancel alarm
            except (AttributeError, OSError):
                pass
'''
        
        return wrapper
    
    def _prepare_input_data(self, temp_dir: str, input_data: Dict[str, Any]) -> str:
        """Prepare input data file."""
        input_file = os.path.join(temp_dir, "input.json")
        with open(input_file, 'w') as f:
            json.dump(input_data, f)
        return input_file
    
    def _run_agent_safely(self, temp_dir: str, agent_file: str, input_file: str, python_executable: Optional[str] = None) -> RuntimeResult:
        """Run agent code safely with subprocess."""
        try:
            # Use provided Python executable or default to system Python
            if python_executable is None:
                python_executable = sys.executable
            
            # Determine how to run the agent based on file extension
            file_ext = Path(agent_file).suffix.lower()
            
            if file_ext == '.py':
                cmd = [python_executable, agent_file]
            elif file_ext == '.js':
                cmd = ['node', agent_file]
            elif file_ext == '.sh':
                cmd = ['bash', agent_file]
            else:
                # For other files, try to read and process them
                return self._process_text_file(agent_file, input_file)
            
            # Run the agent with timeout (resource limits handled by timeout)
            process = subprocess.Popen(
                cmd,
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=self.max_execution_time)
                exit_code = process.returncode
                
                # Check for security violations
                security_violations = self._check_security_violations(stdout, stderr)
                
                if security_violations:
                    return RuntimeResult(
                        status=RuntimeStatus.SECURITY_VIOLATION,
                        error=f"Security violations detected: {', '.join(security_violations)}",
                        exit_code=exit_code
                    )
                
                # Read output file if it exists
                output_file = os.path.join(temp_dir, "output.json")
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        output_data = json.load(f)
                    
                    if output_data.get('status') == 'success':
                        return RuntimeResult(
                            status=RuntimeStatus.COMPLETED,
                            output=output_data.get('output', ''),
                            error=output_data.get('error'),
                            exit_code=exit_code
                        )
                    else:
                        return RuntimeResult(
                            status=RuntimeStatus.FAILED,
                            error=output_data.get('error', 'Unknown error'),
                            exit_code=exit_code
                        )
                else:
                    # Fallback to stdout/stderr
                    return RuntimeResult(
                        status=RuntimeStatus.COMPLETED if exit_code == 0 else RuntimeStatus.FAILED,
                        output=stdout,
                        error=stderr,
                        exit_code=exit_code
                    )
                    
            except subprocess.TimeoutExpired:
                process.kill()
                return RuntimeResult(
                    status=RuntimeStatus.TIMEOUT,
                    error="Execution timeout"
                )
                
        except Exception as e:
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"Execution error: {str(e)}"
            )
    
    def _process_text_file(self, agent_file: str, input_file: str) -> RuntimeResult:
        """Process text-based agent files (JSON, YAML, etc.)."""
        try:
            with open(agent_file, 'r') as f:
                content = f.read()
            
            with open(input_file, 'r') as f:
                input_data = json.load(f)
            
            # Simple text processing - replace placeholders with input data
            output = content
            for key, value in input_data.items():
                placeholder = f"${{{key}}}"
                if placeholder in output:
                    output = output.replace(placeholder, str(value))
            
            return RuntimeResult(
                status=RuntimeStatus.COMPLETED,
                output=output
            )
            
        except Exception as e:
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"Text processing error: {str(e)}"
            )
    
    def _set_process_limits(self):
        """Set process resource limits for security."""
        try:
            import resource
            # Set memory limit (100MB)
            resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))
            # Set CPU time limit
            resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        except ImportError:
            # resource module not available on Windows
            pass
    
    def _check_security_violations(self, stdout: str, stderr: str) -> List[str]:
        """Check for security violations in output."""
        violations = []
        
        # Check for forbidden commands
        output_text = (stdout + stderr).lower()
        for cmd in self.forbidden_commands:
            if cmd in output_text:
                violations.append(f"Forbidden command: {cmd}")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            'rm -rf', 'del /s', 'format', 'shutdown', 'sudo',
            'chmod 777', 'chown root', 'mount'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in output_text:
                violations.append(f"Suspicious pattern: {pattern}")
        
        return violations 