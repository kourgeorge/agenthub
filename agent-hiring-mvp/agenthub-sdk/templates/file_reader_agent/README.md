# File Reader Agent

A simple functional agent that reads a file and outputs its content with metadata.

## Overview

This agent takes a file reference ID as input and returns the complete file content along with useful metadata such as file size, content length, filename, and file type.

## Features

- **Simple Input**: Just provide a file reference ID
- **File Download**: Downloads files from the AgentHub file service
- **Size Limits**: Prevents reading files larger than 10MB
- **Encoding Support**: Handles UTF-8 and fallback to Latin-1 encoding
- **Error Handling**: Comprehensive error handling with informative messages
- **Metadata**: Returns file ID, filename, file type, size, content length, URLs, and timestamp

## Usage

### Input Schema

```json
{
  "file_references": ["file_id_123"],
  "api_key": "your_api_key_here",
  "server_host": "192.168.1.132",
  "server_port": "8002"
}
```

### Output Schema

```json
{
  "content": "File content here...",
  "file_id": "file_id_123",
  "filename": "example.txt",
  "file_type": "text/plain",
  "file_size_bytes": 1024,
  "content_length": 50,
  "file_url": "http://host.docker.internal:8002/api/v1/files/file_id_123",
  "download_url": "http://host.docker.internal:8002/api/v1/files/file_id_123/download",
  "timestamp": "2024-01-01T12:00:00Z",
  "agent_type": "file_reader"
}
```

## Examples

### Basic Usage

```bash
agenthub execute agent <agent_id> --input '{"file_references": ["file_id_123"], "api_key": "your_api_key"}'
```

### Reading Different File Types

The agent can read any text-based file:
- `.txt` files
- `.md` files  
- `.py` files
- `.json` files
- Any other text-based format

## Limitations

- Maximum file size: 10MB
- Only supports text files (not binary)
- File must be uploaded to the AgentHub platform first
- Only one file can be read per execution

## Error Handling

The agent handles various error scenarios:
- File not found
- Download failures
- File too large
- Invalid file reference
- Encoding issues

## Testing

You can test the agent locally by running:

```bash
python file_reader_agent.py
```

This will create a test file, read it, and display the results.

## Configuration Options

### Environment Variables
You can set server configuration using environment variables:
```bash
export AGENTHUB_SERVER_HOST="192.168.1.132"
export AGENTHUB_SERVER_PORT="8002"
```

### Priority Order
1. **Input parameters** (highest priority)
2. **Config from server execution context**
3. **Environment variables**
4. **Default values** (lowest priority: `host.docker.internal:8002`)

## Security Notes

- The agent can only read files that have been uploaded to the AgentHub platform
- File access is controlled through the platform's authentication system
- File references are validated before processing
- **Authentication**: Provide an `api_key` in the input to authenticate file access
- **Header Format**: Uses `X-API-Key` header for authentication
