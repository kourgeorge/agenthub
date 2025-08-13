
import requests

API_BASE = "http://localhost:8002/api/v1"
AGENT_ID = "REPRA432"
API_KEY = "7u87uNckrQRQrz1ukykH9GfvJ4xRZ6UCh2UhwsdqhLc"



headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# 1. Hire and deploy agent
hire_response = requests.post(
    f"{API_BASE}/agents/{AGENT_ID}/hire",
    json={},
    headers=headers
)
hiring_id = hire_response.json()["hiring_id"]

# 2. Initialize agent (required for persistent agents)
init_response = requests.post(
    f"{API_BASE}/agents/{AGENT_ID}/initialize",
    json={
        "hiring_id": hiring_id,
        "input_data": {
  "website_url": "https://example.com"
}
    },
    headers=headers
)

# 3. Execute queries (can be called multiple times)
exec_response = requests.post(
    f"{API_BASE}/agents/{AGENT_ID}/execute",
    json={
        "hiring_id": hiring_id,
        "input_data": {
  "question": "What is this website about?"
}
    },
    headers=headers
)
result = exec_response.json()["result"]

# 4. Cleanup when done
cleanup_response = requests.post(
    f"{API_BASE}/agents/{AGENT_ID}/cleanup",
    json={
        "hiring_id": hiring_id,
        "input_data": {}
    },
    headers=headers
)