from acp_sdk.client import Client
import asyncio
from colorama import Fore 

async def run_hospital_workflow() -> None:
    try:

        async with Client(base_url="http://192.168.1.104:8001") as client:
            #http://avi.kour.me:8002/api/v1/agent-proxy/endpoint/15
            "http://avi.kour.me:8012"
            print(Fore.CYAN + "Connecting to ACP SDK server..." + Fore.RESET)
            
            # Test with the correct agent name and format
            run1 = await client.run_sync(
                agent="health_agent",  # Use the correct agent name from the server
                input="Do I need rehabilitation after a shoulder reconstruction?"
            )
            
            if run1 and run1.output and len(run1.output) > 0:
                content = run1.output[0].parts[0].content
                print(Fore.LIGHTMAGENTA_EX + "Response: " + content + Fore.RESET)
            else:
                print(Fore.RED + "No response received" + Fore.RESET)
                
    except Exception as e:
        print(Fore.RED + f"Error connecting to server: {e}" + Fore.RESET)
        print(Fore.YELLOW + "Make sure the server is running with: python example_usage.py" + Fore.RESET)

if __name__ == "__main__":
    asyncio.run(run_hospital_workflow())