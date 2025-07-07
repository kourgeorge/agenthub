#!/usr/bin/env python3
"""
ACP Agent Template - A template for creating ACP (Agent Communication Protocol) server agents.

This template provides a complete starting point for building ACP server agents with:
- Standard HTTP endpoints (health, info, chat)
- Proper error handling and logging
- CORS support for web clients
- Environment-based configuration
- Session and message tracking
- Extensible architecture for custom functionality

Usage:
    1. Copy this template to your agent directory
    2. Rename the file and class to match your agent
    3. Customize the endpoints and add your business logic
    4. Update config.json with your agent details
    5. Deploy using AgentHub CLI
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


class ACPAgentTemplate:
    """
    Template ACP Agent implementation with standard endpoints and functionality.
    
    This class provides a foundation for building ACP server agents with:
    - Health monitoring
    - Agent information API
    - Chat/message processing
    - Session management
    - Error handling
    """
    
    def __init__(self, 
                 name: str = "ACP Agent Template",
                 version: str = "1.0.0",
                 description: str = "A template ACP server agent"):
        """
        Initialize the ACP agent.
        
        Args:
            name: Agent name
            version: Agent version
            description: Agent description
        """
        self.name = name
        self.version = version
        self.description = description
        self.started_at = None
        self.session_count = 0
        self.message_count = 0
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Load configuration from environment
        self.config = {
            'debug': os.getenv('DEBUG', 'false').lower() == 'true',
            'cors_origins': os.getenv('CORS_ORIGINS', '*').split(','),
            'max_message_length': int(os.getenv('MAX_MESSAGE_LENGTH', '10000')),
            'session_timeout': int(os.getenv('SESSION_TIMEOUT', '3600')),  # 1 hour
        }
        
        logger.info(f"Initialized {self.name} v{self.version}")
    
    async def create_app(self) -> web.Application:
        """
        Create and configure the aiohttp web application.
        
        Returns:
            Configured aiohttp Application
        """
        app = web.Application()
        
        # Configure CORS
        cors = aiohttp_cors.setup(app, defaults={
            origin: aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            ) for origin in self.config['cors_origins']
        })
        
        # Add routes
        app.router.add_get('/health', self.health_check)
        app.router.add_get('/info', self.get_info)
        app.router.add_post('/chat', self.handle_chat)
        app.router.add_post('/message', self.handle_message)
        app.router.add_get('/sessions', self.list_sessions)
        app.router.add_get('/sessions/{session_id}', self.get_session)
        app.router.add_delete('/sessions/{session_id}', self.delete_session)
        app.router.add_get('/', self.get_status)
        
        # Add CORS to all routes
        for route in list(app.router.routes()):
            cors.add(route)
        
        # Add middleware
        app.middlewares.append(self.error_middleware)
        app.middlewares.append(self.logging_middleware)
        
        self.started_at = datetime.now(timezone.utc)
        return app
    
    # =============================================================================
    # STANDARD ACP ENDPOINTS
    # =============================================================================
    
    async def health_check(self, request: web.Request) -> web.Response:
        """
        Health check endpoint for monitoring and load balancers.
        
        Returns:
            JSON response with health status and uptime information
        """
        uptime = (datetime.now(timezone.utc) - self.started_at).total_seconds() if self.started_at else 0
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": uptime,
            "version": self.version,
            "sessions_active": len(self.sessions),
            "messages_processed": self.message_count
        }
        
        return web.json_response(health_data)
    
    async def get_info(self, request: web.Request) -> web.Response:
        """
        Get comprehensive agent information and capabilities.
        
        Returns:
            JSON response with agent metadata, endpoints, and capabilities
        """
        info_data = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "agent_type": "acp_server",
            "endpoints": {
                "health": "/health",
                "info": "/info",
                "chat": "/chat",
                "message": "/message",
                "sessions": "/sessions",
                "status": "/"
            },
            "capabilities": [
                "text_processing",
                "session_management",
                "persistent_service",
                "health_monitoring",
                "message_tracking"
            ],
            "configuration": {
                "max_message_length": self.config['max_message_length'],
                "session_timeout": self.config['session_timeout'],
                "cors_enabled": True
            },
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stats": {
                "sessions_active": len(self.sessions),
                "sessions_total": self.session_count,
                "messages_processed": self.message_count
            }
        }
        
        return web.json_response(info_data)
    
    async def handle_chat(self, request: web.Request) -> web.Response:
        """
        Handle chat messages with session management.
        
        Expected JSON payload:
        {
            "message": "string",
            "session_id": "optional_string",
            "context": "optional_object"
        }
        
        Returns:
            JSON response with agent's reply and session information
        """
        try:
            data = await request.json()
            message = data.get('message', '')
            session_id = data.get('session_id')
            context = data.get('context', {})
            
            # Validate message
            if not message:
                return web.json_response({
                    "error": "Message cannot be empty",
                    "code": "EMPTY_MESSAGE"
                }, status=400)
            
            if len(message) > self.config['max_message_length']:
                return web.json_response({
                    "error": f"Message too long (max {self.config['max_message_length']} characters)",
                    "code": "MESSAGE_TOO_LONG"
                }, status=400)
            
            # Get or create session
            session = await self.get_or_create_session(session_id, context)
            
            # Process the message
            response = await self.process_chat_message(message, session, context)
            
            # Update session history
            session['messages'].append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'type': 'user',
                'content': message
            })
            session['messages'].append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'type': 'agent',
                'content': response['response']
            })
            session['last_activity'] = datetime.now(timezone.utc)
            
            self.message_count += 1
            
            # Return response
            return web.json_response({
                **response,
                "session_id": session['id'],
                "message_count": len(session['messages'])
            })
            
        except json.JSONDecodeError:
            return web.json_response({
                "error": "Invalid JSON payload",
                "code": "INVALID_JSON"
            }, status=400)
        except Exception as e:
            logger.error(f"Error in chat handler: {e}")
            return web.json_response({
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "details": str(e) if self.config['debug'] else None
            }, status=500)
    
    async def handle_message(self, request: web.Request) -> web.Response:
        """
        Handle generic messages (alternative to chat endpoint).
        
        This endpoint provides a more flexible message processing interface
        that can handle different message types and formats.
        """
        try:
            data = await request.json()
            message_type = data.get('type', 'text')
            content = data.get('content')
            session_id = data.get('session_id')
            metadata = data.get('metadata', {})
            
            if not content:
                return web.json_response({
                    "error": "Content cannot be empty",
                    "code": "EMPTY_CONTENT"
                }, status=400)
            
            # Get or create session
            session = await self.get_or_create_session(session_id)
            
            # Process the message based on type
            result = await self.process_message(message_type, content, session, metadata)
            
            self.message_count += 1
            
            return web.json_response(result)
            
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            return web.json_response({
                "error": "Failed to process message",
                "code": "PROCESSING_ERROR",
                "details": str(e) if self.config['debug'] else None
            }, status=500)
    
    # =============================================================================
    # SESSION MANAGEMENT ENDPOINTS
    # =============================================================================
    
    async def list_sessions(self, request: web.Request) -> web.Response:
        """List all active sessions."""
        sessions = [
            {
                "id": session['id'],
                "created_at": session['created_at'].isoformat(),
                "last_activity": session['last_activity'].isoformat(),
                "message_count": len(session['messages'])
            }
            for session in self.sessions.values()
        ]
        
        return web.json_response({
            "sessions": sessions,
            "total": len(sessions)
        })
    
    async def get_session(self, request: web.Request) -> web.Response:
        """Get detailed information about a specific session."""
        session_id = request.match_info['session_id']
        
        if session_id not in self.sessions:
            return web.json_response({
                "error": "Session not found",
                "code": "SESSION_NOT_FOUND"
            }, status=404)
        
        session = self.sessions[session_id]
        return web.json_response({
            "id": session['id'],
            "created_at": session['created_at'].isoformat(),
            "last_activity": session['last_activity'].isoformat(),
            "context": session['context'],
            "messages": session['messages']
        })
    
    async def delete_session(self, request: web.Request) -> web.Response:
        """Delete a session and its history."""
        session_id = request.match_info['session_id']
        
        if session_id not in self.sessions:
            return web.json_response({
                "error": "Session not found",
                "code": "SESSION_NOT_FOUND"
            }, status=404)
        
        del self.sessions[session_id]
        return web.json_response({
            "message": "Session deleted successfully",
            "session_id": session_id
        })
    
    async def get_status(self, request: web.Request) -> web.Response:
        """Get general server status and information."""
        uptime = (datetime.now(timezone.utc) - self.started_at).total_seconds() if self.started_at else 0
        
        return web.json_response({
            "message": f"🚀 {self.name} is running!",
            "agent": self.name,
            "version": self.version,
            "status": "operational",
            "uptime_seconds": uptime,
            "endpoints": ["/health", "/info", "/chat", "/message", "/sessions"],
            "stats": {
                "sessions_active": len(self.sessions),
                "sessions_total": self.session_count,
                "messages_processed": self.message_count
            }
        })
    
    # =============================================================================
    # CORE PROCESSING METHODS (CUSTOMIZE THESE)
    # =============================================================================
    
    async def process_chat_message(self, message: str, session: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a chat message and generate a response.
        
        This is the main method you should customize for your agent's functionality.
        
        Args:
            message: The user's message
            session: Session data including history
            context: Additional context from the request
            
        Returns:
            Dictionary with response data
        """
        # Default implementation - replace with your agent logic
        response_text = f"Hello! I received your message: '{message}'. I'm a template ACP agent."
        
        # Add some context-aware responses
        if len(session['messages']) > 0:
            response_text += f" This is message #{len(session['messages']) // 2 + 1} in our conversation."
        
        if 'hello' in message.lower():
            response_text = f"Hello! Nice to meet you. I'm {self.name}, running version {self.version}."
        elif 'help' in message.lower():
            response_text = "I'm a template ACP agent. You can chat with me, and I'll respond with helpful information. Try asking about my capabilities!"
        elif 'capabilities' in message.lower() or 'what can you do' in message.lower():
            response_text = "I can process text messages, maintain conversation sessions, provide health monitoring, and serve as a foundation for building custom ACP agents."
        
        return {
            "agent": self.name,
            "version": self.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response": response_text,
            "processed": True,
            "message_id": f"msg_{self.message_count + 1}",
            "processing_time_ms": 50  # Placeholder - measure actual processing time
        }
    
    async def process_message(self, message_type: str, content: Any, session: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process different types of messages.
        
        Args:
            message_type: Type of message (text, file, data, etc.)
            content: Message content
            session: Session data
            metadata: Additional metadata
            
        Returns:
            Processing result
        """
        if message_type == 'text':
            return await self.process_chat_message(str(content), session, metadata)
        elif message_type == 'ping':
            return {
                "type": "pong",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session['id']
            }
        else:
            return {
                "error": f"Unsupported message type: {message_type}",
                "code": "UNSUPPORTED_MESSAGE_TYPE",
                "supported_types": ["text", "ping"]
            }
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    async def get_or_create_session(self, session_id: Optional[str] = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get existing session or create a new one."""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        
        # Create new session
        if not session_id:
            session_id = f"session_{self.session_count + 1}_{int(datetime.now().timestamp())}"
        
        self.session_count += 1
        session = {
            'id': session_id,
            'created_at': datetime.now(timezone.utc),
            'last_activity': datetime.now(timezone.utc),
            'messages': [],
            'context': context or {}
        }
        
        self.sessions[session_id] = session
        return session
    
    async def cleanup_expired_sessions(self):
        """Remove expired sessions based on timeout."""
        now = datetime.now(timezone.utc)
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if (now - session['last_activity']).total_seconds() > self.config['session_timeout']:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
    
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
            logger.error(f"Unhandled error: {e}\n{traceback.format_exc()}")
            return web.json_response({
                "error": "Internal server error",
                "code": "UNHANDLED_ERROR",
                "details": str(e) if self.config['debug'] else None
            }, status=500)
    
    async def logging_middleware(self, request: web.Request, handler):
        """Request logging middleware."""
        start_time = datetime.now()
        response = await handler(request)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds() * 1000
        logger.info(f"{request.method} {request.path} - {response.status} - {duration:.2f}ms")
        
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
    agent = ACPAgentTemplate(
        name=os.getenv("AGENT_NAME", "ACP Agent Template"),
        version=os.getenv("AGENT_VERSION", "1.0.0"),
        description=os.getenv("AGENT_DESCRIPTION", "A template ACP server agent")
    )
    
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
    
    logger.info(f"🚀 {agent.name} server started on {host}:{port}")
    logger.info(f"Health check: http://{host}:{port}/health")
    logger.info(f"Agent info: http://{host}:{port}/info")
    logger.info(f"Chat endpoint: http://{host}:{port}/chat")
    
    # Start background tasks
    async def cleanup_task():
        while True:
            await asyncio.sleep(300)  # Clean up every 5 minutes
            await agent.cleanup_expired_sessions()
    
    cleanup_task_handle = asyncio.create_task(cleanup_task())
    
    # Keep the server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        cleanup_task_handle.cancel()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 