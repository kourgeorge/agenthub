import requests

API_BASE = "http://localhost:8002/api/v1"
AGENT_ID, USER_ID = 8, 1

# Hire agent
hiring_resp = requests.post(f"{API_BASE}/hiring/", json={"agent_id": AGENT_ID, "user_id": USER_ID})
hiring_id = hiring_resp.json().get("hiring_id")

# Execute agent
task_data = {
    "message": "Latest developments in quantum computing", "depth": 2, "breadth": 3
}

exec_resp = requests.post(f"{API_BASE}/execution/",
                          json={"hiring_id": hiring_id, "input_data": task_data})
exec_id = exec_resp.json().get("execution_id")

# Run the execution
run_resp = requests.post(f"{API_BASE}/execution/{exec_id}/run")

result_resp = requests.get(f"{API_BASE}/execution/{exec_id}")
result_data = result_resp.json()
output = result_data.get("output_data", {})
print(output.get('answer', output.get('output', output.get('report', output))))
