#!/usr/bin/env python3
"""
academic_research - This agent performs academic research by searching across multiple academic sources
including Semantic Scholar, arXiv, and Google Scholar to find papers, summarize research, and identify gaps.
"""

import json
import os
import requests
import time
import tempfile
from typing import List, Dict, Any, Optional
from openai import OpenAI
import dotenv
from urllib.parse import quote_plus, urlparse
import PyPDF2
import io


class AcademicResearchAgent:

    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.model = model

        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY environment variable is required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = OpenAI(api_key=self.openai_api_key)

    def is_pdf_url(self, url: str) -> bool:
        """Check if URL is likely to be a PDF"""
        url_lower = url.lower()
        
        # Direct PDF indicators
        if url_lower.endswith('.pdf'):
            return True
        
        # Common PDF URL patterns
        pdf_patterns = [
            '/pdf/', '/paper/', '/document/', '/file/',
            'pdf', 'paper', 'document', 'file'
        ]
        
        for pattern in pdf_patterns:
            if pattern in url_lower:
                return True
        
        return False
    
    def extract_pdf_urls_from_content(self, content: str) -> List[str]:
        """Extract PDF URLs from text content"""
        import re
        
        pdf_urls = []
        
        # Common PDF URL patterns
        patterns = [
            r'https?://[^\s<>"]+\.pdf',  # Direct PDF links
            r'https?://[^\s<>"]+/pdf/[^\s<>"]+',  # PDF directory links
            r'https?://[^\s<>"]+/paper/[^\s<>"]+',  # Paper links
            r'https?://[^\s<>"]+/document/[^\s<>"]+',  # Document links
            r'https?://arxiv\.org/abs/[^\s<>"]+',  # arXiv links (can be converted to PDF)
            r'https?://[^\s<>"]+/download/[^\s<>"]+',  # Download links
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            pdf_urls.extend(matches)
        
        # Remove duplicates and clean URLs
        unique_urls = []
        for url in pdf_urls:
            url = url.strip('.,;:!?()[]{}"\'').strip()
            if url not in unique_urls and self.is_pdf_url(url):
                unique_urls.append(url)
        
        return unique_urls
    
    def convert_arxiv_to_pdf_url(self, url: str) -> str:
        """Convert arXiv abstract URL to PDF URL"""
        if 'arxiv.org/abs/' in url:
            return url.replace('/abs/', '/pdf/') + '.pdf'
        return url
    
    def download_and_read_pdf(self, url: str) -> Optional[str]:
        """Download and extract text from a PDF URL"""
        try:
            # Convert arXiv URLs to PDF URLs
            if 'arxiv.org/abs/' in url:
                url = self.convert_arxiv_to_pdf_url(url)
            
            # Download the content
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Check if it's actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            content_length = len(response.content)
            
            # Better PDF detection
            is_pdf = (
                'pdf' in content_type or 
                url.lower().endswith('.pdf') or
                response.content.startswith(b'%PDF') or  # PDF magic number
                (content_length > 1000 and b'%PDF' in response.content[:1000])  # PDF magic number in first 1KB
            )
            
            if not is_pdf:
                print(f"URL does not appear to be a PDF: {url} (Content-Type: {content_type})")
                return None
            
            # Read PDF content
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from all pages
            text_content = ""
            for page_num in range(min(len(pdf_reader.pages), 10)):  # Limit to first 10 pages
                try:
                    page = pdf_reader.pages[page_num]
                    text_content += page.extract_text() + "\n"
                except Exception as e:
                    print(f"Error extracting text from page {page_num}: {e}")
                    continue
            
            return text_content.strip() if text_content else None
            
        except Exception as e:
            print(f"Error downloading/reading PDF from {url}: {e}")
            return None

    def extract_pdf_content(self, pdf_content: str, max_length: int = 3000) -> str:
        """Extract and clean PDF content for analysis"""
        if not pdf_content:
            return ""
        
        # Clean the text
        cleaned_text = pdf_content.replace('\n', ' ').replace('\r', ' ')
        cleaned_text = ' '.join(cleaned_text.split())  # Remove extra whitespace
        
        # Extract key sections (abstract, introduction, conclusion)
        sections = []
        
        # Look for common section headers
        section_keywords = ['abstract', 'introduction', 'conclusion', 'summary', 'results', 'discussion']
        text_lower = cleaned_text.lower()
        
        for keyword in section_keywords:
            if keyword in text_lower:
                # Find the section
                start_idx = text_lower.find(keyword)
                if start_idx != -1:
                    # Extract a reasonable amount of text after the section header
                    end_idx = min(start_idx + 1000, len(cleaned_text))
                    section_text = cleaned_text[start_idx:end_idx]
                    sections.append(f"{keyword.title()}: {section_text}")
        
        # If no sections found, take the beginning
        if not sections:
            sections.append(cleaned_text[:max_length])
        
        # Combine sections and limit length
        combined_text = " ".join(sections)
        if len(combined_text) > max_length:
            combined_text = combined_text[:max_length] + "..."
        
        return combined_text

    def search_semantic_scholar(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Semantic Scholar for academic papers"""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,abstract,authors.name,year,venue,citationCount,influentialCitationCount,url,paperId"
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for paper in data.get("data", []):
                if not paper or not isinstance(paper, dict):
                    continue
                    
                authors = []
                if paper.get("authors"):
                    authors = [author.get("name", "") for author in paper.get("authors", []) if author and isinstance(author, dict)]
                
                results.append({
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", ""),
                    "authors": authors,
                    "year": paper.get("year"),
                    "venue": paper.get("venue", ""),
                    "citation_count": paper.get("citationCount", 0),
                    "influential_citations": paper.get("influentialCitationCount", 0),
                    "url": paper.get("url", ""),
                    "paper_id": paper.get("paperId", ""),
                    "source": "semantic_scholar"
                })

            return results
        except Exception as e:
            print(f"Semantic Scholar search error: {e}")
            return []

    def search_arxiv(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search arXiv for papers"""
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            # Parse XML response (simplified)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            results = []
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                title = entry.find(".//{http://www.w3.org/2005/Atom}title")
                summary = entry.find(".//{http://www.w3.org/2005/Atom}summary")
                published = entry.find(".//{http://www.w3.org/2005/Atom}published")
                link = entry.find(".//{http://www.w3.org/2005/Atom}link")
                
                # Extract authors
                authors = []
                for author in entry.findall(".//{http://www.w3.org/2005/Atom}author"):
                    name = author.find(".//{http://www.w3.org/2005/Atom}name")
                    if name is not None:
                        authors.append(name.text)
                
                results.append({
                    "title": title.text if title is not None else "",
                    "abstract": summary.text if summary is not None else "",
                    "authors": authors,
                    "year": published.text[:4] if published is not None else None,
                    "venue": "arXiv",
                    "citation_count": 0,  # arXiv doesn't provide citation count
                    "influential_citations": 0,
                    "url": link.get("href") if link is not None else "",
                    "paper_id": "",
                    "source": "arxiv"
                })

            return results
        except Exception as e:
            print(f"arXiv search error: {e}")
            return []

    def search_google_scholar(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google Scholar using Serper API"""
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": f"{query} site:scholar.google.com",
            "num": num_results
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "abstract": item.get("snippet", ""),
                    "authors": [],  # Google Scholar doesn't provide structured author data
                    "year": None,
                    "venue": item.get("displayLink", ""),
                    "citation_count": 0,
                    "influential_citations": 0,
                    "url": item.get("link", ""),
                    "paper_id": "",
                    "source": "google_scholar"
                })

            return results
        except Exception as e:
            print(f"Google Scholar search error: {e}")
            return []

    def generate_search_queries(self, research_topic: str, num_queries: int = 4) -> List[str]:
        """Generate academic search queries for the research topic"""
        prompt = f"""Given the academic research topic: "{research_topic}", generate {num_queries} specific academic search queries to investigate this topic thoroughly. 
        
        Focus on:
        1. Core concepts and terminology
        2. Recent developments and trends
        3. Key researchers and institutions
        4. Related methodologies or approaches
        
        Each query should be unique and target different aspects of the topic.
        Return only the queries, one per line. Do not include any quotes or numbering, just the search query."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )

            queries = response.choices[0].message.content.strip().split('\n')
            return [q.strip() for q in queries if q.strip()][:num_queries]
        except Exception as e:
            print(f"Error generating queries: {e}")
            return [research_topic]

    def analyze_papers(self, query: str, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze academic papers and extract key insights, including PDF content"""
        if not papers:
            return {"key_findings": [], "research_gaps": [], "trends": [], "pdfs_analyzed": 0}

        # Prepare papers for analysis
        papers_analysis = []
        pdfs_analyzed = 0
        
        for i, paper in enumerate(papers):
            title = paper.get('title', 'Unknown Title')
            abstract = paper.get('abstract', '')
            authors = paper.get('authors', [])
            year = paper.get('year', 'Unknown')
            venue = paper.get('venue', 'Unknown')
            citation_count = paper.get('citation_count', 0)
            source = paper.get('source', 'unknown')
            
            # Handle None values safely
            if title is None:
                title = 'Unknown Title'
            if abstract is None:
                abstract = ''
            if authors is None:
                authors = []
            if year is None:
                year = 'Unknown'
            if venue is None:
                venue = 'Unknown'
            if citation_count is None:
                citation_count = 0
            
            # Safely slice abstract
            abstract_preview = abstract[:500] + "..." if len(abstract) > 500 else abstract
            
            paper_info = f"Title: {title}\nAbstract: {abstract_preview}\nAuthors: {', '.join(authors) if authors else 'Unknown'}\nYear: {year}\nVenue: {venue}\nCitations: {citation_count}\nSource: {source}"
            
            # Try to get PDF content from the paper's URL
            pdf_content = ""
            pdf_analyzed = False
            
            # Check if the paper's URL is a PDF
            if paper.get('url') and self.is_pdf_url(paper['url']):
                title = paper.get('title', 'Unknown')
                if title is None:
                    title = 'Unknown'
                print(f"  Downloading PDF for paper {i+1}: {title[:50]}...")
                pdf_raw = self.download_and_read_pdf(paper['url'])
                if pdf_raw:
                    pdf_content = self.extract_pdf_content(pdf_raw)
                    paper_info += f"\nPDF Content: {pdf_content}"
                    pdfs_analyzed += 1
                    pdf_analyzed = True
            
            # If no PDF found in URL, try to extract PDF URLs from abstract/content
            if not pdf_analyzed:
                # Extract PDF URLs from abstract
                abstract_text = paper.get('abstract', '')
                pdf_urls = self.extract_pdf_urls_from_content(abstract_text) if abstract_text else []
                
                # Also check the paper's URL if it's not already a PDF
                paper_url = paper.get('url', '')
                if paper_url:
                    url_pdf_urls = self.extract_pdf_urls_from_content(paper_url)
                    pdf_urls.extend(url_pdf_urls)
                
                # Try each extracted PDF URL
                for pdf_url in pdf_urls[:2]:  # Limit to first 2 PDF URLs found
                    if not pdf_analyzed:  # Only try if we haven't already analyzed a PDF
                        print(f"  Found PDF URL in content for paper {i+1}: {pdf_url}")
                        pdf_raw = self.download_and_read_pdf(pdf_url)
                        if pdf_raw:
                            pdf_content = self.extract_pdf_content(pdf_raw)
                            paper_info += f"\nPDF Content: {pdf_content}"
                            pdfs_analyzed += 1
                            pdf_analyzed = True
                            break  # Stop after first successful PDF
            
            papers_analysis.append(paper_info)
        
        papers_text = "\n\n---\n\n".join(papers_analysis)

        prompt = f"""Analyze the following academic papers for the query: "{query}"

Papers:
{papers_text}

Extract key insights and identify research gaps. Return a JSON object with:
- "key_findings": List of main findings from the papers (3-5 items)
- "research_gaps": List of identified research gaps or areas needing more study (2-3 items)
- "trends": List of emerging trends or patterns in the research (2-3 items)
- "quality_assessment": Brief assessment of paper quality and relevance"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.3
            )

            content = response.choices[0].message.content.strip()
            # Try to extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            analysis = json.loads(content)
            analysis["pdfs_analyzed"] = pdfs_analyzed
            return analysis
        except Exception as e:
            print(f"Error analyzing papers: {e}")
            return {"key_findings": [], "research_gaps": [], "trends": [], "pdfs_analyzed": pdfs_analyzed}

    def generate_research_summary(self, research_topic: str, all_papers: List[Dict[str, Any]], 
                                all_findings: List[str], all_gaps: List[str], all_trends: List[str]) -> str:
        """Generate a comprehensive academic research summary"""
        
        # Group papers by source
        papers_by_source = {}
        for paper in all_papers:
            source = paper.get("source", "unknown")
            if source not in papers_by_source:
                papers_by_source[source] = []
            papers_by_source[source].append(paper)

        # Create summary of papers found
        papers_summary = ""
        for source, papers in papers_by_source.items():
            papers_summary += f"\n**{source.replace('_', ' ').title()} Papers ({len(papers)}):**\n"
            for paper in papers[:3]:  # Show top 3 per source
                papers_summary += f"- {paper['title']} ({paper.get('year', 'N/A')})\n"

        findings_text = "\n".join([f"- {finding}" for finding in all_findings])
        gaps_text = "\n".join([f"- {gap}" for gap in all_gaps])
        trends_text = "\n".join([f"- {trend}" for trend in all_trends])

        prompt = f"""Write a comprehensive academic research summary on: "{research_topic}"

Papers Found:
{papers_summary}

Key Findings:
{findings_text}

Research Gaps:
{gaps_text}

Emerging Trends:
{trends_text}

Write a detailed academic summary (2-3 pages) that:
1. Synthesizes the current state of research
2. Highlights key findings and contributions
3. Identifies gaps and opportunities for future research
4. Discusses emerging trends and directions
5. Provides recommendations for researchers

Use markdown format with proper academic structure."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating summary: {e}")
            return f"Error generating summary: {e}"

    def research(self, topic: str, max_papers_per_source: int = 10, search_depth: int = 2, model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
        """Main academic research function"""
        print(f"Starting academic research on: {topic}")
        print(f"Max papers per source: {max_papers_per_source}, Search depth: {search_depth}")

        all_papers = []
        all_findings = []
        all_gaps = []
        all_trends = []
        total_pdfs_analyzed = 0

        # Generate search queries
        search_queries = self.generate_search_queries(topic, 4)

        for i, query in enumerate(search_queries):
            print(f"\nResearching query {i + 1}/{len(search_queries)}: {query}")

            # Search across all sources
            semantic_papers = self.search_semantic_scholar(query, max_papers_per_source)
            arxiv_papers = self.search_arxiv(query, max_papers_per_source)
            scholar_papers = self.search_google_scholar(query, max_papers_per_source)

            # Combine and deduplicate papers
            query_papers = semantic_papers + arxiv_papers + scholar_papers
            
            # Simple deduplication by title similarity
            unique_papers = []
            seen_titles = set()
            for paper in query_papers:
                title = paper.get('title', '')
                if title is None:
                    title = ''
                title_lower = title.lower()
                if title_lower and title_lower not in seen_titles:
                    seen_titles.add(title_lower)
                    unique_papers.append(paper)

            all_papers.extend(unique_papers)

            # Analyze papers for this query
            analysis = self.analyze_papers(query, unique_papers)
            all_findings.extend(analysis.get("key_findings", []))
            all_gaps.extend(analysis.get("research_gaps", []))
            all_trends.extend(analysis.get("trends", []))
            total_pdfs_analyzed += analysis.get("pdfs_analyzed", 0)

            # Add delay to respect API limits
            time.sleep(1)

        # Remove duplicates
        all_findings = list(set(all_findings))
        all_gaps = list(set(all_gaps))
        all_trends = list(set(all_trends))

        print(f"\nResearch completed!")
        print(f"Total papers found: {len(all_papers)}")
        print(f"Total findings: {len(all_findings)}")
        print(f"Total gaps identified: {len(all_gaps)}")
        print(f"PDFs analyzed: {total_pdfs_analyzed}")

        # Generate comprehensive summary
        research_summary = self.generate_research_summary(topic, all_papers, all_findings, all_gaps, all_trends)

        return {
            "topic": topic,
            "summary": research_summary,
            "papers": all_papers,
            "key_findings": all_findings,
            "research_gaps": all_gaps,
            "emerging_trends": all_trends,
            "stats": {
                "total_papers": len(all_papers),
                "papers_by_source": {
                    "semantic_scholar": len([p for p in all_papers if p["source"] == "semantic_scholar"]),
                    "arxiv": len([p for p in all_papers if p["source"] == "arxiv"]),
                    "google_scholar": len([p for p in all_papers if p["source"] == "google_scholar"])
                },
                "total_findings": len(all_findings),
                "total_gaps": len(all_gaps),
                "total_trends": len(all_trends),
                "pdfs_analyzed": total_pdfs_analyzed
            }
        }


dotenv.load_dotenv()


def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main agent function.
    
    Args:
        input_data: User input data containing:
            - topic: The academic research topic to investigate
            - max_papers_per_source: Maximum papers to retrieve per source (default: 10)
            - search_depth: How deep to go in search queries (default: 2)
        config: Agent configuration
    
    Returns:
        Agent response with academic research results
    """

    try:
        # Extract parameters from input
        topic = input_data.get("topic", "Machine Learning in Healthcare")
        max_papers_per_source = input_data.get("max_papers_per_source", 2)
        search_depth = input_data.get("search_depth", 2)
        model = input_data.get("model", "gpt-3.5-turbo")

        # Create agent and perform research
        agent = AcademicResearchAgent(model=model)
        result = agent.research(topic, max_papers_per_source, search_depth, model)

        # Return structured response
        return {
            "topic": result["topic"],
            "summary": result["summary"],
            "papers": result["papers"],
            "key_findings": result["key_findings"],
            "research_gaps": result["research_gaps"],
            "emerging_trends": result["emerging_trends"],
            "stats": result["stats"],
            "status": "success",
            "agent": "academic_research",
            "version": "1.0.0"
        }

    except Exception as e:
        import traceback
        error_details = f"Error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(f"Academic Research Agent Error: {error_details}")
        return {
            "status": "error",
            "error": str(e),
            "error_details": error_details,
            "agent": "academic_research",
            "version": "1.0.0"
        }


if __name__ == "__main__":
    # Only run test if explicitly called as main script
    # This prevents the agent from running automatically when container starts
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test the agent
        test_input = {
            "topic": "Transformer models in natural language processing",
            "max_papers_per_source": 5,
            "search_depth": 2
        }
        
        result = main(test_input, {})
        print(json.dumps(result, indent=2))
    else:
        # Keep the container running
        import time
        while True:
            time.sleep(3600)  # Sleep for 1 hour 