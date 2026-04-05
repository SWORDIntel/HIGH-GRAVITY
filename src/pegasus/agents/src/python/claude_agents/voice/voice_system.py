#!/usr/bin/env python3
"""
Voice System Integration for Claude Agents
Restored from deprecated/old-scripts/VOICE_INPUT_SYSTEM.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add agents directory to path
sys.path.append('${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents')
sys.path.append('${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../03-BRIDGES')
sys.path.append('${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../04-SOURCE/python-modules')

from claude_agents.bridges.claude_agent_bridge import (
    AgentConfig,
    BinaryBridgeConnection,
)


class VoiceSystem:
    """Voice input system for agent control"""
    
    def __init__(self):
        self.config_path = Path("${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../05-CONFIG/voice_config.json")
        self.config = self.load_config()
        self.bridge = BinaryBridgeConnection()
        
    def load_config(self):
        """Load voice configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {
            "enabled": False,
            "auto_start": False,
            "wake_words": ["claude", "agent"],
            "interface": "voice_system.py",
            "shortcuts_enabled": True
        }
    
    def is_enabled(self):
        """Check if voice system is enabled"""
        return self.config.get("enabled", False)
    
    async def process_voice_command(self, command: str):
        """Process a voice command and route to appropriate agent"""
        print(f"Processing voice command: {command}")
        
        # Connect to binary bridge if available
        if self.bridge.connect():
            # Send voice command as message
            msg = json.dumps({
                "type": "voice_command",
                "command": command,
                "timestamp": str(asyncio.get_event_loop().time())
            }).encode()
            
            response = self.bridge.send_message(msg)
            if response:
                print(f"Response: {response.decode()}")
                return response.decode()
        else:
            print("Binary bridge not available, processing locally")
            # Fallback to local processing
            return self.process_locally(command)
    
    def process_locally(self, command: str):
        """Process command locally without binary bridge"""
        # Simple command routing
        command_lower = command.lower()
        
        if "status" in command_lower:
            return "Voice system operational. Binary bridge not connected."
        elif "help" in command_lower:
            return "Available commands: status, help, invoke [agent_name], configure"
        elif "invoke" in command_lower:
            agent = command_lower.split("invoke")[-1].strip()
            return f"Would invoke agent: {agent} (bridge not connected)"
        else:
            return f"Unknown command: {command}"

def main():
    """Main entry point for voice system"""
    print("🎤 Voice System Starting...")
    
    voice = VoiceSystem()
    
    if not voice.is_enabled():
        print("⚠️  Voice system is disabled in configuration")
        print("   Enable it in: ${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../05-CONFIG/voice_config.json")
        return
    
    print("✅ Voice system ready")
    print("   Wake words:", voice.config.get("wake_words"))
    
    # Run async event loop
    loop = asyncio.get_event_loop()
    
    try:
        # Test with a sample command
        result = loop.run_until_complete(
            voice.process_voice_command("status")
        )
        print(f"Test result: {result}")
    except KeyboardInterrupt:
        print("\n👋 Voice system shutting down")
    finally:
        voice.bridge.close()

if __name__ == "__main__":
    main()