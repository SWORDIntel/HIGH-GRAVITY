#!/usr/bin/env python3
"""
Status Line Bridge for Claude Agent System v7.0
Integrates with statusline.lua for real-time status display
Updated with environment-relative paths
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional


class StatusLineBridge:
    """Bridge between Python agent system and Lua statusline"""

    def __init__(self):
        # Use environment-relative paths
        self.claude_root = Path(
            os.getenv(
                "CLAUDE_AGENTS_ROOT", os.path.expanduser("~/Documents/Claude/agents")
            )
        )
        self.runtime_dir = self.claude_root / "runtime"
        self.log_dir = self.claude_root / "logs"
        self.status_file = self.runtime_dir / "status.json"
        self.agent_socket = self.runtime_dir / "claude_agent_bridge.sock"
        self.lua_script = self.claude_root / "statusline.lua"
        self.ensure_paths()

    def ensure_paths(self):
        """Ensure required paths exist"""
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def update_status(self, status_data: Dict[str, Any]):
        """Update status file for Lua script to read"""
        try:
            with open(self.status_file, "w") as f:
                json.dump(
                    {
                        "timestamp": time.time(),
                        "binary_bridge": self.check_binary_bridge(),
                        "socket": self.check_socket(),
                        "agents": self.count_agents(),
                        **status_data,
                    },
                    f,
                )
        except Exception as e:
            print(f"Failed to update status: {e}")

    def check_binary_bridge(self) -> str:
        """Check if binary bridge is running"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "ultra_hybrid_enhanced"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            return "running" if result.returncode == 0 else "stopped"
        except:
            return "unknown"

    def check_socket(self) -> bool:
        """Check if socket exists"""
        return self.agent_socket.exists() and self.agent_socket.is_socket()

    def count_agents(self) -> int:
        """Count available agent definitions"""
        # Count .md files in the main agents directory
        if self.claude_root.exists():
            return len(list(self.claude_root.glob("*.md")))
        return 0

    def get_status_line(self) -> str:
        """Get formatted status line"""
        status = []

        # Binary bridge
        bridge_status = self.check_binary_bridge()
        bridge_icon = "🟢" if bridge_status == "running" else "🔴"
        status.append(f"{bridge_icon} Bridge")

        # Socket
        socket_icon = "🔌" if self.check_socket() else "⚠️"
        status.append(f"{socket_icon} Socket")

        # Agents
        agent_count = self.count_agents()
        status.append(f"🤖 {agent_count} agents")

        # Read additional metrics from status file
        if self.status_file.exists():
            try:
                with open(self.status_file, "r") as f:
                    data = json.load(f)
                    if "tasks" in data:
                        tasks = data["tasks"]
                        if tasks.get("pending", 0) > 0:
                            status.append(f"⏳ {tasks['pending']}")
                        if tasks.get("completed", 0) > 0:
                            status.append(f"✅ {tasks['completed']}")
                        if tasks.get("errors", 0) > 0:
                            status.append(f"❌ {tasks['errors']}")
            except:
                pass

        return " | ".join(status)

    def task_started(self, agent_name: str):
        """Record task start"""
        self.update_status(
            {
                "last_event": "task_started",
                "agent": agent_name,
                "event_time": time.time(),
            }
        )

    def task_completed(self, agent_name: str):
        """Record task completion"""
        self.update_status(
            {
                "last_event": "task_completed",
                "agent": agent_name,
                "event_time": time.time(),
            }
        )

    def task_error(self, agent_name: str, error: str):
        """Record task error"""
        self.update_status(
            {
                "last_event": "task_error",
                "agent": agent_name,
                "error": error,
                "event_time": time.time(),
            }
        )


# Global instance
_statusline = None


def get_statusline():
    """Get or create statusline singleton"""
    global _statusline
    if _statusline is None:
        _statusline = StatusLineBridge()
    return _statusline


def update_statusline(event: str, **kwargs):
    """Quick update function for statusline"""
    sl = get_statusline()
    if event == "task_started":
        sl.task_started(kwargs.get("agent", "unknown"))
    elif event == "task_completed":
        sl.task_completed(kwargs.get("agent", "unknown"))
    elif event == "task_error":
        sl.task_error(kwargs.get("agent", "unknown"), kwargs.get("error", ""))
    else:
        sl.update_status(kwargs)


def main():
    """Test statusline functionality"""
    print("📊 Testing Status Line Bridge")
    print("=" * 50)

    sl = get_statusline()

    # Get current status
    status = sl.get_status_line()
    print(f"Current status: {status}")

    # Test task tracking
    print("\nSimulating task events:")
    sl.task_started("Director")
    print(f"After start: {sl.get_status_line()}")

    time.sleep(1)
    sl.task_completed("Director")
    print(f"After complete: {sl.get_status_line()}")

    # Check components
    print("\n📋 Component Status:")
    print(f"  Binary Bridge: {sl.check_binary_bridge()}")
    print(f"  Socket Exists: {sl.check_socket()}")
    print(f"  Agent Count: {sl.count_agents()}")
    print(f"  Status File: {sl.status_file}")


if __name__ == "__main__":
    main()
