# Manual Server Setup Guide

This guide provides step-by-step instructions for setting up and running the Agent Hiring System server manually.

## Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- Git (for cloning the repository)

## Step 1: Clone and Navigate to Project

```bash
git clone <repository-url>
cd agent-hiring-mvp
```

## Step 2: Create Virtual Environment

### Option A: Using venv (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Option B: Using conda
```bash
conda create -n agenthubserver python=3.9
conda activate agenthubserver
```

## Step 3: Install Server Dependencies

### Install Core Dependencies
```bash
pip install -r requirements.txt
```

### Alternative: Install Minimal Dependencies
If you only need basic functionality:
```bash
pip install -r requirements_minimal.txt
```

## Step 4: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=sqlite:///./agent_hiring.db

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true

# Security (optional)
SECRET_KEY=your-secret-key-here
```

## Step 5: Initialize Database

```bash
python -c "from server.database.init_db import init_database; init_database()"
```

This will:
- Create the SQLite database file
- Create all tables
- Insert sample data (agents, users, etc.)

## Step 6: Start the Server

### Development Mode (with auto-reload)
```bash
python -m server.main --dev --port 8002 --reload
```

### Production Mode
```bash
python -m server.main --port 8000
```

### Using uvicorn directly
```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

## Step 7: Verify Server Installation

1. **Check server is running:**
   ```bash
   curl http://localhost:8002/health
   ```

2. **Access API documentation:**
   - Swagger UI: http://localhost:8002/docs
   - ReDoc: http://localhost:8002/redoc

3. **Test basic endpoints:**
   ```bash
   # List agents
   curl http://localhost:8002/api/v1/agents
   
   # Health check
   curl http://localhost:8002/health
   ```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
If you get "Address already in use" error:
```bash
# Find process using the port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
python -m server.main --port 8002
```

#### 2. Database Errors
If you get database-related errors:
```bash
# Remove existing database
rm agent_hiring.db

# Reinitialize database
python -c "from server.database.init_db import init_database; init_database()"
```

#### 3. Import Errors
If you get "ModuleNotFoundError":
```bash
# Make sure you're in the correct directory
pwd  # Should show /path/to/agent-hiring-mvp

# Reinstall dependencies
pip install -r requirements.txt
```

#### 4. Permission Errors (macOS/Linux)
If you get permission errors:
```bash
# Make sure you have write permissions
chmod 755 .

# Or run with sudo (not recommended for development)
sudo python -m server.main --port 8000
```

### Corporate Network Issues

If you're behind a corporate firewall:

1. **Configure pip to use corporate proxy:**
   ```bash
   pip install --proxy http://proxy.company.com:8080 -r requirements.txt
   ```

2. **Use alternative package sources:**
   ```bash
   pip install -i https://pypi.org/simple/ -r requirements.txt
   ```

3. **Install packages individually if needed:**
   ```bash
   pip install fastapi uvicorn pydantic sqlalchemy python-dotenv
   ```

## Development Workflow

### Running Server Tests
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
pytest --cov=server
```

### Code Formatting
```bash
# Format code
black server/ tests/

# Sort imports
isort server/ tests/

# Lint code
flake8 server/ tests/
```

### Database Management
```bash
# View database (if using SQLite)
sqlite3 agent_hiring.db

# Reset database
rm agent_hiring.db
python -c "from server.database.init_db import init_database; init_database()"
```

## Server API Endpoints

Once the server is running, you can access:

- **Health Check:** `GET /health`
- **API Documentation:** `GET /docs` (Swagger UI)
- **Agents:** `GET /api/v1/agents`
- **Hiring:** `POST /api/v1/hiring`
- **Execution:** `POST /api/v1/execution`
- **ACP Protocol:** `POST /api/v1/acp`

## Next Steps

After successful server setup:

1. **Explore the API:** Visit http://localhost:8002/docs
2. **Run the demo:** Execute `python tests/e2e/demo_workflow.py`
3. **Test agent execution:** Use the provided test scripts
4. **Read the documentation:** Check `documentation/` folder

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the server logs for error messages
3. Check the API documentation at `/docs`
4. Review the test files for usage examples


