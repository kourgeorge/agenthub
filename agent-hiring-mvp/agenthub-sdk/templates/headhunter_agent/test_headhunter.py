#!/usr/bin/env python3
"""
Test script for the Headhunter Agent
"""

import json
import os
from headhunter_agent import main

def test_basic_search():
    """Test basic headhunting search"""
    print("Testing basic headhunting search...")
    
    input_data = {
        "job_title": "Senior Software Engineer",
        "region": "San Francisco, CA",
        "search_depth": 2,
        "candidates_per_search": 5
    }
    
    config = {
        "job_title": "Software Engineer",
        "region": "San Francisco, CA",
        "description": "",
        "search_depth": 3,
        "candidates_per_search": 10,
        "include_remote": True
    }
    
    result = main(input_data, config)
    print(json.dumps(result, indent=2))
    return result

def test_advanced_search():
    """Test advanced search with detailed description"""
    print("\nTesting advanced search with description...")
    
    input_data = {
        "job_title": "Data Scientist",
        "region": "New York, NY",
        "description": "Looking for experienced data scientists with Python, machine learning, and AWS skills. Must have 3+ years experience in fintech or e-commerce.",
        "search_depth": 3,
        "candidates_per_search": 8,
        "include_remote": True
    }
    
    config = {
        "job_title": "Data Scientist",
        "region": "New York, NY",
        "description": "",
        "search_depth": 3,
        "candidates_per_search": 10,
        "include_remote": True
    }
    
    result = main(input_data, config)
    print(json.dumps(result, indent=2))
    return result

def test_remote_search():
    """Test remote work search"""
    print("\nTesting remote work search...")
    
    input_data = {
        "job_title": "Product Manager",
        "region": "United States",
        "description": "Remote product manager with experience in SaaS and B2B products",
        "search_depth": 2,
        "candidates_per_search": 6,
        "include_remote": True
    }
    
    config = {
        "job_title": "Product Manager",
        "region": "United States",
        "description": "",
        "search_depth": 3,
        "candidates_per_search": 10,
        "include_remote": True
    }
    
    result = main(input_data, config)
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    # Check if environment variables are set
    required_vars = ["SERPER_API_KEY", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {missing_vars}")
        print("Please set the following environment variables:")
        for var in missing_vars:
            print(f"  export {var}=your_key_here")
        exit(1)
    
    print("Headhunter Agent Test Suite")
    print("=" * 50)
    
    # Run tests
    try:
        test_basic_search()
        test_advanced_search()
        test_remote_search()
        print("\nAll tests completed successfully!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc() 