#!/usr/bin/env python3
"""File Reader Agent - Reads a file from file references and outputs its content with metadata."""

import json
import logging
import os
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def execute(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Main execution function for the File Reader Agent."""
    try:
        logger.info("File Reader Agent execution started")
        
        # Validate input
        if not isinstance(input_data, dict):
            raise ValueError("Input data must be a dictionary")
        file_references = input_data.get('file_references')
        if not file_references or not isinstance(file_references, list) or len(file_references) == 0:
            raise ValueError("'file_references' is required and must be a non-empty array")
        if len(file_references) > 1:
            raise ValueError("Only one file reference is supported")
        
        # Get file URLs from file_references
        file_references = input_data.get('file_references', [])
        if not file_references or len(file_references) == 0:
            raise Exception("No file references provided")
        
        # Get the first file URL
        file_url = file_references[0]
        if not isinstance(file_url, str):
            raise Exception("File reference must be a string URL")
        
        # Extract file_id from the URL for metadata
        try:
            # URL format: /api/v1/files/{file_id}/download?token={token}
            file_id = file_url.split('/files/')[1].split('/download')[0]
        except (IndexError, AttributeError):
            file_id = f"file_{hash(file_url) % 10000:04d}"  # Fallback ID
        
        logger.info(f"Downloading file from: {file_url}")
        
        # Download file content
        try:
            # Get server configuration
            server_host = (
                input_data.get('server_host') or 
                (config.get('server_host') if config else None) or 
                os.environ.get('AGENTHUB_SERVER_HOST', '')
            )
            server_port = (
                input_data.get('server_port') or 
                (config.get('server_port') if config else None) or 
                os.environ.get('AGENTHUB_SERVER_PORT', '8002')
            )
            
            # If no server_host is provided, try to extract it from the file reference context
            if not server_host and input_data.get('file_context'):
                file_context = input_data.get('file_context', {})
                if isinstance(file_context, dict):
                    # Try to extract host from various possible sources
                    server_host = (
                        file_context.get('server_host') or
                        file_context.get('host') or
                        file_context.get('base_url', '').replace('http://', '').replace('https://', '').split(':')[0] or
                        file_context.get('api_base', '').replace('http://', '').replace('https://', '').split(':')[0]
                    )
            
            # If still no host, use default
            if not server_host:
                server_host = 'host.docker.internal'
            
            # Download the file directly using the full URL
            download_url = f"http://{server_host}:{server_port}{file_url}"
            with urlopen(download_url, timeout=60) as response:
                file_content = response.read()
                file_size = len(file_content)
                if file_size > 10 * 1024 * 1024:  # 10MB limit
                    raise ValueError(f"File too large ({file_size} bytes). Maximum size is 10MB.")
                
                # Try to get filename from response headers or use fallback
                filename = response.headers.get('X-File-Name') or f"file_{file_id[:8]}"
                file_type = response.headers.get('X-File-Type') or 'unknown'
                
                # Decode content
                try:
                    content = file_content.decode('utf-8')
                except UnicodeDecodeError:
                    content = file_content.decode('latin-1')
                
                timestamp = datetime.now(timezone.utc).isoformat()
                result = {
                    "content": content,
                    "file_id": file_id,
                    "filename": filename,
                    "file_type": file_type,
                    "file_size_bytes": file_size,
                    "content_length": len(content),
                    "file_url": f"http://{server_host}:{server_port}/api/v1/files/{file_id}",
                    "download_url": download_url,
                    "timestamp": timestamp,
                    "agent_type": "file_reader"
                }
                
                logger.info(f"File Reader Agent execution completed successfully. File size: {file_size} bytes")
                print(f"File content length: {len(content)} characters")
                print(f"File ID: {file_id}")
                return result
                    
        except (HTTPError, URLError) as e:
            raise Exception(f"Failed to download file {file_id}: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to process file {file_id}: {str(e)}")
        
    except (ValueError, Exception) as e:
        logger.error(f"File reading error: {e}")
        file_id = input_data.get('file_references', ['Unknown'])[0] if input_data.get('file_references') else 'Unknown'
        
        # Use the same host detection logic as the main execution path
        server_host = (
            input_data.get('server_host') or 
            (config.get('server_host') if config else None) or 
            os.environ.get('AGENTHUB_SERVER_HOST', '')
        )
        server_port = (
            input_data.get('server_port') or 
            (config.get('server_port') if config else None) or 
            os.environ.get('AGENTHUB_SERVER_PORT', '8002')
        )
        
        # If no server_host is provided, try to extract it from the file reference context
        if not server_host and input_data.get('file_context'):
            file_context = input_data.get('file_context', {})
            if isinstance(file_context, dict):
                # Try to extract host from various possible sources
                server_host = (
                    file_context.get('server_host') or
                    file_context.get('host') or
                    file_context.get('base_url', '').replace('http://', '').replace('https://', '').split(':')[0] or
                    file_context.get('api_base', '').replace('http://', '').replace('https://', '').split(':')[0]
                )
        
        # If still no host, use default
        if not server_host:
            server_host = 'host.docker.internal'
            
        return {
            "content": f"Error: {str(e)}",
            "file_id": file_id,
            "filename": "Error",
            "file_type": "error",
            "file_size_bytes": 0,
            "content_length": 0,
            "file_url": f"http://{server_host}:{server_port}/api/v1/files/{file_id}" if file_id != 'Unknown' else "Unknown",
            "download_url": f"http://{server_host}:{server_port}/api/v1/files/{file_id}/download" if file_id != 'Unknown' else "Unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_type": "file_reader"
        }


def main(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Main entry point for the agent."""
    return execute(input_data, config)


if __name__ == "__main__":
    test_input = {"file_references": ["test_file_123"]}
    print("🧪 Testing File Reader Agent Locally")
    print("=" * 40)
    print(f"Input: {json.dumps(test_input, indent=2)}")
    print("Note: This test requires a running file service to actually download files.")
    print("The agent is designed to work with file references from the AgentHub platform.")
