#!/usr/bin/env python3
"""
Test script for ACP Agent Template

This script demonstrates how to test the ACP agent template locally
before deployment. It includes tests for all standard endpoints.

Usage:
    python test_template.py
"""

import asyncio
import json
import aiohttp
import time
from typing import Dict, Any


class ACPAgentTester:
    """Simple test client for ACP agent endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health(self) -> Dict[str, Any]:
        """Test the health endpoint."""
        async with self.session.get(f"{self.base_url}/health") as response:
            return {
                "status_code": response.status,
                "data": await response.json() if response.status == 200 else await response.text()
            }
    
    async def test_info(self) -> Dict[str, Any]:
        """Test the info endpoint."""
        async with self.session.get(f"{self.base_url}/info") as response:
            return {
                "status_code": response.status,
                "data": await response.json() if response.status == 200 else await response.text()
            }
    
    async def test_chat(self, message: str, session_id: str = None) -> Dict[str, Any]:
        """Test the chat endpoint."""
        payload = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        
        async with self.session.post(
            f"{self.base_url}/chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            return {
                "status_code": response.status,
                "data": await response.json() if response.status == 200 else await response.text()
            }
    
    async def test_message(self, content: str, message_type: str = "text") -> Dict[str, Any]:
        """Test the generic message endpoint."""
        payload = {
            "type": message_type,
            "content": content
        }
        
        async with self.session.post(
            f"{self.base_url}/message",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            return {
                "status_code": response.status,
                "data": await response.json() if response.status == 200 else await response.text()
            }
    
    async def test_sessions(self) -> Dict[str, Any]:
        """Test the sessions list endpoint."""
        async with self.session.get(f"{self.base_url}/sessions") as response:
            return {
                "status_code": response.status,
                "data": await response.json() if response.status == 200 else await response.text()
            }
    
    async def test_status(self) -> Dict[str, Any]:
        """Test the status endpoint."""
        async with self.session.get(f"{self.base_url}/") as response:
            return {
                "status_code": response.status,
                "data": await response.json() if response.status == 200 else await response.text()
            }


async def run_tests():
    """Run comprehensive tests on the ACP agent template."""
    
    print("🧪 ACP Agent Template Test Suite")
    print("=" * 50)
    
    # Wait for server to be ready
    print("⏳ Waiting for server to be ready...")
    await asyncio.sleep(2)
    
    async with ACPAgentTester() as tester:
        tests = [
            ("Health Check", tester.test_health),
            ("Agent Info", tester.test_info),
            ("Status", tester.test_status),
            ("Chat - Hello", lambda: tester.test_chat("Hello, how are you?")),
            ("Chat - Help", lambda: tester.test_chat("help")),
            ("Chat - Capabilities", lambda: tester.test_chat("what can you do?")),
            ("Message - Text", lambda: tester.test_message("Test message")),
            ("Message - Ping", lambda: tester.test_message("ping", "ping")),
            ("Sessions List", tester.test_sessions),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running: {test_name}")
            try:
                result = await test_func()
                
                if result["status_code"] == 200:
                    print(f"   ✅ PASS - Status: {result['status_code']}")
                    if isinstance(result["data"], dict):
                        # Print key information
                        if "response" in result["data"]:
                            print(f"   📝 Response: {result['data']['response']}")
                        elif "message" in result["data"]:
                            print(f"   📝 Message: {result['data']['message']}")
                        elif "status" in result["data"]:
                            print(f"   📝 Status: {result['data']['status']}")
                else:
                    print(f"   ❌ FAIL - Status: {result['status_code']}")
                    print(f"   📝 Error: {result['data']}")
                
                results.append((test_name, result["status_code"] == 200, result))
                
            except Exception as e:
                print(f"   ❌ ERROR - {str(e)}")
                results.append((test_name, False, {"error": str(e)}))
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed! Your ACP agent is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        # Show detailed results for failures
        failures = [(name, result) for name, success, result in results if not success]
        if failures:
            print("\n❌ Failed Tests Details:")
            for name, result in failures:
                print(f"   • {name}: {result}")
        
        return passed == total


async def test_conversation_flow():
    """Test a complete conversation flow with session management."""
    
    print("\n🗣️  Testing Conversation Flow")
    print("-" * 30)
    
    async with ACPAgentTester() as tester:
        # Start a conversation
        result1 = await tester.test_chat("Hello, my name is Alice")
        session_id = result1["data"].get("session_id") if result1["status_code"] == 200 else None
        
        if session_id:
            print(f"✅ Session created: {session_id}")
            
            # Continue the conversation with the same session
            result2 = await tester.test_chat("What's my name?", session_id)
            
            if result2["status_code"] == 200:
                print(f"✅ Session maintained: {result2['data']['response']}")
            else:
                print(f"❌ Session continuation failed: {result2['data']}")
        else:
            print(f"❌ Session creation failed: {result1['data']}")


def print_usage():
    """Print usage instructions."""
    print("\n" + "=" * 50)
    print("🚀 Usage Instructions")
    print("=" * 50)
    print("1. Start your ACP agent:")
    print("   python acp_agent_template.py")
    print("")
    print("2. In another terminal, run this test:")
    print("   python test_template.py")
    print("")
    print("3. Or test manually with curl:")
    print("   curl http://localhost:8001/health")
    print("   curl -X POST http://localhost:8001/chat \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"message\": \"Hello!\"}'")
    print("")
    print("📝 Expected behavior:")
    print("   - All endpoints should return 200 status")
    print("   - Chat should provide intelligent responses")
    print("   - Sessions should be maintained across requests")
    print("   - Health check should show uptime and stats")


async def main():
    """Main test runner."""
    print_usage()
    
    # Basic connectivity test
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8001/health", timeout=5) as response:
                if response.status == 200:
                    print("\n✅ Server is running and accessible")
                else:
                    print(f"\n❌ Server returned status {response.status}")
                    return
    except Exception as e:
        print(f"\n❌ Cannot connect to server: {e}")
        print("Make sure your ACP agent is running on http://localhost:8001")
        return
    
    # Run the test suite
    success = await run_tests()
    
    # Test conversation flow
    await test_conversation_flow()
    
    # Final message
    if success:
        print("\n🎉 Your ACP agent template is working perfectly!")
        print("Ready for customization and deployment.")
    else:
        print("\n⚠️  Some issues detected. Please check the agent implementation.")


if __name__ == "__main__":
    asyncio.run(main()) 