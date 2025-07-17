"""
Prompts for ACL Review Agent
Contains all the prompts used for generating reviews, analyzing papers, and extracting information.
"""

# Literature Review Prompts
LITERATURE_QUERIES_PROMPT = """Generate effective search queries for finding related academic papers and literature for this paper:

Title: {title}
Abstract: {abstract}
Authors: {authors}

Generate {depth} diverse search queries that would help find:
1. Directly related papers on the same topic
2. Papers using similar methodologies
3. Papers by the same authors
4. Papers in the same research area
5. Recent developments in this field

Each query should be:
- Specific enough to find relevant papers
- Broad enough to capture related work
- Include key technical terms and concepts
- Use appropriate academic search syntax

Return only the search queries as a JSON list of strings, one per line.
Example format: ["query 1", "query 2", "query 3"]"""

KEY_TERMS_PROMPT = """Extract the most important technical terms and concepts from this text for academic search purposes:

Text: {text}

Identify 10-15 key terms that would be most useful for finding related academic papers. Focus on:
- Technical concepts and methodologies
- Domain-specific terminology
- Novel approaches or techniques mentioned
- Important keywords for literature search

Return only the key terms as a JSON list of strings.
Example format: ["term1", "term2", "term3"]"""

CITED_PAPERS_PROMPT = """Extract all cited papers from the following academic paper content. For each citation, return a dictionary with at least the title and authors (if available). If possible, also include year and venue. Only include actual cited works, not section headers or unrelated text.

Content:
{content}

Return the result as a JSON list of dicts, e.g.:
[
  {"title": "Title 1", "authors": ["Author A", "Author B"], "year": 2020, "venue": "ACL"},
  {"title": "Title 2", "authors": ["Author C"], "year": 2019}
]"""

# Analysis Prompts
CONTRIBUTIONS_ANALYSIS_PROMPT = """Analyze the contributions of this paper:

Title: {title}
Abstract: {abstract}

Identify and rate the following aspects:
1. Novelty of the approach/methodology
2. Technical contribution
3. Empirical contribution
4. Practical impact
5. Theoretical contribution

For each aspect, provide:
- A score from 1-5 (5 being highest)
- A brief explanation
- Specific examples from the paper

Return as JSON with these fields."""

GAPS_ANALYSIS_PROMPT = """Based on this paper and related work, identify the research gaps that this paper addresses:

Paper: {title}
Abstract: {abstract}

Related Work:
{related_summary}

Identify 3-5 specific research gaps that this paper fills. Be specific and concrete.

Return as a JSON list of strings."""

METHODOLOGY_COMPARISON_PROMPT = """Compare the methodology of this paper with related work:

Paper: {title}
Abstract: {abstract}

Related Work:
{related_summary}

Analyze:
1. How does the methodology differ from existing approaches?
2. What are the advantages of this approach?
3. What are the potential limitations?
4. How does it compare in terms of complexity and efficiency?

Return as JSON with these fields."""

# Review Generation Prompts
PAPER_SUMMARY_PROMPT = """{style_note}Provide a concise summary of this paper for ACL ARR review:

Title: {title}
Abstract: {abstract}

Summarize the paper in 2-3 paragraphs, covering:
1. Main problem/objective
2. Key methodology/approach
3. Main results/findings
4. Significance/impact

Focus on what makes this paper interesting and important.
Maximum length: 1000 characters."""

STRENGTHS_PROMPT = """{style_note}Analyze the strengths of this paper for ACL ARR review following these guidelines:

{arr_guidelines}

SUMMARY OF STRENGTHS GUIDELINES:
What are the major reasons to publish this paper at a selective *ACL venue? These could include novel and useful methodology, insightful empirical results or theoretical analysis, clear organization of related literature, or any other reason why interested readers of *ACL papers may find the paper useful. Maximum length 20000 characters.

Paper Information:
Title: {title}
Abstract: {abstract}

{literature_info}

Identify the major reasons to publish this paper at a selective ACL venue. Consider:
1. Novel and useful methodology
2. Insightful empirical results or theoretical analysis
3. Clear organization of related literature
4. Significant impact on the field
5. Technical soundness
6. Practical applications

Maximum length: 20000 characters. Be specific and provide concrete examples."""

# Additional Review Generation Prompts
WEAKNESSES_PROMPT = """{style_note}Analyze the weaknesses of this paper for ACL ARR review:

Title: {title}
Abstract: {abstract}

Literature Review Findings:
{literature_info}

Identify concerns that would cause you to favor other high-quality papers. Consider:
1. Correctness of results or argumentation
2. Limited perceived impact
3. Lack of clarity in exposition
4. Methodological issues
5. Insufficient experimental validation
6. Weak theoretical foundations

IMPORTANT: Do not repeat limitations mentioned in the paper's own limitations section unless they are major weaknesses.

Number your concerns so authors can respond individually.
Maximum length: {max_chars} characters. Be constructive and specific."""

COMMENTS_SUGGESTIONS_PROMPT = """{style_note}Provide comments and suggestions for improving this paper:

Title: {title}
Abstract: {abstract}

Provide constructive feedback on:
1. Writing clarity and organization
2. Experimental design improvements
3. Additional experiments that could strengthen the paper
4. Presentation of results
5. Discussion of limitations
6. Future work directions
7. Minor issues (typos, formatting, etc.)

Focus on actionable suggestions that would improve the paper.
Maximum length: {max_chars} characters."""

RATINGS_PROMPT = """Rate this paper for ACL ARR review:

Title: {title}
Abstract: {abstract}

Literature Review:
{literature_info}

Provide ratings for:

1. CONFIDENCE (1-5):
5 = Positive that my evaluation is correct
4 = Quite sure
3 = Pretty sure, but there's a chance I missed something
2 = Willing to defend, but likely missed some details
1 = Not my area, or paper is very hard to understand

2. SOUNDNESS (1-5):
5 = Excellent: One of the most thorough studies
4 = Strong: Sufficient support for all claims
3 = Acceptable: Sufficient support for major claims
2 = Poor: Main claims not sufficiently supported
1 = Major Issues: Not ready for publication

3. OVERALL ASSESSMENT (0-5):
5 = Top-Notch: One of the best papers recently
4 = Solid work of significant interest
3 = Good: Reasonable contribution
2 = Revisions Needed: Some merit but significant flaws
1 = Major Revisions Needed: Significant flaws
0 = Not relevant to ACL community

Return as JSON with these three fields."""

BEST_PAPER_PROMPT = """Assess if this paper merits consideration for an outstanding paper award:

Title: {title}
Abstract: {abstract}

Literature Review:
{literature_info}

Outstanding papers should be either:
- Fascinating
- Controversial
- Surprising
- Impressive
- Potentially field-changing

Answer: Yes/Maybe/No
If Yes or Maybe, provide brief justification (max {max_chars} characters).

Return as JSON with 'decision' and 'justification' fields."""

ADDITIONAL_INSIGHTS_PROMPT = """Provide additional insights for the reviewer about this paper:

Title: {title}
Abstract: {abstract}

Literature Review:
{literature_info}

Provide insights on:
1. Key papers to compare against
2. Potential conflicts with existing work
3. Areas where the paper could be strengthened
4. Questions to ask during discussion
5. Potential impact on the field
6. Reviewer expertise needed

Return as JSON with these fields."""

# Reviewer Style Analysis Prompt
REVIEWER_STYLE_PROMPT = """Analyze the following reviews to summarize the reviewer's style, tone, and typical feedback patterns. Provide a concise summary that can be used to guide the writing of new reviews.

Reviews:
{reviews}"""

# Literature Review Info Templates
LITERATURE_INFO_TEMPLATE = """Literature Review Findings:
- Novelty Score: {novelty_score}
- Key Contributions: {contribution_analysis}
- Research Gaps Addressed: {gaps_identified}
- Most Similar Papers: {similar_papers_count}
- OpenReview Reviews Found: {openreview_count}"""

LITERATURE_INFO_WEAKNESSES_TEMPLATE = """Literature Review Findings:
- Novelty Score: {novelty_score}
- Methodology Comparison: {methodology_comparison}"""

LITERATURE_INFO_RATINGS_TEMPLATE = """Literature Review:
- Novelty Score: {novelty_score}
- Contributions: {contribution_analysis}"""

LITERATURE_INFO_BEST_PAPER_TEMPLATE = """Literature Review:
- Novelty Score: {novelty_score}
- Contributions: {contribution_analysis}"""

LITERATURE_INFO_INSIGHTS_TEMPLATE = """Literature Review:
- Novelty Score: {novelty_score}
- Related Papers: {related_papers_count}
- Gaps Identified: {gaps_identified}"""

# Default messages
LITERATURE_REVIEW_NOT_PERFORMED = "Literature Review not performed" 