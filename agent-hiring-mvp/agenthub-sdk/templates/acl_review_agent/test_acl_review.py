#!/usr/bin/env python3
"""
Test script for ACL Review Agent
"""

import os
import json
from acl_review_agent import ACLReviewAgent

def test_acl_review_agent():
    """Test the ACL Review Agent with a sample paper"""
    
    # Check required environment variables
    required_vars = ["SERPER_API_KEY", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these environment variables before running the test.")
        return False
    
    # Check optional environment variables
    optional_vars = ["OPENREVIEW_USERNAME", "OPENREVIEW_PASSWORD"]
    missing_optional = [var for var in optional_vars if not os.getenv(var)]
    
    if missing_optional:
        print(f"⚠️  Missing optional environment variables: {', '.join(missing_optional)}")
        print("OpenReview features may be limited without these variables.")
    
    # Check Semantic Scholar API key (optional but provides better rate limits)
    if not os.getenv("SEMANTIC_SCHOLAR_KEY"):
        print("ℹ️  No Semantic Scholar API key provided - using shared rate limits")
    else:
        print("✅ Semantic Scholar API key provided - using enhanced rate limits")
    
    try:
        # Initialize the agent
        print("🔧 Initializing ACL Review Agent...")
        agent = ACLReviewAgent()
        print("✅ Agent initialized successfully")
        
        # Test paper URL (a recent NLP paper)
        test_url = "https://arxiv.org/abs/2303.08774"  # "PaLM 2 Technical Report"
        
        print(f"\n📄 Testing with paper: {test_url}")
        
        # Perform review
        result = agent.review_paper(
            paper_url=test_url,
            review_depth=3,  # Reduced for testing
            include_related_work=True,
            novelty_analysis=True,
            technical_analysis=True,
            experimental_validation=True
        )
        
        if result["status"] == "success":
            print("✅ Review completed successfully!")
            
            # Display key results
            paper_info = result["result"]["paper"]
            review_info = result["result"]["review"]
            lit_review = result["result"]["literature_review"]
            
            print(f"\n📊 Review Summary:")
            print(f"   Paper: {paper_info['title']}")
            print(f"   Authors: {', '.join(paper_info['authors'])}")
            print(f"   Confidence: {review_info['confidence']}/5")
            print(f"   Soundness: {review_info['soundness']}/5")
            print(f"   Overall Assessment: {review_info['overall_assessment']}/5")
            print(f"   Novelty Score: {lit_review['novelty_score']:.2f}")
            print(f"   Related Papers Found: {lit_review['related_papers_count']}")
            
            # Check for new features
            if 'similar_papers' in lit_review:
                print(f"   Similar Papers: {len(lit_review.get('similar_papers', []))}")
            if 'openreview_reviews' in lit_review:
                print(f"   OpenReview Reviews: {len(lit_review.get('openreview_reviews', []))}")
            if 'semantic_scholar_papers' in lit_review:
                print(f"   Semantic Scholar Papers: {len(lit_review.get('semantic_scholar_papers', []))}")
            
            # Save detailed results
            output_file = "acl_review_test_results.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Detailed results saved to: {output_file}")
            
            # Display formatted review
            print(f"\n📝 Formatted Review Preview:")
            formatted_review = result["result"]["formatted_review"]
            print(formatted_review[:1000] + "..." if len(formatted_review) > 1000 else formatted_review)
            
            return True
            
        else:
            print(f"❌ Review failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_arr_guidelines():
    """Test ARR guidelines loading"""
    try:
        agent = ACLReviewAgent()
        guidelines = agent.arr_guidelines
        
        if guidelines:
            print("✅ ARR guidelines loaded successfully")
            print(f"   Guidelines length: {len(guidelines)} characters")
            return True
        else:
            print("❌ Failed to load ARR guidelines")
            return False
    except Exception as e:
        print(f"❌ ARR guidelines test failed: {e}")
        return False

def test_similar_papers():
    """Test similar papers functionality"""
    try:
        agent = ACLReviewAgent()
        
        # Create a sample paper
        from acl_review_agent import Paper
        sample_paper = Paper(
            title="Attention Is All You Need",
            authors=["Vaswani, A.", "Shazeer, N.", "Parmar, N."],
            abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
            content="",
            url="",
            venue="NIPS",
            year=2017,
            keywords=[],
            references=[],
            citations=None
        )
        
        similar_papers = agent.find_most_similar_papers(sample_paper, max_results=5)
        
        if similar_papers:
            print("✅ Similar papers found successfully")
            print(f"   Found {len(similar_papers)} similar papers")
            for i, paper in enumerate(similar_papers[:3], 1):
                print(f"   {i}. {paper.get('title', 'Unknown')} (similarity: {paper.get('similarity_score', 0):.3f})")
            return True
        else:
            print("⚠️  No similar papers found (this may be normal)")
            return True
            
    except Exception as e:
        print(f"❌ Similar papers test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 ACL Review Agent Test Suite")
    print("=" * 50)
    
    # Test ARR guidelines
    print("\n1. Testing ARR Guidelines Loading...")
    arr_test = test_arr_guidelines()
    
    # Test similar papers (if dependencies available)
    print("\n2. Testing Similar Papers Functionality...")
    similar_test = test_similar_papers()
    
    # Test full review
    print("\n3. Testing Full Review Process...")
    review_test = test_acl_review_agent()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"   ARR Guidelines: {'✅ PASS' if arr_test else '❌ FAIL'}")
    print(f"   Similar Papers: {'✅ PASS' if similar_test else '❌ FAIL'}")
    print(f"   Full Review: {'✅ PASS' if review_test else '❌ FAIL'}")
    
    if all([arr_test, similar_test, review_test]):
        print("\n🎉 All tests passed! The ACL Review Agent is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.") 