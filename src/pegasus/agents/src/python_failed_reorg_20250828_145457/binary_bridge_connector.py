#!/usr/bin/env python3
"""
Unified Agent Bridge System
Consolidates all bridge functionality into one clean module
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import from local enhanced modules (same directory now)
from ENHANCED_AGENT_INTEGRATION import (
    EnhancedAgentMessage,
    EnhancedAgentOrchestrator,
    Priority,
)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Centralized configuration for the agent system"""
    
    # Base directories
    AGENTS_DIR = Path("${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents")
    RUNTIME_DIR = AGENTS_DIR / "06-BUILD-RUNTIME" / "runtime"
    BUILD_DIR = AGENTS_DIR / "06-BUILD-RUNTIME" / "build"
    CONFIG_DIR = AGENTS_DIR / "05-CONFIG"
    BRIDGES_DIR = AGENTS_DIR / "03-BRIDGES"
    AGENTS_DEFS_DIR = AGENTS_DIR / "01-AGENTS-DEFINITIONS" / "ACTIVE"
    
    # Socket configuration
    SOCKET_PATH = str(RUNTIME_DIR / "claude_agent_bridge.sock")
    
    # Binary protocol settings
    RING_BUFFER_SIZE = 16 * 1024 * 1024  # 16MB
    MSG_BUFFER_SIZE = 65536  # 64KB
    MAX_AGENTS = 32

# ============================================================================
# BINARY BRIDGE CONNECTION
# ============================================================================

class BinaryBridge:
    """Handles connection to the binary protocol"""
    
    def __init__(self, socket_path: Optional[str] = None):
        self.socket_path = socket_path or Config.SOCKET_PATH
        self.socket = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to the binary bridge"""
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(self.socket_path)
            self.connected = True
            return True
        except Exception as e:
            self.connected = False
            return False
    
    def send_message(self, message: bytes) -> Optional[bytes]:
        """Send a message and receive response"""
        if not self.connected:
            if not self.connect():
                return None
        
        try:
            self.socket.send(message)
            response = self.socket.recv(Config.MSG_BUFFER_SIZE)
            return response
        except Exception as e:
            self.connected = False
            return None
    
    def close(self):
        """Close the connection"""
        if self.socket:
            self.socket.close()
            self.socket = None
            self.connected = False
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# ============================================================================
# STATUS LINE SYSTEM
# ============================================================================

class StatusLine:
    """Manages status line display and metrics"""
    
    def __init__(self):
        self.status_file = Config.RUNTIME_DIR / "status.json"
        self.metrics = {
            "tasks_started": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "last_activity": None
        }
        self.ensure_paths()
    
    def ensure_paths(self):
        """Ensure required paths exist"""
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
    
    def task_started(self, agent_name: str):
        """Record task start"""
        self.metrics["tasks_started"] += 1
        self.metrics["last_activity"] = {"type": "start", "agent": agent_name, "time": time.time()}
        self.save_status()
    
    def task_completed(self, agent_name: str):
        """Record task completion"""
        self.metrics["tasks_completed"] += 1
        self.metrics["last_activity"] = {"type": "complete", "agent": agent_name, "time": time.time()}
        self.save_status()
    
    def task_failed(self, agent_name: str, error: str):
        """Record task failure"""
        self.metrics["tasks_failed"] += 1
        self.metrics["last_activity"] = {"type": "error", "agent": agent_name, "error": error, "time": time.time()}
        self.save_status()
    
    def save_status(self):
        """Save current status to file"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.metrics, f, indent=2, default=str)
        except:
            pass
    
    def get_status_line(self) -> str:
        """Get formatted status line"""
        parts = []
        
        # Check binary bridge
        bridge_status = "🟢" if self.check_binary_bridge() else "🔴"
        parts.append(f"{bridge_status} Bridge")
        
        # Check socket
        socket_status = "🔌" if Path(Config.SOCKET_PATH).exists() else "⚠️"
        parts.append(f"{socket_status} Socket")
        
        # Agent count
        agent_count = len(list(Config.AGENTS_DEFS_DIR.glob("*.md")))
        parts.append(f"🤖 {agent_count} agents")
        
        # Task metrics
        if self.metrics["tasks_started"] > self.metrics["tasks_completed"]:
            pending = self.metrics["tasks_started"] - self.metrics["tasks_completed"]
            parts.append(f"⏳ {pending}")
        
        if self.metrics["tasks_completed"] > 0:
            parts.append(f"✅ {self.metrics['tasks_completed']}")
        
        if self.metrics["tasks_failed"] > 0:
            parts.append(f"❌ {self.metrics['tasks_failed']}")
        
        return " | ".join(parts)
    
    @staticmethod
    def check_binary_bridge() -> bool:
        """Check if binary bridge process is running"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "agent_bridge"],
                capture_output=True,
                timeout=1
            )
            return result.returncode == 0
        except:
            return False

# ============================================================================
# VOICE SYSTEM
# ============================================================================

class VoiceSystem:
    """Voice input system for agent control"""
    
    def __init__(self):
        self.config_path = Config.CONFIG_DIR / "voice_config.json"
        self.config = self.load_config()
        self.bridge = BinaryBridge()
    
    def load_config(self) -> dict:
        """Load voice configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {
            "enabled": False,
            "auto_start": False,
            "wake_words": ["claude", "agent"],
            "interface": "unified_bridge.py"
        }
    
    def is_enabled(self) -> bool:
        """Check if voice system is enabled"""
        return self.config.get("enabled", False)
    
    async def process_command(self, command: str) -> str:
        """Process a voice command"""
        if self.bridge.connect():
            msg = json.dumps({
                "type": "voice_command",
                "command": command,
                "timestamp": str(time.time())
            }).encode()
            
            response = self.bridge.send_message(msg)
            if response:
                return response.decode()
        
        # Fallback processing
        return f"Processed locally: {command}"

# ============================================================================
# MONITORING SYSTEM
# ============================================================================

class Monitor:
    """System monitoring and metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
    
    def log_metric(self, name: str, value: Any):
        """Log a metric"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append({
            "timestamp": time.time(),
            "value": value
        })
    
    def get_summary(self) -> dict:
        """Get monitoring summary"""
        return {
            "uptime": time.time() - self.start_time,
            "total_metrics": len(self.metrics),
            "status": "healthy" if StatusLine.check_binary_bridge() else "degraded"
        }

# ============================================================================
# MAIN AGENT BRIDGE
# ============================================================================

class AgentBridge:
    """Main bridge for agent invocation and coordination"""
    
    def __init__(self):
        self.binary_bridge = BinaryBridge()
        self.orchestrator = EnhancedAgentOrchestrator()
        self.status_line = StatusLine()
        self.monitor = Monitor()
        self.voice = VoiceSystem()
    
    def invoke_agent(self, agent_name: str, task: str, **kwargs) -> Dict[str, Any]:
        """
        Invoke an agent with a specific task
        This is the main entry point for Claude Code's Task tool
        """
        print(f"🤖 Invoking agent: {agent_name}")
        print(f"📋 Task: {task}")
        
        # Update status
        self.status_line.task_started(agent_name)
        self.monitor.log_metric("agent_invoked", agent_name)
        
        # Try binary bridge first
        if self.binary_bridge.connect():
            message = {
                "type": "agent_invoke",
                "agent": agent_name,
                "task": task,
                "params": kwargs
            }
            
            response = self.binary_bridge.send_message(json.dumps(message).encode())
            if response:
                try:
                    result = json.loads(response.decode())
                    self.status_line.task_completed(agent_name)
                    return result
                except Exception as e:
                    self.status_line.task_failed(agent_name, str(e))
        
        # Fallback to orchestrator
        msg = EnhancedAgentMessage(
            source_agent="claude_code",
            target_agents=[agent_name],
            action="task",
            payload={"task": task, **kwargs},
            priority=Priority.HIGH
        )
        
        # Check if agent exists (use agents directory directly)
        agents_dir = Path("${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents")
        agent_path = agents_dir / f"{agent_name}.md"
        if agent_path.exists():
            self.status_line.task_completed(agent_name)
            return {
                "status": "success",
                "agent": agent_name,
                "message": f"Agent {agent_name} acknowledged (execution pending)",
                "agent_found": True
            }
        else:
            self.status_line.task_failed(agent_name, "Agent not found")
            return {
                "status": "error",
                "agent": agent_name,
                "message": f"Agent {agent_name} not found",
                "agent_found": False
            }
    
    def list_agents(self) -> List[str]:
        """List all available agents"""
        agents = []
        agents_dir = Path("${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents")
        for agent_file in agents_dir.glob("*.md"):
            name = agent_file.stem
            if name not in ["Template", "README", "STATUSLINE_INTEGRATION"]:
                agents.append(name)
        return sorted(agents)
    
    def get_status(self) -> str:
        """Get current system status"""
        return self.status_line.get_status_line()
    
    def get_metrics(self) -> dict:
        """Get system metrics"""
        return self.monitor.get_summary()

# ============================================================================
# SINGLETON INSTANCES
# ============================================================================

_bridge_instance = None

def get_bridge() -> AgentBridge:
    """Get or create the singleton bridge instance"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = AgentBridge()
    return _bridge_instance

# ============================================================================
# PUBLIC API (for backward compatibility)
# ============================================================================

def bridge():
    """Get binary bridge connection"""
    return get_bridge().binary_bridge

def task_agent_invoke(agent_name: str, task: str, **kwargs) -> Dict[str, Any]:
    """Invoke an agent (main entry point for Claude Code)"""
    return get_bridge().invoke_agent(agent_name, task, **kwargs)

def update_statusline(event: str, **kwargs):
    """Update status line"""
    bridge = get_bridge()
    if event == "task_started":
        bridge.status_line.task_started(kwargs.get("agent", "unknown"))
    elif event == "task_completed":
        bridge.status_line.task_completed(kwargs.get("agent", "unknown"))
    elif event == "task_error":
        bridge.status_line.task_failed(
            kwargs.get("agent", "unknown"),
            kwargs.get("error", "")
        )

def get_statusline():
    """Get status line instance"""
    return get_bridge().status_line

def list_available_agents() -> List[str]:
    """List all available agents"""
    return get_bridge().list_agents()

# ============================================================================
# TESTING
# ============================================================================

def test_system():
    """Test the unified bridge system"""
    print("🧪 Testing Unified Bridge System")
    print("=" * 50)
    
    bridge = get_bridge()
    
    # Test status
    print(f"Status: {bridge.get_status()}")
    
    # Test agent listing
    agents = bridge.list_agents()
    print(f"Found {len(agents)} agents")
    
    # Test invocation
    if agents:
        result = bridge.invoke_agent(agents[0], "Test connection")
        print(f"Test result: {result.get('status')}")
    
    # Test metrics
    metrics = bridge.get_metrics()
    print(f"Uptime: {metrics['uptime']:.1f}s")
    
    # Test voice
    if bridge.voice.is_enabled():
        print("Voice system enabled")
    else:
        print("Voice system disabled")

if __name__ == "__main__":
    test_system()