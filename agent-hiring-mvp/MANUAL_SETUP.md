# 🔧 Manual Setup Guide

If the automated setup fails due to corporate proxy or dependency issues, follow this manual setup guide.

## 🚨 Quick Fix for Corporate Proxy Issues

### Option 1: Use Minimal Requirements
```bash
# Remove existing venv (if any)
rm -rf venv

# Create new virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Unix/Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install minimal requirements only
pip install -r requirements_minimal.txt --index-url https://pypi.org/simple/ --trusted-host pypi.org
```

### Option 2: Bypass Corporate Proxy
```bash
# Set pip to use only public PyPI
pip install --upgrade pip --index-url https://pypi.org/simple/ --trusted-host pypi.org

# Install requirements with public PyPI only
pip install -r requirements.txt --index-url https://pypi.org/simple/ --trusted-host pypi.org
```

### Option 3: Install Dependencies One by One
```bash
# Core dependencies only
pip install fastapi uvicorn pydantic sqlalchemy --index-url https://pypi.org/simple/

# Additional dependencies as needed
pip install python-dotenv pyyaml requests aiohttp --index-url https://pypi.org/simple/
```

## 🔧 Complete Manual Setup

### Step 1: Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Unix/Linux/macOS
# or
venv\Scripts\activate     # Windows
```

### Step 2: Install Dependencies
```bash
# Upgrade pip
pip install --upgrade pip --index-url https://pypi.org/simple/

# Install minimal requirements
pip install -r requirements_minimal.txt --index-url https://pypi.org/simple/
```

### Step 3: Create Configuration
```bash
# Create .env file
cat > .env << 'EOF'
# Database Configuration
DB_DATABASE_URL=sqlite:///./agent_hiring.db
DB_ECHO=false
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_PRE_PING=true

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Agent Runtime
AGENT_TIMEOUT_SECONDS=300
AGENT_MEMORY_LIMIT_MB=512
AGENT_CPU_LIMIT_PERCENT=50

# File Storage
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=10

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
EOF
```

### Step 4: Create Directories
```bash
# Create necessary directories
mkdir -p uploads logs temp web-ui/public
```

### Step 5: Initialize Database
```bash
# Initialize database
python -m server.database.init_db
```

### Step 6: Start Server
```bash
# Start the server
python -m server.main --dev
```

## 🧪 Test the Setup

### Test Basic Functionality
```bash
# Test database models
python -c "
from server.models.agent import Agent
from server.models.hiring import Hiring
print('Database models imported successfully')
"

# Test server startup
python -c "
from server.main import app
print('FastAPI app created successfully')
"
```

### Test API Endpoints
```bash
# Health check (if server is running)
curl http://localhost:8000/health

# List agents
curl http://localhost:8000/api/agents
```

## 🚨 Troubleshooting

### Corporate Proxy Issues
```bash
# Disable pip proxy
pip install --no-proxy=* -r requirements_minimal.txt

# Use different index
pip install -r requirements_minimal.txt --index-url https://pypi.org/simple/ --trusted-host pypi.org

# Install without dependencies
pip install --no-deps -r requirements_minimal.txt
```

### Permission Issues
```bash
# Install with user flag
pip install --user -r requirements_minimal.txt

# Fix permissions
chmod +x start_server.sh
```

### Database Issues
```bash
# Remove existing database
rm -f agent_hiring.db

# Reinitialize database
python -m server.database.init_db
```

### Import Errors
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Install missing packages
pip install fastapi uvicorn pydantic sqlalchemy
```

## ✅ Verification Checklist

- [ ] Virtual environment created and activated
- [ ] Dependencies installed successfully
- [ ] `.env` file created
- [ ] Directories created (uploads, logs, temp)
- [ ] Database initialized
- [ ] Server starts without errors
- [ ] API endpoints respond
- [ ] Health check returns 200 OK

## 🎯 Next Steps After Setup

1. **Start the server**: `python -m server.main --dev`
2. **Open API docs**: http://localhost:8000/docs
3. **Test endpoints**: Use the interactive documentation
4. **Create agents**: Use the Creator SDK examples
5. **Run tests**: `python test_system.py`

## 📞 Getting Help

If you're still having issues:

1. **Check Python version**: `python --version` (should be 3.9+)
2. **Check pip version**: `pip --version`
3. **Check virtual environment**: `which python` (should point to venv)
4. **Check network**: `curl https://pypi.org/simple/`
5. **Review error messages**: Look for specific package failures

---

**Remember**: The minimal setup includes only essential dependencies. Additional features can be added as needed. 