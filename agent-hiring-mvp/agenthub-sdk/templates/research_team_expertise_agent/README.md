# Team Expertise Analysis Agent

A comprehensive persistent agent that analyzes team expertise by collecting information from Semantic Scholar, arXiv, and other academic sources. Provides both team-level and individual-level insights about expertise domains, research directions, and collective capabilities.

## Features

- **Persistent Storage**: Maintains collected data across sessions
- **RAG Capabilities**: Query the knowledge base for insights
- **Deep Analysis**: Comprehensive analysis of academic publications and profiles
- **Expertise Domain Categorization**: Automatic mapping using arXiv taxonomy
- **Collaboration Network Analysis**: Identify collaboration patterns and networks
- **Research Direction Insights**: Discover emerging research trends and opportunities
- **Multi-Source Data Collection**: Integrates data from multiple academic sources
- **LLM-Powered Analysis**: Uses advanced language models for intelligent insights

## Installation

### Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file with your API keys:

```bash
# OpenAI API key for embeddings and LLM
OPENAI_API_KEY=your_openai_api_key_here

# Azure OpenAI configuration (optional, for Azure users)
AZURE_API_BASE=your_azure_endpoint_here
AZURE_API_KEY=your_azure_api_key_here
AZURE_API_VERSION=2024-02-15-preview
AZURE_MODEL=azure/gpt-4o-2024-08-06

# LLM Provider (azure or openai)
LLM_PROVIDER=azure
```

## Configuration

### Team Members Input Format

The agent now accepts `team_members` as a **string** instead of an array, providing flexibility in how you specify team members:

#### 1. Multiline Format (Recommended)
```json
{
  "team_members": "George Kour\nBoaz Carmeli\nJohn Doe"
}
```

#### 2. Comma-Separated Format
```json
{
  "team_members": "George Kour, Boaz Carmeli, John Doe"
}
```

#### 3. Mixed Format
```json
{
  "team_members": "George Kour, Boaz Carmeli\nJohn Doe\nJane Smith, Bob Johnson"
}
```

### Complete Configuration Example

```json
{
  "team_members": "George Kour\nBoaz Carmeli",
  "model_name": "gpt-4o-mini",
  "temperature": 0.1,
  "max_publications_per_member": 30,
  "include_citations": true,
  "include_collaboration_network": true,
  "enable_paper_enrichment": false
}
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `team_members` | string | **Required** | Team member names (multiline or comma-separated) |
| `expertise_domains` | array | arXiv taxonomy | Custom expertise domains to analyze |
| `model_name` | string | gpt-4o-mini | LLM model for analysis |
| `temperature` | number | 0.1 | LLM response temperature |
| `max_publications_per_member` | integer | 50 | Max publications to analyze per member |
| `include_citations` | boolean | true | Include citation analysis |
| `llm_provider` | string | azure | LLM provider (azure/openai) |
| `enable_paper_enrichment` | boolean | true | Enable enhanced paper analysis |

## Usage

### Basic Usage

```python
from team_expertise_agent import TeamExpertiseAgent

# Create agent instance
agent = TeamExpertiseAgent()

# Initialize with team configuration
config = {
    "team_members": "George Kour\nBoaz Carmeli",
    "max_publications_per_member": 30
}

init_result = agent.initialize(config)

# Execute queries
if init_result.get("status") == "success":
    response = agent.execute({
        "query_type": "team_overview",
        "query": "What are the main research strengths of this team?"
    })
    print(response["answer"])
```

### CLI Usage

```bash
# Test the parsing functionality
python example_usage.py --parsing

# Run complete test suite
python example_usage.py

# Test background analysis only
python example_usage.py --backgrounds
```

## API Reference

### Methods

#### `initialize(config)`
Initializes the agent with team configuration and collects data.

**Input**: Configuration object with team members and analysis parameters
**Output**: Initialization status and summary

#### `execute(query_params)`
Executes queries about team expertise and research insights.

**Query Types**:
- `team_overview`: General team analysis
- `individual_analysis`: Focus on specific team member
- `expertise_domain_analysis`: Domain-specific insights
- `research_directions`: Future research opportunities
- `collaboration_insights`: Team collaboration patterns
- `custom_question`: Custom analysis requests

#### `cleanup()`
Cleans up resources and performs cleanup operations.

## Data Sources

- **Semantic Scholar**: Academic publications and citations
- **arXiv**: Research papers and preprints
- **Google Scholar**: Additional publication data
- **Collaboration Networks**: Co-author relationships

## Output Examples

### Team Overview
```
Team Expertise Analysis Results:
- Total Members: 2
- Publications Analyzed: 45
- Expertise Domains: 8
- Research Timeline: 2015-2024
- Collaboration Strength: High
```

### Individual Analysis
```
George Kour:
- Primary Domains: Machine Learning, Computer Vision
- H-Index: 15
- Total Citations: 1,234
- Research Focus: Deep Learning Applications
```

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure OpenAI API key is set correctly
2. **Rate Limiting**: Academic APIs may have rate limits
3. **Data Collection Failures**: Check internet connection and API availability
4. **LLM Configuration**: Verify Azure/OpenAI settings

### Debug Mode

Enable detailed logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Testing

The agent includes comprehensive testing:

```bash
# Test parsing functionality
python example_usage.py --parsing

# Run full test suite
python example_usage.py
```

## Architecture

The agent uses a modular architecture:

- **TeamExpertiseAgent**: Main agent class with persistent state
- **TeamMemberExtractor**: Modular data collection component
- **Knowledge Base**: FAISS vector store for RAG queries
- **LLM Integration**: LiteLLM for provider-agnostic access

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review error logs
3. Test with minimal configuration
4. Open an issue with detailed information
