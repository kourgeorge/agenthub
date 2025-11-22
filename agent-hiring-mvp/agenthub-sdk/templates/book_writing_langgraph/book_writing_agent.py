#!/usr/bin/env python3
"""
Book Writing Agent - A simple LangGraph-based agent that creates a complete book.

This agent uses LangGraph to:
1. Research the topic
2. Generate a book outline
3. Extract chapters from the outline
4. Write each chapter
5. Assemble the complete book
"""

import os
import re
import json
from typing import Dict, Any, Optional, List, TypedDict
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage


def get_search_tool():
    """Get the best available search tool (Tavily > SerpAPI > Serper > DuckDuckGo)"""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    serpapi_api_key = os.getenv("SERPAPI_API_KEY")
    serper_api_key = os.getenv("SERPER_API_KEY")
    
    if tavily_api_key:
        try:
            from tavily import TavilyClient
            class TavilySearchTool:
                def __init__(self, api_key):
                    self.client = TavilyClient(api_key=api_key)
                
                def run(self, query: str) -> str:
                    response = self.client.search(query, max_results=5)
                    results = []
                    for item in response.get('results', [])[:5]:
                        title = item.get('title', '')
                        content = item.get('content', '')
                        url = item.get('url', '')
                        if title or content:
                            results.append(f"{title}: {content}")
                    return '\n'.join(results) if results else "No results found"
            return TavilySearchTool(tavily_api_key)
        except ImportError:
            pass
    
    if serpapi_api_key:
        try:
            from serpapi import GoogleSearch
            
            class SerpAPISearchTool:
                def __init__(self, api_key):
                    self.api_key = api_key
                
                def run(self, query: str) -> str:
                    params = {
                        "q": query,
                        "api_key": self.api_key
                    }
                    search = GoogleSearch(params)
                    results_dict = search.get_dict()
                    
                    # Extract results
                    results = []
                    
                    # Include AI overview if available
                    # if "ai_overview" in results_dict and results_dict["ai_overview"]:
                    #     results.append(f"AI Overview: {results_dict['ai_overview']}")
                    
                    # Extract organic results
                    organic_results = results_dict.get("organic_results", [])
                    for item in organic_results[:5]:
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        date = item.get("date", "")
                        link = item.get("link", "")
                        if title or snippet:
                            results.append(f"{title}: {snippet}; {link}; {date}")
                    
                    return '\n'.join(results) if results else "No results found"
            
            return SerpAPISearchTool(serpapi_api_key)
        except ImportError:
            pass
        except Exception as e:
            # Fall back to next option if SerpAPI fails
            pass
    
    if serper_api_key:
        try:
            # Use GoogleSerperAPIWrapper from langchain_community
            search = GoogleSerperAPIWrapper(serper_api_key=serper_api_key)
            return search
        except Exception as e:
            # Fall back to DuckDuckGo if Serper initialization fails
            pass
    
    return DuckDuckGoSearchRun()


def search_arxiv(query: str, max_results: int = 5) -> str:
    """Search arXiv for academic papers"""
    try:
        import arxiv
        
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        results = []
        for paper in search.results():
            title = paper.title
            authors = ', '.join([author.name for author in paper.authors[:3]])
            summary = paper.summary[:300] + "..." if len(paper.summary) > 300 else paper.summary
            published = paper.published.strftime("%Y-%m-%d") if paper.published else ""
            link = paper.entry_id
            
            results.append(f"Title: {title}\nAuthors: {authors}\nPublished: {published}\nSummary: {summary}\nLink: {link}")
        
        return '\n\n'.join(results) if results else "No arXiv results found"
    except ImportError:
        return "arXiv library not available. Install with: pip install arxiv"
    except Exception as e:
        return f"arXiv search error: {str(e)}"


def search_wikipedia(query: str, max_results: int = 3) -> str:
    """Search Wikipedia for information"""
    try:
        wikipedia = WikipediaAPIWrapper()
        # WikipediaQueryRun uses WikipediaAPIWrapper internally
        wiki_tool = WikipediaQueryRun(api_wrapper=wikipedia)
        results = wiki_tool.run(query)
        return results if results else "No Wikipedia results found"
    except Exception as e:
        return f"Wikipedia search error: {str(e)}"


class BookState(TypedDict):
    """State for the book writing workflow"""
    topic: str
    goal: str
    book_purpose: str
    target_reader: str
    research: str
    outline: str
    chapters: List[Dict[str, str]]
    book: str
    current_chapter_index: int
    current_chapter_questions: List[str]
    current_chapter_research: str
    book_folder: str
    current_chapter_critique: str


def create_llm(model_name: str = None, temperature: float = 0.7):
    """Create LLM instance - supports both OpenAI and Azure OpenAI"""
    model_name = model_name or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", str(temperature)))
    
    azure_api_key = os.getenv("AZURE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_API_BASE") or os.getenv("AZURE_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_version = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")
    
    if azure_api_key and azure_endpoint:
        deployment_name = model_name.replace("azure/", "")
        base_endpoint = azure_endpoint
        if "/openai/deployments/" in base_endpoint:
            base_endpoint = base_endpoint.split("/openai/deployments/")[0]
        if not base_endpoint.endswith("/"):
            base_endpoint = base_endpoint.rstrip("/")
        
        return AzureChatOpenAI(
            azure_endpoint=base_endpoint,
            azure_deployment=deployment_name,
            api_key=azure_api_key,
            api_version=azure_api_version,
            temperature=temperature
        )
    else:
        return ChatOpenAI(
            model=model_name,
            temperature=temperature
        )


def enhance_book_description(state: BookState) -> BookState:
    """Enhance and augment the book description, define purpose and target reader using initial research"""
    model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    llm = create_llm(model_name, temperature)
    
    # Include research results if available
    research_context = ""
    if state.get('research'):
        research_context = f"\n\nInitial Research Results:\n{state['research']}\n\nUse this research to better understand the topic, current market, existing content, and what readers might be looking for."
    
    prompt = f"""You are an expert book planning consultant. Analyze the following book proposal and enhance it using the provided research results.

Book Topic: {state['topic']}
Initial Book Description/Goal: {state['goal']}
{research_context}

Your task is to:
(a) Define the Book Purpose - Extract and clearly articulate the core purpose of this book as can be understood from the description and research. What is the main objective this book aims to achieve? Consider what gaps exist in the current market based on the research.

(b) Define the Target Reader - Identify and describe the target reader profile based on the description and research. Include:
- Reader's background and expertise level
- Reader's needs and goals
- What the reader expects to gain from this book
- Reader's prior knowledge assumptions
- What similar content exists and how this book will be different

(c) Enhance the Book Description - Augment and improve the original description to make it more complete, incorporating:
- The defined book purpose
- Information about the target reader
- More specific details about what the book will cover (informed by research)
- Expected outcomes for readers
- How this book addresses gaps or provides unique value based on the research

Format your response as:
BOOK_PURPOSE:
[Clear statement of the book's purpose]

TARGET_READER:
[Detailed description of the target reader]

ENHANCED_DESCRIPTION:
[Enhanced and augmented book description]"""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    response_text = response.content
    
    book_purpose = ""
    target_reader = ""
    enhanced_goal = state['goal']
    
    if "BOOK_PURPOSE:" in response_text:
        purpose_part = response_text.split("BOOK_PURPOSE:")[1]
        if "TARGET_READER:" in purpose_part:
            book_purpose = purpose_part.split("TARGET_READER:")[0].strip()
        else:
            book_purpose = purpose_part.strip()
    
    if "TARGET_READER:" in response_text:
        reader_part = response_text.split("TARGET_READER:")[1]
        if "ENHANCED_DESCRIPTION:" in reader_part:
            target_reader = reader_part.split("ENHANCED_DESCRIPTION:")[0].strip()
        else:
            target_reader = reader_part.strip()
    
    if "ENHANCED_DESCRIPTION:" in response_text:
        enhanced_part = response_text.split("ENHANCED_DESCRIPTION:")[1].strip()
        if enhanced_part:
            enhanced_goal = enhanced_part
    
    if not book_purpose:
        book_purpose = f"To provide comprehensive knowledge and practical guidance about {state['topic']}"
    
    if not target_reader:
        target_reader = "General readers interested in the topic"
    
    return {
        **state,
        "goal": enhanced_goal,
        "book_purpose": book_purpose,
        "target_reader": target_reader
    }


def search_topic(state: BookState) -> BookState:
    """Research the book topic using web search - first generates questions, then searches"""
    model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    llm = create_llm(model_name, temperature)
    
    # First, generate research questions based on topic and description
    prompt = f"""You are a research expert. Given the following book proposal, generate 5-8 specific research questions that will help understand:
- The current state of knowledge about this topic
- What already exists in the market (books, articles, resources)
- Key concepts, trends, and developments
- What readers are looking for
- Gaps or opportunities in existing content
- Best practices and expert insights

Book Topic: {state['topic']}
Book Description/Goal: {state['goal']}

Generate specific, researchable questions that will help inform the book's direction, target audience, and content strategy.

Format your response as:
QUESTIONS:
1. [first question]
2. [second question]
3. [third question]
..."""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    response_text = response.content
    
    # Extract questions
    questions = []
    questions_part = response_text
    if "QUESTIONS:" in response_text:
        questions_part = response_text.split("QUESTIONS:")[1]
    
    for line in questions_part.split('\n'):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith('-')):
            question = re.sub(r'^\d+[\.\)]\s*', '', line)
            question = re.sub(r'^-\s*', '', question)
            if question:
                questions.append(question)
    
    # If no questions extracted, create default ones
    if not questions:
        questions = [
            f"What are the key concepts and fundamentals of {state['topic']}?",
            f"What books, articles, or resources already exist about {state['topic']}?",
            f"What are the latest trends and developments in {state['topic']}?",
            f"What do readers want to learn about {state['topic']}?",
            f"What are the best practices and expert insights on {state['topic']}?"
        ]
    
    # Now perform searches for each question
    search = get_search_tool()
    research_results = []
    
    # Also do a general search on the topic
    general_query = f"{state['topic']} {state['goal']}"
    general_results = search.run(general_query)
    research_results.append(f"General Web Research on '{state['topic']}':\n{general_results}\n\n")
    
    # Add Wikipedia search for general topic overview
    wiki_results = search_wikipedia(state['topic'], max_results=3)
    if wiki_results and "error" not in wiki_results.lower():
        research_results.append(f"Wikipedia Overview of '{state['topic']}':\n{wiki_results}\n\n")
    
    # Add arXiv search for academic papers
    arxiv_results = search_arxiv(state['topic'], max_results=5)
    if arxiv_results and "error" not in arxiv_results.lower() and "not available" not in arxiv_results.lower():
        research_results.append(f"arXiv Academic Papers on '{state['topic']}':\n{arxiv_results}\n\n")
    
    # Search for each question using web search
    for i, question in enumerate(questions, 1):
        query = f"{state['topic']} {question}"
        results = search.run(query)
        research_results.append(f"Research Question {i}: {question}\nWeb Results: {results}\n\n")
        
        # Also search arXiv for academic perspective on specific questions
        arxiv_question_results = search_arxiv(query, max_results=3)
        if arxiv_question_results and "error" not in arxiv_question_results.lower() and "not available" not in arxiv_question_results.lower():
            research_results.append(f"Research Question {i} - arXiv Papers: {question}\n{arxiv_question_results}\n\n")
    
    combined_research = ''.join(research_results)
    
    return {**state, "research": combined_research}


def generate_outline(state: BookState) -> BookState:
    """Generate book outline using LLM"""
    model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    llm = create_llm(model_name, temperature)
    
    prompt = f"""You are an expert book writer. Create a detailed book outline for a book about: {state['topic']}

Book Purpose: {state.get('book_purpose', '')}
Target Reader: {state.get('target_reader', '')}
Author's goal: {state['goal']}

Research information:
{state['research']}

Create a comprehensive book outline in plain text format with:
- A clear title
- Chapter titles and brief descriptions for each chapter
- At least 5-8 chapters
- The outline should align with the book purpose and be appropriate for the target reader

Format the outline with "Chapter X: Title" on one line, followed by a description on the next line."""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    outline = response.content
    
    return {**state, "outline": outline}


def extract_chapters(state: BookState) -> BookState:
    """Extract chapter titles and descriptions from outline and initialize metadata"""
    outline = state['outline']
    chapters = []
    
    lines = outline.split('\n')
    current_chapter = None
    current_description = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_chapter and current_description:
                chapters.append({
                    "title": current_chapter,
                    "description": ' '.join(current_description),
                    "goal": ' '.join(current_description),
                    "metadata": {
                        "goal": ' '.join(current_description),
                        "research_resources": [],
                        "critiques": [],
                        "questions": []
                    }
                })
                current_chapter = None
                current_description = []
            continue
        
        if 'Chapter' in line and (line.startswith('Chapter') or ':' in line):
            if current_chapter:
                chapters.append({
                    "title": current_chapter,
                    "description": ' '.join(current_description) if current_description else current_chapter,
                    "goal": ' '.join(current_description) if current_description else current_chapter,
                    "metadata": {
                        "goal": ' '.join(current_description) if current_description else current_chapter,
                        "research_resources": [],
                        "critiques": [],
                        "questions": []
                    }
                })
            current_chapter = re.sub(r'^Chapter\s+\d+[:\-]?\s*', '', line, flags=re.IGNORECASE).strip()
            current_description = []
        elif current_chapter and not line.startswith('#'):
            current_description.append(line)
    
    if current_chapter:
        chapters.append({
            "title": current_chapter,
            "description": ' '.join(current_description) if current_description else current_chapter,
            "goal": ' '.join(current_description) if current_description else current_chapter,
            "metadata": {
                "goal": ' '.join(current_description) if current_description else current_chapter,
                "research_resources": [],
                "critiques": [],
                "questions": []
            }
        })
    
    if not chapters:
        chapters = [
            {
                "title": f"Introduction to {state['topic']}",
                "description": f"Introduction to {state['topic']}",
                "goal": f"Introduce readers to {state['topic']}",
                "metadata": {
                    "goal": f"Introduce readers to {state['topic']}",
                    "research_resources": [],
                    "critiques": [],
                    "questions": []
                }
            },
            {
                "title": f"Understanding {state['topic']}",
                "description": f"Understanding {state['topic']}",
                "goal": f"Help readers understand {state['topic']}",
                "metadata": {
                    "goal": f"Help readers understand {state['topic']}",
                    "research_resources": [],
                    "critiques": [],
                    "questions": []
                }
            },
            {
                "title": f"Advanced {state['topic']}",
                "description": f"Advanced {state['topic']}",
                "goal": f"Cover advanced topics in {state['topic']}",
                "metadata": {
                    "goal": f"Cover advanced topics in {state['topic']}",
                    "research_resources": [],
                    "critiques": [],
                    "questions": []
                }
            },
            {
                "title": f"Conclusion",
                "description": f"Conclusion about {state['topic']}",
                "goal": f"Summarize and conclude the book about {state['topic']}",
                "metadata": {
                    "goal": f"Summarize and conclude the book about {state['topic']}",
                    "research_resources": [],
                    "critiques": [],
                    "questions": []
                }
            }
        ]
    
    return {**state, "chapters": chapters, "current_chapter_index": 0}


def generate_chapter_questions(state: BookState) -> BookState:
    """Generate research questions for the current chapter and refine chapter goal"""
    model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    llm = create_llm(model_name, temperature)
    
    idx = state['current_chapter_index']
    chapter = state['chapters'][idx]
    
    prompt = f"""You are a research expert. For a book chapter about: {state['topic']}

Chapter Title: {chapter['title']}
Chapter Description: {chapter['description']}
Current Chapter Goal: {chapter.get('goal', chapter['description'])}

Book Purpose: {state.get('book_purpose', '')}
Target Reader: {state.get('target_reader', '')}
Book Goal: {state['goal']}

First, refine the chapter goal to be more specific and actionable. Then generate 5-8 specific research questions that need to be answered to write a comprehensive chapter on this topic.

Format your response as:
GOAL: [refined chapter goal - one clear sentence]

QUESTIONS:
1. [first question]
2. [second question]
...

The questions should help gather detailed information, examples, case studies, and technical details. Each question should be specific and researchable."""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    response_text = response.content
    
    refined_goal = chapter.get('goal', chapter['description'])
    questions = []
    
    if "GOAL:" in response_text:
        goal_part = response_text.split("GOAL:")[1].split("QUESTIONS:")[0].strip()
        if goal_part:
            refined_goal = goal_part.split('\n')[0].strip()
    
    questions_part = response_text
    if "QUESTIONS:" in response_text:
        questions_part = response_text.split("QUESTIONS:")[1]
    
    for line in questions_part.split('\n'):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith('-')):
            question = re.sub(r'^\d+[\.\)]\s*', '', line)
            question = re.sub(r'^-\s*', '', question)
            if question:
                questions.append(question)
    
    if not questions:
        questions = [
            f"What are the key concepts related to {chapter['title']}?",
            f"What are real-world examples or case studies of {chapter['title']}?",
            f"What are the best practices for {chapter['title']}?",
            f"What are common challenges or pitfalls related to {chapter['title']}?",
            f"How does {chapter['title']} relate to {state['topic']}?"
        ]
    
    updated_chapters = state['chapters'].copy()
    updated_chapters[idx]['goal'] = refined_goal
    if 'metadata' not in updated_chapters[idx]:
        updated_chapters[idx]['metadata'] = {
            "goal": refined_goal,
            "research_resources": [],
            "critiques": [],
            "questions": []
        }
    else:
        updated_chapters[idx]['metadata']['goal'] = refined_goal
    
    # Store questions in metadata
    updated_chapters[idx]['metadata']['questions'] = questions
    
    return {
        **state,
        "current_chapter_questions": questions,
        "chapters": updated_chapters
    }


def research_chapter_questions(state: BookState) -> BookState:
    """Search the web, Wikipedia, and arXiv for answers to chapter questions and store in metadata"""
    search = get_search_tool()
    research_results = []
    research_resources = []
    
    idx = state['current_chapter_index']
    
    for question in state['current_chapter_questions']:
        query = f"{state['topic']} {question}"
        
        # Web search
        web_results = search.run(query)
        research_results.append(f"Question: {question}\nWeb Research: {web_results}\n\n")
        
        # Wikipedia search for background/overview
        wiki_results = search_wikipedia(query, max_results=2)
        if wiki_results and "error" not in wiki_results.lower():
            research_results.append(f"Question: {question}\nWikipedia: {wiki_results}\n\n")
        
        # arXiv search for academic papers
        arxiv_results = search_arxiv(query, max_results=3)
        if arxiv_results and "error" not in arxiv_results.lower() and "not available" not in arxiv_results.lower():
            research_results.append(f"Question: {question}\narXiv Papers: {arxiv_results}\n\n")
        
        # Store all results
        combined_results = f"Web: {web_results}"
        if wiki_results and "error" not in wiki_results.lower():
            combined_results += f"\nWikipedia: {wiki_results}"
        if arxiv_results and "error" not in arxiv_results.lower() and "not available" not in arxiv_results.lower():
            combined_results += f"\narXiv: {arxiv_results}"
        
        research_resources.append({
            "question": question,
            "query": query,
            "results": combined_results
        })
    
    combined_research = ''.join(research_results)
    
    updated_chapters = state['chapters'].copy()
    if 'metadata' not in updated_chapters[idx]:
        updated_chapters[idx]['metadata'] = {
            "goal": updated_chapters[idx].get('goal', updated_chapters[idx]['description']),
            "research_resources": [],
            "critiques": [],
            "questions": []
        }
    updated_chapters[idx]['metadata']['research_resources'] = research_resources
    
    return {
        **state,
        "current_chapter_research": combined_research,
        "chapters": updated_chapters
    }


def write_chapter(state: BookState) -> BookState:
    """Write a single chapter using collected research and save it to disk"""
    model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    llm = create_llm(model_name, temperature)
    
    idx = state['current_chapter_index']
    chapter = state['chapters'][idx]
    
    prompt = f"""You are an expert book writer. Write a complete chapter for a book about: {state['topic']}

Book Purpose: {state.get('book_purpose', '')}
Target Reader: {state.get('target_reader', '')}
Book Goal: {state['goal']}

Book Outline:
{state['outline']}

Chapter Title: {chapter['title']}
Chapter Description: {chapter['description']}

Initial Research Information:
{state['research']}

Chapter-Specific Research Questions:
{chr(10).join(f"- {q}" for q in state['current_chapter_questions'])}

Detailed Research Material Collected:
{state['current_chapter_research']}

Write a comprehensive, well-structured chapter (at least 1000 words) in LaTeX format. The output should be valid LaTeX code that can be compiled.

Requirements:
- Use \\section{{}} for main sections
- Use \\subsection{{}} for subsections
- Use \\paragraph{{}} for paragraphs if needed
- Use proper LaTeX formatting: \\textbf{{}} for bold, \\textit{{}} for italic, \\emph{{}} for emphasis
- Use \\begin{{itemize}} and \\end{{itemize}} for bullet lists
- Use \\begin{{enumerate}} and \\end{{enumerate}} for numbered lists
- Use proper LaTeX escaping for special characters ($, %, &, #, _, {{, }})
- Include an engaging introduction
- Include clear sections with proper LaTeX sectioning commands
- Include detailed content based on the research material
- Include a conclusion that ties back to the chapter's purpose
- Write in a style and depth appropriate for the target reader: {state.get('target_reader', 'general readers')}
- Ensure the content aligns with the book purpose: {state.get('book_purpose', '')}
- Do NOT include \\documentclass, \\begin{{document}}, or \\end{{document}} - just the chapter content
- Do NOT include the chapter title as a section - it will be added separately
- Do NOT use markdown formatting (no **, no ```, no code blocks) - output pure LaTeX code only
- Do NOT wrap the output in code blocks or markdown - output the LaTeX code directly
- Make sure to incorporate information from the research material to answer the research questions"""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    chapter_content = response.content
    
    # Clean any markdown formatting or code blocks that might have been added
    chapter_content = clean_latex_output(chapter_content)
    
    updated_chapters = state['chapters'].copy()
    updated_chapters[idx] = {**updated_chapters[idx], "content": chapter_content, "filepath": ""}
    
    chapter_metadata = updated_chapters[idx].get('metadata', {})
    chapter_filepath = save_chapter_to_file(
        chapter_content, 
        idx + 1, 
        chapter['title'], 
        state['book_folder'],
        chapter_metadata
    )
    updated_chapters[idx]["filepath"] = chapter_filepath
    
    return {
        **state,
        "chapters": updated_chapters,
        "current_chapter_questions": [],
        "current_chapter_research": ""
    }


def critique_chapter(state: BookState) -> BookState:
    """Critique a chapter that was just written and store in metadata"""
    model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    llm = create_llm(model_name, temperature)
    
    idx = state['current_chapter_index']
    chapter = state['chapters'][idx]
    chapter_filepath = chapter.get('filepath', '')
    
    if not chapter_filepath or not Path(chapter_filepath).exists():
        return {**state, "current_chapter_critique": ""}
    
    current_content = load_chapter_from_file(chapter_filepath)
    
    prompt = f"""You are an expert book editor. Critically review the following chapter for a book about: {state['topic']}

Book Purpose: {state.get('book_purpose', '')}
Target Reader: {state.get('target_reader', '')}
Book Goal: {state['goal']}

Chapter Title: {chapter['title']}
Chapter Goal: {chapter.get('goal', chapter['description'])}

Chapter Content to Critique:
{current_content}

Provide a detailed critique covering:
1. Content quality and depth - are all research questions addressed?
2. Structure and organization - is the flow logical and clear?
3. Clarity and readability - are concepts explained well?
4. Completeness - are there gaps or missing information?
5. LaTeX formatting - are there any formatting issues?
6. Alignment with book goals - does it fit the overall purpose?
7. Alignment with chapter goal - does it achieve the chapter's specific goal?
8. Specific suggestions for improvement

Be constructive and specific. Focus on what needs to be improved and how."""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    critique = response.content
    
    updated_chapters = state['chapters'].copy()
    if 'metadata' not in updated_chapters[idx]:
        updated_chapters[idx]['metadata'] = {
            "goal": updated_chapters[idx].get('goal', updated_chapters[idx]['description']),
            "research_resources": [],
            "critiques": [],
            "questions": []
        }
    updated_chapters[idx]['metadata']['critiques'].append({
        "iteration": len(updated_chapters[idx]['metadata']['critiques']) + 1,
        "critique": critique,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        **state,
        "current_chapter_critique": critique,
        "chapters": updated_chapters
    }


def rewrite_chapter(state: BookState) -> BookState:
    """Rewrite a chapter using the original content, critique, and metadata"""
    model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    llm = create_llm(model_name, temperature)
    
    idx = state['current_chapter_index']
    chapter = state['chapters'][idx]
    chapter_filepath = chapter.get('filepath', '')
    
    if not chapter_filepath or not Path(chapter_filepath).exists():
        return {
        **state,
        "chapters": state['chapters'],
        "current_chapter_index": idx + 1,
        "current_chapter_critique": ""
    }
    
    original_content = load_chapter_from_file(chapter_filepath)
    critique = state.get('current_chapter_critique', '')
    metadata = chapter.get('metadata', {})
    chapter_goal = metadata.get('goal', chapter.get('goal', chapter['description']))
    all_critiques = [c.get('critique', '') for c in metadata.get('critiques', [])]
    
    critiques_text = '\n\n'.join([f"Iteration {i+1} Critique:\n{c}" for i, c in enumerate(all_critiques)])
    
    prompt = f"""You are an expert book writer. Rewrite the following chapter based on the editor's critique and previous critiques.

Book Topic: {state['topic']}
Book Purpose: {state.get('book_purpose', '')}
Target Reader: {state.get('target_reader', '')}
Book Goal: {state['goal']}

Chapter Title: {chapter['title']}
Chapter Goal: {chapter_goal}

    Original Chapter Content:
{original_content}

Current Editor's Critique:
{critique}

Previous Critiques (if any):
{critiques_text if critiques_text else "None"}

Rewrite the chapter addressing all the points in the critiques. Keep the same LaTeX structure but improve:
- Content quality and depth based on the critiques
- Structure and organization as suggested
- Clarity and readability improvements
- Fill any gaps or missing information
- Fix LaTeX formatting issues
- Better align with book goals and chapter goal

Return the rewritten chapter in LaTeX format.
Do NOT include \\documentclass, \\begin{{document}}, or \\end{{document}} - just the chapter content.
Do NOT use markdown formatting (no **, no ```, no code blocks) - output pure LaTeX code only.
Do NOT wrap the output in code blocks or markdown - output the LaTeX code directly.
Make sure to incorporate all critique suggestions while maintaining the chapter's core purpose and achieving the chapter goal."""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    rewritten_content = response.content
    
    # Clean any markdown formatting or code blocks that might have been added
    rewritten_content = clean_latex_output(rewritten_content)
    
    updated_chapters = state['chapters'].copy()
    updated_chapters[idx] = {**updated_chapters[idx], "content": rewritten_content}
    
    chapter_metadata = updated_chapters[idx].get('metadata', {})
    chapter_filepath = save_chapter_to_file(
        rewritten_content,
        idx + 1,
        chapter['title'],
        state['book_folder'],
        chapter_metadata
    )
    updated_chapters[idx]["filepath"] = chapter_filepath
    
    return {
        **state,
        "chapters": updated_chapters,
        "current_chapter_index": idx + 1,
        "current_chapter_critique": ""
    }


def should_continue_writing(state: BookState) -> str:
    """Check if more chapters need to be written"""
    if state['current_chapter_index'] < len(state['chapters']):
        return "generate_questions"
    return "assemble_book"


def should_critique_chapter(state: BookState) -> str:
    """Always critique the chapter after writing it"""
    return "critique_chapter"


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters for use in text"""
    result = text
    result = result.replace('\\', '\\textbackslash{}')
    result = result.replace('{', '\\{')
    result = result.replace('}', '\\}')
    result = result.replace('$', '\\$')
    result = result.replace('&', '\\&')
    result = result.replace('%', '\\%')
    result = result.replace('#', '\\#')
    result = result.replace('^', '\\textasciicircum{}')
    result = result.replace('_', '\\_')
    result = result.replace('~', '\\textasciitilde{}')
    return result


def clean_latex_output(content: str) -> str:
    """Remove markdown formatting and code blocks from LaTeX output"""
    if not content:
        return content
    
    # Remove markdown code blocks (```latex, ```, etc.)
    # Match patterns like ```latex ... ``` or ``` ... ```
    content = re.sub(r'```(?:latex|LaTeX)?\s*\n', '', content)
    content = re.sub(r'```\s*\n', '', content)
    content = re.sub(r'\n```\s*$', '', content)
    content = re.sub(r'^```\s*\n', '', content, flags=re.MULTILINE)
    
    # Remove markdown bold formatting (**text**)
    content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
    
    # Remove any remaining markdown emphasis (*text* or _text_)
    # But be careful not to remove LaTeX commands that use *
    # Only remove standalone * or _ that are markdown
    content = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', content)
    content = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'\1', content)
    
    # Strip leading/trailing whitespace
    content = content.strip()
    
    return content


def create_chapter_appendix(metadata: Dict[str, Any], chapter_num: int) -> str:
    """Create LaTeX appendix section with chapter metadata, especially the research questions"""
    if not metadata:
        return ""
    
    appendix_parts = []
    appendix_parts.append("\\section*{Appendix: Chapter Research Questions and Metadata}\n")
    appendix_parts.append("\\addcontentsline{toc}{section}{Appendix: Chapter Research Questions and Metadata}\n\n")
    
    # Add chapter goal if available
    goal = metadata.get('goal', '')
    if goal:
        goal_escaped = escape_latex(goal)
        appendix_parts.append(f"\\textbf{{Chapter Goal:}} {goal_escaped}\n\n")
    
    # Add research questions
    questions = metadata.get('questions', [])
    if questions:
        appendix_parts.append("\\textbf{Research Questions:}\n")
        appendix_parts.append("\\begin{enumerate}\n")
        for question in questions:
            question_escaped = escape_latex(question)
            appendix_parts.append(f"    \\item {question_escaped}\n")
        appendix_parts.append("\\end{enumerate}\n\n")
    
    # Add research resources summary if available
    research_resources = metadata.get('research_resources', [])
    if research_resources:
        appendix_parts.append(f"\\textbf{{Research Resources:}} {len(research_resources)} research queries were performed for this chapter.\n\n")
    
    # Add critiques summary if available
    critiques = metadata.get('critiques', [])
    if critiques:
        appendix_parts.append(f"\\textbf{{Revision Iterations:}} This chapter underwent {len(critiques)} revision cycle(s) based on editorial feedback.\n\n")
    
    return ''.join(appendix_parts)


def sanitize_filename(text: str) -> str:
    """Sanitize text for use as a filename"""
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def setup_book_folder(topic: str, output_dir: Optional[str] = None) -> str:
    """Create a folder structure for the book"""
    if output_dir:
        base_path = Path(output_dir)
    else:
        base_path = Path.cwd() / "books"
    
    sanitized_topic = sanitize_filename(topic)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    book_folder = base_path / f"{sanitized_topic}_{timestamp}"
    book_folder.mkdir(parents=True, exist_ok=True)
    
    chapters_folder = book_folder / "chapters"
    chapters_folder.mkdir(exist_ok=True)
    
    return str(book_folder)


def save_chapter_to_file(chapter_content: str, chapter_num: int, chapter_title: str, book_folder: str, metadata: Optional[Dict] = None) -> str:
    """Save a chapter to a .tex file and its metadata to a .json file"""
    book_path = Path(book_folder)
    chapters_folder = book_path / "chapters"
    
    sanitized_title = sanitize_filename(chapter_title)
    filename = f"chapter_{chapter_num:02d}_{sanitized_title}.tex"
    filepath = chapters_folder / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(chapter_content)
    
    if metadata:
        metadata_filename = f"chapter_{chapter_num:02d}_{sanitized_title}_metadata.json"
        metadata_filepath = chapters_folder / metadata_filename
        with open(metadata_filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return str(filepath)


def load_chapter_metadata(chapter_filepath: str) -> Optional[Dict]:
    """Load chapter metadata from JSON file"""
    chapter_path = Path(chapter_filepath)
    metadata_path = chapter_path.parent / f"{chapter_path.stem}_metadata.json"
    
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_chapter_from_file(chapter_filepath: str) -> str:
    """Load a chapter from a .tex file"""
    with open(chapter_filepath, 'r', encoding='utf-8') as f:
        return f.read()


def save_book_to_file(book_content: str, book_folder: str) -> str:
    """Save the complete book to a .tex file in the book folder"""
    book_path = Path(book_folder)
    filename = "book.tex"
    filepath = book_path / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(book_content)
    
    return str(filepath)


def assemble_book(state: BookState) -> BookState:
    """Assemble the complete book as a compilable LaTeX document, loading chapters from disk"""
    topic_escaped = escape_latex(state['topic'])
    
    book_parts = [
        "\\documentclass[11pt,a4paper]{book}\n",
        "\\usepackage[utf8]{inputenc}\n",
        "\\usepackage[T1]{fontenc}\n",
        "\\usepackage{geometry}\n",
        "\\geometry{margin=1in}\n",
        "\\usepackage{graphicx}\n",
        "\\usepackage{hyperref}\n",
        "\\hypersetup{\n",
        "    colorlinks=true,\n",
        "    linkcolor=blue,\n",
        "    filecolor=magenta,\n",
        "    urlcolor=cyan,\n",
        "}\n",
        "\\usepackage{amsmath}\n",
        "\\usepackage{amsfonts}\n",
        "\\usepackage{amssymb}\n",
        "\\usepackage{listings}\n",
        "\\usepackage{xcolor}\n",
        "\n",
        "\\title{" + topic_escaped + "}\n",
        "\\author{Generated by Book Writing Agent}\n",
        "\\date{\\today}\n",
        "\n",
        "\\begin{document}\n",
        "\n",
        "\\maketitle\n",
        "\n",
        "\\frontmatter\n",
        "\n",
        "\\tableofcontents\n",
        "\n",
        "\\mainmatter\n",
        "\n"
    ]
    
    for i, chapter in enumerate(state['chapters'], 1):
        chapter_title_escaped = escape_latex(chapter['title'])
        book_parts.append(f"\\chapter{{{chapter_title_escaped}}}\n\n")
        
        chapter_filepath = chapter.get('filepath', '')
        if chapter_filepath and Path(chapter_filepath).exists():
            chapter_content = load_chapter_from_file(chapter_filepath)
            # Try to load metadata from file
            chapter_metadata = load_chapter_metadata(chapter_filepath)
        else:
            chapter_content = chapter.get('content', '')
            chapter_metadata = chapter.get('metadata', {})
        
        if chapter_content:
            book_parts.append(chapter_content)
            book_parts.append("\n\n")
            
            # Add appendix with chapter metadata/questions
            if chapter_metadata:
                appendix_content = create_chapter_appendix(chapter_metadata, i)
                if appendix_content:
                    book_parts.append(appendix_content)
                    book_parts.append("\n\n")
    
    book_parts.append("\n\\backmatter\n\n")
    book_parts.append("\\end{document}\n")
    
    complete_book = ''.join(book_parts)
    return {**state, "book": complete_book}


def create_workflow():
    """Create the LangGraph workflow"""
    workflow = StateGraph(BookState)
    
    workflow.add_node("enhance_description", enhance_book_description)
    workflow.add_node("search_topic", search_topic)
    workflow.add_node("generate_outline", generate_outline)
    workflow.add_node("extract_chapters", extract_chapters)
    workflow.add_node("generate_questions", generate_chapter_questions)
    workflow.add_node("research_questions", research_chapter_questions)
    workflow.add_node("write_chapter", write_chapter)
    workflow.add_node("critique_chapter", critique_chapter)
    workflow.add_node("rewrite_chapter", rewrite_chapter)
    workflow.add_node("assemble_book", assemble_book)
    
    workflow.set_entry_point("search_topic")
    workflow.add_edge("search_topic", "enhance_description")
    workflow.add_edge("enhance_description", "generate_outline")
    workflow.add_edge("generate_outline", "extract_chapters")
    workflow.add_edge("extract_chapters", "generate_questions")
    workflow.add_edge("generate_questions", "research_questions")
    workflow.add_edge("research_questions", "write_chapter")
    workflow.add_conditional_edges(
        "write_chapter",
        should_critique_chapter,
        {
            "critique_chapter": "critique_chapter",
            "generate_questions": "generate_questions"
        }
    )
    workflow.add_edge("critique_chapter", "rewrite_chapter")
    workflow.add_conditional_edges(
        "rewrite_chapter",
        should_continue_writing,
        {
            "generate_questions": "generate_questions",
            "assemble_book": "assemble_book"
        }
    )
    workflow.add_edge("assemble_book", END)
    
    return workflow.compile()


def execute(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Main execution function for the Book Writing Agent"""
    topic = input_data.get("topic")
    if not topic:
        return {"status": "error", "error": "topic is required"}
    
    goal = input_data.get("goal", "")
    model_name = input_data.get("model_name", "gpt-4o-mini")
    temperature = input_data.get("temperature", 0.7)
    
    os.environ["OPENAI_MODEL"] = model_name
    os.environ["OPENAI_TEMPERATURE"] = str(temperature)
    
    use_azure = input_data.get("use_azure", False)
    azure_api_key = input_data.get("azure_api_key") or os.getenv("AZURE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = input_data.get("azure_endpoint") or os.getenv("AZURE_API_BASE") or os.getenv("AZURE_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_version = input_data.get("azure_api_version") or os.getenv("AZURE_API_VERSION", "2024-02-15-preview")
    
    if use_azure or (azure_api_key and azure_endpoint):
        if azure_api_key:
            os.environ["AZURE_API_KEY"] = azure_api_key
        if azure_endpoint:
            os.environ["AZURE_API_BASE"] = azure_endpoint
        if azure_api_version:
            os.environ["AZURE_API_VERSION"] = azure_api_version
    
    output_dir = input_data.get("output_dir")
    book_folder = setup_book_folder(topic, output_dir)
    
    initial_state = {
        "topic": topic,
        "goal": goal,
        "book_purpose": "",
        "target_reader": "",
        "research": "",
        "outline": "",
        "chapters": [],
        "book": "",
        "current_chapter_index": 0,
        "current_chapter_questions": [],
        "current_chapter_research": "",
        "book_folder": book_folder,
        "current_chapter_critique": ""
    }
    
    workflow = create_workflow()
    
    recursion_limit = input_data.get("recursion_limit", 150)
    config = {"recursion_limit": recursion_limit}
    
    final_state = workflow.invoke(initial_state, config=config)
    
    tex_filepath = save_book_to_file(final_state["book"], book_folder)
    
    return {
        "status": "success",
        "result": {
            "book": final_state["book"],
            "outline": final_state["outline"],
            "tex_file": tex_filepath,
            "metadata": {
                "topic": topic,
                "num_chapters": len(final_state["chapters"]),
                "model": model_name,
                "temperature": temperature
            }
        }
    }


def main(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Main entry point for the agent"""
    return execute(input_data, config)


if __name__ == "__main__":
    import json
    
    test_input = {
        "topic": "Agentic Design Patterns",
        "goal": """This book is a practical and accessible guide to agentic AI design patterns for software engineers. It introduces the core principles behind modern LLM-based agents and gradually builds toward advanced capabilities such as retrieval-augmented agents, tool-using agents, multi-agent systems, and deep agents capable of reflection and long-horizon reasoning.

The book opens with a concise historical overview of AI agents—from expert systems and classical planning to today’s transformer-based autonomous agents. It then establishes foundational knowledge that every engineer needs, including embeddings, vector databases, short- and long-term memory, context management, reasoning loops, and action-selection mechanisms.

Each design pattern—ReAct agents, RAG agents, tool agents, planner-executor architectures, multi-agent orchestration, and deep agents—is explained through clear diagrams, architectural illustrations, and code snippets. The emphasis is on understanding the building blocks of agentic systems and how they interact in real implementations.

Beyond the conceptual patterns, the book also provides full system design examples, covering:

Key architectural components (LLM layer, memory store, tool layer, orchestrator, event bus, logging and monitoring systems, etc.)

Patterns for scaling agents (caching, batching, streaming, microservice boundaries, concurrency models, autoscaling strategies)

Observability and safety mechanisms (tracing, guardrails, policy enforcement, evaluation frameworks)

Deployment considerations (serverless vs. containerized agents, multi-tenant isolation, cost-aware design)

Performance optimization for high-traffic production environments

Real-world case studies demonstrate how these patterns are applied in practice—such as building a RAG pipeline for enterprise knowledge bases, creating code agents that plan and execute tasks, designing tool-using agents for IT automation, and orchestrating multi-agent teams for complex workflows.

By the end of the book, readers will have a comprehensive and practical understanding of how to design, architect, implement, and scale LLM-based agents—from simple interactive assistants to robust, production-grade agentic systems.""",
        "model_name": "gpt-4o-mini",
        "temperature": 0.7
    }
    
    result = execute(test_input)
    print(json.dumps(result, indent=2))

