"""Example Chat Assistant Agent."""

import json
import logging
import re
from typing import Any, Dict, List

from ..agent import ChatAgent, AgentConfig

logger = logging.getLogger(__name__)


class ChatAssistantAgent(ChatAgent):
    """A helpful chat assistant that can answer questions and provide guidance."""
    
    def __init__(self):
        config = AgentConfig(
            name="Chat Assistant",
            description="A helpful chat assistant that can answer questions and provide guidance",
            version="1.0.0",
            author="Example Creator",
            email="creator@example.com",
            entry_point="chat_assistant_agent.py:ChatAssistantAgent",
            requirements=["openai", "markdown"],
            tags=["chat", "assistant", "help", "guidance"],
            category="communication",
            pricing_model="per_use",
            price_per_use=0.05,
        )
        super().__init__(config)
        
        # Initialize knowledge base
        self.knowledge_base = {
            "greetings": [
                "Hello!", "Hi there!", "Greetings!", "Welcome!",
                "How can I help you today?", "Nice to meet you!"
            ],
            "farewells": [
                "Goodbye!", "See you later!", "Take care!", "Have a great day!",
                "Until next time!", "Bye!"
            ],
            "help": [
                "I'm here to help! What would you like to know?",
                "I can assist you with various topics. What's on your mind?",
                "Feel free to ask me anything!"
            ],
        }
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a chat message."""
        user_message = message.get("message", "").strip()
        
        if not user_message:
            return {
                "status": "error",
                "error": "Empty message received",
            }
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Generate response
        response = await self._generate_response(user_message)
        
        # Add response to history
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return {
            "status": "success",
            "response": response,
            "conversation_id": message.get("conversation_id"),
            "conversation_length": len(self.conversation_history),
        }
    
    async def _generate_response(self, message: str) -> str:
        """Generate a response to the user message."""
        message_lower = message.lower()
        
        # Check for greetings
        if any(greeting in message_lower for greeting in ["hello", "hi", "hey", "greetings"]):
            import random
            return random.choice(self.knowledge_base["greetings"])
        
        # Check for farewells
        if any(farewell in message_lower for farewell in ["bye", "goodbye", "see you", "farewell"]):
            import random
            return random.choice(self.knowledge_base["farewells"])
        
        # Check for help requests
        if any(help_word in message_lower for help_word in ["help", "assist", "support"]):
            import random
            return random.choice(self.knowledge_base["help"])
        
        # Check for questions
        if message_lower.endswith("?") or message_lower.startswith(("what", "how", "why", "when", "where", "who")):
            return await self._answer_question(message)
        
        # Check for specific topics
        if any(topic in message_lower for topic in ["weather", "temperature"]):
            return "I can't check the weather in real-time, but I can help you with other questions!"
        
        if any(topic in message_lower for topic in ["time", "date"]):
            from datetime import datetime
            now = datetime.now()
            return f"The current time is {now.strftime('%H:%M:%S')} and the date is {now.strftime('%Y-%m-%d')}."
        
        if any(topic in message_lower for topic in ["math", "calculate", "equation"]):
            return await self._handle_math_request(message)
        
        # Default response
        return await self._generate_default_response(message)
    
    async def _answer_question(self, question: str) -> str:
        """Answer a specific question."""
        question_lower = question.lower()
        
        if "name" in question_lower:
            return "My name is Chat Assistant, and I'm here to help you!"
        
        if "capabilities" in question_lower or "can you" in question_lower:
            return "I can help with general questions, basic math, time/date queries, and casual conversation. What would you like to know?"
        
        if "how are you" in question_lower:
            return "I'm doing well, thank you for asking! How are you?"
        
        # Default question response
        return "That's an interesting question! I'm still learning, but I'll do my best to help. Could you rephrase that or ask something else?"
    
    async def _handle_math_request(self, message: str) -> str:
        """Handle basic math calculations."""
        try:
            # Extract numbers and operators
            import re
            numbers = re.findall(r'\d+', message)
            operators = re.findall(r'[\+\-\*\/]', message)
            
            if len(numbers) >= 2 and len(operators) >= 1:
                num1 = float(numbers[0])
                num2 = float(numbers[1])
                op = operators[0]
                
                if op == '+':
                    result = num1 + num2
                elif op == '-':
                    result = num1 - num2
                elif op == '*':
                    result = num1 * num2
                elif op == '/':
                    if num2 == 0:
                        return "Sorry, I can't divide by zero!"
                    result = num1 / num2
                else:
                    return "I can only handle basic arithmetic operations (+, -, *, /)."
                
                return f"The result of {num1} {op} {num2} = {result}"
            else:
                return "I can help with basic math! Try asking something like 'What is 5 + 3?'"
        
        except Exception as e:
            logger.error(f"Error handling math request: {e}")
            return "Sorry, I couldn't process that math request. Could you try rephrasing it?"
    
    async def _generate_default_response(self, message: str) -> str:
        """Generate a default response for unrecognized messages."""
        responses = [
            "I understand you said: '{message}'. That's interesting!",
            "Thanks for sharing that with me. Is there anything specific you'd like to know?",
            "I'm here to help! What would you like to discuss?",
            "That's a good point. How can I assist you further?",
            "I appreciate your message. Is there anything I can help you with?",
        ]
        
        import random
        response_template = random.choice(responses)
        return response_template.format(message=message)
    
    async def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation."""
        if not self.conversation_history:
            return {"summary": "No conversation history"}
        
        user_messages = [msg["content"] for msg in self.conversation_history if msg["role"] == "user"]
        assistant_messages = [msg["content"] for msg in self.conversation_history if msg["role"] == "assistant"]
        
        return {
            "total_messages": len(self.conversation_history),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "conversation_start": self.conversation_history[0]["content"] if self.conversation_history else None,
            "last_message": self.conversation_history[-1]["content"] if self.conversation_history else None,
        }


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_agent():
        agent = ChatAssistantAgent()
        
        # Test greetings
        result = await agent.process_message({"message": "Hello!"})
        print("Greeting response:", result["response"])
        
        # Test questions
        result = await agent.process_message({"message": "What's your name?"})
        print("Question response:", result["response"])
        
        # Test math
        result = await agent.process_message({"message": "What is 5 + 3?"})
        print("Math response:", result["response"])
        
        # Test time
        result = await agent.process_message({"message": "What time is it?"})
        print("Time response:", result["response"])
        
        # Get conversation summary
        summary = await agent.get_conversation_summary()
        print("Conversation summary:", summary)
    
    asyncio.run(test_agent()) 