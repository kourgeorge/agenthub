# Deep Research Agent

A comprehensive research agent that conducts deep, multi-source research using web search, MCP tools, and AI-powered analysis to provide detailed, well-sourced reports on any topic.

## Features

- **Multi-Source Research**: Uses web search APIs (Tavily, Serper, OpenAI, Anthropic) to gather information from multiple sources
- **Intelligent Research Planning**: Automatically breaks down complex research topics into manageable sub-topics
- **Parallel Research**: Conducts multiple research tasks concurrently for faster results
- **Source Attribution**: Provides comprehensive source citations and references
- **AI-Powered Analysis**: Uses advanced language models to synthesize and analyze findings
- **Configurable Depth**: Adjustable research depth from shallow to comprehensive
- **MCP Integration**: Optional integration with Model Context Protocol servers for additional tools
- **Structured Output**: Generates well-formatted, professional research reports

## Architecture

The Deep Research Agent uses a sophisticated multi-agent architecture:

1. **Clarification Agent**: Determines if additional information is needed from the user
2. **Research Supervisor**: Coordinates the overall research process and manages sub-researchers
3. **Individual Researchers**: Conduct focused research on specific topics
4. **Compression Agent**: Synthesizes and cleans up research findings
5. **Report Generator**: Creates the final comprehensive report

## Configuration

### Required Parameters

- `research_query` (string): The research question or topic to investigate

### Optional Parameters

- `research_depth` (string): Level of research depth - "shallow", "moderate", "deep", or "comprehensive"
- `max_iterations` (integer): Maximum number of research iterations (1-10, default: 3)
- `max_concurrent_research` (integer): Maximum concurrent research units (1-20, default: 5)
- `max_tool_calls` (integer): Maximum tool calls per research step (1-30, default: 5)
- `search_api` (string): Search API to use - "tavily", "serper", "openai", "anthropic", or "none" (default: "tavily")
- `include_sources` (boolean): Whether to include source citations (default: true)
- `allow_clarification` (boolean): Whether to ask clarifying questions (default: true)

### Model Configuration

- `research_model` (string): Model for conducting research (default: "openai:gpt-4o")
- `research_model_max_tokens` (integer): Maximum output tokens for research model (default: 10000)
- `compression_model` (string): Model for compressing findings (default: "openai:gpt-4o-mini")
- `compression_model_max_tokens` (integer): Maximum output tokens for compression model (default: 8192)
- `final_report_model` (string): Model for final report (default: "openai:gpt-4o")
- `final_report_model_max_tokens` (integer): Maximum output tokens for final report (default: 10000)

### API Keys

- `openai_api_key` (string): OpenAI API key (optional, can use environment variable)
- `anthropic_api_key` (string): Anthropic API key (optional, can use environment variable)
- `tavily_api_key` (string): Tavily API key (optional, can use environment variable)
- `serper_api_key` (string): Serper API key (optional, can use environment variable)

### MCP Configuration

- `mcp_config` (object): Optional MCP server configuration
  - `url` (string): The URL of the MCP server
  - `tools` (array): The tools to make available to the LLM
  - `auth_required` (boolean): Whether authentication is required

## Usage Examples

### Basic Research Query

```json
{
  "research_query": "What are the latest developments in artificial intelligence and machine learning?",
  "research_depth": "moderate",
  "max_iterations": 3,
  "search_api": "tavily"
}
```

### Comprehensive Research with Custom Models

```json
{
  "research_query": "Analyze the impact of climate change on global food security",
  "research_depth": "comprehensive",
  "max_iterations": 5,
  "max_concurrent_research": 8,
  "research_model": "openai:gpt-4o",
  "final_report_model": "openai:gpt-4o",
  "include_sources": true,
  "search_api": "tavily"
}
```

### Research with Serper (Google Search)

```json
{
  "research_query": "What are the current trends in renewable energy adoption?",
  "research_depth": "deep",
  "search_api": "serper",
  "serper_api_key": "your-serper-api-key"
}
```

### Research with MCP Integration

```json
{
  "research_query": "What are the current trends in renewable energy adoption?",
  "research_depth": "deep",
  "mcp_config": {
    "url": "https://your-mcp-server.com",
    "tools": ["database_query", "financial_data"],
    "auth_required": true
  }
}
```

## Output Format

The agent returns a comprehensive research report with the following structure:

```json
{
  "status": "success",
  "research_query": "Original research question",
  "research_brief": "Refined research brief",
  "final_report": "Comprehensive research report with sections",
  "execution_time": 45.2,
  "research_iterations": 3,
  "notes_count": 15,
  "generated_at": "2024-01-15T10:30:00Z",
  "sources": ["List of research sources and notes"]
}
```

## Installation

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up API keys (optional, can be provided in configuration):
   ```bash
   export OPENAI_API_KEY="your-openai-key"
   export ANTHROPIC_API_KEY="your-anthropic-key"
   export TAVILY_API_KEY="your-tavily-key"
   export SERPER_API_KEY="your-serper-key"
   ```

## Research Process

1. **Clarification Phase**: The agent determines if it needs more information from the user
2. **Research Planning**: The research supervisor creates a detailed research brief
3. **Parallel Research**: Multiple researchers work on different aspects simultaneously
4. **Information Synthesis**: Research findings are compressed and organized
5. **Report Generation**: A comprehensive final report is created with proper citations

## Best Practices

- **Be Specific**: Provide detailed research queries for better results
- **Choose Appropriate Depth**: Use "shallow" for quick overviews, "comprehensive" for detailed analysis
- **Monitor Costs**: Higher concurrency and more iterations increase API costs
- **Use MCP Wisely**: MCP tools can provide specialized data but may require authentication
- **Review Sources**: Always verify the quality and relevance of sources in the final report

## Limitations

- **API Rate Limits**: Search APIs have rate limits that may affect research speed
- **Token Limits**: Large research projects may hit model token limits
- **Source Quality**: The agent relies on web search results, which may vary in quality
- **Cost Considerations**: Extensive research can be expensive due to API usage

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure API keys are properly configured
2. **Rate Limit Errors**: Reduce `max_concurrent_research` or `max_iterations`
3. **Token Limit Errors**: Use smaller models or reduce `max_tokens` parameters
4. **Search API Failures**: Try switching to a different `search_api`

### Performance Optimization

- Use appropriate `research_depth` for your needs
- Adjust `max_concurrent_research` based on API limits
- Consider using faster models for compression tasks
- Monitor execution time and adjust parameters accordingly

## License

MIT License - see LICENSE file for details. 