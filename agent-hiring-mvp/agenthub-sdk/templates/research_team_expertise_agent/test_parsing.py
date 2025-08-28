#!/usr/bin/env python3
"""
Standalone test for team members parsing functionality.
This test doesn't require the full agent dependencies.
"""

def parse_team_members(team_members_input: str) -> list:
    """
    Parse team members input string into a list of names.
    
    Args:
        team_members_input: String containing team member names (multiline or comma-separated)
        
    Returns:
        List of cleaned team member names
    """
    if not team_members_input or not isinstance(team_members_input, str):
        raise ValueError("team_members must be a non-empty string")
    
    # Split by newlines first, then by commas for any remaining lines
    lines = team_members_input.strip().split('\n')
    members = []
    
    for line in lines:
        line = line.strip()
        if line:
            # Split by comma if the line contains commas
            if ',' in line:
                comma_separated = [name.strip() for name in line.split(',') if name.strip()]
                members.extend(comma_separated)
            else:
                members.append(line)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_members = []
    for member in members:
        if member not in seen:
            seen.add(member)
            unique_members.append(member)
    
    if not unique_members:
        raise ValueError("No valid team member names found in input")
    
    return unique_members


def test_parsing():
    """Test the parsing function with various input formats."""
    
    # Test different input formats
    test_cases = [
        ("Multiline format", """George Kour
Boaz Carmeli"""),
        ("Comma-separated format", "George Kour, Boaz Carmeli"),
        ("Mixed format", """George Kour, Boaz Carmeli
John Doe
Jane Smith, Bob Johnson"""),
        ("Single name", "George Kour"),
        ("With extra whitespace", """  George Kour  
  Boaz Carmeli  """),
        ("Empty lines", """George Kour

Boaz Carmeli

"""),
        ("Multiple commas", "George Kour, , Boaz Carmeli, , John Doe"),
        ("Trailing commas", "George Kour, Boaz Carmeli,"),
        ("Leading commas", ", George Kour, Boaz Carmeli")
    ]

    print("🧪 Testing Team Members Parsing Function")
    print("=" * 60)
    
    all_passed = True
    
    for test_name, test_input in test_cases:
        try:
            parsed = parse_team_members(test_input)
            print(f"✅ {test_name}: {len(parsed)} members parsed")
            print(f"   Input: {repr(test_input)}")
            print(f"   Output: {parsed}")
            print()
        except Exception as e:
            print(f"❌ {test_name}: Error - {str(e)}")
            print(f"   Input: {repr(test_input)}")
            print()
            all_passed = False
    
    # Test error cases
    error_cases = [
        ("Empty string", ""),
        ("None input", None),
        ("Whitespace only", "   \n  \t  "),
        ("Empty after cleaning", "  ,  ,  ,  ")
    ]
    
    print("🧪 Testing Error Cases")
    print("=" * 30)
    
    for test_name, test_input in error_cases:
        try:
            parsed = parse_team_members(test_input)
            print(f"❌ {test_name}: Should have failed but returned {parsed}")
            all_passed = False
        except Exception as e:
            print(f"✅ {test_name}: Correctly failed with error: {str(e)}")
        print()
    
    # Summary
    print("=" * 60)
    if all_passed:
        print("🎉 All tests passed! The parsing function works correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return all_passed


if __name__ == "__main__":
    success = test_parsing()
    exit(0 if success else 1)
