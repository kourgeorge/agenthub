# RAG Agent Template

A functional RAG (Retrieval-Augmented Generation) agent that takes a document source and question as input to provide accurate answers based on document content.

## Overview

This RAG agent uses LlamaIndex to:
1. Load documents from URLs or local files
2. Process and chunk the document content
3. Create embeddings for semantic search
4. Retrieve relevant document chunks for a given question
5. Generate accurate answers using an LLM

## Features

- **Multiple Document Sources**: Supports both URLs and local file paths
- **Configurable Processing**: Adjustable chunk sizes, overlap, and model parameters
- **Robust Error Handling**: Comprehensive error handling and logging
- **Debug Mode**: Optional debug information for troubleshooting
- **OpenAI Integration**: Uses OpenAI models for LLM and embeddings

## Configuration

### Required Environment Variables

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### Agent Configuration Schema

The agent accepts the following configuration parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `debug` | boolean | false | Enable debug mode for additional logging |
| `model_name` | string | "gpt-3.5-turbo" | OpenAI model to use for LLM |
| `embedding_model` | string | "text-embedding-ada-002" | OpenAI model to use for embeddings |
| `temperature` | number | 0 | Temperature for LLM responses |
| `chunk_size` | integer | 1024 | Size of text chunks for processing |
| `chunk_overlap` | integer | 200 | Overlap between text chunks |
| `max_tokens` | integer | 1000 | Maximum tokens for response |

## Input Schema

The agent expects input data with the following structure:

```json
{
  "document_source": "string",  // URL or file path
  "question": "string"          // Question to ask about the document
}
```

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_source` | string | Yes | URL or local file path to the document |
| `question` | string | Yes | Question to ask about the document content |

## Output Schema

The agent returns a dictionary with the following structure:

```json
{
  "answer": "string",                    // Generated answer
  "document_source": "string",           // Original document source
  "question": "string",                  // Original question
  "model_used": "string",                // LLM model used
  "embedding_model": "string",           // Embedding model used
  "chunk_size": integer,                 // Chunk size used
  "chunk_overlap": integer,              // Chunk overlap used
  "debug_info": {                        // Only if debug=true
    "document_length": integer,
    "document_preview": "string"
  }
}
```

## Usage Examples

### Example 1: URL Document

```python
from agent import main

input_data = {
    "document_source": "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "question": "What is artificial intelligence and what are its main applications?"
}

config = {
    "debug": True,
    "model_name": "gpt-3.5-turbo",
    "temperature": 0
}

result = main(input_data, config)
print(result["answer"])
```

### Example 2: Local File

```python
input_data = {
    "document_source": "/path/to/document.txt",
    "question": "What are the key points mentioned in this document?"
}

result = main(input_data, config)
print(result["answer"])
```

### Example 3: Using with AgentHub CLI

```bash
# Test the agent locally
cd agent-hiring-mvp/agenthub-sdk/templates/rag
python test_rag_agent.py

# Publish to AgentHub
agenthub agent publish

# Execute the agent
agenthub execute hiring <hiring_id> --input '{
  "document_source": "https://example.com/document",
  "question": "What is this document about?"
}'
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

3. Test the agent:
```bash
python test_rag_agent.py
```

## Supported Document Sources

### URLs
- Web pages (HTML)
- Wikipedia articles
- Blog posts
- Documentation sites

### Local Files
- Text files (.txt)
- Markdown files (.md)
- Any plain text format

## Error Handling

The agent handles various error scenarios:

- **Missing API Key**: Returns error if OpenAI API key is not set
- **Invalid URL**: Handles network errors and invalid URLs
- **File Not Found**: Handles missing local files
- **Empty Content**: Detects and reports empty documents
- **Processing Errors**: Comprehensive error messages for debugging

## Performance Considerations

- **Chunk Size**: Larger chunks (1024+ tokens) work well for detailed documents
- **Chunk Overlap**: 200 tokens overlap helps maintain context between chunks
- **Model Selection**: GPT-3.5-turbo provides good balance of speed and quality
- **Memory Usage**: Large documents may require significant memory for processing

## Troubleshooting

### Common Issues

1. **"OPENAI_API_KEY environment variable not set"**
   - Solution: Set the environment variable with your OpenAI API key

2. **"Failed to load document from URL"**
   - Check if the URL is accessible
   - Verify the URL returns HTML content
   - Check network connectivity

3. **"File not found"**
   - Verify the file path is correct
   - Ensure the file exists and is readable

4. **"No content found in the document"**
   - The document may be empty or contain only whitespace
   - Check the document source

### Debug Mode

Enable debug mode to get additional information:

```python
config = {"debug": True}
result = main(input_data, config)
print(result.get("debug_info", {}))
```

## Dependencies

- `llama-index`: Core RAG functionality
- `llama-index-readers-web`: Web document loading
- `llama-index-llms-openai`: OpenAI LLM integration
- `llama-index-embeddings-openai`: OpenAI embeddings
- `python-dotenv`: Environment variable management
- `requests`: HTTP requests for URL loading
- `beautifulsoup4`: HTML parsing for web documents

## License

This template is part of the AgentHub project and follows the same licensing terms. 