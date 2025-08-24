# Paper Analysis Agent

A persistent AgentHub agent that analyzes academic papers, extracts metadata, and performs similarity analysis using vector embeddings and research APIs.

## Overview

The Paper Analysis Agent is designed to:
1. **Initialize** by processing a multi-line text input containing paper titles and authors
2. **Extract** paper metadata using LLM-based analysis
3. **Enrich** papers with research data from ArXiv and Semantic Scholar
4. **Index** papers using vector embeddings for similarity search
5. **Execute** queries to find related papers based on content similarity

## Features

- **Direct Input Processing**: Accepts paper lists as multi-line text input
- **LLM Extraction**: Uses OpenAI models to extract structured paper metadata
- **Research Enrichment**: Automatically fetches abstracts and additional data from academic APIs
- **Vector Embeddings**: Creates FAISS-based vector database for similarity search
- **Persistent Storage**: Saves paper database and embeddings to disk for reuse
- **Environment-based Configuration**: Uses .env file for API key management

## Architecture

The agent follows the AgentHub persistent agent pattern:

```
PaperAnalysisAgent (PersistentAgent)
├── initialize() - Setup and data processing
├── execute() - Query processing and similarity search
├── cleanup() - Resource cleanup
└── Helper methods for data processing
```

## Usage

### Initialization

```python
# Initialize the agent with paper list content
result = agent.initialize({
    "paper_list_content": "Paper Title 1\nAuthor1, Author2\nPaper Title 2\nAuthor3, Author4",
    "model_name": "gpt-4o-mini",
    "temperature": 0,
    "agent_id": "my_paper_agent"
})
```

### Execution

```python
# Find related papers
result = agent.execute({
    "paper_content": "This paper discusses machine learning algorithms...",
    "max_results": 10,
    "similarity_threshold": 0.5
})
```

### Cleanup

```python
# Clean up resources
result = agent.cleanup()
```

## Configuration

### Input Schema

The agent accepts configuration for:
- `paper_list_content`: Multi-line text containing paper titles and authors
- `model_name`: OpenAI model for LLM processing
- `temperature`: LLM response randomness (0-2)
- `chunk_size`: Text chunk size for embeddings (100-4000)
- `chunk_overlap`: Overlap between chunks (0-1000)
- `agent_id`: Unique identifier for storage isolation

### Output Schema

Returns structured data including:
- Paper metadata (title, authors, abstract, URL)
- Similarity scores
- Processing statistics
- Storage location information

## Dependencies

- **LangChain**: Vector embeddings and text processing
- **FAISS**: Vector similarity search
- **OpenAI**: LLM processing and embeddings
- **ArXiv**: Academic paper search
- **Semantic Scholar**: Research paper metadata
- **python-dotenv**: Environment variable management

## Environment Setup

Create a `.env` file in the agent directory with your API keys:

```bash
# Copy the template
cp env_template.txt .env

# Edit the file and add your OpenAI API key
OPENAI_API_KEY=your_actual_api_key_here
```

## Storage

The agent stores data in:
- `/tmp/agenthub_paper_analysis/agent_{agent_id}/`
  - `faiss_index/` - Vector embeddings
  - `papers_database.json` - Paper metadata

## Error Handling

- Graceful fallbacks when external APIs are unavailable
- Comprehensive logging for debugging
- Input validation and error reporting
- State persistence across executions

## Development

### Local Testing

```bash
cd agenthub-sdk/templates/paper_analysis_agent
python paper_analysis_agent.py
```

### Platform Deployment

The agent is designed to work with AgentHub's persistent agent infrastructure:
- Platform handles lifecycle management
- Docker containerization for isolation
- Automatic state persistence
- Resource management and cleanup

## Examples

### Example Paper List URL

The agent expects a webpage with paper titles and authors in a readable format:

```html
<h1>Research Papers</h1>
<p>Machine Learning Approaches to Natural Language Processing</p>
<p>By John Smith, Jane Doe</p>
<p>Deep Learning for Computer Vision</p>
<p>By Alice Johnson, Bob Wilson</p>
```

### Example Output

```json
{
  "input_paper": "This paper discusses machine learning...",
  "related_papers": [
    {
      "title": "Machine Learning Approaches to Natural Language Processing",
      "authors": ["John Smith", "Jane Doe"],
      "abstract": "We present novel approaches...",
      "similarity_score": 0.85,
      "url": "https://arxiv.org/abs/1234.5678",
      "source": "arxiv"
    }
  ],
  "total_papers_analyzed": 25,
  "processing_time": 2.3
}
```

## Performance

- **Initialization**: O(n) where n is number of papers
- **Query Execution**: O(log n) for vector search
- **Storage**: Efficient FAISS indexing with disk persistence
- **Memory**: Configurable chunk sizes for optimal memory usage

## Limitations

- Requires OpenAI API key for LLM processing
- Web scraping depends on page structure
- Research API rate limits may apply
- Vector similarity is approximate

## Contributing

This agent follows AgentHub's persistent agent patterns:
- Inherit from `PersistentAgent` base class
- Implement required lifecycle methods
- Use state management helpers
- Focus on business logic, not platform concerns

## License

Part of the AgentHub project - see main project license.
