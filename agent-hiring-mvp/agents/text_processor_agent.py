#!/usr/bin/env python3
"""
Text Processor Agent
This agent processes and analyzes text input.
"""

def main():
    """Main agent function."""
    # Get input data
    text = input_data.get('text', 'Hello World!')
    operation = input_data.get('operation', 'analyze')
    
    # Process text based on operation
    if operation == 'analyze':
        # Basic text analysis
        word_count = len(text.split())
        char_count = len(text)
        line_count = len(text.splitlines())
        
        analysis = {
            "text": text,
            "word_count": word_count,
            "character_count": char_count,
            "line_count": line_count,
            "average_word_length": char_count / word_count if word_count > 0 else 0
        }
        
        print(f"Text Analysis Results:")
        print(f"Word count: {analysis['word_count']}")
        print(f"Character count: {analysis['character_count']}")
        print(f"Line count: {analysis['line_count']}")
        print(f"Average word length: {analysis['average_word_length']:.2f}")
        
    elif operation == 'uppercase':
        result = text.upper()
        print(f"Uppercase text: {result}")
        
    elif operation == 'lowercase':
        result = text.lower()
        print(f"Lowercase text: {result}")
        
    elif operation == 'reverse':
        result = text[::-1]
        print(f"Reversed text: {result}")
        
    elif operation == 'word_count':
        words = text.split()
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        print(f"Word frequency:")
        for word, count in word_freq.items():
            print(f"  '{word}': {count}")
            
    else:
        print(f"Error: Unknown operation '{operation}'")
        return
    
    print(f"Text processing complete for operation: {operation}")

if __name__ == "__main__":
    main() 