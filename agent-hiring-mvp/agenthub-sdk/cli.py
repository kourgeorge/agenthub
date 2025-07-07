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
              type=click.Choice(['simple', 'data', 'chat', 'acp_server']), 
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
        
        # 🔧 FIX: Read local requirements.txt and merge with config requirements
        requirements_file = agent_dir / "requirements.txt"
        local_requirements = []
        if requirements_file.exists():
            try:
                with open(requirements_file, 'r') as f:
                    local_requirements = [
                        line.strip() 
                        for line in f.readlines() 
                        if line.strip() and not line.strip().startswith('#')
                    ]
                if verbose and local_requirements:
                    echo(f"  Found local requirements: {', '.join(local_requirements)}")
            except Exception as e:
                echo(style(f"⚠ Warning: Could not read requirements.txt: {e}", fg='yellow'))
        
        # Merge config requirements with local requirements
        all_requirements = list(set(config.requirements + local_requirements))
        config.requirements = all_requirements
        
        if verbose and all_requirements:
            echo(f"  Total requirements to publish: {', '.join(all_requirements)}")
        elif all_requirements:
            echo(f"  📦 Publishing with {len(all_requirements)} requirements")
        
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


@agent.command(name='list')
@click.option('--query', '-q', help='Search query')
@click.option('--category', '-c', help='Filter by category')
@click.option('--limit', '-l', default=10, help='Number of results to show')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def list_agents(ctx, query, category, limit, base_url):
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
@click.argument('agent_id', type=int)
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def approve(ctx, agent_id, base_url):
    """Approve an agent (admin only)."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style(f"✅ Approving agent {agent_id}...", fg='blue'))
        
        async def approve_agent():
            async with AgentHubClient(base_url) as client:
                result = await client.approve_agent(agent_id)
                return result
        
        result = asyncio.run(approve_agent())
        
        echo(style("✅ Agent approved successfully!", fg='green'))
        echo(f"  Agent ID: {result.get('agent_id')}")
        echo(f"  Status: {result.get('status')}")
        echo(f"  Message: {result.get('message')}")
        
        if verbose:
            echo("Full response:")
            echo(json.dumps(result, indent=2))
            
    except Exception as e:
        echo(style(f"✗ Error approving agent: {e}", fg='red'))
        sys.exit(1)


@agent.command()
@click.argument('agent_id', type=int)
@click.option('--reason', '-r', required=True, help='Reason for rejection')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def reject(ctx, agent_id, reason, base_url):
    """Reject an agent (admin only)."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style(f"❌ Rejecting agent {agent_id}...", fg='blue'))
        
        async def reject_agent():
            async with AgentHubClient(base_url) as client:
                result = await client.reject_agent(agent_id, reason)
                return result
        
        result = asyncio.run(reject_agent())
        
        echo(style("❌ Agent rejected successfully!", fg='yellow'))
        echo(f"  Agent ID: {result.get('agent_id')}")
        echo(f"  Status: {result.get('status')}")
        echo(f"  Reason: {result.get('reason')}")
        
        if verbose:
            echo("Full response:")
            echo(json.dumps(result, indent=2))
            
    except Exception as e:
        echo(style(f"✗ Error rejecting agent: {e}", fg='red'))
        sys.exit(1)


@agent.command()
@click.argument('template_type', type=click.Choice(['simple', 'data', 'chat', 'acp_server', 'acp_template']))
@click.argument('target_directory', required=False)
@click.pass_context
def template(ctx, template_type, target_directory):
    """Generate agent templates or copy full template directory."""
    verbose = ctx.obj.get('verbose', False)
    
    if template_type == 'acp_template':
        # Copy the full ACP template directory
        if not target_directory:
            target_directory = 'my_acp_agent'
        
        sdk_dir = Path(__file__).parent
        template_dir = sdk_dir / "templates" / "acp_agent_template"
        target_path = Path(target_directory)
        
        if not template_dir.exists():
            echo(style("❌ ACP template directory not found. Make sure the templates are installed.", fg='red'))
            sys.exit(1)
        
        if target_path.exists():
            if not click.confirm(f"Directory '{target_directory}' already exists. Continue?"):
                sys.exit(0)
        
        try:
            import shutil
            shutil.copytree(template_dir, target_path, dirs_exist_ok=True)
            
            echo(style(f"✅ ACP agent template copied to '{target_directory}'", fg='green'))
            echo("📝 Next steps:")
            echo(f"  1. cd {target_directory}")
            echo("  2. Customize config.json with your agent details")
            echo("  3. Modify acp_agent_template.py for your use case")
            echo("  4. pip install -r requirements.txt")
            echo("  5. python acp_agent_template.py")
            echo("  6. agenthub agent validate")
            echo("  7. agenthub agent publish")
            
        except Exception as e:
            echo(style(f"❌ Error copying template: {e}", fg='red'))
            sys.exit(1)
    else:
        # Generate single template file
        template_code = _generate_template(template_type)
        
        if not target_directory:
            target_directory = f"{template_type}_agent.py"
        
        target_path = Path(target_directory)
        
        try:
            with open(target_path, 'w') as f:
                f.write(template_code)
            
            echo(style(f"✅ Template generated: {target_path}", fg='green'))
            if verbose:
                echo(f"Template type: {template_type}")
                echo(f"Output file: {target_path}")
                
        except Exception as e:
            echo(style(f"❌ Error generating template: {e}", fg='red'))
            sys.exit(1)


@cli.group()
def marketplace():
    """Browse and discover agents in the marketplace."""
    pass


@cli.group()
def hire():
    """Hire agents for your use cases."""
    pass


@cli.group()
def execute():
    """Execute hired agents."""
    pass


@cli.group()
def jobs():
    """Manage agent execution jobs."""
    pass


@cli.group()
def hired():
    """Manage your hired agents."""
    pass


@cli.group()
def deploy():
    """Deploy and manage ACP server agents."""
    pass


@marketplace.command()
@click.option('--query', '-q', help='Search query')
@click.option('--category', '-c', help='Filter by category')
@click.option('--pricing', '-p', help='Filter by pricing model')
@click.option('--limit', '-l', default=10, help='Number of results to show')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def search(ctx, query, category, pricing, limit, base_url):
    """Search for agents in the marketplace."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style("🔍 Searching marketplace...", fg='blue'))
        
        async def search_agents():
            async with AgentHubClient(base_url) as client:
                result = await client.list_agents(
                    query=query,
                    category=category,
                    limit=limit
                )
                return result
        
        result = asyncio.run(search_agents())
        agents = result.get('agents', [])
        
        if not agents:
            echo(style("No agents found matching your criteria.", fg='yellow'))
            return
        
        echo(style(f"Found {len(agents)} agents:", fg='green'))
        echo()
        
        for agent in agents:
            # Filter by pricing if specified
            if pricing and agent.get('pricing_model') != pricing:
                continue
                
            echo(f"🤖 {style(agent['name'], fg='cyan', bold=True)} (ID: {agent['id']})")
            echo(f"   {agent['description']}")
            echo(f"   Author: {agent['author']} | Category: {agent['category']}")
            echo(f"   Pricing: {agent['pricing_model']}", nl=False)
            
            if agent.get('price_per_use'):
                echo(f" (${agent['price_per_use']}/use)", nl=False)
            if agent.get('monthly_price'):
                echo(f" (${agent['monthly_price']}/month)", nl=False)
            echo()
            
            if agent.get('tags'):
                echo(f"   Tags: {', '.join(agent['tags'])}")
            echo()
            
    except Exception as e:
        echo(style(f"✗ Error searching marketplace: {e}", fg='red'))
        sys.exit(1)


@marketplace.command()
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def categories(ctx, base_url):
    """List available agent categories."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style("📋 Fetching categories...", fg='blue'))
        
        async def get_categories():
            async with AgentHubClient(base_url) as client:
                result = await client.list_agents(limit=1000)  # Get all to extract categories
                agents = result.get('agents', [])
                categories = set(agent.get('category', 'general') for agent in agents)
                return sorted(categories)
        
        categories = asyncio.run(get_categories())
        
        echo(style("Available categories:", fg='green'))
        for category in categories:
            echo(f"  • {category}")
            
    except Exception as e:
        echo(style(f"✗ Error fetching categories: {e}", fg='red'))
        sys.exit(1)


@hire.command(name='agent')
@click.argument('agent_id', type=int)
@click.option('--config', '-c', help='JSON configuration for the agent')
@click.option('--billing-cycle', '-b', help='Billing cycle (per_use, monthly)')
@click.option('--user-id', '-u', type=int, help='User ID (for multi-user scenarios)')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def hire_agent_cmd(ctx, agent_id, config, billing_cycle, user_id, base_url):
    """Hire an agent by ID."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        # Parse config if provided
        agent_config = {}
        if config:
            agent_config = json.loads(config)
        
        echo(style(f"🤝 Hiring agent {agent_id}...", fg='blue'))
        
        async def hire_agent():
            async with AgentHubClient(base_url) as client:
                result = await client.hire_agent(
                    agent_id=agent_id,
                    config=agent_config,
                    billing_cycle=billing_cycle,
                    user_id=user_id
                )
                return result
        
        result = asyncio.run(hire_agent())
        
        echo(style("✅ Agent hired successfully!", fg='green'))
        echo(f"  Hiring ID: {result.get('hiring_id')}")
        echo(f"  Status: {result.get('status')}")
        echo(f"  Billing cycle: {result.get('billing_cycle')}")
        
        if verbose:
            echo("Full response:")
            echo(json.dumps(result, indent=2))
            
    except Exception as e:
        echo(style(f"✗ Error hiring agent: {e}", fg='red'))
        sys.exit(1)


@execute.command(name='agent')
@click.argument('agent_id', type=int)
@click.option('--input', '-i', required=True, help='JSON input data for the agent')
@click.option('--config', '-c', help='JSON configuration for the agent')
@click.option('--hiring-id', '-h', type=int, help='Hiring ID (if already hired)')
@click.option('--user-id', '-u', type=int, help='User ID')
@click.option('--wait', '-w', is_flag=True, help='Wait for completion')
@click.option('--timeout', '-t', default=60, help='Timeout in seconds')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def execute_agent_cmd(ctx, agent_id, input, config, hiring_id, user_id, wait, timeout, base_url):
    """Execute an agent with input data."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        # Parse input and config
        input_data = json.loads(input)
        agent_config = json.loads(config) if config else {}
        
        echo(style(f"🚀 Executing agent {agent_id}...", fg='blue'))
        if verbose:
            echo(f"Input: {json.dumps(input_data, indent=2)}")
            echo(f"Config: {json.dumps(agent_config, indent=2)}")
        
        async def execute_agent():
            async with AgentHubClient(base_url) as client:
                if wait:
                    result = await client.run_agent(
                        agent_id=agent_id,
                        input_data=input_data,
                        hiring_id=hiring_id,
                        user_id=user_id,
                        wait_for_completion=True,
                        timeout=timeout
                    )
                else:
                    result = await client.execute_agent(
                        agent_id=agent_id,
                        input_data=input_data,
                        hiring_id=hiring_id,
                        user_id=user_id
                    )
                return result
        
        result = asyncio.run(execute_agent())
        
        echo(style("✅ Agent execution completed!", fg='green'))
        echo(f"  Execution ID: {result.get('execution_id')}")
        echo(f"  Status: {result.get('status')}")
        
        # Display results - check both possible locations
        output_data = result.get('output_data')
        if output_data:
            echo("\n📊 Result:")
            if isinstance(output_data, dict):
                if 'output' in output_data:
                    echo(output_data['output'])
                else:
                    echo(json.dumps(output_data, indent=2))
            else:
                echo(str(output_data))
        elif result.get('result'):
            echo("\n📊 Result:")
            echo(json.dumps(result['result'], indent=2))
        
        if verbose:
            echo("\nFull response:")
            echo(json.dumps(result, indent=2))
            
    except Exception as e:
        echo(style(f"✗ Error executing agent: {e}", fg='red'))
        sys.exit(1)


@execute.command()
@click.argument('agent_id', type=int)
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--config', '-c', help='JSON configuration for the agent')
@click.option('--hiring-id', '-h', type=int, help='Hiring ID (if already hired)')
@click.option('--user-id', '-u', type=int, help='User ID')
@click.option('--wait', '-w', is_flag=True, help='Wait for completion')
@click.option('--timeout', '-t', default=60, help='Timeout in seconds')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def file(ctx, agent_id, input_file, config, hiring_id, user_id, wait, timeout, base_url):
    """Execute an agent with input from a file."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Read input from file
        with open(input_file, 'r') as f:
            input_data = json.load(f)
        
        echo(style(f"📁 Loading input from: {input_file}", fg='blue'))
        
        # Call the agent execution with the loaded data
        ctx.invoke(execute_agent_cmd, agent_id=agent_id, input=json.dumps(input_data), 
                  config=config, hiring_id=hiring_id, user_id=user_id, 
                  wait=wait, timeout=timeout, base_url=base_url)
        
    except Exception as e:
        echo(style(f"✗ Error reading input file: {e}", fg='red'))
        sys.exit(1)


@jobs.command(name='list')
@click.option('--user-id', '-u', type=int, help='User ID')
@click.option('--limit', '-l', default=10, help='Number of results to show')
@click.option('--status', '-s', help='Filter by status')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def list_jobs(ctx, user_id, limit, status, base_url):
    """List recent agent execution jobs."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style("📋 Fetching execution jobs...", fg='blue'))
        
        # Note: This would require an API endpoint for listing executions
        # For now, we'll show a placeholder
        echo(style("⚠️  Job listing feature requires server-side implementation", fg='yellow'))
        echo("Contact your AgentHub administrator to enable execution history.")
        
    except Exception as e:
        echo(style(f"✗ Error fetching jobs: {e}", fg='red'))
        sys.exit(1)


@jobs.command()
@click.argument('execution_id')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def status(ctx, execution_id, base_url):
    """Get the status of an execution job."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style(f"🔍 Checking status of execution {execution_id}...", fg='blue'))
        
        async def get_execution_status():
            async with AgentHubClient(base_url) as client:
                result = await client.get_execution_status(execution_id)
                return result
        
        result = asyncio.run(get_execution_status())
        
        echo(style("📊 Execution Status:", fg='green'))
        echo(f"  ID: {result.get('execution_id')}")
        echo(f"  Status: {result.get('status')}")
        echo(f"  Created: {result.get('created_at')}")
        echo(f"  Updated: {result.get('updated_at')}")
        
        # Display results - check both possible locations
        output_data = result.get('output_data')
        if output_data:
            echo("\n📋 Result:")
            if isinstance(output_data, dict):
                if 'output' in output_data:
                    echo(output_data['output'])
                else:
                    echo(json.dumps(output_data, indent=2))
            else:
                echo(str(output_data))
        elif result.get('result'):
            echo("\n📋 Result:")
            echo(json.dumps(result['result'], indent=2))
        
        if result.get('error'):
            echo(f"\n❌ Error: {result['error']}")
        elif result.get('error_message'):
            echo(f"\n❌ Error: {result['error_message']}")
            
    except Exception as e:
        echo(style(f"✗ Error getting execution status: {e}", fg='red'))
        sys.exit(1)


@hired.command(name='list')
@click.option('--user-id', '-u', type=int, help='User ID')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def list_hired(ctx, user_id, base_url):
    """List your hired agents."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style("📋 Fetching hired agents...", fg='blue'))
        
        async def get_hired_agents():
            async with AgentHubClient(base_url) as client:
                result = await client.list_hired_agents(user_id=user_id)
                return result
        
        result = asyncio.run(get_hired_agents())
        hired_agents = result.get('hired_agents', [])
        
        if not hired_agents:
            echo(style("No hired agents found.", fg='yellow'))
            return
        
        echo(style(f"Found {len(hired_agents)} hired agents:", fg='green'))
        echo()
        
        for hiring in hired_agents:
            agent = hiring.get('agent', {})
            echo(f"🤖 {style(agent.get('name', 'Unknown'), fg='cyan', bold=True)} (Hiring ID: {hiring.get('id')})")
            echo(f"   Agent ID: {agent.get('id')} | Category: {agent.get('category')}")
            echo(f"   Hired: {hiring.get('hired_at')} | Status: {hiring.get('status')}")
            echo(f"   Billing: {hiring.get('billing_cycle')}")
            echo()
            
    except Exception as e:
        echo(style(f"✗ Error fetching hired agents: {e}", fg='red'))
        sys.exit(1)


@hired.command(name='info')
@click.argument('hiring_id', type=int)
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def info_hired(ctx, hiring_id, base_url):
    """Get detailed information about a hired agent."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style(f"🔍 Fetching hiring details for {hiring_id}...", fg='blue'))
        
        # Note: This would require an API endpoint for hiring details
        # For now, we'll show a placeholder
        echo(style("⚠️  Hiring details feature requires server-side implementation", fg='yellow'))
        echo("Contact your AgentHub administrator to enable hiring management.")
        
    except Exception as e:
        echo(style(f"✗ Error fetching hiring details: {e}", fg='red'))
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


# ============================================================================
# ACP Server Deployment Commands
# ============================================================================

@deploy.command()
@click.argument('hiring_id', type=int)
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.option('--wait', '-w', is_flag=True, help='Wait for deployment completion')
@click.option('--timeout', '-t', default=300, help='Timeout in seconds')
@click.pass_context
def create(ctx, hiring_id, base_url, wait, timeout):
    """Create a deployment for a hired ACP agent."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style(f"🚀 Creating deployment for hiring {hiring_id}...", fg='blue'))
        
        async def create_deployment():
            async with AgentHubClient(base_url) as client:
                result = await client.create_deployment(hiring_id)
                return result
        
        result = asyncio.run(create_deployment())
        
        echo(style("✅ Deployment created successfully!", fg='green'))
        echo(f"  Deployment ID: {result.get('deployment_id')}")
        echo(f"  Status: {result.get('status')}")
        echo(f"  Proxy Endpoint: {result.get('proxy_endpoint')}")
        echo(f"  Message: {result.get('message')}")
        
        if wait and result.get('deployment_id'):
            echo(style("⏳ Waiting for deployment to complete...", fg='yellow'))
            import time
            
            deployment_id = result.get('deployment_id')
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                time.sleep(5)  # Check every 5 seconds
                
                # Check deployment status via direct API call
                import requests
                try:
                    response = requests.get(f"{base_url}/api/v1/deployment/status/{deployment_id}")
                    if response.status_code == 200:
                        status_data = response.json()
                        current_status = status_data.get('status', 'unknown')
                        
                        echo(f"  Current status: {current_status}")
                        
                        if current_status == 'running':
                            echo(style("🎉 Deployment completed successfully!", fg='green'))
                            echo(f"  Container Status: {status_data.get('container_status')}")
                            echo(f"  Health Check: {status_data.get('is_healthy')}")
                            break
                        elif current_status == 'failed':
                            echo(style("❌ Deployment failed!", fg='red'))
                            echo(f"  Error: {status_data.get('error')}")
                            sys.exit(1)
                except Exception as e:
                    echo(f"  Error checking status: {e}")
            else:
                echo(style("⏱️ Deployment timeout reached", fg='yellow'))
                echo("Use 'agenthub deploy status <deployment_id>' to check progress")
        
        if verbose:
            echo("Full response:")
            echo(json.dumps(result, indent=2))
            
    except Exception as e:
        echo(style(f"✗ Error creating deployment: {e}", fg='red'))
        sys.exit(1)


@deploy.command()
@click.argument('agent_id', type=int)
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.option('--wait', '-w', is_flag=True, help='Wait for deployment completion')
@click.option('--timeout', '-t', default=300, help='Timeout in seconds')
@click.pass_context
def start(ctx, agent_id, base_url, wait, timeout):
    """Deploy an ACP server agent."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style(f"🚀 Deploying agent {agent_id}...", fg='blue'))
        
        async def deploy_agent():
            async with AgentHubClient(base_url) as client:
                result = await client.deploy_agent(agent_id)
                return result
        
        result = asyncio.run(deploy_agent())
        
        echo(style("✅ Deployment initiated!", fg='green'))
        echo(f"  Deployment ID: {result.get('deployment_id')}")
        echo(f"  Status: {result.get('status')}")
        echo(f"  Port: {result.get('port', 'TBD')}")
        
        if wait:
            echo(style("⏳ Waiting for deployment to complete...", fg='yellow'))
            import time
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                time.sleep(5)  # Check every 5 seconds
                
                # Check deployment status
                async def check_status():
                    async with AgentHubClient(base_url) as client:
                        status = await client.get_deployment_status(agent_id)
                        return status
                
                status = asyncio.run(check_status())
                current_status = status.get('status', 'unknown')
                
                if current_status == 'running':
                    echo(style("🎉 Deployment completed successfully!", fg='green'))
                    echo(f"  URL: {status.get('url')}")
                    echo(f"  Health: {status.get('health_status')}")
                    break
                elif current_status == 'failed':
                    echo(style("❌ Deployment failed!", fg='red'))
                    echo(f"  Error: {status.get('error')}")
                    sys.exit(1)
                else:
                    echo(f"  Status: {current_status}")
            else:
                echo(style("⏱️ Deployment timeout reached", fg='yellow'))
                
        if verbose:
            echo("Full response:")
            echo(json.dumps(result, indent=2))
            
    except Exception as e:
        echo(style(f"✗ Error deploying agent: {e}", fg='red'))
        sys.exit(1)


@deploy.command()
@click.argument('agent_id', type=int)
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def stop(ctx, agent_id, base_url):
    """Stop a deployed ACP server agent."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style(f"🛑 Stopping deployment for agent {agent_id}...", fg='blue'))
        
        async def stop_agent():
            async with AgentHubClient(base_url) as client:
                result = await client.stop_deployment(agent_id)
                return result
        
        result = asyncio.run(stop_agent())
        
        echo(style("✅ Deployment stopped!", fg='green'))
        echo(f"  Status: {result.get('status')}")
        
        if verbose:
            echo("Full response:")
            echo(json.dumps(result, indent=2))
            
    except Exception as e:
        echo(style(f"✗ Error stopping deployment: {e}", fg='red'))
        sys.exit(1)


@deploy.command(name='list')
@click.option('--status', '-s', help='Filter by status')
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def list_deployments(ctx, status, base_url):
    """List all agent deployments."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style("📋 Fetching deployments...", fg='blue'))
        
        async def get_deployments():
            async with AgentHubClient(base_url) as client:
                result = await client.list_deployments()
                return result
        
        result = asyncio.run(get_deployments())
        deployments = result.get('deployments', [])
        
        if status:
            deployments = [d for d in deployments if d.get('status') == status]
        
        if not deployments:
            echo(style("No deployments found.", fg='yellow'))
            return
        
        echo(style(f"Found {len(deployments)} deployments:", fg='green'))
        echo()
        
        for deployment in deployments:
            status_color = {
                'running': 'green',
                'building': 'yellow',
                'deploying': 'blue',
                'failed': 'red',
                'stopped': 'grey'
            }.get(deployment.get('status'), 'white')
            
            # Extract port from proxy_endpoint
            proxy_endpoint = deployment.get('proxy_endpoint', '')
            port = 'N/A'
            if proxy_endpoint and ':' in proxy_endpoint:
                port = proxy_endpoint.split(':')[-1]
            
            # Map health status
            health_status = 'Healthy' if deployment.get('is_healthy') else 'Unhealthy'
            if deployment.get('is_healthy') is None:
                health_status = 'N/A'
            
            # Display deployment info with corrected field mapping
            echo(f"🚀 Agent ID {deployment.get('agent_id')} (Deployment: {deployment.get('deployment_id', 'Unknown')[:16]}...)")
            echo(f"   Status: {style(deployment.get('status', 'unknown'), fg=status_color)}")
            echo(f"   Port: {port}")
            echo(f"   URL: {deployment.get('proxy_endpoint', 'N/A')}")
            echo(f"   Health: {health_status}")
            if deployment.get('created_at'):
                echo(f"   Created: {deployment.get('created_at')}")
            echo()
            
    except Exception as e:
        echo(style(f"✗ Error fetching deployments: {e}", fg='red'))
        sys.exit(1)


@deploy.command()
@click.argument('agent_id', type=int)
@click.option('--base-url', help='Base URL of the AgentHub server')
@click.pass_context
def status(ctx, agent_id, base_url):
    """Check deployment status for an agent."""
    verbose = ctx.obj.get('verbose', False)
    
    base_url = base_url or cli_config.get('base_url', 'http://localhost:8002')
    
    try:
        echo(style(f"📊 Checking deployment status for agent {agent_id}...", fg='blue'))
        
        async def check_status():
            async with AgentHubClient(base_url) as client:
                result = await client.get_deployment_status(agent_id)
                return result
        
        result = asyncio.run(check_status())
        
        status_color = {
            'running': 'green',
            'building': 'yellow',
            'deploying': 'blue',
            'failed': 'red',
            'stopped': 'grey'
        }.get(result.get('status'), 'white')
        
        echo(style("📊 Deployment Status:", fg='green'))
        echo(f"  Agent ID: {result.get('agent_id')}")
        echo(f"  Status: {style(result.get('status', 'unknown'), fg=status_color)}")
        echo(f"  Port: {result.get('port', 'N/A')}")
        echo(f"  URL: {result.get('url', 'N/A')}")
        echo(f"  Health: {result.get('health_status', 'N/A')}")
        
        if result.get('error'):
            echo(f"  Error: {style(result.get('error'), fg='red')}")
        
        if result.get('logs'):
            echo(f"  Recent logs:")
            for log in result.get('logs')[-5:]:  # Last 5 log entries
                echo(f"    {log}")
        
        if verbose:
            echo("Full response:")
            echo(json.dumps(result, indent=2))
            
    except Exception as e:
        echo(style(f"✗ Error checking deployment status: {e}", fg='red'))
        sys.exit(1)


def _create_agent_files(target_dir: Path, config: AgentConfig, agent_type: str, verbose: bool):
    """Create agent files in the target directory."""
    
    # For ACP server agents, modify the config to include ACP manifest
    if agent_type == 'acp_server':
        config_dict = config.to_dict()
        config_dict['agent_type'] = 'acp_server'
        config_dict['acp_manifest'] = {
            "acp_version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "info": "/info", 
                "chat": "/chat",
                "status": "/"
            },
            "capabilities": [
                "text_processing",
                "session_management",
                "persistent_service",
                "health_monitoring"
            ],
            "deployment": {
                "port": 8001,
                "health_check_path": "/health",
                "startup_timeout": 30,
                "shutdown_timeout": 10,
                "environment_variables": {
                    "PORT": "Server port (default: 8001)",
                    "HOST": "Server host (default: 0.0.0.0)", 
                    "DEBUG": "Enable debug mode (default: false)",
                    "CORS_ORIGINS": "Comma-separated allowed origins (default: *)",
                    "MAX_MESSAGE_LENGTH": "Maximum message length (default: 10000)",
                    "SESSION_TIMEOUT": "Session timeout in seconds (default: 3600)"
                }
            }
        }
    else:
        config_dict = config.to_dict()
    
    # Create config.json
    config_file = target_dir / "config.json"
    with open(config_file, 'w') as f:
        json.dump(config_dict, f, indent=2)
    
    # Create main agent file
    agent_code = _generate_agent_code(config, agent_type)
    agent_file = target_dir / config.entry_point
    with open(agent_file, 'w') as f:
        f.write(agent_code)
    
    # Create requirements.txt
    requirements_file = target_dir / "requirements.txt"
    with open(requirements_file, 'w') as f:
        if agent_type == 'acp_server':
            # Add ACP server requirements
            f.write("aiohttp>=3.8.0,<4.0.0\n")
            f.write("aiohttp-cors>=0.7.0,<1.0.0\n")
            if config.requirements:
                f.write('\n'.join(config.requirements))
        elif config.requirements:
            f.write('\n'.join(config.requirements))
        else:
            f.write("# Add your agent dependencies here\n")
    
    # Create README.md
    readme_file = target_dir / "README.md"
    with open(readme_file, 'w') as f:
        f.write(_generate_readme(config, agent_type))
    
    # Create .gitignore
    gitignore_file = target_dir / ".gitignore"
    with open(gitignore_file, 'w') as f:
        f.write(_generate_gitignore())
    
    # Create Dockerfile for ACP server agents
    if agent_type == 'acp_server':
        dockerfile = target_dir / "Dockerfile"
        with open(dockerfile, 'w') as f:
            f.write(_generate_dockerfile(config))
    
    if verbose:
        echo(f"  Created: {config_file}")
        echo(f"  Created: {agent_file}")
        echo(f"  Created: {requirements_file}")
        echo(f"  Created: {readme_file}")
        echo(f"  Created: {gitignore_file}")
        if agent_type == 'acp_server':
            echo(f"  Created: {dockerfile}")


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
    
    elif agent_type == 'acp_server':
        agent_class_name = config.name.replace(' ', '').replace('-', '_').replace('.', '_')
        return f'''#!/usr/bin/env python3
"""
{config.name} - ACP Server Agent
{config.description}

This is an ACP (Agent Communication Protocol) server agent that provides
HTTP endpoints for health monitoring, agent information, and chat processing.
"""

import asyncio
import json
import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from aiohttp import web, ClientSession
import aiohttp_cors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class {agent_class_name}:
    """
    {config.name} - ACP Server Agent
    
    This agent provides standard ACP endpoints and can be customized
    for specific use cases.
    """
    
    def __init__(self, 
                 name: str = "{config.name}",
                 version: str = "{config.version}",
                 description: str = "{config.description}"):
        self.name = name
        self.version = version
        self.description = description
        self.started_at = None
        self.session_count = 0
        self.message_count = 0
        self.sessions: Dict[str, Dict[str, Any]] = {{}}
        
        # Load configuration from environment
        self.config = {{
            'debug': os.getenv('DEBUG', 'false').lower() == 'true',
            'cors_origins': os.getenv('CORS_ORIGINS', '*').split(','),
            'max_message_length': int(os.getenv('MAX_MESSAGE_LENGTH', '10000')),
            'session_timeout': int(os.getenv('SESSION_TIMEOUT', '3600')),  # 1 hour
        }}
        
        logger.info(f"Initialized {{self.name}} v{{self.version}}")
    
    async def create_app(self) -> web.Application:
        """Create and configure the aiohttp web application."""
        app = web.Application()
        
        # Configure CORS
        cors = aiohttp_cors.setup(app, defaults={{
            origin: aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            ) for origin in self.config['cors_origins']
        }})
        
        # Add routes
        app.router.add_get('/health', self.health_check)
        app.router.add_get('/info', self.get_info)
        app.router.add_post('/chat', self.handle_chat)
        app.router.add_get('/', self.get_status)
        
        # Add CORS to all routes
        for route in list(app.router.routes()):
            cors.add(route)
        
        # Add middleware (wrapped to handle self parameter correctly)
        @web.middleware
        async def error_middleware_wrapper(request, handler):
            return await self.error_middleware(request, handler)
        
        @web.middleware
        async def logging_middleware_wrapper(request, handler):
            return await self.logging_middleware(request, handler)
        
        app.middlewares.append(error_middleware_wrapper)
        app.middlewares.append(logging_middleware_wrapper)
        
        self.started_at = datetime.now(timezone.utc)
        return app
    
    # =============================================================================
    # STANDARD ACP ENDPOINTS
    # =============================================================================
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint for monitoring and load balancers."""
        uptime = (datetime.now(timezone.utc) - self.started_at).total_seconds() if self.started_at else 0
        
        health_data = {{
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": uptime,
            "version": self.version,
            "sessions_active": len(self.sessions),
            "messages_processed": self.message_count
        }}
        
        return web.json_response(health_data)
    
    async def get_info(self, request: web.Request) -> web.Response:
        """Get comprehensive agent information and capabilities."""
        info_data = {{
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "agent_type": "acp_server",
            "endpoints": {{
                "health": "/health",
                "info": "/info",
                "chat": "/chat",
                "status": "/"
            }},
            "capabilities": [
                "text_processing",
                "session_management", 
                "persistent_service",
                "health_monitoring"
            ],
            "configuration": {{
                "max_message_length": self.config['max_message_length'],
                "session_timeout": self.config['session_timeout'],
                "cors_enabled": True
            }},
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stats": {{
                "sessions_active": len(self.sessions),
                "sessions_total": self.session_count,
                "messages_processed": self.message_count
            }}
        }}
        
        return web.json_response(info_data)
    
    async def handle_chat(self, request: web.Request) -> web.Response:
        """Handle chat messages with session management."""
        try:
            data = await request.json()
            message = data.get('message', '')
            session_id = data.get('session_id')
            context = data.get('context', {{}})
            
            # Validate message
            if not message:
                return web.json_response({{
                    "error": "Message cannot be empty",
                    "code": "EMPTY_MESSAGE"
                }}, status=400)
            
            # Get or create session
            session = await self.get_or_create_session(session_id, context)
            
            # Process the message
            response = await self.process_chat_message(message, session, context)
            
            # Update session history
            session['messages'].append({{
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'type': 'user',
                'content': message
            }})
            session['messages'].append({{
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'type': 'agent',
                'content': response['response']
            }})
            session['last_activity'] = datetime.now(timezone.utc)
            
            self.message_count += 1
            
            # Return response
            return web.json_response({{
                **response,
                "session_id": session['id'],
                "message_count": len(session['messages'])
            }})
            
        except json.JSONDecodeError:
            return web.json_response({{
                "error": "Invalid JSON payload",
                "code": "INVALID_JSON"
            }}, status=400)
        except Exception as e:
            logger.error(f"Error in chat handler: {{e}}")
            return web.json_response({{
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "details": str(e) if self.config['debug'] else None
            }}, status=500)
    
    async def get_status(self, request: web.Request) -> web.Response:
        """Get general server status and information."""
        uptime = (datetime.now(timezone.utc) - self.started_at).total_seconds() if self.started_at else 0
        
        return web.json_response({{
            "message": f"🚀 {{self.name}} is running!",
            "agent": self.name,
            "version": self.version,
            "status": "operational",
            "uptime_seconds": uptime,
            "endpoints": ["/health", "/info", "/chat"],
            "stats": {{
                "sessions_active": len(self.sessions),
                "sessions_total": self.session_count,
                "messages_processed": self.message_count
            }}
        }})
    
    # =============================================================================
    # CORE PROCESSING METHODS (CUSTOMIZE THESE)
    # =============================================================================
    
    async def process_chat_message(self, message: str, session: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a chat message and generate a response.
        
        CUSTOMIZE THIS METHOD for your agent's specific functionality.
        
        Args:
            message: The user's message
            session: Session data including history
            context: Additional context from the request
            
        Returns:
            Dictionary with response data
        """
        # Default implementation - replace with your agent logic
        response_text = f"Hello! I received your message: '{{message}}'. I'm {{self.name}}."
        
        # Add some context-aware responses
        if 'hello' in message.lower():
            response_text = f"Hello! Nice to meet you. I'm {{self.name}}, version {{self.version}}."
        elif 'help' in message.lower():
            response_text = "I'm here to help! You can chat with me. Try asking about my capabilities!"
        elif 'capabilities' in message.lower():
            response_text = "I can process text messages, maintain conversations, and provide information. You can customize my functionality by modifying the process_chat_message method."
        
        return {{
            "agent": self.name,
            "version": self.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response": response_text,
            "processed": True,
            "message_id": f"msg_{{self.message_count + 1}}"
        }}
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    async def get_or_create_session(self, session_id: Optional[str] = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get existing session or create a new one."""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        
        # Create new session
        if not session_id:
            session_id = f"session_{{self.session_count + 1}}_{{int(datetime.now().timestamp())}}"
        
        self.session_count += 1
        session = {{
            'id': session_id,
            'created_at': datetime.now(timezone.utc),
            'last_activity': datetime.now(timezone.utc),
            'messages': [],
            'context': context or {{}}
        }}
        
        self.sessions[session_id] = session
        return session
    
    # =============================================================================
    # MIDDLEWARE
    # =============================================================================
    
    async def error_middleware(self, request: web.Request, handler):
        """Global error handling middleware."""
        try:
            return await handler(request)
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unhandled error: {{e}}\\n{{traceback.format_exc()}}")
            return web.json_response({{
                "error": "Internal server error",
                "code": "UNHANDLED_ERROR",
                "details": str(e) if self.config['debug'] else None
            }}, status=500)
    
    async def logging_middleware(self, request: web.Request, handler):
        """Request logging middleware."""
        start_time = datetime.now()
        response = await handler(request)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds() * 1000
        logger.info(f"{{request.method}} {{request.path}} - {{response.status}} - {{duration:.2f}}ms")
        
        return response


async def main():
    """
    Main entry point for the ACP agent server.
    
    Environment variables:
        PORT: Server port (default: 8001)
        HOST: Server host (default: 0.0.0.0)
        DEBUG: Enable debug mode (default: false)
        CORS_ORIGINS: Comma-separated list of allowed origins (default: *)
        MAX_MESSAGE_LENGTH: Maximum message length (default: 10000)
        SESSION_TIMEOUT: Session timeout in seconds (default: 3600)
    """
    # Create agent instance
    agent = {agent_class_name}()
    
    # Create web application
    app = await agent.create_app()
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))
    
    # Start the server
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"🚀 {{agent.name}} server started on {{host}}:{{port}}")
    logger.info(f"Health check: http://{{host}}:{{port}}/health")
    logger.info(f"Agent info: http://{{host}}:{{port}}/info")
    logger.info(f"Chat endpoint: http://{{host}}:{{port}}/chat")
    
    # Keep the server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
'''
    
    return ""


def _generate_readme(config: AgentConfig, agent_type: str) -> str:
    """Generate README file content."""
    if agent_type == 'acp_server':
        return f"""# {config.name}

{config.description}

## Configuration

- **Version**: {config.version}
- **Author**: {config.author}
- **Email**: {config.email}
- **Category**: {config.category}
- **Pricing**: {config.pricing_model}
- **Agent Type**: ACP Server
- **Entry Point**: {config.entry_point}

## ACP Server Agent

This is an ACP (Agent Communication Protocol) server agent that provides HTTP endpoints for communication.

### Endpoints

- `GET /health` - Health check and status
- `GET /info` - Agent information and capabilities
- `POST /chat` - Chat with the agent
- `GET /` - Server status

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8001` | Server port |
| `HOST` | `0.0.0.0` | Server host |
| `DEBUG` | `false` | Enable debug mode |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `MAX_MESSAGE_LENGTH` | `10000` | Maximum message length |
| `SESSION_TIMEOUT` | `3600` | Session timeout in seconds |

### Usage

#### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent
python {config.entry_point}

# Test the endpoints
curl http://localhost:8001/health
curl http://localhost:8001/info
curl -X POST http://localhost:8001/chat \\
  -H "Content-Type: application/json" \\
  -d '{{"message": "Hello!"}}'
```

#### Docker

```bash
# Build image
docker build -t {config.name.lower().replace(' ', '-')} .

# Run container
docker run -d \\
  --name {config.name.lower().replace(' ', '-')} \\
  -p 8001:8001 \\
  {config.name.lower().replace(' ', '-')}
```

#### Publishing to AgentHub

```bash
# Validate the agent
agenthub agent validate

# Publish to platform
agenthub agent publish
```

### Customization

To customize the agent's behavior, modify the `process_chat_message` method in `{config.entry_point}`:

```python
async def process_chat_message(self, message: str, session: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    # Add your custom logic here
    if "weather" in message.lower():
        response = "I can help with weather information!"
    else:
        response = f"You said: {{message}}"
    
    return {{
        "agent": self.name,
        "response": response,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }}
```

### Support

For questions about agent development and deployment, refer to the AgentHub documentation.
"""
    else:
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

### Publishing to AgentHub

```bash
# Validate the agent
agenthub agent validate

# Publish to platform
agenthub agent publish
```

## Development

Add your agent logic to the main function in `{config.entry_point}`.

## Support

For questions about agent development, refer to the AgentHub documentation.
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


def _generate_dockerfile(config: AgentConfig) -> str:
    """Generate Dockerfile for ACP server agents."""
    return f"""FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY . .

# Expose ACP port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Run the agent
CMD ["python", "{config.entry_point}"]
"""


def _generate_acp_manifest(config: AgentConfig) -> str:
    """Generate ACP manifest.json for agent discovery."""
    manifest = {
        "name": config.name,
        "version": config.version,
        "description": config.description,
        "author": config.author,
        "email": config.email,
        "acp_version": "1.0.0",
        "agent_type": "acp_server",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "tools": "/tools"
        },
        "capabilities": [
            "text_processing",
            "tool_calling",
            "async_processing"
        ],
        "requirements": {
            "python": ">=3.8",
            "acp_sdk": ">=0.1.0"
        },
        "deployment": {
            "port": 8080,
            "health_check_path": "/health",
            "startup_timeout": 30,
            "shutdown_timeout": 10
        },
        "tags": config.tags or [],
        "category": config.category or "general",
        "pricing": {
            "model": config.pricing_model,
            "price_per_use": config.price_per_use,
            "monthly_price": config.monthly_price
        }
    }
    
    return json.dumps(manifest, indent=2)


if __name__ == '__main__':
    # Add click dependency requirement
    try:
        import click
    except ImportError:
        echo("Error: click is required. Install with: pip install click")
        sys.exit(1)
    
    cli() 