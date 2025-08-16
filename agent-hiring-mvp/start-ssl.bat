@echo off
REM AgentHub SSL Server Startup Script for Windows
echo 🚀 Starting AgentHub SSL with Caddy reverse proxy...

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ docker-compose not found. Please install docker-compose first.
    pause
    exit /b 1
)

REM Check if your web UI is running
curl -s http://localhost:8080 >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Warning: Your web UI doesn't seem to be running on port 8080
    echo    Please start your web UI first on port 8080
    echo.
    echo    Or in another terminal:
    echo    cd ai-agent-marketplace-core ^&^& npm run dev
    echo.
    set /p dummy="Press Enter when your web UI is running on port 8080, or Ctrl+C to cancel..."
)

REM Check if your FastAPI server is running
curl -s http://localhost:8002/health >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Warning: Your FastAPI server doesn't seem to be running on port 8002
    echo    Please start your FastAPI server first:
    echo    cd server ^&^& python -m server.main --host 0.0.0.0 --port 8002
    echo.
    echo    Or in another terminal:
    echo    cd server ^&^& python -m server.main --host 0.0.0.0 --port 8002
    echo.
    set /p dummy="Press Enter when your FastAPI server is running on port 8002, or Ctrl+C to cancel..."
)

REM Start Caddy only
echo 🔨 Starting Caddy reverse proxy...
docker-compose up -d

REM Wait for Caddy to be ready
echo ⏳ Waiting for Caddy to be ready...
timeout /t 5 /nobreak >nul

REM Check service status
echo 📊 Caddy status:
docker-compose ps

echo.
echo ✅ Caddy is now running with SSL!
echo.
echo 🌐 Access your services:
echo    - Web UI (HTTPS): https://localhost
echo    - HTTP (redirects to HTTPS): http://localhost
echo    - FastAPI Server (internal): http://localhost:8002
echo    - Web UI (internal): http://localhost:8080
echo.
echo 📚 API Documentation:
echo    - Swagger UI: http://localhost:8002/docs
echo    - ReDoc: http://localhost:8002/redoc
echo.
echo 🔧 Management commands:
echo    - View Caddy logs: docker-compose logs -f caddy
echo    - Stop Caddy: docker-compose down
echo    - Restart Caddy: docker-compose restart
echo.
echo ⚠️  Note: For localhost, you'll see a browser warning about self-signed certificates.
echo    This is normal for development. Click 'Advanced' and 'Proceed' to continue.
echo.
echo 💡 Remember: Keep your services running:
echo    - Web UI on port 8080
echo    - FastAPI server on port 8002
echo.
echo 🔄 Environment switching:
echo    - Development (self-signed): switch-to-dev.bat
echo    - Production (Let's Encrypt): switch-to-prod.bat
echo.
pause
