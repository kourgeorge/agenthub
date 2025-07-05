"""Example Data Analyzer Agent."""

import json
import logging
from typing import Any, Dict, List

from ..agent import DataProcessingAgent, AgentConfig

logger = logging.getLogger(__name__)


class DataAnalyzerAgent(DataProcessingAgent):
    """An intelligent agent that analyzes data and provides insights."""
    
    def __init__(self):
        config = AgentConfig(
            name="Data Analyzer",
            description="An intelligent agent that analyzes data and provides insights",
            version="1.0.0",
            author="Example Creator",
            email="creator@example.com",
            entry_point="data_analyzer_agent.py:DataAnalyzerAgent",
            requirements=["pandas", "numpy", "matplotlib"],
            tags=["data-analysis", "insights", "visualization"],
            category="data-science",
            pricing_model="per_use",
            price_per_use=0.10,
        )
        super().__init__(config)
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process data analysis request."""
        data = message.get("data", {})
        operation = message.get("operation", "analyze")
        
        if operation == "analyze":
            return await self._analyze_data(data)
        elif operation == "visualize":
            return await self._create_visualization(data)
        elif operation == "summary":
            return await self._generate_summary(data)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
            }
    
    async def _analyze_data(self, data: Any) -> Dict[str, Any]:
        """Analyze the provided data."""
        try:
            # Simulate data analysis
            if isinstance(data, list):
                analysis = {
                    "count": len(data),
                    "type": "list",
                    "summary": f"List with {len(data)} items",
                }
            elif isinstance(data, dict):
                analysis = {
                    "count": len(data),
                    "type": "dictionary",
                    "keys": list(data.keys()),
                    "summary": f"Dictionary with {len(data)} keys",
                }
            else:
                analysis = {
                    "type": type(data).__name__,
                    "summary": str(data),
                }
            
            return {
                "status": "success",
                "operation": "analyze",
                "result": analysis,
            }
        
        except Exception as e:
            logger.error(f"Error analyzing data: {e}")
            return {
                "status": "error",
                "error": f"Analysis failed: {str(e)}",
            }
    
    async def _create_visualization(self, data: Any) -> Dict[str, Any]:
        """Create visualization of the data."""
        try:
            # Simulate visualization creation
            if isinstance(data, list) and len(data) > 0:
                viz_data = {
                    "type": "chart",
                    "chart_type": "bar",
                    "data_points": len(data),
                    "preview": data[:5] if len(data) > 5 else data,
                }
            else:
                viz_data = {
                    "type": "text",
                    "content": "No visualization available for this data type",
                }
            
            return {
                "status": "success",
                "operation": "visualize",
                "result": viz_data,
            }
        
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            return {
                "status": "error",
                "error": f"Visualization failed: {str(e)}",
            }
    
    async def _generate_summary(self, data: Any) -> Dict[str, Any]:
        """Generate a summary of the data."""
        try:
            if isinstance(data, list):
                summary = f"List containing {len(data)} items"
                if len(data) > 0:
                    summary += f". First item: {data[0]}"
            elif isinstance(data, dict):
                summary = f"Dictionary with {len(data)} key-value pairs"
                if len(data) > 0:
                    first_key = list(data.keys())[0]
                    summary += f". Sample key: {first_key}"
            else:
                summary = f"Data of type {type(data).__name__}: {str(data)}"
            
            return {
                "status": "success",
                "operation": "summary",
                "result": {"summary": summary},
            }
        
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {
                "status": "error",
                "error": f"Summary generation failed: {str(e)}",
            }


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_agent():
        agent = DataAnalyzerAgent()
        
        # Test data analysis
        test_data = [1, 2, 3, 4, 5]
        result = await agent.process_message({
            "operation": "analyze",
            "data": test_data,
        })
        print("Analysis result:", result)
        
        # Test visualization
        result = await agent.process_message({
            "operation": "visualize",
            "data": test_data,
        })
        print("Visualization result:", result)
        
        # Test summary
        result = await agent.process_message({
            "operation": "summary",
            "data": test_data,
        })
        print("Summary result:", result)
    
    asyncio.run(test_agent()) 