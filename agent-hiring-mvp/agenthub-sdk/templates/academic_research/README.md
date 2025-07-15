# Academic Research Agent

A comprehensive academic research agent that searches across multiple academic sources to find papers, summarize research, and identify gaps in the literature.

## Features

### 🔍 **Multi-Source Academic Search**
- **Semantic Scholar**: Access to millions of academic papers with citation data
- **arXiv**: Latest preprints and published papers in computer science, physics, and more
- **Google Scholar**: Broad academic search across all disciplines

### 📊 **Intelligent Analysis**
- **Paper Analysis**: Extracts key findings, methodologies, and contributions
- **PDF Content Analysis**: Downloads and analyzes full PDF papers for deeper insights
- **Gap Identification**: Identifies research gaps and opportunities for future work
- **Trend Analysis**: Discovers emerging trends and patterns in the field
- **Quality Assessment**: Evaluates paper relevance and impact

### 📝 **Comprehensive Reporting**
- **Research Summary**: Detailed academic summary with proper structure
- **Paper Metadata**: Complete information including authors, citations, venues
- **Statistical Insights**: Breakdown of papers by source and impact metrics

## Usage

### Basic Usage
```python
from academic_research import main

result = main({
    "topic": "Transformer models in natural language processing",
    "max_papers_per_source": 10,
    "search_depth": 2
}, {})
```

### Advanced Usage
```python
# Deep research with more papers
result = main({
    "topic": "Quantum machine learning applications",
    "max_papers_per_source": 15,
    "search_depth": 3
}, {})
```

## Input Parameters

| Parameter | Type | Description | Default | Range |
|-----------|------|-------------|---------|-------|
| `topic` | string | Research topic, paper title, or domain | "Machine Learning in Healthcare" | Required |
| `max_papers_per_source` | integer | Papers per source | 10 | 5-20 |
| `search_depth` | integer | Analysis depth | 2 | 1-3 |
| `enable_pdf_analysis` | boolean | Download and analyze PDF content | true | true/false |
| `model` | string | OpenAI model for analysis | "gpt-3.5-turbo" | gpt-3.5-turbo, gpt-4, gpt-4-turbo, gpt-4o, gpt-4o-mini |

## Output Format

The agent returns a structured response with:

```json
{
  "topic": "Research topic",
  "summary": "Comprehensive academic summary in markdown",
  "papers": [
    {
      "title": "Paper title",
      "abstract": "Abstract text",
      "authors": ["Author 1", "Author 2"],
      "year": 2023,
      "venue": "Conference/Journal name",
      "citation_count": 150,
      "url": "Paper URL",
      "source": "semantic_scholar|arxiv|google_scholar"
    }
  ],
  "key_findings": ["Finding 1", "Finding 2"],
  "research_gaps": ["Gap 1", "Gap 2"],
  "emerging_trends": ["Trend 1", "Trend 2"],
  "stats": {
    "total_papers": 45,
    "papers_by_source": {
      "semantic_scholar": 20,
      "arxiv": 15,
      "google_scholar": 10
    }
  }
}
```

## Example Use Cases

### 1. **Literature Review**
Research a specific topic to understand the current state of knowledge:
```python
result = main({
    "topic": "Federated learning in healthcare",
    "max_papers_per_source": 12
}, {})
```

### 2. **Gap Analysis**
Identify research opportunities and unexplored areas:
```python
result = main({
    "topic": "Explainable AI in autonomous vehicles",
    "search_depth": 3
}, {})
```

### 3. **Trend Discovery**
Find emerging trends and recent developments:
```python
result = main({
    "topic": "Large language models in education",
    "max_papers_per_source": 15
}, {})
```

### 4. **Paper Investigation**
Research a specific paper or author's work:
```python
result = main({
    "topic": "Attention is All You Need Vaswani",
    "max_papers_per_source": 8
}, {})
```

### 5. **Deep PDF Analysis**
Enable PDF content analysis for more detailed insights:
```python
result = main({
    "topic": "Quantum computing applications",
    "enable_pdf_analysis": True,
    "max_papers_per_source": 12
}, {})
```

### 6. **Advanced Model Usage**
Use different OpenAI models for analysis:
```python
result = main({
    "topic": "Advanced machine learning techniques",
    "model": "gpt-4",
    "enable_pdf_analysis": True
}, {})
```

## Requirements

- `openai>=1.0.0` - For AI analysis and summarization
- `requests>=2.28.0` - For API calls to academic sources
- `python-dotenv>=1.0.0` - For environment variable management
- `PyPDF2>=3.0.0` - For PDF text extraction and analysis

## Environment Variables

The agent requires these API keys (configured in `api_keys.txt`):
- `OPENAI_API_KEY` - For AI analysis and summarization
- `SERPER_API_KEY` - For Google Scholar search

## Academic Sources

### Semantic Scholar
- **Coverage**: Millions of academic papers across all disciplines
- **Features**: Citation counts, influential citations, author information
- **API**: Free tier with rate limits

### arXiv
- **Coverage**: Preprints in computer science, physics, mathematics, etc.
- **Features**: Latest research, full-text access, categorization
- **API**: Free, no rate limits

### Google Scholar
- **Coverage**: Broad academic search across all disciplines
- **Features**: Citation tracking, related papers, full-text search
- **Access**: Via Serper API

## Best Practices

1. **Specific Topics**: Use specific, well-defined research topics for better results
2. **Balanced Sources**: The agent automatically balances results across sources
3. **Depth vs Speed**: Higher search depth provides more thorough analysis but takes longer
4. **Paper Limits**: Adjust `max_papers_per_source` based on your needs (5-20 recommended)
5. **PDF Analysis**: Enable PDF analysis for deeper insights, but be aware it increases processing time
6. **Network Stability**: PDF downloads require stable internet connection
7. **Model Selection**: Use GPT-4 for complex analysis, GPT-3.5-turbo for faster processing

## Limitations

- **Rate Limits**: Academic APIs have rate limits that may affect large searches
- **Content Access**: Some papers may require institutional access
- **Language**: Primarily focused on English-language research
- **Recency**: arXiv provides latest research, other sources may have delays
- **PDF Access**: Not all papers have publicly accessible PDFs
- **PDF Quality**: Some PDFs may have poor text extraction quality

## Troubleshooting

### No Papers Found
- Check if the topic is too specific or obscure
- Try broader search terms
- Verify API keys are properly configured

### Limited Results
- Increase `max_papers_per_source`
- Try alternative topic phrasings
- Check if the field has limited recent research

### API Errors
- Verify API keys in `api_keys.txt`
- Check network connectivity
- Respect rate limits by reducing search parameters 