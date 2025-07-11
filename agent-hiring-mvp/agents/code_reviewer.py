#!/usr/bin/env python3
"""
Code Review Expert - ACP Agent
Professional code review and analysis with ACP protocol support.
"""

import ast
import re
from typing import Dict, Any, List

class CodeReviewer:
    def __init__(self):
        self.name = "Code Review Expert"
        self.version = "1.5.0"
        self.review_criteria = [
            "code_quality", "security", "performance", "readability", "maintainability"
        ]
    
    def review_code(self, code: str, language: str = "python", focus_areas: List[str] = None) -> Dict[str, Any]:
        """Review code for quality, security, and best practices."""
        print(f"🔍 Reviewing {language} code...")
        print(f"📏 Code length: {len(code)} characters")
        
        if focus_areas is None:
            focus_areas = ["quality", "security", "performance"]
        
        review_results = {
            "language": language,
            "code_length": len(code),
            "focus_areas": focus_areas,
            "overall_score": 0,
            "issues": [],
            "suggestions": [],
            "security_concerns": [],
            "performance_notes": []
        }
        
        # Analyze code structure
        try:
            if language.lower() == "python":
                tree = ast.parse(code)
                review_results["syntax_valid"] = True
                review_results["functions"] = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
                review_results["classes"] = len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])
            else:
                review_results["syntax_valid"] = True
        except SyntaxError as e:
            review_results["syntax_valid"] = False
            review_results["issues"].append(f"Syntax error: {str(e)}")
        
        # Check for common issues
        if "security" in focus_areas:
            security_issues = self._check_security(code, language)
            review_results["security_concerns"] = security_issues
        
        if "performance" in focus_areas:
            performance_notes = self._check_performance(code, language)
            review_results["performance_notes"] = performance_notes
        
        if "quality" in focus_areas:
            quality_suggestions = self._check_quality(code, language)
            review_results["suggestions"] = quality_suggestions
        
        # Calculate overall score
        review_results["overall_score"] = self._calculate_score(review_results)
        
        print(f"✅ Code review complete. Score: {review_results['overall_score']}/10")
        return review_results
    
    def suggest_improvements(self, code: str, issues: List[str] = None) -> Dict[str, Any]:
        """Suggest specific improvements for code."""
        print(f"💡 Generating improvement suggestions...")
        
        suggestions = {
            "code": code,
            "improvements": [],
            "refactored_code": code,
            "explanation": ""
        }
        
        if issues:
            for issue in issues:
                if "naming" in issue.lower():
                    suggestions["improvements"].append({
                        "type": "naming",
                        "description": "Use more descriptive variable and function names",
                        "example": "Instead of 'x', use 'user_count' or 'total_items'"
                    })
                elif "complexity" in issue.lower():
                    suggestions["improvements"].append({
                        "type": "complexity",
                        "description": "Break down complex functions into smaller, more manageable pieces",
                        "example": "Extract helper functions for better readability"
                    })
                elif "documentation" in issue.lower():
                    suggestions["improvements"].append({
                        "type": "documentation",
                        "description": "Add docstrings and comments to explain complex logic",
                        "example": "Add function docstrings following PEP 257"
                    })
        
        print(f"✅ Improvement suggestions generated")
        return suggestions
    
    def _check_security(self, code: str, language: str) -> List[str]:
        """Check for security vulnerabilities."""
        security_issues = []
        
        # Check for common security patterns
        dangerous_patterns = [
            r"eval\s*\(",
            r"exec\s*\(",
            r"subprocess\.call\s*\(",
            r"os\.system\s*\(",
            r"input\s*\("
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                security_issues.append(f"Potential security risk: {pattern.strip()}")
        
        return security_issues
    
    def _check_performance(self, code: str, language: str) -> List[str]:
        """Check for performance issues."""
        performance_notes = []
        
        # Check for common performance issues
        if "for" in code and "range" in code:
            performance_notes.append("Consider using list comprehensions for better performance")
        
        if "import *" in code:
            performance_notes.append("Avoid wildcard imports for better performance and clarity")
        
        return performance_notes
    
    def _check_quality(self, code: str, language: str) -> List[str]:
        """Check for code quality issues."""
        quality_suggestions = []
        
        # Check line length
        lines = code.split('\n')
        long_lines = [i+1 for i, line in enumerate(lines) if len(line) > 79]
        if long_lines:
            quality_suggestions.append(f"Lines {long_lines} exceed 79 characters")
        
        # Check for magic numbers
        if re.search(r'\b\d{3,}\b', code):
            quality_suggestions.append("Consider extracting magic numbers to named constants")
        
        return quality_suggestions
    
    def _calculate_score(self, review_results: Dict[str, Any]) -> int:
        """Calculate overall code quality score."""
        score = 10
        
        # Deduct points for issues
        score -= len(review_results["issues"]) * 2
        score -= len(review_results["security_concerns"]) * 3
        score -= len(review_results["performance_notes"]) * 1
        
        return max(0, min(10, score))

def main():
    """Main ACP agent function."""
    reviewer = CodeReviewer()
    
    # Get input data
    task = input_data.get('task', 'review_code')
    code = input_data.get('code', 'print("Hello World")')
    
    if task == 'review_code':
        language = input_data.get('language', 'python')
        focus_areas = input_data.get('focus_areas', None)
        result = reviewer.review_code(code, language, focus_areas)
    elif task == 'suggest_improvements':
        issues = input_data.get('issues', None)
        result = reviewer.suggest_improvements(code, issues)
    else:
        result = {"error": f"Unknown task: {task}"}
    
    print(f"🎯 Code Review Expert completed task: {task}")
    print(f"📋 Result: {result}")

if __name__ == "__main__":
    main() 