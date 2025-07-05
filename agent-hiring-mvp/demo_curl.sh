#!/bin/bash

# AI Agent Hiring System - Curl Demo Script
# This script demonstrates how to hire an agent and run requests against it using curl

BASE_URL="http://localhost:8002"
API_BASE="$BASE_URL/api/v1"

echo "🚀 AI AGENT HIRING SYSTEM - CURL DEMO"
echo "======================================"

# Test server connection
echo "Testing server connection..."
curl -s "$BASE_URL/health" | jq .

echo -e "\n📋 STEP 1: List available agents"
echo "======================================"
curl -s "$API_BASE/agents/" | jq .

echo -e "\n🤝 STEP 2: Hire an agent"
echo "======================================"
AGENT_ID=1
USER_ID=1

HIRING_RESPONSE=$(curl -s -X POST "$API_BASE/hiring/" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": '$AGENT_ID',
    "user_id": '$USER_ID',
    "requirements": {
      "task_type": "data_analysis",
      "priority": "high",
      "expected_duration": "2 hours"
    },
    "budget": 50.0,
    "duration_hours": 2
  }')

echo "$HIRING_RESPONSE" | jq .

# Extract hiring ID
HIRING_ID=$(echo "$HIRING_RESPONSE" | jq -r '.id')
echo "Hiring ID: $HIRING_ID"

echo -e "\n✅ STEP 3: Activate the hiring"
echo "======================================"
curl -s -X PUT "$API_BASE/hiring/$HIRING_ID/activate" | jq .

echo -e "\n⚡ STEP 4: Create an execution"
echo "======================================"
EXECUTION_RESPONSE=$(curl -s -X POST "$API_BASE/execution/" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": '$AGENT_ID',
    "hiring_id": '$HIRING_ID',
    "user_id": '$USER_ID',
    "input_data": {
      "message": "Hello! I need help analyzing some data.",
      "data": "Sample dataset for analysis",
      "requirements": "Please provide insights and recommendations"
    }
  }')

echo "$EXECUTION_RESPONSE" | jq .

# Extract execution ID
EXECUTION_ID=$(echo "$EXECUTION_RESPONSE" | jq -r '.execution_id')
echo "Execution ID: $EXECUTION_ID"

echo -e "\n🚀 STEP 5: Run the agent"
echo "======================================"
curl -s -X POST "$API_BASE/execution/$EXECUTION_ID/run" | jq .

echo -e "\n📊 STEP 6: Check execution status"
echo "======================================"
curl -s "$API_BASE/execution/$EXECUTION_ID" | jq .

echo -e "\n🔧 STEP 7: ACP Communication Demo"
echo "======================================"

# Create ACP session
echo "Creating ACP session..."
ACP_SESSION=$(curl -s -X POST "$API_BASE/acp/session" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": '$AGENT_ID',
    "user_id": '$USER_ID'
  }')

echo "$ACP_SESSION" | jq .

SESSION_ID=$(echo "$ACP_SESSION" | jq -r '.session_id')
echo "Session ID: $SESSION_ID"

# Send start message
echo -e "\nSending ACP start message..."
curl -s -X POST "$API_BASE/acp/$SESSION_ID/message" \
  -H "Content-Type: application/json" \
  -d '{"type": "start"}' | jq .

# Call a tool
echo -e "\nCalling a tool via ACP..."
curl -s -X POST "$API_BASE/acp/$SESSION_ID/message" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "tool_call",
    "tool": "search",
    "args": {"query": "data analysis best practices"}
  }' | jq .

# Submit result
echo -e "\nSubmitting result via ACP..."
curl -s -X POST "$API_BASE/acp/$SESSION_ID/message" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "result",
    "result": {
      "analysis": "Data analysis completed successfully",
      "insights": ["Trend identified", "Anomaly detected"],
      "recommendations": ["Implement monitoring", "Review data quality"]
    }
  }' | jq .

# End session
echo -e "\nEnding ACP session..."
curl -s -X POST "$API_BASE/acp/$SESSION_ID/message" \
  -H "Content-Type: application/json" \
  -d '{"type": "end"}' | jq .

echo -e "\n📈 STEP 8: View statistics"
echo "======================================"
echo "User hiring statistics:"
curl -s "$API_BASE/hiring/stats/user/$USER_ID" | jq .

echo -e "\nAgent execution statistics:"
curl -s "$API_BASE/execution/stats/agent/$AGENT_ID" | jq .

echo -e "\n📋 STEP 9: List user hirings"
echo "======================================"
curl -s "$API_BASE/hiring/user/$USER_ID" | jq .

echo -e "\n⚡ STEP 10: List agent executions"
echo "======================================"
curl -s "$API_BASE/execution/agent/$AGENT_ID" | jq .

echo -e "\n🎉 DEMO COMPLETED!"
echo "======================================"
echo "This demo showed the complete workflow:"
echo "1. ✅ Browse available agents"
echo "2. ✅ Hire an agent"
echo "3. ✅ Activate the hiring"
echo "4. ✅ Create an execution"
echo "5. ✅ Run the agent"
echo "6. ✅ Check execution status"
echo "7. ✅ Use ACP communication"
echo "8. ✅ View statistics"
echo "9. ✅ List user hirings"
echo "10. ✅ List agent executions"

echo -e "\n🌐 API Documentation: $BASE_URL/docs"
echo "📊 ReDoc Documentation: $BASE_URL/redoc"
echo "🔗 Base API URL: $API_BASE" 