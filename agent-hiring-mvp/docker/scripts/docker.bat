@echo off
REM Main Docker management script for AgentHub (Windows)
REM Usage: docker\scripts\docker.bat [command] [options]

setlocal enabledelayedexpansion

REM Get the directory of this script
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."

REM Change to project root
cd /d "%PROJECT_ROOT%"

REM Function to show help
:show_help
echo AgentHub Docker Management Script
echo.
echo Usage: %~nx0 [command] [options]
echo.
echo Commands:
echo   start [service]     Start services (or specific service)
echo   stop [service]      Stop services (or specific service)
echo   restart [service]   Restart services (or specific service)
echo   status              Show service status
echo   logs [service]      Show logs (or specific service)
echo   logs -f [service]   Follow logs in real-time
echo   cleanup             Clean up Docker resources
echo   build               Build Docker images
echo   help                Show this help message
echo.
echo Examples:
echo   %~nx0 start                    # Start all services
echo   %~nx0 start caddy             # Start only Caddy
echo   %~nx0 logs -f litellm         # Follow LiteLLM logs
echo   %~nx0 status                  # Check service status
echo   %~nx0 cleanup                 # Clean up resources
echo.
echo Services:
echo   caddy              Reverse proxy with SSL
echo   litellm            AI model proxy
echo   prometheus         Metrics collection
goto :eof

REM Function to start services
:start_services
set "service=%1"
if "%service%"=="" (
    echo [INFO] Starting all services...
    docker-compose -f docker\compose\docker-compose.yml -f docker\compose\docker-compose.override.yml up -d
) else (
    echo [INFO] Starting %service% service...
    docker-compose -f docker\compose\docker-compose.yml -f docker\compose\docker-compose.override.yml up -d %service%
)
echo [INFO] Services started successfully!
echo [INFO] Use 'docker\scripts\docker.bat status' to check service status
goto :eof

REM Function to stop services
:stop_services
set "service=%1"
if "%service%"=="" (
    echo [INFO] Stopping all services...
    docker-compose -f docker\compose\docker-compose.yml -f docker\compose\docker-compose.override.yml down
) else (
    echo [INFO] Stopping %service% service...
    docker-compose -f docker\compose\docker-compose.yml -f docker\compose\docker-compose.override.yml stop %service%
)
echo [INFO] Services stopped successfully!
goto :eof

REM Function to show status
:show_status
echo [STATUS] Docker Services Status
echo.
docker-compose -f docker\compose\docker-compose.yml -f docker\compose\docker-compose.override.yml ps
echo.
echo [STATUS] Service URLs
echo Caddy (Reverse Proxy): http://localhost:8080
echo LiteLLM (if running):  http://localhost:4000
echo Prometheus (if running): http://localhost:9091
echo.
echo [STATUS] Useful Commands
echo View logs:     docker\scripts\docker.bat logs [service]
echo Restart:       docker\scripts\docker.bat restart [service]
echo Clean up:      docker\scripts\docker.bat cleanup
goto :eof

REM Function to show logs
:show_logs
set "service=%1"
set "follow=%2"
if "%follow%"=="-f" (
    if "%service%"=="" (
        echo [INFO] Following logs for all services (Ctrl+C to stop)...
        docker-compose -f docker\compose\docker-compose.yml -f docker\compose\docker-compose.override.yml logs -f
    ) else (
        echo [INFO] Following logs for %service% service (Ctrl+C to stop)...
        docker-compose -f docker\compose\docker-compose.yml -f docker\compose\docker-compose.override.yml logs -f %service%
    )
) else (
    if "%service%"=="" (
        echo [INFO] Showing logs for all services...
        docker-compose -f docker\compose\docker-compose.yml -f docker\compose\docker-compose.override.yml logs
    ) else (
        echo [INFO] Showing logs for %service% service...
        docker-compose -f docker\compose\docker-compose.yml -f docker\compose\docker-compose.override.yml logs %service%
    )
)
goto :eof

REM Function to cleanup
:cleanup
echo [WARNING] This will clean up Docker resources for AgentHub
echo [WARNING] This includes:
echo   - Stopping all services
echo   - Removing containers
echo   - Removing networks
echo   - Removing volumes (if --force is used)
echo.
set /p confirm="Are you sure you want to continue? (y/N): "
if /i not "%confirm%"=="y" (
    echo [INFO] Cleanup cancelled
    goto :eof
)
echo [INFO] Stopping all services...
docker-compose -f docker\compose\docker-compose.yml -f docker\compose\docker-compose.override.yml down
echo [INFO] Cleaning up unused Docker resources...
docker system prune -f
echo [INFO] Cleanup completed successfully!
goto :eof

REM Function to build
:build
echo [INFO] Building Docker images...
docker-compose -f docker\compose\docker-compose.yml build
echo [INFO] Build completed!
goto :eof

REM Main execution
if "%1"=="" goto show_help
if "%1"=="help" goto show_help
if "%1"=="--help" goto show_help
if "%1"=="-h" goto show_help

echo [AGENTHUB DOCKER] AgentHub Docker Management
echo.

if "%1"=="start" (
    call :start_services %2
) else if "%1"=="stop" (
    call :stop_services %2
) else if "%1"=="restart" (
    call :stop_services %2
    timeout /t 2 /nobreak >nul
    call :start_services %2
) else if "%1"=="status" (
    call :show_status
) else if "%1"=="logs" (
    call :show_logs %2 %3
) else if "%1"=="cleanup" (
    call :cleanup
) else if "%1"=="build" (
    call :build
) else (
    echo [ERROR] Unknown command: %1
    echo.
    call :show_help
    exit /b 1
)
