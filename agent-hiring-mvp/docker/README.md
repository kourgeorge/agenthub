# AgentHub Docker Configuration

This directory contains all Docker-related configuration files for the AgentHub project, organized following Docker best practices.

## Directory Structure

```
docker/
├── compose/                          # Docker Compose files
│   ├── docker-compose.yml           # Main application services
│   ├── docker-compose.litellm.yml   # LiteLLM proxy services
│   ├── docker-compose.monitoring.yml # Monitoring services (Prometheus)
│   └── docker-compose.override.yml  # Local development overrides
├── configs/                         # Configuration files
│   ├── litellm/
│   │   └── litellm_config.yaml      # LiteLLM model configuration
│   ├── prometheus/
│   │   └── prometheus.yml           # Prometheus monitoring configuration
│   └── caddy/
│       ├── Caddyfile                # Production Caddy configuration
│       ├── Caddyfile.dev            # Development Caddy configuration
│       └── Caddyfile.production     # Production Caddy configuration
├── scripts/                         # Cross-platform convenience scripts
│   ├── docker                       # Universal launcher (auto-detects platform)
│   ├── docker.py                    # Python script (cross-platform)
│   ├── docker.sh                    # Unix shell script (Linux/macOS)
│   ├── docker.bat                   # Windows batch script
│   ├── docker.ps1                   # Windows PowerShell script
│   ├── start.sh                     # Legacy start script
│   ├── stop.sh                      # Legacy stop script
│   ├── status.sh                    # Legacy status script
│   ├── logs.sh                      # Legacy logs script
│   └── cleanup.sh                   # Legacy cleanup script
├── Dockerfile                       # Main application Dockerfile
└── README.md                        # This file
```

## Quick Start

### Cross-Platform Scripts

The Docker management scripts work on Windows, Linux, and macOS:

#### Using Universal Launcher (Recommended)
```bash
# All platforms - automatically detects platform and uses appropriate script
./docker/scripts/docker start
./docker/scripts/docker start caddy
./docker/scripts/docker status
./docker/scripts/docker logs -f litellm
./docker/scripts/docker stop
./docker/scripts/docker cleanup
```

#### Using Python (Cross-platform)
```bash
# All platforms
python docker/scripts/docker.py start
python docker/scripts/docker.py start caddy
python docker/scripts/docker.py status
python docker/scripts/docker.py logs -f litellm
python docker/scripts/docker.py stop
python docker/scripts/docker.py cleanup
```

#### Using Platform-Specific Scripts

**Linux/macOS:**
```bash
./docker/scripts/docker.sh start
./docker/scripts/docker.sh start caddy
./docker/scripts/docker.sh status
./docker/scripts/docker.sh logs -f litellm
./docker/scripts/docker.sh stop
./docker/scripts/docker.sh cleanup
```

**Windows (Command Prompt):**
```cmd
docker\scripts\docker.bat start
docker\scripts\docker.bat start caddy
docker\scripts\docker.bat status
docker\scripts\docker.bat logs -f litellm
docker\scripts\docker.bat stop
docker\scripts\docker.bat cleanup
```

**Windows (PowerShell):**
```powershell
.\docker\scripts\docker.ps1 start
.\docker\scripts\docker.ps1 start caddy
.\docker\scripts\docker.ps1 status
.\docker\scripts\docker.ps1 logs -Follow litellm
.\docker\scripts\docker.ps1 stop
.\docker\scripts\docker.ps1 cleanup
```

## Service Overview

### Main Application (`docker-compose.yml`)
- **Caddy**: Reverse proxy with automatic SSL
- **Ports**: 80 (HTTP), 443 (HTTPS)

### LiteLLM Proxy (`docker-compose.litellm.yml`)
- **LiteLLM**: AI model proxy service
- **PostgreSQL**: Database for LiteLLM
- **Prometheus**: Metrics collection
- **Ports**: 4000 (LiteLLM), 5432 (PostgreSQL), 9090 (Prometheus)

### Monitoring (`docker-compose.monitoring.yml`)
- **Prometheus**: Metrics collection and storage
- **cAdvisor**: Container metrics
- **Ports**: 9091 (Prometheus), 8082 (cAdvisor)

## Configuration

### Environment Variables
Create a `.env` file in the project root with your configuration:

```bash
# Database
DATABASE_URL=postgresql://llmproxy:dbpassword9090@db:5432/litellm

# Azure OpenAI (for LiteLLM)
AZURE_API_BASE=your_azure_endpoint
AZURE_API_KEY=your_azure_key

# Other configurations...
```

### LiteLLM Configuration
Edit `docker/configs/litellm/litellm_config.yaml` to configure your AI models:

```yaml
model_list:
  - model_name: azure-gpt-4o-mini
    litellm_params:
      model: azure/gpt-4o-mini-2024-07-18
      api_base: os.environ/AZURE_API_BASE
      api_key: os.environ/AZURE_API_KEY
      api_version: "2024-08-01-preview"
```

### Caddy Configuration
- **Development**: `docker/configs/caddy/Caddyfile.dev`
- **Production**: `docker/configs/caddy/Caddyfile.production`

## Development vs Production

### Development
- Uses `docker-compose.override.yml` for local development settings
- Different ports to avoid conflicts
- Development-specific configurations

### Production
- Uses production configurations
- SSL certificates
- Optimized settings

## Best Practices

1. **Configuration Management**: All configs are in `docker/configs/`
2. **Environment Separation**: Use different compose files for different environments
3. **Volume Management**: Persistent data is stored in Docker volumes
4. **Health Checks**: Services include health checks for reliability
5. **Resource Limits**: Set appropriate resource limits for production
6. **Security**: Use secrets management for sensitive data

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Check if ports are already in use
2. **Permission Issues**: Ensure scripts are executable (`chmod +x`)
3. **Configuration Errors**: Check YAML syntax in config files
4. **Volume Issues**: Use `docker/scripts/cleanup.sh --force` to reset

### Useful Commands

```bash
# Check Docker status
docker ps -a

# View all containers
docker-compose -f docker/compose/docker-compose.yml ps

# Rebuild services
docker-compose -f docker/compose/docker-compose.yml build --no-cache

# View resource usage
docker stats
```

## Contributing

When adding new services or configurations:

1. Add new compose files to `docker/compose/`
2. Add configurations to appropriate `docker/configs/` subdirectory
3. Update scripts if needed
4. Update this README
5. Test with both development and production configurations
