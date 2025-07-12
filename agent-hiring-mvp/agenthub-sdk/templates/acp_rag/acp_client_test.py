import asyncio
import logging
from acp_sdk import Message
from acp_sdk.client import Client
from colorama import Fore, init

# Initialize colorama
init()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server_base = "http://localhost:8006"
async def test_rag_agent() -> None:
    """Test the RAG agent with sample questions."""
    try:
        async with Client(base_url=server_base) as client:
            print(Fore.CYAN + "🔗 Connecting to ACP RAG server..." + Fore.RESET)

            # Test questions about the document
            test_questions = [
                "What is the main topic of the document?",
                "Can you summarize the key findings?",
                "What methodology is used in this research?"
            ]
            
            for i, question in enumerate(test_questions, 1):
                print(f"\n{Fore.YELLOW}🤖 Question {i}: {question}{Fore.RESET}")
                print("-" * 60)
                
                # Test with the correct agent name and format
                run_result = await client.run_sync(
                    agent="llamaindex_rag_agent",  # Use the correct agent name from the server
                    input=question
                )
                
                if run_result and run_result.output and len(run_result.output) > 0:
                    content = run_result.output[0].parts[0].text
                    print(f"{Fore.LIGHTMAGENTA_EX}📝 Response: {content}{Fore.RESET}")
                else:
                    print(f"{Fore.RED}❌ No response received{Fore.RESET}")
                    
    except Exception as e:
        print(f"{Fore.RED}❌ Error connecting to server: {e}{Fore.RESET}")
        print(f"{Fore.YELLOW}💡 Make sure the RAG server is running with: python agent.py{Fore.RESET}")


if __name__ == "__main__":
    print(f"{Fore.CYAN}🧪 Testing ACP RAG Agent{Fore.RESET}")
    print("=" * 60)

    # Test the RAG agent
    asyncio.run(test_rag_agent())