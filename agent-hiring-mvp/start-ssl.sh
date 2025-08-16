#!/bin/bash

# AgentHub SSL Server Startup Script (Cross-platform)
echo "🚀 Starting AgentHub SSL with Caddy reverse proxy..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    echo "   - macOS: Start Docker Desktop"
    echo "   - Windows: Start Docker Desktop"
    echo "   - Linux: sudo systemctl start docker"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install docker-compose first."
    echo "   - macOS: brew install docker-compose"
    echo "   - Windows: Install with Docker Desktop"
    echo "   - Linux: sudo apt-get install docker-compose"
    exit 1
fi

# Detect OS for better curl commands
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows with Git Bash
    CURL_OPTS="-s"
    echo "🪟 Windows detected - using Windows-compatible settings"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CURL_OPTS="-s"
    echo "🍎 macOS detected"
else
    # Linux
    CURL_OPTS="-s"
    echo "🐧 Linux detected"
fi

# Check if your web UI is running
if ! curl $CURL_OPTS http://localhost:8080 > /dev/null 2>&1; then
    echo "⚠️  Warning: Your web UI doesn't seem to be running on port 8080"
    echo "   Please start your web UI first on port 8080"
    echo ""
    echo "   Or in another terminal:"
    echo "   cd ai-agent-marketplace-core && npm run dev"
    echo ""
    read -p "Press Enter when your web UI is running on port 8080, or Ctrl+C to cancel..."
fi

# Check if your FastAPI server is running
if ! curl $CURL_OPTS http://localhost:8002/health > /dev/null 2>&1; then
    echo "⚠️  Warning: Your FastAPI server doesn't seem to be running on port 8002"
    echo "   Please start your FastAPI server first:"
    echo "   cd server && python -m server.main --host 0.0.0.0 --port 8002"
    echo ""
    echo "   Or in another terminal:"
    echo "   cd server && python -m server.main --host 0.0.0.0 --port 8002 &"
    echo ""
    read -p "Press Enter when your FastAPI server is running on port 8002, or Ctrl+C to cancel..."
fi

# Start Caddy only
echo "🔨 Starting Caddy reverse proxy..."
docker-compose up -d

# Wait for Caddy to be ready
echo "⏳ Waiting for Caddy to be ready..."
sleep 5

# Check service status
echo "📊 Caddy status:"
docker-compose ps

echo ""
echo "✅ Caddy is now running with SSL!"
echo ""
echo "🌐 Access your services:"
echo "   - Web UI (HTTPS): https://localhost"
echo "   - HTTP (redirects to HTTPS): http://localhost"
echo "   - FastAPI Server (internal): http://localhost:8002"
echo "   - Web UI (internal): http://localhost:8080"
echo ""
echo "📚 API Documentation:"
echo "   - Swagger UI: http://localhost:8002/docs"
echo "   - ReDoc: http://localhost:8002/redoc"
echo ""
echo "🔧 Management commands:"
echo "   - View Caddy logs: docker-compose logs -f caddy"
echo "   - Stop Caddy: docker-compose down"
echo "   - Restart Caddy: docker-compose restart"
echo ""
echo "⚠️  Note: For localhost, you'll see a browser warning about self-signed certificates."
echo "   This is normal for development. Click 'Advanced' and 'Proceed' to continue."
echo ""
echo "💡 Remember: Keep your services running:"
echo "   - Web UI on port 8080"
echo "   - FastAPI server on port 8002"
echo ""
echo "🌍 Cross-platform compatibility:"
echo "   - macOS: ✅ Supported"
echo "   - Windows: ✅ Supported (use start-ssl.bat for Windows CMD)"
echo "   - Linux: ✅ Supported"
echo ""
echo "🔄 Environment switching:"
echo "   - Development (self-signed): ./switch-to-dev.sh"
echo "   - Production (Let's Encrypt): ./switch-to-prod.sh"
