# Integration Tests

This directory contains integration tests that test the interaction between different components of the system.

## Test Files

### `test_agent_submission.py`
**Purpose**: Tests the complete agent submission workflow
**What it tests**:
- Server health check
- Agent code creation and packaging
- Agent submission via API
- Agent listing and retrieval
- Agent execution
- Agent approval process

**Features**:
- Creates a real test agent with multiple files
- Packages agent code into ZIP file
- Submits agent via REST API
- Tests full execution workflow
- Comprehensive error handling and reporting

### `test_runtime_directly.py`
**Purpose**: Tests the agent runtime service directly
**What it tests**:
- Direct agent execution without API
- Security violation detection
- Timeout handling
- Different agent types (echo, calculator, text processor)

### `debug_execution.py`
**Purpose**: Debug execution issues
**What it tests**:
- Execution status checking
- Debug information retrieval

## Running the Tests

### Prerequisites
1. Server must be running (`python server/main.py`)
2. Database must be initialized
3. Required dependencies installed

### Method 1: Using the Test Runner Script
```bash
# From the project root
python run_agent_submission_test.py
```

### Method 2: Direct Test Execution
```bash
# From the project root
python tests/integration/test_agent_submission.py

# With custom server URL
python tests/integration/test_agent_submission.py http://localhost:8002
```

### Method 3: Runtime Tests
```bash
# Test runtime directly
python tests/integration/test_runtime_directly.py

# Debug executions
python tests/integration/debug_execution.py
```

## Test Output

The agent submission test provides detailed output including:

- ✅ **Step-by-step progress** with clear indicators
- 📋 **API responses** with status codes and data
- 🧪 **Test results** with pass/fail status
- 🎉 **Final summary** of all tests

## Example Output
```
============================================================
 AGENT SUBMISSION INTEGRATION TEST
============================================================
Testing the complete agent submission workflow...

📋 STEP 1: SERVER HEALTH CHECK
--------------------------------------------------
✅ Server is running and healthy

📋 STEP 2: AGENT SUBMISSION
--------------------------------------------------
Submitting agent to server...

Agent Submission:
Status: 200
Response: {
  "message": "Agent submitted successfully",
  "agent_id": 4,
  "status": "submitted"
}
✅ Agent submitted successfully with ID: 4

...

🎉 All tests passed! Agent submission workflow is working correctly.
```

## Troubleshooting

### Server Not Running
```
❌ Cannot connect to server. Is it running?
```
**Solution**: Start the server with `python server/main.py`

### Database Issues
```
❌ Database connection failed
```
**Solution**: Initialize the database with `python server/database/init_db.py`

### Port Already in Use
```
❌ Server health check failed: 500
```
**Solution**: Check if another process is using port 8000, or use a different port

### Test Agent Not Found
```
❌ Our submitted agent not found in listing
```
**Solution**: Check if the agent submission was successful and the database is properly updated

## Adding New Tests

To add new integration tests:

1. Create a new test file in this directory
2. Follow the naming convention: `test_*.py`
3. Include proper error handling and logging
4. Add documentation to this README
5. Ensure tests are independent and can run in any order

## Test Data Cleanup

The tests create temporary data that may remain in the database:
- Test agents (marked with "Integration Test" author)
- Test executions
- Temporary files

In production, you would want to add cleanup functionality to remove test data after tests complete. 