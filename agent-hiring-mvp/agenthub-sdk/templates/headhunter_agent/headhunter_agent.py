#!/usr/bin/env python3
"""
Headhunter Agent - A specialized agent that searches for top talent candidates on LinkedIn and the web.
"""

import json
import os
import time
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import dotenv

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Warning: Selenium not available. LinkedIn scraping will be limited.")


@dataclass
class Candidate:
    """Represents a candidate found during the search"""
    name: str
    title: str
    company: str
    location: str
    experience_years: Optional[int]
    skills: List[str]
    education: Optional[str]
    linkedin_url: Optional[str]
    source: str
    confidence_score: float
    summary: str


class HeadhunterAgent:
    """Headhunter agent that searches for top talent candidates"""

    def __init__(self):
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.linkedin_email = os.getenv("LINKEDIN_EMAIL")
        self.linkedin_password = os.getenv("LINKEDIN_PASSWORD")

        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY environment variable is required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = OpenAI(api_key=self.openai_api_key)
        self.driver = None

    def setup_selenium(self):
        """Setup Selenium WebDriver for LinkedIn scraping"""
        if not SELENIUM_AVAILABLE:
            return False

        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

            self.driver = webdriver.Chrome(
                ChromeDriverManager().install(),
                options=chrome_options
            )
            return True
        except Exception as e:
            print(f"Failed to setup Selenium: {e}")
            return False

    def cleanup_selenium(self):
        """Clean up Selenium WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def search_web(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Search the web using Serper API"""
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
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
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "domain": item.get("displayLink", "")
                })

            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def generate_search_queries(self, job_title: str, region: str, description: str = "") -> List[str]:
        """Generate search queries for finding candidates"""
        base_queries = [
            f'"{job_title}" "{region}" LinkedIn',
            f'"{job_title}" "{region}" "top talent"',
            f'"{job_title}" "{region}" "experienced"',
            f'"{job_title}" "{region}" "senior"',
            f'"{job_title}" "{region}" "expert"'
        ]

        if description:
            # Extract key skills from description
            skills_prompt = f"""Extract 3-5 key technical skills or requirements from this job description:
            {description}
            
            Return only the skills, separated by commas."""
            
            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": skills_prompt}],
                    max_tokens=100,
                    temperature=0.3
                )
                skills = response.choices[0].message.content.strip()
                if skills:
                    base_queries.append(f'"{job_title}" "{region}" {skills}')
            except Exception as e:
                print(f"Error extracting skills: {e}")

        return base_queries

    def search_linkedin_people(self, query: str, max_results: int = 10) -> List[Candidate]:
        """Search for people on LinkedIn (simulated - requires proper LinkedIn API access)"""
        candidates = []
        
        # This is a simulated search since LinkedIn has strict API limitations
        # In a real implementation, you would use LinkedIn's Talent Solutions API
        
        try:
            # Search for LinkedIn profiles using web search
            search_results = self.search_web(f'{query} site:linkedin.com/in/', max_results)
            
            for result in search_results:
                if 'linkedin.com/in/' in result['url']:
                    # Extract profile information from search snippet
                    candidate = self.extract_candidate_from_snippet(result)
                    if candidate:
                        candidates.append(candidate)
                        
        except Exception as e:
            print(f"LinkedIn search error: {e}")
            
        return candidates

    def extract_candidate_from_snippet(self, search_result: Dict[str, Any]) -> Optional[Candidate]:
        """Extract candidate information from search result snippet"""
        try:
            snippet = search_result['snippet']
            url = search_result['url']
            
            # Extract name from URL
            name_match = re.search(r'/in/([^/]+)', url)
            if not name_match:
                return None
                
            name = name_match.group(1).replace('-', ' ').title()
            
            # Extract title and company from snippet
            title = ""
            company = ""
            
            # Look for patterns like "Title at Company" or "Title • Company"
            patterns = [
                r'([^•]+)\s+at\s+([^•]+)',
                r'([^•]+)\s+•\s+([^•]+)',
                r'([^•]+)\s+-\s+([^•]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, snippet)
                if match:
                    title = match.group(1).strip()
                    company = match.group(2).strip()
                    break
            
            # Extract skills from snippet
            skills = []
            skill_keywords = ['Python', 'JavaScript', 'React', 'Node.js', 'AWS', 'Docker', 'Kubernetes', 
                            'Machine Learning', 'AI', 'Data Science', 'DevOps', 'Agile', 'Scrum']
            
            for skill in skill_keywords:
                if skill.lower() in snippet.lower():
                    skills.append(skill)
            
            # Generate confidence score based on snippet quality
            confidence_score = min(0.8, len(skills) * 0.1 + 0.3)
            
            return Candidate(
                name=name,
                title=title or "Professional",
                company=company or "Unknown",
                location="",
                experience_years=None,
                skills=skills,
                education=None,
                linkedin_url=url,
                source="LinkedIn Search",
                confidence_score=confidence_score,
                summary=snippet[:200] + "..." if len(snippet) > 200 else snippet
            )
            
        except Exception as e:
            print(f"Error extracting candidate: {e}")
            return None

    def search_job_boards(self, job_title: str, region: str) -> List[Candidate]:
        """Search job boards for active job seekers"""
        candidates = []
        
        # Search for job postings to find companies hiring for this role
        job_search_queries = [
            f'"{job_title}" "{region}" "hiring" "job"',
            f'"{job_title}" "{region}" "careers"',
            f'"{job_title}" "{region}" "opportunity"'
        ]
        
        for query in job_search_queries:
            results = self.search_web(query, 5)
            
            for result in results:
                # Extract company information from job postings
                company = self.extract_company_from_job_posting(result)
                if company:
                    # Search for people at that company with similar roles
                    company_candidates = self.search_web(f'"{job_title}" "{company}" site:linkedin.com/in/', 3)
                    for candidate_result in company_candidates:
                        candidate = self.extract_candidate_from_snippet(candidate_result)
                        if candidate:
                            candidates.append(candidate)
        
        return candidates

    def extract_company_from_job_posting(self, job_posting: Dict[str, Any]) -> Optional[str]:
        """Extract company name from job posting"""
        try:
            title = job_posting['title']
            snippet = job_posting['snippet']
            
            # Look for company patterns
            patterns = [
                r'at\s+([A-Z][a-zA-Z\s&]+)',
                r'-\s+([A-Z][a-zA-Z\s&]+)',
                r'([A-Z][a-zA-Z\s&]+)\s+is\s+hiring'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, title + " " + snippet)
                if match:
                    company = match.group(1).strip()
                    # Clean up company name
                    company = re.sub(r'\s+', ' ', company)
                    return company
            
            return None
            
        except Exception as e:
            print(f"Error extracting company: {e}")
            return None

    def analyze_candidate_fit(self, candidate: Candidate, job_title: str, description: str) -> Dict[str, Any]:
        """Analyze how well a candidate fits the job requirements"""
        try:
            prompt = f"""Analyze this candidate's fit for a {job_title} position:

Candidate:
- Name: {candidate.name}
- Current Title: {candidate.title}
- Company: {candidate.company}
- Skills: {', '.join(candidate.skills)}
- Summary: {candidate.summary}

Job Description: {description if description else 'Standard requirements for ' + job_title}

Rate the candidate on:
1. Skills Match (0-10)
2. Experience Level (0-10)
3. Overall Fit (0-10)
4. Key Strengths (list)
5. Potential Concerns (list)
6. Recommended Next Steps

Return as JSON with these fields."""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3
            )

            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

            analysis = json.loads(content)
            return analysis
            
        except Exception as e:
            print(f"Error analyzing candidate fit: {e}")
            return {
                "skills_match": 5,
                "experience_level": 5,
                "overall_fit": 5,
                "key_strengths": ["Unable to analyze"],
                "potential_concerns": ["Analysis failed"],
                "recommended_next_steps": ["Manual review required"]
            }

    def generate_candidate_report(self, candidates: List[Candidate], job_title: str, region: str) -> str:
        """Generate a comprehensive candidate report"""
        if not candidates:
            return "No candidates found for the specified criteria."

        # Sort candidates by confidence score
        candidates.sort(key=lambda x: x.confidence_score, reverse=True)

        report = f"""# Headhunter Report: {job_title} in {region}

## Executive Summary
Found {len(candidates)} potential candidates for the {job_title} position in {region}.

## Top Candidates

"""

        for i, candidate in enumerate(candidates[:10], 1):
            report += f"""### {i}. {candidate.name}
- **Current Role**: {candidate.title} at {candidate.company}
- **Skills**: {', '.join(candidate.skills) if candidate.skills else 'Not specified'}
- **Confidence Score**: {candidate.confidence_score:.2f}/1.0
- **LinkedIn**: {candidate.linkedin_url if candidate.linkedin_url else 'Not available'}
- **Summary**: {candidate.summary}

"""

        report += f"""
## Search Statistics
- Total candidates found: {len(candidates)}
- Average confidence score: {sum(c.confidence_score for c in candidates) / len(candidates):.2f}
- Sources: LinkedIn, Job Boards, Web Search

## Next Steps
1. Review top 5 candidates in detail
2. Reach out to candidates with confidence scores > 0.6
3. Schedule initial screening calls
4. Request detailed resumes and portfolios

## Search Details
- Job Title: {job_title}
- Region: {region}
- Search completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report

    def headhunt(self, job_title: str, region: str, description: str = "", 
                search_depth: int = 3, candidates_per_search: int = 10, 
                include_remote: bool = True) -> Dict[str, Any]:
        """Main headhunting function"""
        print(f"Starting headhunting search for: {job_title} in {region}")
        print(f"Search depth: {search_depth}, Candidates per search: {candidates_per_search}")

        all_candidates = []
        
        try:
            # Setup Selenium if available
            selenium_available = self.setup_selenium()

            # Generate search queries
            search_queries = self.generate_search_queries(job_title, region, description)
            search_queries = search_queries[:search_depth]

            for i, query in enumerate(search_queries):
                print(f"\nSearch {i + 1}/{len(search_queries)}: {query}")

                # Search LinkedIn
                linkedin_candidates = self.search_linkedin_people(query, candidates_per_search)
                all_candidates.extend(linkedin_candidates)

                # Search job boards
                job_board_candidates = self.search_job_boards(job_title, region)
                all_candidates.extend(job_board_candidates)

                # Add remote search if requested
                if include_remote:
                    remote_query = f'{query} "remote" "work from home"'
                    remote_candidates = self.search_linkedin_people(remote_query, candidates_per_search // 2)
                    all_candidates.extend(remote_candidates)

            # Remove duplicates based on LinkedIn URL
            unique_candidates = []
            seen_urls = set()
            
            for candidate in all_candidates:
                if candidate.linkedin_url and candidate.linkedin_url in seen_urls:
                    continue
                if candidate.linkedin_url:
                    seen_urls.add(candidate.linkedin_url)
                unique_candidates.append(candidate)

            print(f"\nHeadhunting completed!")
            print(f"Total unique candidates found: {len(unique_candidates)}")

            # Analyze top candidates
            top_candidates = unique_candidates[:5]
            candidate_analyses = []
            
            for candidate in top_candidates:
                analysis = self.analyze_candidate_fit(candidate, job_title, description)
                candidate_analyses.append({
                    "candidate": candidate,
                    "analysis": analysis
                })

            # Generate final report
            final_report = self.generate_candidate_report(unique_candidates, job_title, region)

            return {
                "job_title": job_title,
                "region": region,
                "description": description,
                "total_candidates": len(unique_candidates),
                "top_candidates": [
                    {
                        "name": c["candidate"].name,
                        "title": c["candidate"].title,
                        "company": c["candidate"].company,
                        "skills": c["candidate"].skills,
                        "confidence_score": c["candidate"].confidence_score,
                        "linkedin_url": c["candidate"].linkedin_url,
                        "analysis": c["analysis"]
                    }
                    for c in candidate_analyses
                ],
                "report": final_report,
                "all_candidates": [
                    {
                        "name": c.name,
                        "title": c.title,
                        "company": c.company,
                        "skills": c.skills,
                        "confidence_score": c.confidence_score,
                        "linkedin_url": c.linkedin_url,
                        "source": c.source
                    }
                    for c in unique_candidates
                ],
                "search_queries": search_queries,
                "timestamp": datetime.now().isoformat()
            }

        finally:
            # Cleanup
            self.cleanup_selenium()


def execute(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point for the headhunter agent"""
    try:
        # Load environment variables
        dotenv.load_dotenv()

        # Extract parameters
        job_title = input_data.get("job_title", config.get("job_title", "Software Engineer"))
        region = input_data.get("region", config.get("region", "San Francisco, CA"))
        description = input_data.get("description", config.get("description", ""))
        search_depth = input_data.get("search_depth", config.get("search_depth", 3))
        candidates_per_search = input_data.get("candidates_per_search", config.get("candidates_per_search", 10))
        include_remote = input_data.get("include_remote", config.get("include_remote", True))

        # Create and run headhunter agent
        agent = HeadhunterAgent()
        result = agent.headhunt(
            job_title=job_title,
            region=region,
            description=description,
            search_depth=search_depth,
            candidates_per_search=candidates_per_search,
            include_remote=include_remote
        )

        return {
            "status": "success",
            "result": result
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "result": None
        }


if __name__ == "__main__":
    # Test the agent
    test_input = {
        "job_title": "AI researcher",
        "region": "Israel",
        "description": "have extensive experience in enterprises with large language models, especially in the context of AI and machine learning.",
        "search_depth": 3,
        "candidates_per_search": 10
    }
    
    test_config = {
        "job_title": "AI researcher",
        "region": "Israel",
        "description": "have extensive experience in enterprises with large language models, especially in the context of AI and machine learning.",
        "search_depth": 3,
        "candidates_per_search": 10,
        "include_remote": True
    }
    
    result = main(test_input, test_config)
    print(json.dumps(result, indent=2)) 