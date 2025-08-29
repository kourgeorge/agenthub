#!/usr/bin/env python3
"""File Reader Agent - Reads a file from file references and outputs its content with metadata."""

import json
import logging
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def execute(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Main execution function for the File Reader Agent."""
    try:
        logger.info("File Reader Agent execution started")

        # First, test external connectivity by downloading from Hetzner speed test server
        test_url = "https://nbg1-speed.hetzner.com/100MB.bin"
        logger.info(f"Testing external connectivity with: {test_url}")

        try:
            with urlopen(test_url, timeout=30) as test_response:
                test_content = test_response.read()
                test_size = len(test_content)
                logger.info(f"✅ External connectivity test successful! Downloaded {test_size} bytes from Hetzner")
        except (HTTPError, URLError) as e:
            logger.warning(f"⚠️ External connectivity test failed: {e}")
            logger.info("This may indicate network/DNS issues within the container")
        except Exception as e:
            logger.warning(f"⚠️ External connectivity test failed with unexpected error: {e}")

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

        # Download file directly from the provided URL
        logger.info(f"Downloading file from: {file_url}")
        with urlopen(file_url, timeout=60) as response:
            file_content = response.read()

        file_size = len(file_content)
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            raise ValueError(f"File too large ({file_size} bytes). Maximum size is 10MB.")

        # Try to get filename from response headers or use fallback
        filename = response.headers.get('X-File-Name')
        file_type = response.headers.get('X-File-Type')
        content = file_content.decode('utf-8')

        timestamp = datetime.now(timezone.utc).isoformat()
        result = {
            "content": content,
            "filename": filename,
            "file_type": file_type,
            "file_size_bytes": file_size,
            "content_length": len(content),
            "download_url": file_url,
            "timestamp": timestamp,
            "agent_type": "file_reader"
        }

        logger.info(f"File Reader Agent execution completed successfully. File size: {file_size} bytes")
        return result

    except (ValueError, Exception) as e:
        logger.error(f"File reading error: {e}")

        return {
            "content": f"Error: {str(e)}",
            "filename": "Error",
            "file_type": "error",
            "file_size_bytes": 0,
            "content_length": 0,
            "download_url": "Unknown",
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
