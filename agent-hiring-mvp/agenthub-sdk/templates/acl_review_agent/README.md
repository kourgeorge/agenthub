# ACL Review Agent

An advanced AI agent that downloads academic papers, performs comprehensive analysis, and generates detailed ACL ARR (Action Editor Recommendation Report) reviews following official guidelines with multi-source literature analysis and similarity assessment.

## Overview

The ACL Review Agent is designed to assist reviewers and action editors in the ACL (Association for Computational Linguistics) review process by:

1. **Automatically downloading papers** from arXiv, ACL Anthology, and other sources
2. **Performing multi-source literature review** using arXiv, Semantic Scholar, Google Scholar, and OpenReview
3. **Identifying most similar papers** to help reviewers understand the research landscape
4. **Retrieving OpenReview reviews** of similar papers for context
5. **Analyzing novelty and contributions** using AI-powered assessment
6. **Generating comprehensive ACL ARR reviews** following official guidelines
7. **Providing additional insights** to help reviewers improve their assessments

## Features

### **Paper Processing**
- **Multi-source support**: arXiv, ACL Anthology, generic URLs
- **PDF text extraction**: Advanced PDF parsing with PyMuPDF and PyPDF2
- **Metadata extraction**: Title, authors, abstract, venue, year
- **Content analysis**: Full paper text analysis

### **Literature Review**
- **Multi-source search**: arXiv, Semantic Scholar, Google Scholar, and web search
- **Similar paper identification**: Finds and ranks most similar papers
- **OpenReview integration**: Retrieves reviews of similar papers
- **Novelty assessment**: Quantitative novelty scoring
- **Contribution analysis**: Detailed analysis of paper contributions
- **Gap identification**: Research gaps addressed by the paper
- **Methodology comparison**: Comparison with existing approaches

### **ACL ARR Review Generation**
- **ARR Guidelines Compliance**: Follows official ACL ARR guidelines for all sections
- **Paper Summary**: Comprehensive paper description (20,000 char limit)
- **Strengths Analysis**: Major reasons for publication (ARR compliant)
- **Weaknesses Assessment**: Concerns and limitations (numbered, ARR compliant)
- **Comments & Suggestions**: Constructive feedback for improvement
- **Confidence Rating**: Reviewer confidence (1-5 scale)
- **Soundness Assessment**: Technical soundness (1-5 scale)
- **Overall Assessment**: Publication recommendation (0-5 scale)
- **Best Paper Consideration**: Outstanding paper award assessment

### **Additional Insights**
- **Most Similar Papers**: Top similar papers with similarity scores and metadata
- **OpenReview Reviews**: Reviews of similar papers from OpenReview
- **Reviewer guidance**: Additional information for human reviewers
- **Discussion points**: Questions for review discussion
- **Expertise requirements**: Suggested reviewer expertise
- **Impact assessment**: Potential field impact analysis

## Configuration

### Required Environment Variables

```bash
# Required API Keys
SERPER_API_KEY=your_serper_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Optional API Keys (for enhanced features)
SEMANTIC_SCHOLAR_KEY=your_semantic_scholar_key_here  # Optional - provides better rate limits
OPENREVIEW_USERNAME=your_openreview_username_here    # Optional - for OpenReview integration
OPENREVIEW_PASSWORD=your_openreview_password_here    # Optional - for OpenReview integration
```

### Input Parameters

- **paper_url** (required): URL to the academic paper
- **paper_title** (optional): Title if URL not provided
- **review_depth** (optional): Depth of literature review (1-5, default: 4)
- **include_related_work** (optional): Perform literature review (default: true)
- **novelty_analysis** (optional): Analyze novelty (default: true)
- **technical_analysis** (optional): Technical analysis (default: true)
- **experimental_validation** (optional): Validate experiments (default: true)

## Usage Examples

### Basic Review
```python
input_data = {
    "paper_url": "https://arxiv.org/abs/2303.08774"
}
```

### Advanced Review with Custom Settings
```python
input_data = {
    "paper_url": "https://arxiv.org/abs/2303.08774",
    "review_depth": 5,
    "include_related_work": True,
    "novelty_analysis": True,
    "technical_analysis": True,
    "experimental_validation": True
}
```

## Output Format

The agent returns a comprehensive result with:

```json
{
  "status": "success",
  "result": {
    "paper": {
      "title": "Paper Title",
      "authors": ["Author 1", "Author 2"],
      "url": "https://arxiv.org/abs/...",
      "venue": "arXiv",
      "year": 2023
    },
    "review": {
      "paper_summary": "Comprehensive summary...",
      "strengths": "Major strengths...",
      "weaknesses": "1. First concern...\n2. Second concern...",
      "comments_suggestions": "Constructive feedback...",
      "confidence": 4,
      "soundness": 4.0,
      "overall_assessment": 4.0,
      "best_paper": "Maybe",
      "best_paper_justification": "Brief justification..."
    },
    "literature_review": {
      "novelty_score": 0.75,
      "related_papers_count": 15,
      "gaps_identified": ["Gap 1", "Gap 2"],
      "contribution_analysis": {
        "novelty": {"score": 4, "explanation": "..."},
        "technical": {"score": 4, "explanation": "..."}
      }
    },
    "additional_insights": {
      "key_papers": ["Paper 1", "Paper 2"],
      "potential_conflicts": ["Conflict 1"],
      "strengthening_areas": ["Area 1", "Area 2"]
    },
    "formatted_review": "# ACL ARR Review Report\n\n## Paper Summary\n...",
    "timestamp": "2024-01-15T10:30:00"
  }
}
```

## ACL ARR Review Format

The generated review follows the official ACL ARR format:

### **Paper Summary** (20,000 char limit)
- Clear description of the paper's topic
- Main contributions and methodology
- Key results and findings
- Helps action editors understand the work

### **Summary of Strengths** (20,000 char limit)
- Novel and useful methodology
- Insightful empirical results
- Clear organization of related literature
- Significant impact on the field

### **Summary of Weaknesses** (20,000 char limit)
- Concerns about correctness
- Limited perceived impact
- Lack of clarity in exposition
- Methodological issues
- **Note**: Does not repeat limitations mentioned in the paper unless they are major weaknesses

### **Comments, Suggestions and Typos** (20,000 char limit)
- Writing clarity improvements
- Experimental design suggestions
- Additional experiments needed
- Minor issues and typos

### **Confidence** (1-5 scale)
- 5: Positive evaluation is correct
- 4: Quite sure
- 3: Pretty sure, but may have missed something
- 2: Willing to defend, but likely missed details
- 1: Not my area or paper is hard to understand

### **Soundness** (1-5 scale)
- 5: Excellent - most thorough study
- 4: Strong - sufficient support for all claims
- 3: Acceptable - sufficient support for major claims
- 2: Poor - main claims not sufficiently supported
- 1: Major Issues - not ready for publication

### **Overall Assessment** (0-5 scale)
- 5: Top-Notch - one of the best papers recently
- 4: Solid work of significant interest
- 3: Good - reasonable contribution
- 2: Revisions Needed - some merit but significant flaws
- 1: Major Revisions Needed - significant flaws
- 0: Not relevant to ACL community

### **Best Paper Consideration**
- Yes/Maybe/No with justification
- Considers if paper is fascinating, controversial, surprising, impressive, or field-changing

## Literature Review Process

The agent performs a sophisticated literature review:

1. **Query Generation**: Creates search queries based on paper content
2. **Related Work Search**: Searches for related papers using web search
3. **Novelty Analysis**: Calculates novelty score using TF-IDF similarity
4. **Contribution Analysis**: AI-powered analysis of paper contributions
5. **Gap Identification**: Identifies research gaps addressed
6. **Methodology Comparison**: Compares with existing approaches

## Technical Implementation

### **Paper Download**
- **arXiv**: Uses arxiv library for metadata and PDF download
- **ACL Anthology**: Web scraping with BeautifulSoup
- **Generic URLs**: PDF download and text extraction

### **Text Processing**
- **PDF Extraction**: PyMuPDF (primary) and PyPDF2 (fallback)
- **Text Analysis**: NLTK for tokenization and processing
- **Similarity Calculation**: TF-IDF and cosine similarity

### **AI Analysis**
- **OpenAI GPT-4**: For comprehensive analysis and review generation
- **Structured Output**: JSON parsing for consistent results
- **Context-Aware**: Uses paper content and literature review findings

## Setup Instructions

### Option 1: Automatic Installation (Recommended)
```bash
python install_dependencies.py
```

### Option 2: Manual Installation
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   **Note for Python 3.13+ users**: If you encounter `urllib3` compatibility issues, use the automatic installation script or manually install:
   ```bash
   pip install 'urllib3>=2.0.0' 'requests>=2.31.0'
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   export SERPER_API_KEY="your_key_here"
   export OPENAI_API_KEY="your_key_here"
   export SEMANTIC_SCHOLAR_KEY="your_key_here"  # Optional
   ```

3. **Test the Agent**:
   ```bash
   python test_acl_review.py
   ```

## Best Practices

1. **Use Specific URLs**: Provide direct links to papers for best results
2. **Review Generated Content**: Always review and edit the generated review
3. **Verify Claims**: Cross-check important claims and assessments
4. **Add Personal Insights**: Supplement with domain-specific knowledge
5. **Consider Context**: Adjust ratings based on paper length and venue

## Limitations

- **PDF Quality**: Text extraction depends on PDF quality
- **API Limits**: Web search and AI APIs have rate limits
- **Domain Expertise**: May miss domain-specific nuances
- **Bias**: Inherits biases from training data
- **Novelty Assessment**: Based on available related work

## Ethical Considerations

- **Academic Integrity**: Use as a tool to assist, not replace human judgment
- **Confidentiality**: Respect paper confidentiality during review process
- **Attribution**: Acknowledge AI assistance in review process
- **Quality Control**: Ensure generated reviews meet academic standards
- **Bias Awareness**: Be aware of potential biases in AI-generated content

## Troubleshooting

### Common Issues

1. **PDF Download Fails**: Check URL accessibility and PDF availability
2. **Text Extraction Poor**: Try different PDF sources or formats
3. **API Errors**: Check API keys and rate limits
4. **Review Quality**: Adjust review_depth and analysis parameters

### Getting Help

If you encounter issues:
1. Check environment variables are set correctly
2. Verify API keys have sufficient credits
3. Test with a simple arXiv paper first
4. Review the logs for specific error messages

## Future Enhancements

Potential improvements for future versions:
- Integration with Semantic Scholar API
- Citation network analysis
- Multi-language paper support
- Conference-specific review formats
- Collaborative review features
- Review quality assessment
- Integration with review management systems 