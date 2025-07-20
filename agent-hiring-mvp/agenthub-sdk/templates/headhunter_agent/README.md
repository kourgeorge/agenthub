# Headhunter Agent

A specialized AI agent that searches for top talent candidates on LinkedIn and the web based on job title, region, and requirements.

## Overview

The Headhunter Agent is designed to automate the initial stages of talent acquisition by:

1. **Searching LinkedIn profiles** for candidates matching specific criteria
2. **Analyzing job boards** to find companies hiring for similar roles
3. **Extracting candidate information** from search results
4. **Analyzing candidate fit** using AI to rate skills match and experience
5. **Generating comprehensive reports** with ranked candidates and next steps

## Features

- **Multi-source search**: LinkedIn, job boards, and web search
- **AI-powered analysis**: Automated candidate fit assessment
- **Confidence scoring**: Rate candidates based on available information
- **Duplicate removal**: Eliminate duplicate candidates across sources
- **Remote work support**: Include remote candidates in searches
- **Comprehensive reporting**: Detailed reports with actionable insights

## Configuration

### Required Environment Variables

```bash
# API Keys
SERPER_API_KEY=your_serper_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Optional LinkedIn credentials (for enhanced scraping)
LINKEDIN_EMAIL=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password
```

### Input Parameters

- **job_title** (required): The job title or position to search for
- **region** (required): Geographic region or location for the search
- **description** (optional): Detailed job description or requirements
- **search_depth** (optional): How many search variations to try (1-5, default: 3)
- **candidates_per_search** (optional): Number of candidates per search (5-20, default: 10)
- **include_remote** (optional): Whether to include remote work opportunities (default: true)

## Usage Examples

### Basic Search
```python
input_data = {
    "job_title": "Senior Software Engineer",
    "region": "San Francisco, CA"
}
```

### Advanced Search with Description
```python
input_data = {
    "job_title": "Data Scientist",
    "region": "New York, NY",
    "description": "Looking for experienced data scientists with Python, machine learning, and AWS skills. Must have 3+ years experience in fintech.",
    "search_depth": 4,
    "candidates_per_search": 15,
    "include_remote": True
}
```

## Output Format

The agent returns a comprehensive result with:

```json
{
  "status": "success",
  "result": {
    "job_title": "Senior Software Engineer",
    "region": "San Francisco, CA",
    "total_candidates": 25,
    "top_candidates": [
      {
        "name": "John Doe",
        "title": "Senior Software Engineer",
        "company": "Tech Corp",
        "skills": ["Python", "React", "AWS"],
        "confidence_score": 0.85,
        "linkedin_url": "https://linkedin.com/in/johndoe",
        "analysis": {
          "skills_match": 8,
          "experience_level": 9,
          "overall_fit": 8.5,
          "key_strengths": ["Strong Python skills", "Relevant experience"],
          "potential_concerns": ["May be overqualified"],
          "recommended_next_steps": ["Schedule screening call"]
        }
      }
    ],
    "report": "# Headhunter Report: Senior Software Engineer in San Francisco, CA\n\n## Executive Summary\nFound 25 potential candidates...",
    "all_candidates": [...],
    "search_queries": [...],
    "timestamp": "2024-01-15T10:30:00"
  }
}
```

## Search Strategy

The agent uses a sophisticated search strategy:

1. **Query Generation**: Creates multiple search variations based on job title, region, and skills
2. **LinkedIn Search**: Searches for LinkedIn profiles using web search APIs
3. **Job Board Analysis**: Finds companies hiring for similar roles
4. **Company Targeting**: Searches for candidates at companies with relevant job postings
5. **Remote Expansion**: Includes remote candidates if requested
6. **Deduplication**: Removes duplicate candidates based on LinkedIn URLs
7. **AI Analysis**: Analyzes top candidates for fit and provides recommendations

## Limitations

- **LinkedIn API Restrictions**: LinkedIn has strict API limitations, so the agent uses web search as a workaround
- **Data Quality**: Information is extracted from search snippets, which may be incomplete
- **Rate Limiting**: Web search APIs have rate limits that may affect search depth
- **Privacy**: The agent respects privacy and only uses publicly available information

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   export SERPER_API_KEY="your_key_here"
   export OPENAI_API_KEY="your_key_here"
   ```

3. **Test the Agent**:
   ```bash
   python headhunter_agent.py
   ```

## Best Practices

1. **Be Specific**: Provide detailed job descriptions for better candidate matching
2. **Use Relevant Regions**: Specify exact cities or regions for targeted searches
3. **Review Results**: Always manually review top candidates before reaching out
4. **Respect Privacy**: Only contact candidates through appropriate channels
5. **Follow Up**: Use the generated reports to guide your outreach strategy

## Legal and Ethical Considerations

- This agent only uses publicly available information
- Respect LinkedIn's terms of service and rate limits
- Always obtain proper consent before contacting candidates
- Follow local data protection and privacy laws
- Use the agent as a tool to supplement, not replace, human judgment

## Troubleshooting

### Common Issues

1. **No candidates found**: Try broadening the search region or job title
2. **Low confidence scores**: Provide more detailed job descriptions
3. **API errors**: Check your API keys and rate limits
4. **Selenium issues**: Ensure Chrome/Chromium is installed for enhanced scraping

### Getting Help

If you encounter issues:
1. Check the environment variables are set correctly
2. Verify API keys have sufficient credits
3. Review the search queries being generated
4. Check the logs for specific error messages

## Future Enhancements

Potential improvements for future versions:
- Integration with LinkedIn Talent Solutions API
- Advanced candidate scoring algorithms
- Email outreach automation
- Integration with ATS systems
- Multi-language support
- Advanced filtering options 