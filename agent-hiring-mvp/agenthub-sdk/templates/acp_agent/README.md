# ACP Agent Template

A comprehensive template for creating ACP (Agent Communication Protocol) server agents with the AgentHub platform. This template provides a production-ready foundation with standard endpoints, session management, error handling, and extensible architecture.

## Features

✅ **Standard ACP Endpoints**
- `/health` - Health monitoring and uptime tracking
- `/info` - Agent information and capabilities
- `/chat` - Interactive chat interface with session support
- `/message` - Generic message processing
- `/sessions` - Session management (list, get, delete)

✅ **Advanced Functionality**
- Session management with automatic cleanup
- Message history and conversation tracking
- CORS support for web clients
- Comprehensive error handling and logging
- Environment-based configuration
- Request/response middleware
- Concurrent session support

✅ **Production Ready**
- Docker containerization
- Health checks for monitoring
- Non-root user security
- Proper logging and debugging
- Input validation and sanitization
- Graceful shutdown handling

## Quick Start

### 1. Copy the Template

```bash
# Copy this template to your project directory
cp -r templates/acp_agent_template my_agent
cd my_agent
```

### 2. Customize Your Agent

1. **Rename the files:**
   ```bash
   mv acp_agent_template.py my_agent.py
   ```

2. **Update config.json:**
   ```json
   {
     "name": "my_agent",
     "description": "My custom ACP agent",
     "author": "Your Name",
     "email": "your.email@example.com",
     "entry_point": "my_agent.py"
   }
   ```

3. **Customize the agent class:**
   ```python
   class MyAgent(ACPAgentTemplate):
       def __init__(self):
           super().__init__(
               name="My Agent",
               version="1.0.0",
               description="My custom ACP agent"
           )
       
       async def process_chat_message(self, message, session, context):
           # Add your custom logic here
           response = f"My agent processed: {message}"
           return {
               "agent": self.name,
               "response": response,
               "timestamp": datetime.now(timezone.utc).isoformat()
           }
   ```

### 3. Test Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent
python my_agent.py

# Test endpoints
curl http://localhost:8001/health
curl http://localhost:8001/info
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

### 4. Deploy with AgentHub

```bash
# Validate the agent
agenthub agent validate

# Publish to AgentHub
agenthub agent publish

# The agent will be available for hiring and deployment
```

## Configuration

### Environment Variables

Configure your agent using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8001` | Server port |
| `HOST` | `0.0.0.0` | Server host |
| `DEBUG` | `false` | Enable debug mode |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `MAX_MESSAGE_LENGTH` | `10000` | Maximum message length |
| `SESSION_TIMEOUT` | `3600` | Session timeout in seconds |
| `AGENT_NAME` | Template name | Custom agent name |
| `AGENT_VERSION` | `1.0.0` | Custom agent version |
| `AGENT_DESCRIPTION` | Template description | Custom description |

### Example Docker Run

```bash
docker run -d \
  --name my-agent \
  -p 8001:8001 \
  -e AGENT_NAME="My Custom Agent" \
  -e DEBUG=true \
  -e MAX_MESSAGE_LENGTH=5000 \
  my-agent:latest
```

## API Documentation

### Health Check

**GET /health**

Returns agent health status and uptime information.

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "uptime_seconds": 3600,
  "version": "1.0.0",
  "sessions_active": 5,
  "messages_processed": 150
}
```

### Agent Information

**GET /info**

Returns comprehensive agent information and capabilities.

```json
{
  "name": "ACP Agent Template",
  "version": "1.0.0",
  "description": "A template ACP server agent",
  "agent_type": "acp_server",
  "endpoints": {...},
  "capabilities": [...],
  "configuration": {...},
  "stats": {...}
}
```

### Chat Interface

**POST /chat**

Process chat messages with session management.

**Request:**
```json
{
  "message": "Hello, how are you?",
  "session_id": "optional_session_id",
  "context": {"key": "value"}
}
```

**Response:**
```json
{
  "agent": "ACP Agent Template",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00Z",
  "response": "Hello! I'm doing well, thank you for asking.",
  "processed": true,
  "session_id": "session_1_1704110400",
  "message_count": 2
}
```

### Generic Messages

**POST /message**

Process different types of messages.

**Request:**
```json
{
  "type": "text",
  "content": "Your message content",
  "session_id": "optional_session_id",
  "metadata": {"key": "value"}
}
```

### Session Management

**GET /sessions**
- List all active sessions

**GET /sessions/{session_id}**
- Get detailed session information

**DELETE /sessions/{session_id}**
- Delete a session and its history

## Customization Guide

### Adding Custom Endpoints

```python
async def create_app(self) -> web.Application:
    app = await super().create_app()
    
    # Add custom endpoints
    app.router.add_get('/custom', self.custom_endpoint)
    app.router.add_post('/webhook', self.webhook_handler)
    
    return app

async def custom_endpoint(self, request: web.Request) -> web.Response:
    return web.json_response({"message": "Custom endpoint"})
```

### Adding External Services

```python
class MyAgent(ACPAgentTemplate):
    def __init__(self):
        super().__init__()
        self.database = None
        self.redis_client = None
    
    async def create_app(self):
        app = await super().create_app()
        
        # Initialize external services
        self.database = await create_db_connection()
        self.redis_client = await create_redis_connection()
        
        return app
```

### Custom Message Processing

```python
async def process_chat_message(self, message, session, context):
    # Add intent recognition
    intent = await self.detect_intent(message)
    
    if intent == "weather":
        response = await self.get_weather(message)
    elif intent == "calculate":
        response = await self.calculate(message)
    else:
        response = await self.default_response(message)
    
    return {
        "agent": self.name,
        "response": response,
        "intent": intent,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

## Development

### Testing

```bash
# Run unit tests
python -m pytest tests/

# Test with different configurations
DEBUG=true MAX_MESSAGE_LENGTH=1000 python my_agent.py
```

### Docker Development

```bash
# Build the image
docker build -t my-agent .

# Run with volume mapping for development
docker run -d \
  --name my-agent-dev \
  -p 8001:8001 \
  -v $(pwd):/app \
  -e DEBUG=true \
  my-agent
```

### Monitoring

The agent provides built-in monitoring through:
- Health endpoint for load balancers
- Request logging middleware
- Session and message statistics
- Error tracking and reporting

## Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Change the port
   PORT=8002 python my_agent.py
   ```

2. **CORS errors:**
   ```bash
   # Allow specific origins
   CORS_ORIGINS="http://localhost:3000,https://myapp.com" python my_agent.py
   ```

3. **Memory issues with sessions:**
   ```bash
   # Reduce session timeout
   SESSION_TIMEOUT=1800 python my_agent.py
   ```

### Debug Mode

Enable debug mode for detailed error messages:

```bash
DEBUG=true python my_agent.py
```

## Contributing

1. Follow the existing code structure
2. Add comprehensive docstrings
3. Include error handling for all endpoints
4. Update the config.json with new capabilities
5. Test with different configurations

## License

This template is part of the AgentHub SDK and follows the same license terms.

## Support

For questions and support:
- Check the AgentHub documentation
- Join the community forum
- Submit issues on GitHub 