#!/usr/bin/env python3
"""
Test script for the RAG agent.
This script demonstrates how to use the RAG agent with different document sources.
"""

import os
import json
from agent import main

def test_rag_agent():
    """Test the RAG agent with different scenarios."""
    
    # Set up OpenAI API key (you need to set this environment variable)
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        return
    
    # Test configuration
    config = {
        "debug": True,
        "model_name": "gpt-3.5-turbo",
        "embedding_model": "text-embedding-ada-002",
        "temperature": 0,
        "chunk_size": 1024,
        "chunk_overlap": 200,
        "max_tokens": 1000
    }
    
    # Test cases
    test_cases = [
        {
            "name": "Wikipedia Article Test",
            "input_data": {
                "document_source": "https://en.wikipedia.org/wiki/Artificial_intelligence",
                "question": "What is artificial intelligence and what are its main applications?"
            }
        },
        {
            "name": "Local File Test",
            "input_data": {
                "document_source": "sample_document.txt",
                "question": "What are the key points mentioned in this document?"
            }
        }
    ]
    
    # Create a sample local document for testing
    sample_content = """
    # Sample Document for RAG Testing
    
    This is a sample document that demonstrates the capabilities of the RAG agent.
    
    ## Key Features
    - Document processing from URLs and local files
    - Question answering using retrieval-augmented generation
    - Configurable chunk sizes and overlap
    - Support for various document formats
    
    ## How it Works
    The RAG agent uses LlamaIndex to:
    1. Load documents from URLs or local files
    2. Split documents into manageable chunks
    3. Create embeddings for semantic search
    4. Retrieve relevant chunks for a given question
    5. Generate answers using an LLM
    
    ## Benefits
    - Accurate answers based on document content
    - Handles large documents efficiently
    - Supports multiple document sources
    - Configurable for different use cases
    """
    
    # Write sample document
    with open("sample_document.txt", "w") as f:
        f.write(sample_content)
    
    print("🧪 Testing RAG Agent")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print("-" * 30)
        
        try:
            # Run the agent
            result = main(test_case["input_data"], config)
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
            else:
                print(f"✅ Success!")
                print(f"📄 Document: {result['document_source']}")
                print(f"❓ Question: {result['question']}")
                print(f"🤖 Answer: {result['answer']}")
                
                if "debug_info" in result:
                    print(f"📊 Debug Info:")
                    print(f"   Document length: {result['debug_info']['document_length']} characters")
                    print(f"   Document preview: {result['debug_info']['document_preview']}")
                
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
    
    # Clean up
    if os.path.exists("sample_document.txt"):
        os.remove("sample_document.txt")
    
    print("\n🎉 Testing completed!")

if __name__ == "__main__":
    test_rag_agent() 