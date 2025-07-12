# ACP Agent Template - Quick Start Guide

Get your ACP agent up and running in 5 minutes!

## 🚀 Step 1: Copy the Template

```bash
# Copy the template to your project
cp -r /path/to/agenthub-sdk/templates/acp_agent_template my_custom_agent
cd my_custom_agent
```

## 🔧 Step 2: Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

## 🎯 Step 3: Test the Default Agent

```bash
# Run the agent
python acp_agent_template.py
```

The agent will start on `http://localhost:8001`. Test it:

```bash
# Health check
curl http://localhost:8001/health

# Agent info
curl http://localhost:8001/info

# Chat with the agent
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

## ✏️ Step 4: Customize Your Agent

### 4.1 Update Basic Information

Edit `config.json`:

```json
{
  "name": "my_custom_agent",
  "description": "My awesome custom agent",
  "author": "Your Name",
  "email": "your.email@example.com",
  "entry_point": "my_custom_agent.py"
}
```

### 4.2 Rename the Agent File

```bash
mv acp_agent_template.py my_custom_agent.py
```

### 4.3 Customize the Agent Logic

Edit `my_custom_agent.py` and modify the `process_chat_message` method:

```python
async def process_chat_message(self, message: str, session: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    # Your custom logic here
    if "weather" in message.lower():
        response = "I can help with weather information!"
    elif "calculate" in message.lower():
        response = "I can perform calculations for you!"
    else:
        response = f"You said: {message}"
    
    return {
        "agent": self.name,
        "version": self.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response": response,
        "processed": True
    }
```

### 4.4 Add Custom Endpoints (Optional)

```python
async def create_app(self) -> web.Application:
    app = await super().create_app()
    
    # Add your custom endpoints
    app.router.add_get('/custom', self.custom_endpoint)
    
    return app

async def custom_endpoint(self, request: web.Request) -> web.Response:
    return web.json_response({"message": "This is my custom endpoint!"})
```

## 🧪 Step 5: Test Your Customizations

```bash
# Run your customized agent
python my_custom_agent.py

# Test the customizations
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about the weather"}'
```

## 🐳 Step 6: Deploy with Docker

```bash
# Build Docker image
docker build -t my-custom-agent .

# Run in Docker
docker run -d \
  --name my-agent \
  -p 8001:8001 \
  -e AGENT_NAME="My Custom Agent" \
  my-custom-agent
```

## 📝 Step 7: Deploy to AgentHub

```bash
# Validate the agent configuration
agenthub agent validate

# Publish to AgentHub
agenthub agent publish

# Your agent is now available for hiring!
```

## 📚 Common Customizations

### Environment Variables

Configure your agent with environment variables:

```bash
# Custom configuration
export AGENT_NAME="My Weather Agent"
export MAX_MESSAGE_LENGTH=5000
export DEBUG=true
python my_custom_agent.py
```

### Session Management

Access session data in your processing:

```python
async def process_chat_message(self, message: str, session: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    # Remember user preferences
    if "remember" in message.lower():
        session['context']['user_preference'] = "something"
    
    # Use session history
    previous_messages = session.get('messages', [])
    
    return {"response": "I remember our conversation!"}
```

### External APIs

Add external service calls:

```python
async def process_chat_message(self, message: str, session: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    if "weather" in message.lower():
        # Call weather API
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.weather.com/...') as response:
                weather_data = await response.json()
                return {"response": f"Weather: {weather_data}"}
```

## 🔍 Debugging Tips

1. **Enable Debug Mode:**
   ```bash
   DEBUG=true python my_custom_agent.py
   ```

2. **Check Logs:**
   The agent includes comprehensive logging for troubleshooting.

3. **Test Endpoints:**
   Use the included `test_template.py` to verify all endpoints work.

4. **Health Monitoring:**
   The `/health` endpoint provides real-time status information.

## 🆘 Need Help?

- Check the full README.md for detailed documentation
- Review example_usage.py for advanced patterns
- Test with test_template.py to verify functionality
- Use the AgentHub documentation for deployment guidance

## 🎉 You're Ready!

Your ACP agent is now ready for deployment. The template provides:

- ✅ Standard ACP endpoints
- ✅ Session management
- ✅ Error handling
- ✅ Docker support
- ✅ Health monitoring
- ✅ Extensible architecture

Happy building! 🚀 