#!/usr/bin/env python3
"""
AgentHub CLI - Command-line interface for agent creators.
Provides tools for creating, validating, testing, and publishing agents.
"""

import asyncio
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, List

import click
from click import echo, style

try:
    # Try relative imports first (when installed as package)
    from .agent import Agent, AgentConfig, SimpleAgent, DataProcessingAgent, ChatAgent
    from .client import AgentHubClient
except ImportError:
    # Fall back to absolute imports (when run as script)
    sys.path.insert(0, str(Path(__file__).parent))
    from agent import Agent, AgentConfig, SimpleAgent, DataProcessingAgent, ChatAgent
    from client import AgentHubClient


class CLIConfig:
    """Configuration for the CLI."""
    
    def __init__(self):
        self.config_file = Path.home() / ".agenthub" / "config.json"
        self.config_file.parent.mkdir(exist_ok=True)
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load CLI configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "base_url": "http://localhost:8002",
            "api_key": None,
            "default_author": "",
            "default_email": "",
        }
    
    def save_config(self) -> None:
        """Save CLI configuration."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set config value."""
        self.config[key] = value
        self.save_config()


# Global CLI configuration
cli_config = CLIConfig()


@click.group()
@click.version_option(version="1.0.0")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """AgentHub CLI - Tools for creating and publishing AI agents."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    if verbose:
        echo(style("AgentHub CLI v1.0.0", fg='green', bold=True))


@cli.group()
def agent():
    """Agent creation and management commands."""
    pass


@agent.command()
@click.argument('name')
@click.option('--type', '-t', 'agent_type', 
              type=click.Choice(['simple', 'data', 'chat']), 
              default='simple', 
              help='Type of agent to create')
@click.option('--author', '-a', help='Agent author name')
@click.option('--email', '-e', help='Agent author email')
@click.option('--description', '-d', help='Agent description')
@click.option('--category', '-c', default='general', help='Agent category')
@click.option('--pricing', '-p', 
              type=click.Choice(['free', 'per_use', 'monthly']), 
              default='free', 
              help='Pricing model')
@click.option('--price', type=float, help='Price per use or monthly price')
@click.option('--tags', help='Comma-separated tags')
@click.option('--directory', '-dir', help='Target directory (default: current directory)')
@click.pass_context
def init(ctx, name, agent_type, author, email, description, category, pricing, price, tags, directory):
    """Initialize a new agent project."""
    verbose = ctx.obj.get('verbose', False)
    
    # Use defaults from config if not provided
    author = author or cli_config.get('default_author', '')
    email = email or cli_config.get('default_email', '')
    
    # Prompt for required fields if not provided
    if not author:
        author = click.prompt('Author name')
    if not email:
        email = click.prompt('Author email')
    if not description:
        description = click.prompt('Agent description')
    
    # Set target directory
    if directory:
        target_dir = Path(directory)
    else:
        target_dir = Path.cwd() / name.lower().replace(' ', '_').replace('-', '_')
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Create agent configuration
    config = AgentConfig(
        name=name,
        description=description,
        author=author,
        email=email,
        entry_point=f"{name.lower().replace(' ', '_').replace('-', '_')}.py",
        category=category,
        pricing_model=pricing,
        tags=tags.split(',') if tags else [],
    )
    
    if price is not None:
        if pricing == 'per_use':
            config.price_per_use = price
        elif pricing == 'monthly':
            config.monthly_price = price
    
    # Generate agent files
    try:
        _create_agent_files(target_dir, config, agent_type, verbose)
        echo(style(f"✓ Agent '{name}' initialized successfully!", fg='green'))
        echo(f"  Location: {target_dir}")
        echo(f"  Type: {agent_type}")
        echo(f"  Next steps:")
        echo(f"    1. cd {target_dir}")
        echo(f"    2. agenthub agent validate")
        echo(f"    3. agenthub agent test")
        echo(f"    4. agenthub agent publish")
    except Exception as e:
        echo(style(f"✗ Error creating agent: {e}", fg='red'))
        sys.exit(1)


@agent.command()
@click.option('--directory', '-dir', default='.', help='Agent directory to validate')
@click.pass_context
def validate(ctx, directory):
    """Validate agent configuration and code."""
    verbose = ctx.obj.get('verbose', False)
    
    agent_dir = Path(directory)
    config_file = agent_dir / "config.json"
    
    if not config_file.exists():
        echo(style("✗ No config.json found. Run 'agenthub agent init' first.", fg='red'))
        sys.exit(1)
    
    try:
        # Load and validate configuration
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        config = AgentConfig(**config_data)
        errors = config.validate()
        
        if errors:
            echo(style("✗ Configuration validation failed:", fg='red'))
            for error in errors:
                echo(f"  - {error}")
            sys.exit(1)
        
        # Check if main agent file exists
        entry_point = agent_dir / config.entry_point
        if not entry_point.exists():
            echo(style(f"✗ Entry point file not found: {config.entry_point}", fg='red'))
            sys.exit(1)
        
        # Check requirements.txt
        requirements_file = agent_dir / "requirements.txt"
        if not requirements_file.exists():
            echo(style("⚠ requirements.txt not found", fg='yellow'))
        
        echo(style("✓ Agent validation passed!", fg='green'))
        if verbose:
            echo(f"  Name: {config.name}")
            echo(f"  Version: {config.version}")
            echo(f"  Author: {config.author}")
            echo(f"  Entry point: {config.entry_point}")
            echo(f"  Category: {config.category}")
            echo(f"  Pricing: {config.pricing_model}")
            
    except Exception as e:
        echo(style(f"✗ Validation error: {e}", fg='red'))
        sys.exit(1)


@agent.command()
@click.option('--directory', '-dir', default='.', help='Agent directory to test')
@click.option('--input', '-i', help='JSON input data for testing')
@click.option('--config', '-c', help='JSON config data for testing')
@click.pass_context
def test(ctx, directory, input, config):
    """Test agent locally."""
    verbose = ctx.obj.get('verbose', False)
    
    agent_dir = Path(directory)
    config_file = agent_dir / "config.json"
    
    if not config_file.exists():
        echo(style("✗ No config.json found. Run 'agenthub agent init' first.", fg='red'))
        sys.exit(1)
    
    try:
        # Load configuration
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        agent_config = AgentConfig(**config_data)
        
        # Prepare test data
        test_input = {"message": "Hello, test!"} if input is None else json.loads(input)
        test_config = {} if config is None else json.loads(config)
        
        echo(style("Running agent test...", fg='blue'))
        if verbose:
            echo(f"Input: {json.dumps(test_input, indent=2)}")
            echo(f"Config: {json.dumps(test_config, indent=2)}")
        
        # Run the agent
        result = _run_agent_locally(agent_dir, agent_config, test_input, test_config)
        
        echo(style("✓ Agent test completed!", fg='green'))
        echo("Result:")
        echo(json.dumps(result, indent=2))
        
    except Exception as e:
        echo(style(f"✗ Test error: {e}", fg='red'))
        sys.exit(1)


@agent.command()
@click.option('--directory', '-dir', default='.', help='Agent directory to publish')
@click.option('--api-key', help='API key for authentication')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.option('--dry-run', is_flag=True, help='Validate without publishing')
@click.pass_context
def publish(ctx, directory, api_key, base_url, dry_run):
    """Publish agent to the AgentHub platform."""
    verbose = ctx.obj.get('verbose', False)
    
    agent_dir = Path(directory)
    config_file = agent_dir / "config.json"
    
    if not config_file.exists():
        echo(style("✗ No config.json found. Run 'agenthub agent init' first.", fg='red'))
        sys.exit(1)
    
    # Use config defaults if not provided
    api_key = api_key or cli_config.get('api_key')
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    if dry_run:
        echo(style("🔍 Dry run mode - validating only", fg='blue'))
    
    try:
        # Load and validate configuration
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        config = AgentConfig(**config_data)
        errors = config.validate()
        
        if errors:
            echo(style("✗ Configuration validation failed:", fg='red'))
            for error in errors:
                echo(f"  - {error}")
            sys.exit(1)
        
        if dry_run:
            echo(style("✓ Agent validation passed! Ready to publish.", fg='green'))
            return
        
        # Create temporary agent instance for publishing
        agent = _create_agent_instance(config)
        
        # Publish the agent
        echo(style("📤 Publishing agent...", fg='blue'))
        
        async def publish_agent():
            async with AgentHubClient(base_url) as client:
                result = await client.submit_agent(agent, str(agent_dir), api_key)
                return result
        
        result = asyncio.run(publish_agent())
        
        echo(style("✓ Agent published successfully!", fg='green'))
        echo(f"  Agent ID: {result.get('agent_id', 'Unknown')}")
        echo(f"  Status: {result.get('status', 'Unknown')}")
        
        if verbose:
            echo("Full response:")
            echo(json.dumps(result, indent=2))
            
    except Exception as e:
        echo(style(f"✗ Publish error: {e}", fg='red'))
        sys.exit(1)


@agent.command()
@click.option('--query', '-q', help='Search query')
@click.option('--category', '-c', help='Filter by category')
@click.option('--limit', '-l', default=10, help='Number of results to show')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def list(ctx, query, category, limit, base_url):
    """List available agents on the platform."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style("🔍 Fetching agents...", fg='blue'))
        
        async def list_agents():
            async with AgentHubClient(base_url) as client:
                result = await client.list_agents(
                    query=query,
                    category=category,
                    limit=limit
                )
                return result
        
        result = asyncio.run(list_agents())
        agents = result.get('agents', [])
        
        if not agents:
            echo(style("No agents found.", fg='yellow'))
            return
        
        echo(style(f"Found {len(agents)} agents:", fg='green'))
        echo()
        
        for agent in agents:
            echo(f"🤖 {style(agent['name'], fg='cyan', bold=True)} (ID: {agent['id']})")
            echo(f"   {agent['description']}")
            echo(f"   Author: {agent['author']} | Category: {agent['category']}")
            echo(f"   Pricing: {agent['pricing_model']}")
            if agent.get('tags'):
                echo(f"   Tags: {', '.join(agent['tags'])}")
            echo()
            
    except Exception as e:
        echo(style(f"✗ Error listing agents: {e}", fg='red'))
        sys.exit(1)


@agent.command()
@click.argument('agent_id', type=int)
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def info(ctx, agent_id, base_url):
    """Get detailed information about an agent."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style(f"🔍 Fetching agent {agent_id}...", fg='blue'))
        
        async def get_agent():
            async with AgentHubClient(base_url) as client:
                result = await client.get_agent(agent_id)
                return result
        
        agent = asyncio.run(get_agent())
        
        echo(style(f"🤖 {agent['name']}", fg='cyan', bold=True))
        echo(f"   ID: {agent['id']}")
        echo(f"   Description: {agent['description']}")
        echo(f"   Author: {agent['author']} <{agent['email']}>")
        echo(f"   Version: {agent['version']}")
        echo(f"   Category: {agent['category']}")
        echo(f"   Pricing: {agent['pricing_model']}")
        
        if agent.get('price_per_use'):
            echo(f"   Price per use: ${agent['price_per_use']}")
        if agent.get('monthly_price'):
            echo(f"   Monthly price: ${agent['monthly_price']}")
        
        if agent.get('tags'):
            echo(f"   Tags: {', '.join(agent['tags'])}")
        
        echo(f"   Entry point: {agent['entry_point']}")
        echo(f"   Max execution time: {agent['max_execution_time']}s")
        echo(f"   Memory limit: {agent['memory_limit']}")
        
        if agent.get('requirements'):
            echo(f"   Requirements: {', '.join(agent['requirements'])}")
        
        if verbose and agent.get('config_schema'):
            echo("\nConfiguration Schema:")
            echo(json.dumps(agent['config_schema'], indent=2))
            
    except Exception as e:
        echo(style(f"✗ Error getting agent info: {e}", fg='red'))
        sys.exit(1)


@agent.command()
@click.argument('template_type', type=click.Choice(['simple', 'data', 'chat']))
@click.argument('output_file')
@click.pass_context
def template(ctx, template_type, output_file):
    """Generate agent template code."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        template_code = _generate_template(template_type)
        
        with open(output_file, 'w') as f:
            f.write(template_code)
        
        echo(style(f"✓ Template generated: {output_file}", fg='green'))
        echo(f"  Type: {template_type}")
        
    except Exception as e:
        echo(style(f"✗ Error generating template: {e}", fg='red'))
        sys.exit(1)


@cli.command()
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.option('--api-key', help='API key for authentication')
@click.option('--author', help='Default author name')
@click.option('--email', help='Default email address')
@click.option('--show', is_flag=True, help='Show current configuration')
@click.pass_context
def config(ctx, base_url, api_key, author, email, show):
    """Configure CLI settings."""
    
    if show:
        echo(style("Current Configuration:", fg='cyan', bold=True))
        echo(f"  Base URL: {cli_config.get('base_url')}")
        echo(f"  API Key: {'***' if cli_config.get('api_key') else 'Not set'}")
        echo(f"  Default Author: {cli_config.get('default_author')}")
        echo(f"  Default Email: {cli_config.get('default_email')}")
        return
    
    if base_url:
        cli_config.set('base_url', base_url)
        echo(style(f"✓ Base URL set to: {base_url}", fg='green'))
    
    if api_key:
        cli_config.set('api_key', api_key)
        echo(style("✓ API key updated", fg='green'))
    
    if author:
        cli_config.set('default_author', author)
        echo(style(f"✓ Default author set to: {author}", fg='green'))
    
    if email:
        cli_config.set('default_email', email)
        echo(style(f"✓ Default email set to: {email}", fg='green'))
    
    if not any([base_url, api_key, author, email]):
        echo("No configuration changes specified. Use --show to see current config.")


def _create_agent_files(target_dir: Path, config: AgentConfig, agent_type: str, verbose: bool):
    """Create agent files in the target directory."""
    
    # Create config.json
    config_file = target_dir / "config.json"
    with open(config_file, 'w') as f:
        json.dump(config.to_dict(), f, indent=2)
    
    # Create main agent file
    agent_code = _generate_agent_code(config, agent_type)
    agent_file = target_dir / config.entry_point
    with open(agent_file, 'w') as f:
        f.write(agent_code)
    
    # Create requirements.txt
    requirements_file = target_dir / "requirements.txt"
    with open(requirements_file, 'w') as f:
        if config.requirements:
            f.write('\n'.join(config.requirements))
        else:
            f.write("# Add your agent dependencies here\n")
    
    # Create README.md
    readme_file = target_dir / "README.md"
    with open(readme_file, 'w') as f:
        f.write(_generate_readme(config))
    
    # Create .gitignore
    gitignore_file = target_dir / ".gitignore"
    with open(gitignore_file, 'w') as f:
        f.write(_generate_gitignore())
    
    if verbose:
        echo(f"  Created: {config_file}")
        echo(f"  Created: {agent_file}")
        echo(f"  Created: {requirements_file}")
        echo(f"  Created: {readme_file}")
        echo(f"  Created: {gitignore_file}")


def _generate_agent_code(config: AgentConfig, agent_type: str) -> str:
    """Generate agent code based on type."""
    
    if agent_type == 'simple':
        return f'''#!/usr/bin/env python3
"""
{config.name} - {config.description}
"""

import json
from typing import Dict, Any


def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main agent function.
    
    Args:
        input_data: User input data
        config: Agent configuration
    
    Returns:
        Agent response (must be JSON serializable)
    """
    try:
        # Your agent logic here
        message = input_data.get("message", "Hello, World!")
        
        # Process the message
        result = {{
            "response": f"Processed: {{message}}",
            "status": "success",
            "agent": "{config.name}",
            "version": "{config.version}"
        }}
        
        return result
        
    except Exception as e:
        return {{
            "error": str(e),
            "status": "error",
            "agent": "{config.name}",
            "version": "{config.version}"
        }}


# For local testing
if __name__ == "__main__":
    test_input = {{"message": "Hello, test!"}}
    test_config = {{}}
    
    result = main(test_input, test_config)
    print(json.dumps(result, indent=2))
'''
    
    elif agent_type == 'data':
        return f'''#!/usr/bin/env python3
"""
{config.name} - {config.description}
"""

import json
from typing import Dict, Any, List, Union


def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Data processing agent function.
    
    Args:
        input_data: User input data containing data to process
        config: Agent configuration
    
    Returns:
        Agent response with processed data
    """
    try:
        # Get data from input
        data = input_data.get("data", [])
        operation = input_data.get("operation", "count")
        
        # Process the data
        if operation == "count":
            result = len(data) if isinstance(data, list) else 1
        elif operation == "sum":
            result = sum(float(x) for x in data if isinstance(x, (int, float)))
        elif operation == "filter":
            filter_value = input_data.get("filter_value", "")
            result = [item for item in data if filter_value in str(item)]
        else:
            result = data
        
        return {{
            "result": result,
            "operation": operation,
            "status": "success",
            "agent": "{config.name}",
            "version": "{config.version}"
        }}
        
    except Exception as e:
        return {{
            "error": str(e),
            "status": "error",
            "agent": "{config.name}",
            "version": "{config.version}"
        }}


# For local testing
if __name__ == "__main__":
    test_input = {{
        "data": [1, 2, 3, 4, 5],
        "operation": "sum"
    }}
    test_config = {{}}
    
    result = main(test_input, test_config)
    print(json.dumps(result, indent=2))
'''
    
    elif agent_type == 'chat':
        return f'''#!/usr/bin/env python3
"""
{config.name} - {config.description}
"""

import json
from typing import Dict, Any, List


def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chat agent function.
    
    Args:
        input_data: User input data with message
        config: Agent configuration
    
    Returns:
        Agent response with chat reply
    """
    try:
        # Get message from input
        message = input_data.get("message", "").strip()
        conversation_history = input_data.get("conversation_history", [])
        
        if not message:
            return {{
                "error": "No message provided",
                "status": "error",
                "agent": "{config.name}",
                "version": "{config.version}"
            }}
        
        # Simple chat logic
        message_lower = message.lower()
        
        if any(greeting in message_lower for greeting in ["hello", "hi", "hey"]):
            response = f"Hello! I'm {{config.name}}. How can I help you today?"
        elif any(farewell in message_lower for farewell in ["bye", "goodbye", "see you"]):
            response = "Goodbye! Have a great day!"
        elif "help" in message_lower:
            response = "I'm here to help! You can ask me questions or just chat."
        elif message_lower.endswith("?"):
            response = f"That's an interesting question: '{{message}}'. I'm still learning!"
        else:
            response = f"I received your message: '{{message}}'. Thanks for chatting!"
        
        return {{
            "response": response,
            "conversation_length": len(conversation_history) + 1,
            "status": "success",
            "agent": "{config.name}",
            "version": "{config.version}"
        }}
        
    except Exception as e:
        return {{
            "error": str(e),
            "status": "error",
            "agent": "{config.name}",
            "version": "{config.version}"
        }}


# For local testing
if __name__ == "__main__":
    test_input = {{
        "message": "Hello, how are you?",
        "conversation_history": []
    }}
    test_config = {{}}
    
    result = main(test_input, test_config)
    print(json.dumps(result, indent=2))
'''
    
    return ""


def _generate_readme(config: AgentConfig) -> str:
    """Generate README file content."""
    return f"""# {config.name}

{config.description}

## Configuration

- **Version**: {config.version}
- **Author**: {config.author}
- **Email**: {config.email}
- **Category**: {config.category}
- **Pricing**: {config.pricing_model}
- **Entry Point**: {config.entry_point}

## Usage

This agent can be executed through the AgentHub platform or tested locally.

### Local Testing

```bash
python {config.entry_point}
```

### Using the CLI

```bash
# Validate the agent
agenthub agent validate

# Test the agent
agenthub agent test

# Publish the agent
agenthub agent publish
```

## Requirements

{chr(10).join(f'- {req}' for req in config.requirements) if config.requirements else 'No external requirements'}

## Tags

{', '.join(config.tags) if config.tags else 'No tags'}

## Development

1. Modify the agent code in `{config.entry_point}`
2. Update requirements in `requirements.txt`
3. Test locally with sample data
4. Validate with `agenthub agent validate`
5. Publish with `agenthub agent publish`
"""


def _generate_gitignore() -> str:
    """Generate .gitignore file content."""
    return """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
#  Usually these files are written by a python script from a template
#  before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
#   For a library or package, you might want to ignore these files since the code is
#   intended to run in multiple environments; otherwise, check them in:
# .python-version

# pipenv
#   According to pypa/pipenv#598, it is recommended to include Pipfile.lock in version control.
#   However, in case of collaboration, if having platform-specific dependencies or dependencies
#   having no cross-platform support, pipenv may install dependencies that don't work, or not
#   install all needed dependencies.
#Pipfile.lock

# poetry
#   Similar to Pipfile.lock, it is generally recommended to include poetry.lock in version control.
#   This is especially recommended for binary packages to ensure reproducibility, and is more
#   commonly ignored for libraries.
#   https://python-poetry.org/docs/basic-usage/#commit-your-poetrylock-file-to-version-control
#poetry.lock

# pdm
#   Similar to Pipfile.lock, it is generally recommended to include pdm.lock in version control.
#pdm.lock
#   pdm stores project-wide configurations in .pdm.toml, but it is recommended to not include it
#   in version control.
#   https://pdm.fming.dev/#use-with-ide
.pdm.toml

# PEP 582; used by e.g. github.com/David-OConnor/pyflow and github.com/pdm-project/pdm
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# PyCharm
#  JetBrains specific template is maintained in a separate JetBrains.gitignore that can
#  be added to the global gitignore or merged into this project gitignore.  For a PyCharm
#  project, it is recommended to add the JetBrains specific template to the global gitignore
#  or merge it into this project gitignore.
#  This template is maintained in a separate JetBrains.gitignore that can be added to the
#  global gitignore or merged into this project gitignore.
.idea/
*.iws
*.iml
*.ipr

# VSCode
.vscode/

# Agent specific
config.json.bak
*.zip
temp/
"""


def _run_agent_locally(agent_dir: Path, config: AgentConfig, test_input: Dict[str, Any], test_config: Dict[str, Any]) -> Dict[str, Any]:
    """Run agent locally for testing."""
    import subprocess
    import sys
    
    # Run the agent script
    entry_point = agent_dir / config.entry_point
    
    # Create a temporary script to run the agent with input
    test_script = f"""
import sys
sys.path.insert(0, '{agent_dir}')

import json
from {config.entry_point.replace('.py', '')} import main

input_data = {json.dumps(test_input)}
config_data = {json.dumps(test_config)}

result = main(input_data, config_data)
print(json.dumps(result, indent=2))
"""
    
    # Run the test script
    result = subprocess.run([sys.executable, '-c', test_script], 
                          capture_output=True, text=True, cwd=agent_dir)
    
    if result.returncode != 0:
        raise Exception(f"Agent execution failed: {result.stderr}")
    
    return json.loads(result.stdout)


def _create_agent_instance(config: AgentConfig) -> Agent:
    """Create a minimal agent instance for publishing."""
    
    class PublishAgent(SimpleAgent):
        def __init__(self, config: AgentConfig):
            super().__init__(config)
        
        def generate_code(self) -> str:
            return f"# Agent: {config.name}\n# Generated for publishing"
    
    return PublishAgent(config)


def _generate_template(template_type: str) -> str:
    """Generate template code for different agent types."""
    
    base_config = AgentConfig(
        name="Template Agent",
        description="A template agent for development",
        author="Your Name",
        email="your.email@example.com",
        entry_point="template_agent.py"
    )
    
    return _generate_agent_code(base_config, template_type)


if __name__ == '__main__':
    # Add click dependency requirement
    try:
        import click
    except ImportError:
        echo("Error: click is required. Install with: pip install click")
        sys.exit(1)
    
    cli() 