# Cross-platform Docker management script for AgentHub (PowerShell)
# Usage: .\docker\scripts\docker.ps1 [command] [options]

param(
    [Parameter(Position=0)]
    [string]$Command,
    
    [Parameter(Position=1)]
    [string]$Service,
    
    [switch]$Follow,
    [switch]$Force,
    [switch]$Help
)

# Colors for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    White = "White"
}

function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

function Write-Header {
    param([string]$Message)
    Write-Host "[AGENTHUB DOCKER] $Message" -ForegroundColor $Colors.Blue
}

function Show-Help {
    Write-Host "AgentHub Docker Management Script" -ForegroundColor $Colors.White
    Write-Host ""
    Write-Host "Usage: .\docker\scripts\docker.ps1 [command] [options]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  start [service]     Start services (or specific service)"
    Write-Host "  stop [service]      Stop services (or specific service)"
    Write-Host "  restart [service]   Restart services (or specific service)"
    Write-Host "  status              Show service status"
    Write-Host "  logs [service]      Show logs (or specific service)"
    Write-Host "  logs -Follow [service]   Follow logs in real-time"
    Write-Host "  cleanup             Clean up Docker resources"
    Write-Host "  build               Build Docker images"
    Write-Host "  help                Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\docker\scripts\docker.ps1 start                    # Start all services"
    Write-Host "  .\docker\scripts\docker.ps1 start caddy             # Start only Caddy"
    Write-Host "  .\docker\scripts\docker.ps1 logs -Follow litellm    # Follow LiteLLM logs"
    Write-Host "  .\docker\scripts\docker.ps1 status                  # Check service status"
    Write-Host "  .\docker\scripts\docker.ps1 cleanup                 # Clean up resources"
    Write-Host ""
    Write-Host "Services:"
    Write-Host "  caddy              Reverse proxy with SSL"
    Write-Host "  litellm            AI model proxy"
    Write-Host "  prometheus         Metrics collection"
}

function Get-ProjectRoot {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    return Split-Path -Parent (Split-Path -Parent $ScriptDir)
}

function Get-ComposeCommand {
    $ProjectRoot = Get-ProjectRoot
    $ComposeDir = Join-Path $ProjectRoot "docker\compose"
    return "docker-compose -f $ComposeDir\docker-compose.yml -f $ComposeDir\docker-compose.override.yml"
}

function Test-Docker {
    try {
        $null = Get-Command docker -ErrorAction Stop
        return $true
    }
    catch {
        Write-Error "Docker is not installed or not in PATH"
        return $false
    }
}

function Test-DockerCompose {
    try {
        $null = Get-Command docker-compose -ErrorAction Stop
        return $true
    }
    catch {
        Write-Error "docker-compose is not installed or not in PATH"
        return $false
    }
}

function Start-Services {
    param([string]$Service)
    
    if (-not (Test-Docker) -or -not (Test-DockerCompose)) {
        return $false
    }
    
    $ComposeCmd = Get-ComposeCommand
    
    if ($Service) {
        Write-Status "Starting $Service service..."
        $Cmd = "$ComposeCmd up -d $Service"
    } else {
        Write-Status "Starting all services..."
        $Cmd = "$ComposeCmd up -d"
    }
    
    Invoke-Expression $Cmd
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Services started successfully!"
        Write-Status "Use '.\docker\scripts\docker.ps1 status' to check service status"
        return $true
    }
    return $false
}

function Stop-Services {
    param([string]$Service)
    
    if (-not (Test-Docker) -or -not (Test-DockerCompose)) {
        return $false
    }
    
    $ComposeCmd = Get-ComposeCommand
    
    if ($Service) {
        Write-Status "Stopping $Service service..."
        $Cmd = "$ComposeCmd stop $Service"
    } else {
        Write-Status "Stopping all services..."
        $Cmd = "$ComposeCmd down"
    }
    
    Invoke-Expression $Cmd
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Services stopped successfully!"
        return $true
    }
    return $false
}

function Restart-Services {
    param([string]$Service)
    
    Write-Status "Restarting services..."
    Stop-Services $Service
    Start-Sleep -Seconds 2
    return Start-Services $Service
}

function Show-Status {
    if (-not (Test-Docker) -or -not (Test-DockerCompose)) {
        return $false
    }
    
    $ComposeCmd = Get-ComposeCommand
    
    Write-Header "Docker Services Status"
    Write-Host ""
    
    # Show service status
    Invoke-Expression "$ComposeCmd ps"
    
    Write-Host ""
    Write-Header "Service URLs"
    Write-Host "Caddy (Reverse Proxy): http://localhost:8080"
    Write-Host "LiteLLM (if running):  http://localhost:4000"
    Write-Host "Prometheus (if running): http://localhost:9091"
    
    Write-Host ""
    Write-Header "Useful Commands"
    Write-Host "View logs:     .\docker\scripts\docker.ps1 logs [service]"
    Write-Host "Restart:       .\docker\scripts\docker.ps1 restart [service]"
    Write-Host "Clean up:      .\docker\scripts\docker.ps1 cleanup"
    
    return $true
}

function Show-Logs {
    param([string]$Service, [bool]$Follow)
    
    if (-not (Test-Docker) -or -not (Test-DockerCompose)) {
        return $false
    }
    
    $ComposeCmd = Get-ComposeCommand
    
    if ($Follow) {
        if ($Service) {
            Write-Status "Following logs for $Service service (Ctrl+C to stop)..."
            $Cmd = "$ComposeCmd logs -f $Service"
        } else {
            Write-Status "Following logs for all services (Ctrl+C to stop)..."
            $Cmd = "$ComposeCmd logs -f"
        }
        
        Invoke-Expression $Cmd
    } else {
        if ($Service) {
            Write-Status "Showing logs for $Service service..."
            $Cmd = "$ComposeCmd logs $Service"
        } else {
            Write-Status "Showing logs for all services..."
            $Cmd = "$ComposeCmd logs"
        }
        
        Invoke-Expression $Cmd
    }
    
    return $true
}

function Invoke-Cleanup {
    param([bool]$Force)
    
    Write-Warning "This will clean up Docker resources for AgentHub"
    Write-Warning "This includes:"
    Write-Host "  - Stopping all services"
    Write-Host "  - Removing containers"
    Write-Host "  - Removing networks"
    Write-Host "  - Removing volumes (if -Force is used)"
    Write-Host ""
    
    if (-not $Force) {
        $Confirm = Read-Host "Are you sure you want to continue? (y/N)"
        if ($Confirm -notmatch '^[yY]') {
            Write-Status "Cleanup cancelled"
            return $true
        }
    }
    
    if (-not (Test-Docker) -or -not (Test-DockerCompose)) {
        return $false
    }
    
    $ComposeCmd = Get-ComposeCommand
    
    Write-Status "Stopping all services..."
    Invoke-Expression "$ComposeCmd down"
    
    if ($Force) {
        Write-Status "Removing volumes..."
        Invoke-Expression "$ComposeCmd down -v"
    }
    
    Write-Status "Cleaning up unused Docker resources..."
    Invoke-Expression "docker system prune -f"
    
    Write-Status "Cleanup completed successfully!"
    return $true
}

function Build-Images {
    if (-not (Test-Docker) -or -not (Test-DockerCompose)) {
        return $false
    }
    
    $ComposeCmd = Get-ComposeCommand
    
    Write-Status "Building Docker images..."
    Invoke-Expression "$ComposeCmd build"
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Build completed!"
        return $true
    }
    return $false
}

# Main execution
if ($Help -or -not $Command) {
    Show-Help
    exit 0
}

# Change to project root
$ProjectRoot = Get-ProjectRoot
Set-Location $ProjectRoot

Write-Header "AgentHub Docker Management"
Write-Host ""

switch ($Command.ToLower()) {
    "start" {
        $Success = Start-Services $Service
    }
    "stop" {
        $Success = Stop-Services $Service
    }
    "restart" {
        $Success = Restart-Services $Service
    }
    "status" {
        $Success = Show-Status
    }
    "logs" {
        $Success = Show-Logs $Service $Follow
    }
    "cleanup" {
        $Success = Invoke-Cleanup $Force
    }
    "build" {
        $Success = Build-Images
    }
    default {
        Write-Error "Unknown command: $Command"
        Show-Help
        exit 1
    }
}

if (-not $Success) {
    exit 1
}
