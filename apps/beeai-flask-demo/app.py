# app.py
from flask import Flask, render_template, request, jsonify
import httpx
import asyncio
from typing import List, Dict, Any

app = Flask(__name__)

# Configuration
BEEAI_BASE_URL = "http://localhost:8333"
API_BASE_URL = f"{BEEAI_BASE_URL}/api/v1"
ACP_BASE_URL = f"{API_BASE_URL}/acp"

class BeeAIClient:
    def __init__(self, base_url: str = BEEAI_BASE_URL):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.acp_base = f"{self.api_base}/acp"
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.acp_base}/agents")
            response.raise_for_status()
            data = response.json()
            return data.get("agents", [])
    
    async def get_agent_details(self, agent_name: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.acp_base}/agents/{agent_name}")
            response.raise_for_status()
            return response.json()
    
    async def run_agent(self, agent_name: str, input_text: str) -> Dict[str, Any]:
        payload = {
            "agent_name": agent_name,
            "input": [
                {
                    "role": "user",
                    "parts": [{"content": input_text}]
                }
            ]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.acp_base}/runs", json=payload)
            response.raise_for_status()
            return response.json()
    
    async def get_run_status(self, run_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.acp_base}/runs/{run_id}")
            response.raise_for_status()
            return response.json()

beeai_client = BeeAIClient()

def run_async(coro):
    return asyncio.run(coro)

@app.route('/')
def index():
    try:
        agents = run_async(beeai_client.list_agents())
        return render_template('index.html', agents=agents)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/agent/<agent_name>')
def agent_detail(agent_name):
    try:
        agent = run_async(beeai_client.get_agent_details(agent_name))
        return render_template('agent_detail.html', agent=agent)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/api/agents')
def api_list_agents():
    try:
        agents = run_async(beeai_client.list_agents())
        return jsonify({"agents": agents})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/agents/<agent_name>/run', methods=['POST'])
def api_run_agent(agent_name):
    try:
        data = request.get_json()
        input_text = data.get('input', '')
        if not input_text:
            return jsonify({"error": "Input text is required"}), 400
        result = run_async(beeai_client.run_agent(agent_name, input_text))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/runs/<run_id>')
def api_get_run_status(run_id):
    try:
        status = run_async(beeai_client.get_run_status(run_id))
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 