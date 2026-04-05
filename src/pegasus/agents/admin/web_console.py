"""
Claude Agent Communication System - Web Administration Console
============================================================

Real-time web-based administration interface for managing the distributed
Claude agent system. Provides comprehensive dashboards, monitoring, and
management capabilities for all 28 agent types.

Features:
- Real-time system dashboards with live metrics
- Agent lifecycle management interface
- Configuration management with hot-reload
- User and role management
- Performance monitoring and optimization
- Diagnostic tools and troubleshooting
- Backup and restore operations
- WebSocket-based real-time updates

Technology Stack:
- FastAPI backend with WebSocket support
- Vue.js 3 frontend with real-time charts
- Socket.IO for real-time communication
- Prometheus integration for metrics
- JWT authentication and RBAC

Author: Claude Agent Administration System
Version: 1.0.0 Production
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Authentication and security
import jwt
import prometheus_client

# WebSocket and real-time imports
import socketio
import uvicorn

# Local imports
from admin_core import (
    AgentManager,
    BackupManager,
    ConfigManager,
    DeploymentManager,
    DiagnosticTools,
    OperationResult,
    PerformanceOptimizer,
    SystemMonitor,
    UserManager,
)

# FastAPI and web framework imports
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext

# Prometheus and metrics
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from socketio import AsyncServer
from starlette.requests import Request

# ============================================================================
# CONFIGURATION AND CONSTANTS
# ============================================================================

# Web server configuration
WEB_CONFIG = {
    "host": "0.0.0.0",
    "port": 8080,
    "static_dir": "/var/lib/claude-agents/web/static",
    "template_dir": "/var/lib/claude-agents/web/templates",
    "upload_dir": "/var/lib/claude-agents/web/uploads",
}

# WebSocket event types
WEBSOCKET_EVENTS = {
    "SYSTEM_STATUS": "system_status",
    "AGENT_STATUS": "agent_status",
    "PERFORMANCE_METRICS": "performance_metrics",
    "ALERT": "alert",
    "LOG_MESSAGE": "log_message",
    "CONFIG_CHANGE": "config_change",
    "DEPLOYMENT_UPDATE": "deployment_update",
}

# API rate limiting
API_RATE_LIMITS = {
    "default": 100,  # requests per minute
    "metrics": 300,
    "status": 200,
    "config_change": 30,
}

# ============================================================================
# MAIN WEB APPLICATION CLASS
# ============================================================================


class ClaudeWebConsole:
    """Main web administration console"""

    __slots__ = []

    def __init__(self):
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Claude Agent Administration Console",
            description="Web-based administration interface for Claude Agent Communication System",
            version="1.0.0",
        )

        # Initialize Socket.IO server
        self.sio = AsyncServer(
            async_mode="asgi",
            cors_allowed_origins="*",
            logger=True,
            engineio_logger=True,
        )

        # Initialize core managers
        self.agent_manager = AgentManager()
        self.system_monitor = SystemMonitor()
        self.config_manager = ConfigManager()
        self.user_manager = UserManager()
        self.deployment_manager = DeploymentManager()
        self.backup_manager = BackupManager()
        self.diagnostic_tools = DiagnosticTools()
        self.performance_optimizer = PerformanceOptimizer()

        # WebSocket connection management
        self.connected_clients: Set[str] = set()
        self.client_subscriptions: Dict[str, Set[str]] = {}

        # Authentication
        self.security = HTTPBearer()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Initialize web application
        self._setup_middleware()
        self._setup_routes()
        self._setup_websocket_handlers()
        self._setup_static_files()
        self._start_background_tasks()

    def _setup_middleware(self):
        """Setup FastAPI middleware"""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Custom middleware for request logging
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time

            logging.info(
                f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
            )
            response.headers["X-Process-Time"] = str(process_time)
            return response

    def _setup_routes(self):
        """Setup API routes"""

        # ============== AUTHENTICATION ROUTES ==============

        @self.app.post("/api/auth/login")
        async def login(credentials: dict):
            """Authenticate user and return JWT token"""
            username = credentials.get("username")
            password = credentials.get("password")

            if not username or not password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username and password required",
                )

            token = self.user_manager.authenticate_user(username, password)
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                )

            return {"token": token, "type": "bearer"}

        @self.app.post("/api/auth/logout")
        async def logout(
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """Logout user and invalidate token"""
            # Token invalidation would be implemented here
            return {"message": "Logged out successfully"}

        # ============== SYSTEM STATUS ROUTES ==============

        @self.app.get("/api/system/status")
        async def get_system_status(user=Depends(self._get_current_user)):
            """Get overall system status"""
            try:
                status = self.system_monitor.get_system_status()
                return {
                    "status": "success",
                    "data": {
                        "cluster_state": status.cluster_state,
                        "active_nodes": status.active_nodes,
                        "total_agents": status.total_agents,
                        "active_agents": status.active_agents,
                        "failed_agents": status.failed_agents,
                        "total_throughput": status.total_throughput,
                        "avg_latency_ns": status.avg_latency_ns,
                        "cpu_utilization": status.cpu_utilization,
                        "memory_utilization": status.memory_utilization,
                        "disk_utilization": status.disk_utilization,
                        "network_utilization": status.network_utilization,
                        "uptime": str(status.uptime),
                    },
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/system/performance")
        async def get_performance_metrics(user=Depends(self._get_current_user)):
            """Get detailed performance metrics"""
            try:
                metrics = self.system_monitor.get_performance_metrics()
                return {
                    "status": "success",
                    "data": {
                        "timestamp": metrics.timestamp.isoformat(),
                        "throughput": metrics.throughput,
                        "latency_p50_ns": metrics.latency_p50_ns,
                        "latency_p95_ns": metrics.latency_p95_ns,
                        "latency_p99_ns": metrics.latency_p99_ns,
                        "cpu_utilization": metrics.cpu_utilization,
                        "memory_utilization": metrics.memory_utilization,
                        "network_utilization": metrics.network_utilization,
                        "active_connections": metrics.active_connections,
                        "queue_depth": metrics.queue_depth,
                        "error_rate": metrics.error_rate,
                        "processing_rate": metrics.processing_rate,
                    },
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ============== AGENT MANAGEMENT ROUTES ==============

        @self.app.get("/api/agents")
        async def get_agents(user=Depends(self._get_current_user)):
            """Get all agent statuses"""
            try:
                agents = self.agent_manager.get_all_agent_status()
                return {
                    "status": "success",
                    "data": [
                        {
                            "name": agent.name,
                            "type": agent.type,
                            "state": agent.state,
                            "pid": agent.pid,
                            "port": agent.port,
                            "node_id": agent.node_id,
                            "cpu_percent": agent.resource_usage.get("cpu", 0.0),
                            "memory_mb": agent.resource_usage.get("memory", 0.0),
                            "uptime": str(datetime.now() - agent.startup_time),
                            "health_score": agent.health_score,
                            "version": agent.version,
                        }
                        for agent in agents
                    ],
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/agents/{agent_type}/start")
        async def start_agent(
            agent_type: str, config: dict = None, user=Depends(self._get_admin_user)
        ):
            """Start agent instances"""
            try:
                scale = config.get("scale", 1) if config else 1
                result = self.agent_manager.start_agent(agent_type, scale=scale)

                if result.success:
                    # Broadcast update to connected clients
                    await self._broadcast_agent_update(agent_type, "started")

                    return {
                        "status": "success",
                        "message": f"Started {agent_type} agent",
                        "data": result.data,
                    }
                else:
                    raise HTTPException(status_code=500, detail=result.error)

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/agents/{agent_name}/stop")
        async def stop_agent(agent_name: str, user=Depends(self._get_admin_user)):
            """Stop agent instance"""
            try:
                result = self.agent_manager.stop_agent(agent_name)

                if result.success:
                    await self._broadcast_agent_update(agent_name, "stopped")
                    return {
                        "status": "success",
                        "message": f"Stopped {agent_name} agent",
                    }
                else:
                    raise HTTPException(status_code=500, detail=result.error)

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/agents/{agent_name}/restart")
        async def restart_agent(agent_name: str, user=Depends(self._get_admin_user)):
            """Restart agent instance"""
            try:
                result = self.agent_manager.restart_agent(
                    agent_name, zero_downtime=True
                )

                if result.success:
                    await self._broadcast_agent_update(agent_name, "restarted")
                    return {
                        "status": "success",
                        "message": f"Restarted {agent_name} agent",
                        "data": {"downtime_ms": result.metadata.get("downtime_ms", 0)},
                    }
                else:
                    raise HTTPException(status_code=500, detail=result.error)

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ============== CONFIGURATION ROUTES ==============

        @self.app.get("/api/config/{component}")
        async def get_config(component: str, user=Depends(self._get_current_user)):
            """Get configuration for component"""
            try:
                config = self.config_manager.get_config(component)
                return {"status": "success", "data": config}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/config/{component}")
        async def update_config(
            component: str, config_update: dict, user=Depends(self._get_admin_user)
        ):
            """Update configuration with hot reload"""
            try:
                key = config_update.get("key")
                value = config_update.get("value")
                hot_reload = config_update.get("hot_reload", True)

                if not key:
                    raise HTTPException(
                        status_code=400, detail="Configuration key required"
                    )

                result = self.config_manager.set_config_value(
                    component, key, value, hot_reload
                )

                if result.success:
                    await self._broadcast_config_change(component, key, value)
                    return {
                        "status": "success",
                        "message": "Configuration updated",
                        "data": result.data,
                    }
                else:
                    raise HTTPException(status_code=500, detail=result.error)

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ============== USER MANAGEMENT ROUTES ==============

        @self.app.get("/api/users")
        async def get_users(user=Depends(self._get_admin_user)):
            """Get all users"""
            try:
                users = self.user_manager.list_users()
                return {
                    "status": "success",
                    "data": [
                        {
                            "username": u.username,
                            "role": u.role,
                            "email": u.email,
                            "is_active": u.is_active,
                            "created_at": (
                                u.created_at.isoformat() if u.created_at else None
                            ),
                            "last_login": (
                                u.last_login.isoformat() if u.last_login else None
                            ),
                            "permissions": u.permissions,
                        }
                        for u in users
                    ],
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/users")
        async def create_user(user_data: dict, user=Depends(self._get_admin_user)):
            """Create new user"""
            try:
                result = self.user_manager.create_user(
                    username=user_data.get("username"),
                    role=user_data.get("role"),
                    permissions=user_data.get("permissions", []),
                    email=user_data.get("email"),
                )

                if result.success:
                    return {
                        "status": "success",
                        "message": "User created successfully",
                        "data": result.data,
                    }
                else:
                    raise HTTPException(status_code=400, detail=result.error)

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ============== PROMETHEUS METRICS ROUTE ==============

        @self.app.get("/metrics")
        async def prometheus_metrics():
            """Prometheus metrics endpoint"""
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

        # ============== MAIN DASHBOARD ROUTE ==============

        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Main dashboard page"""
            return self.templates.TemplateResponse(
                "dashboard.html", {"request": request}
            )

    def _setup_websocket_handlers(self):
        """Setup WebSocket event handlers"""

        @self.sio.event
        async def connect(sid, environ, auth):
            """Handle client connection"""
            try:
                # Authenticate WebSocket connection
                token = auth.get("token") if auth else None
                if token:
                    user = self._verify_jwt_token(token)
                    if user:
                        self.connected_clients.add(sid)
                        self.client_subscriptions[sid] = set()
                        logging.info(
                            f"WebSocket client {sid} connected (user: {user['username']})"
                        )
                        return True

                logging.warning(f"WebSocket connection rejected for {sid}")
                return False

            except Exception as e:
                logging.error(f"WebSocket connection error: {e}")
                return False

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection"""
            self.connected_clients.discard(sid)
            self.client_subscriptions.pop(sid, None)
            logging.info(f"WebSocket client {sid} disconnected")

        @self.sio.event
        async def subscribe(sid, data):
            """Handle subscription to specific data streams"""
            try:
                subscription_type = data.get("type")
                if subscription_type and sid in self.connected_clients:
                    self.client_subscriptions[sid].add(subscription_type)
                    await self.sio.emit(
                        "subscribed",
                        {"type": subscription_type, "status": "success"},
                        room=sid,
                    )

            except Exception as e:
                await self.sio.emit("error", {"message": str(e)}, room=sid)

        @self.sio.event
        async def unsubscribe(sid, data):
            """Handle unsubscription from data streams"""
            try:
                subscription_type = data.get("type")
                if subscription_type and sid in self.client_subscriptions:
                    self.client_subscriptions[sid].discard(subscription_type)
                    await self.sio.emit(
                        "unsubscribed",
                        {"type": subscription_type, "status": "success"},
                        room=sid,
                    )

            except Exception as e:
                await self.sio.emit("error", {"message": str(e)}, room=sid)

    def _setup_static_files(self):
        """Setup static file serving"""
        # Create directories if they don't exist
        os.makedirs(WEB_CONFIG["static_dir"], exist_ok=True)
        os.makedirs(WEB_CONFIG["template_dir"], exist_ok=True)

        # Mount static files
        self.app.mount(
            "/static", StaticFiles(directory=WEB_CONFIG["static_dir"]), name="static"
        )

        # Setup templates
        self.templates = Jinja2Templates(directory=WEB_CONFIG["template_dir"])

        # Generate default templates if they don't exist
        self._create_default_templates()

    def _start_background_tasks(self):
        """Start background tasks for real-time updates"""
        asyncio.create_task(self._system_metrics_broadcaster())
        asyncio.create_task(self._agent_status_broadcaster())
        asyncio.create_task(self._performance_broadcaster())
        asyncio.create_task(self._log_broadcaster())

    async def _system_metrics_broadcaster(self):
        """Broadcast system metrics to subscribed clients"""
        while True:
            try:
                if self.connected_clients:
                    status = self.system_monitor.get_system_status()

                    await self._broadcast_to_subscribers(
                        "system_status",
                        {
                            "timestamp": datetime.now().isoformat(),
                            "cluster_state": status.cluster_state,
                            "active_nodes": status.active_nodes,
                            "total_agents": status.total_agents,
                            "active_agents": status.active_agents,
                            "failed_agents": status.failed_agents,
                            "cpu_utilization": status.cpu_utilization,
                            "memory_utilization": status.memory_utilization,
                            "disk_utilization": status.disk_utilization,
                            "network_utilization": status.network_utilization,
                        },
                    )

                await asyncio.sleep(5)  # Update every 5 seconds

            except Exception as e:
                logging.error(f"System metrics broadcast error: {e}")
                await asyncio.sleep(10)

    async def _performance_broadcaster(self):
        """Broadcast performance metrics to subscribed clients"""
        while True:
            try:
                if self.connected_clients:
                    metrics = self.system_monitor.get_performance_metrics()

                    await self._broadcast_to_subscribers(
                        "performance_metrics",
                        {
                            "timestamp": metrics.timestamp.isoformat(),
                            "throughput": metrics.throughput,
                            "latency_p99_ns": metrics.latency_p99_ns,
                            "error_rate": metrics.error_rate,
                            "queue_depth": metrics.queue_depth,
                            "processing_rate": metrics.processing_rate,
                        },
                    )

                await asyncio.sleep(2)  # Update every 2 seconds

            except Exception as e:
                logging.error(f"Performance broadcast error: {e}")
                await asyncio.sleep(5)

    async def _broadcast_to_subscribers(self, event_type: str, data: dict):
        """Broadcast data to clients subscribed to specific event type"""
        for sid in self.connected_clients:
            if event_type in self.client_subscriptions.get(sid, set()):
                await self.sio.emit(event_type, data, room=sid)

    async def _broadcast_agent_update(self, agent_name: str, action: str):
        """Broadcast agent status update"""
        await self._broadcast_to_subscribers(
            "agent_update",
            {
                "agent_name": agent_name,
                "action": action,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def _broadcast_config_change(self, component: str, key: str, value: Any):
        """Broadcast configuration change"""
        await self._broadcast_to_subscribers(
            "config_change",
            {
                "component": component,
                "key": key,
                "value": value,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def _get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
    ):
        """Get current authenticated user"""
        try:
            token = credentials.credentials
            payload = self._verify_jwt_token(token)
            if payload:
                return payload
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

    def _get_admin_user(self, user=Depends(_get_current_user)):
        """Get current user and ensure admin role"""
        if user.get("role") not in ["admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
            )
        return user

    def _verify_jwt_token(self, token: str) -> Optional[dict]:
        """Verify JWT token and return user payload"""
        try:
            payload = jwt.decode(
                token, self.user_manager.secret_key, algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def _create_default_templates(self):
        """Create default HTML templates"""
        dashboard_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Agent Administration Console</title>
    <link href="/static/css/dashboard.css" rel="stylesheet">
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div id="app">
        <header class="header">
            <h1>Claude Agent Communication System</h1>
            <div class="status-bar">
                <span class="status-item">Throughput: {{ systemStatus.total_throughput | number }} msg/s</span>
                <span class="status-item">Latency: {{ (systemStatus.avg_latency_ns / 1000) | number(1) }}μs</span>
                <span class="status-item">Active Agents: {{ systemStatus.active_agents }}/{{ systemStatus.total_agents }}</span>
            </div>
        </header>

        <main class="main-content">
            <div class="dashboard-grid">
                <!-- System Overview Panel -->
                <div class="panel">
                    <h2>System Overview</h2>
                    <div class="metrics-grid">
                        <div class="metric">
                            <span class="metric-label">Cluster State</span>
                            <span class="metric-value" :class="systemStatus.cluster_state.toLowerCase()">
                                {{ systemStatus.cluster_state }}
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">CPU Usage</span>
                            <span class="metric-value">{{ (systemStatus.cpu_utilization * 100) | number(1) }}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Memory Usage</span>
                            <span class="metric-value">{{ (systemStatus.memory_utilization * 100) | number(1) }}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Network Usage</span>
                            <span class="metric-value">{{ (systemStatus.network_utilization * 100) | number(1) }}%</span>
                        </div>
                    </div>
                </div>

                <!-- Performance Metrics Panel -->
                <div class="panel">
                    <h2>Performance Metrics</h2>
                    <canvas id="performanceChart" width="400" height="200"></canvas>
                </div>

                <!-- Agent Status Panel -->
                <div class="panel full-width">
                    <h2>Agent Status</h2>
                    <div class="agent-grid">
                        <div v-for="agent in agents" :key="agent.name" class="agent-card" :class="agent.state.toLowerCase()">
                            <div class="agent-header">
                                <h3>{{ agent.name }}</h3>
                                <span class="agent-state">{{ agent.state }}</span>
                            </div>
                            <div class="agent-metrics">
                                <span>CPU: {{ agent.cpu_percent | number(1) }}%</span>
                                <span>Memory: {{ agent.memory_mb | number(0) }}MB</span>
                                <span>Health: {{ (agent.health_score * 100) | number(0) }}%</span>
                            </div>
                            <div class="agent-actions">
                                <button @click="restartAgent(agent.name)" class="btn-restart">Restart</button>
                                <button @click="stopAgent(agent.name)" class="btn-stop">Stop</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script src="/static/js/dashboard.js"></script>
</body>
</html>
        """

        template_path = Path(WEB_CONFIG["template_dir"]) / "dashboard.html"
        if not template_path.exists():
            with open(template_path, "w") as f:
                f.write(dashboard_template)

    def run(self):
        """Run the web console"""
        # Combine FastAPI and Socket.IO
        combined_app = socketio.ASGIApp(self.sio, self.app)

        logging.info("Starting Claude Agent Web Administration Console")
        logging.info(
            f"Dashboard available at http://{WEB_CONFIG['host']}:{WEB_CONFIG['port']}"
        )

        uvicorn.run(
            combined_app,
            host=WEB_CONFIG["host"],
            port=WEB_CONFIG["port"],
            log_level="info",
        )


# ============================================================================
# STATIC ASSETS GENERATOR
# ============================================================================


def generate_static_assets():
    """Generate CSS and JavaScript assets"""

    # Dashboard CSS
    dashboard_css = """
/* Claude Agent Administration Console Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #1a1a1a;
    color: #ffffff;
    line-height: 1.6;
}

.header {
    background: linear-gradient(135deg, #2c3e50, #3498db);
    padding: 1rem 2rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.header h1 {
    color: white;
    font-size: 1.8rem;
    font-weight: 300;
}

.status-bar {
    display: flex;
    gap: 2rem;
}

.status-item {
    background: rgba(255,255,255,0.1);
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.9rem;
    backdrop-filter: blur(10px);
}

.main-content {
    padding: 2rem;
    max-width: 1400px;
    margin: 0 auto;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    margin-bottom: 2rem;
}

.panel {
    background: #2c2c2c;
    border-radius: 10px;
    padding: 1.5rem;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    border: 1px solid #404040;
}

.panel.full-width {
    grid-column: 1 / -1;
}

.panel h2 {
    color: #3498db;
    margin-bottom: 1rem;
    font-weight: 300;
    font-size: 1.4rem;
}

.metrics-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

.metric {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 1rem;
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    border: 1px solid #404040;
}

.metric-label {
    font-size: 0.9rem;
    color: #bbb;
    margin-bottom: 0.5rem;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: bold;
    color: #fff;
}

.metric-value.healthy {
    color: #27ae60;
}

.metric-value.warning {
    color: #f39c12;
}

.metric-value.critical {
    color: #e74c3c;
}

.agent-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
}

.agent-card {
    background: #383838;
    border-radius: 8px;
    padding: 1rem;
    border-left: 4px solid #3498db;
    transition: transform 0.2s ease;
}

.agent-card:hover {
    transform: translateY(-2px);
}

.agent-card.active {
    border-left-color: #27ae60;
}

.agent-card.degraded {
    border-left-color: #f39c12;
}

.agent-card.failed {
    border-left-color: #e74c3c;
}

.agent-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.agent-header h3 {
    font-size: 1.1rem;
    font-weight: 500;
}

.agent-state {
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.8rem;
    text-transform: uppercase;
    font-weight: bold;
}

.agent-metrics {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    color: #ccc;
}

.agent-actions {
    display: flex;
    gap: 0.5rem;
}

.btn-restart, .btn-stop {
    padding: 0.4rem 0.8rem;
    border: none;
    border-radius: 4px;
    font-size: 0.8rem;
    cursor: pointer;
    transition: background-color 0.2s ease;
}

.btn-restart {
    background-color: #3498db;
    color: white;
}

.btn-restart:hover {
    background-color: #2980b9;
}

.btn-stop {
    background-color: #e74c3c;
    color: white;
}

.btn-stop:hover {
    background-color: #c0392b;
}

/* Responsive design */
@media (max-width: 768px) {
    .dashboard-grid {
        grid-template-columns: 1fr;
    }
    
    .status-bar {
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .agent-metrics {
        flex-direction: column;
        gap: 0.2rem;
    }
}
"""

    # Dashboard JavaScript
    dashboard_js = """
// Claude Agent Administration Console Frontend
const { createApp } = Vue;

createApp({
    data() {
        return {
            systemStatus: {
                cluster_state: 'LOADING',
                active_nodes: 0,
                total_agents: 0,
                active_agents: 0,
                failed_agents: 0,
                total_throughput: 0,
                avg_latency_ns: 0,
                cpu_utilization: 0,
                memory_utilization: 0,
                disk_utilization: 0,
                network_utilization: 0
            },
            agents: [],
            performanceChart: null,
            socket: null,
            authenticated: false
        }
    },
    
    mounted() {
        this.initializeWebSocket();
        this.fetchInitialData();
        this.initializePerformanceChart();
    },
    
    methods: {
        initializeWebSocket() {
            // Get JWT token from localStorage or prompt for login
            const token = localStorage.getItem('auth_token');
            if (!token) {
                this.showLoginDialog();
                return;
            }
            
            // Initialize Socket.IO connection
            this.socket = io({
                auth: {
                    token: token
                }
            });
            
            // Handle connection events
            this.socket.on('connect', () => {
                console.log('Connected to WebSocket');
                this.authenticated = true;
                
                // Subscribe to data streams
                this.socket.emit('subscribe', { type: 'system_status' });
                this.socket.emit('subscribe', { type: 'agent_status' });
                this.socket.emit('subscribe', { type: 'performance_metrics' });
            });
            
            this.socket.on('disconnect', () => {
                console.log('Disconnected from WebSocket');
                this.authenticated = false;
            });
            
            // Handle real-time data updates
            this.socket.on('system_status', (data) => {
                this.systemStatus = data;
            });
            
            this.socket.on('agent_update', (data) => {
                this.fetchAgentStatus();
            });
            
            this.socket.on('performance_metrics', (data) => {
                this.updatePerformanceChart(data);
            });
        },
        
        async fetchInitialData() {
            try {
                // Fetch system status
                const statusResponse = await this.apiCall('/api/system/status');
                if (statusResponse.status === 'success') {
                    this.systemStatus = statusResponse.data;
                }
                
                // Fetch agent status
                await this.fetchAgentStatus();
                
            } catch (error) {
                console.error('Error fetching initial data:', error);
            }
        },
        
        async fetchAgentStatus() {
            try {
                const response = await this.apiCall('/api/agents');
                if (response.status === 'success') {
                    this.agents = response.data;
                }
            } catch (error) {
                console.error('Error fetching agent status:', error);
            }
        },
        
        async restartAgent(agentName) {
            if (!confirm(`Are you sure you want to restart ${agentName}?`)) {
                return;
            }
            
            try {
                const response = await this.apiCall(`/api/agents/${agentName}/restart`, 'POST');
                if (response.status === 'success') {
                    this.showNotification(`${agentName} restarted successfully`, 'success');
                } else {
                    this.showNotification(`Failed to restart ${agentName}`, 'error');
                }
            } catch (error) {
                this.showNotification(`Error restarting ${agentName}: ${error.message}`, 'error');
            }
        },
        
        async stopAgent(agentName) {
            if (!confirm(`Are you sure you want to stop ${agentName}?`)) {
                return;
            }
            
            try {
                const response = await this.apiCall(`/api/agents/${agentName}/stop`, 'POST');
                if (response.status === 'success') {
                    this.showNotification(`${agentName} stopped successfully`, 'success');
                } else {
                    this.showNotification(`Failed to stop ${agentName}`, 'error');
                }
            } catch (error) {
                this.showNotification(`Error stopping ${agentName}: ${error.message}`, 'error');
            }
        },
        
        async apiCall(url, method = 'GET', data = null) {
            const token = localStorage.getItem('auth_token');
            
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            };
            
            if (data) {
                options.body = JSON.stringify(data);
            }
            
            const response = await fetch(url, options);
            
            if (response.status === 401) {
                this.showLoginDialog();
                throw new Error('Authentication required');
            }
            
            return await response.json();
        },
        
        initializePerformanceChart() {
            const ctx = document.getElementById('performanceChart').getContext('2d');
            
            this.performanceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Throughput (msg/s)',
                        data: [],
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        yAxisID: 'y'
                    }, {
                        label: 'Latency P99 (μs)',
                        data: [],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#ffffff'
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#ffffff'
                            },
                            grid: {
                                color: '#404040'
                            }
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            ticks: {
                                color: '#3498db'
                            },
                            grid: {
                                color: '#404040'
                            }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            ticks: {
                                color: '#e74c3c'
                            },
                            grid: {
                                drawOnChartArea: false,
                                color: '#404040'
                            }
                        }
                    }
                }
            });
        },
        
        updatePerformanceChart(data) {
            if (!this.performanceChart) return;
            
            const chart = this.performanceChart;
            const maxPoints = 20;
            
            // Add new data point
            chart.data.labels.push(new Date(data.timestamp).toLocaleTimeString());
            chart.data.datasets[0].data.push(data.throughput);
            chart.data.datasets[1].data.push(data.latency_p99_ns / 1000); // Convert to μs
            
            // Remove old data points
            if (chart.data.labels.length > maxPoints) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
                chart.data.datasets[1].data.shift();
            }
            
            chart.update('none');
        },
        
        showNotification(message, type = 'info') {
            // Create notification element
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.textContent = message;
            
            // Style the notification
            Object.assign(notification.style, {
                position: 'fixed',
                top: '20px',
                right: '20px',
                padding: '1rem 1.5rem',
                borderRadius: '8px',
                color: 'white',
                zIndex: '1000',
                opacity: '0',
                transition: 'opacity 0.3s ease',
                backgroundColor: type === 'success' ? '#27ae60' : type === 'error' ? '#e74c3c' : '#3498db'
            });
            
            document.body.appendChild(notification);
            
            // Show notification
            setTimeout(() => {
                notification.style.opacity = '1';
            }, 100);
            
            // Hide and remove notification
            setTimeout(() => {
                notification.style.opacity = '0';
                setTimeout(() => {
                    document.body.removeChild(notification);
                }, 300);
            }, 4000);
        },
        
        showLoginDialog() {
            const username = prompt('Username:');
            const password = prompt('Password:');
            
            if (username && password) {
                this.login(username, password);
            }
        },
        
        async login(username, password) {
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ username, password })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    localStorage.setItem('auth_token', data.token);
                    this.initializeWebSocket();
                } else {
                    alert('Login failed: ' + data.detail);
                }
            } catch (error) {
                alert('Login error: ' + error.message);
            }
        }
    },
    
    filters: {
        number(value, decimals = 0) {
            if (typeof value !== 'number') return value;
            return value.toFixed(decimals);
        }
    }
}).mount('#app');
"""

    # Create static asset directories and files
    css_dir = Path(WEB_CONFIG["static_dir"]) / "css"
    js_dir = Path(WEB_CONFIG["static_dir"]) / "js"

    css_dir.mkdir(parents=True, exist_ok=True)
    js_dir.mkdir(parents=True, exist_ok=True)

    # Write CSS file
    with open(css_dir / "dashboard.css", "w") as f:
        f.write(dashboard_css)

    # Write JavaScript file
    with open(js_dir / "dashboard.js", "w") as f:
        f.write(dashboard_js)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main():
    """Main entry point for web console"""
    # Generate static assets
    generate_static_assets()

    # Create and run web console
    console = ClaudeWebConsole()
    console.run()


if __name__ == "__main__":
    main()
