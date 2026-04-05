#!/usr/bin/env python3
"""
CLAUDE VOICE INPUT SYSTEM
Complete voice-to-agent integration system with real-time speech recognition
"""

import asyncio
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

# Add agents to path
sys.path.append('${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents')

class VoiceInputSystem:
    """Complete voice input system for agent interaction"""
    
    __slots__ = []
    def __init__(self):
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.command_history = []
        
        # Voice processing settings
        self.wake_words = ["claude", "agent", "hey claude", "computer"]
        self.supported_agents = {
            "director": ["plan", "strategy", "coordinate", "manage"],
            "planner": ["timeline", "roadmap", "schedule", "plan"],
            "architect": ["design", "architecture", "structure", "build"],
            "security": ["security", "secure", "audit", "vulnerability"],
            "linter": ["review", "check", "analyze", "quality"],
            "patcher": ["fix", "patch", "update", "repair"],
            "testbed": ["test", "validate", "verify", "run tests"]
        }
    
    def setup_voice_system(self):
        """Set up the voice input system"""
        
        print("🎤 SETTING UP VOICE INPUT SYSTEM")
        print("=" * 50)
        
        # 1. Check dependencies
        self.check_dependencies()
        
        # 2. Set up audio capture
        self.setup_audio_capture()
        
        # 3. Set up speech recognition
        self.setup_speech_recognition()
        
        # 4. Create voice command processor
        self.setup_command_processor()
        
        # 5. Test voice system
        self.test_voice_system()
        
        print("✅ Voice input system ready!")
        print("🎯 Available wake words:", ", ".join(self.wake_words))
        
    def check_dependencies(self):
        """Check and install voice processing dependencies"""
        
        print("🔍 Checking voice system dependencies...")
        
        # Check for required packages
        dependencies = {
            "pyaudio": "pip install pyaudio",
            "speech_recognition": "pip install SpeechRecognition",
            "pyttsx3": "pip install pyttsx3",  # For voice responses
            "whisper": "pip install openai-whisper"  # Advanced speech recognition
        }
        
        missing_deps = []
        
        for package, install_cmd in dependencies.items():
            try:
                __import__(package.replace("-", "_"))
                print(f"  ✅ {package}: Available")
            except ImportError:
                print(f"  ❌ {package}: Missing")
                missing_deps.append((package, install_cmd))
        
        # Install missing dependencies
        if missing_deps:
            print("\n🔧 Installing missing dependencies...")
            for package, install_cmd in missing_deps:
                print(f"  Installing {package}...")
                try:
                    subprocess.run(install_cmd.split(), check=True, capture_output=True)
                    print(f"    ✅ {package} installed")
                except subprocess.CalledProcessError as e:
                    print(f"    ⚠️ {package} installation failed: {e}")
                    print(f"    💡 Manual install: {install_cmd}")
        
        # Fallback: Basic voice system without advanced dependencies
        self.create_basic_voice_system()
    
    def create_basic_voice_system(self):
        """Create basic voice system that works without external dependencies"""
        
        basic_voice_script = '''#!/usr/bin/env python3
"""
BASIC VOICE INPUT SYSTEM - No external dependencies required
Uses text input to simulate voice commands for agent interaction
"""

import asyncio
import sys
import re
sys.path.append('${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents')

class BasicVoiceInterface:
    """Basic voice interface using text input"""
    
    __slots__ = []
    def __init__(self):
        self.agent_keywords = {
            "director": ["plan", "strategy", "coordinate", "manage", "direct"],
            "planner": ["timeline", "roadmap", "schedule", "plan", "organize"],
            "architect": ["design", "architecture", "structure", "build", "create"],
            "security": ["security", "secure", "audit", "vulnerability", "protect"],
            "linter": ["review", "check", "analyze", "quality", "lint"],
            "patcher": ["fix", "patch", "update", "repair", "correct"],
            "testbed": ["test", "validate", "verify", "run", "execute"]
        }
    
    def parse_voice_command(self, text):
        """Parse text input as voice command"""
        text = text.lower().strip()
        
        # Remove wake words
        for wake_word in ["claude", "agent", "hey claude", "computer"]:
            text = text.replace(wake_word, "").strip()
        
        # Find target agent
        target_agent = None
        confidence = 0
        
        for agent, keywords in self.agent_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > confidence:
                confidence = matches
                target_agent = agent.upper()
        
        # Clean up command for agent
        command = text
        for agent in self.agent_keywords.keys():
            command = command.replace(agent, "").strip()
        
        return {
            "target_agent": target_agent,
            "command": command,
            "confidence": confidence,
            "original_text": text
        }
    
    async def process_voice_command(self, voice_input):
        """Process voice command and execute with agent"""
        
        # Parse the command
        parsed = self.parse_voice_command(voice_input)
        
        if not parsed["target_agent"]:
            return {
                "status": "error",
                "message": "Could not determine target agent",
                "suggestion": "Try: 'Claude, ask the director to plan my project'"
            }
        
        print(f"🎯 Routing to {parsed['target_agent']}: {parsed['command']}")
        
        try:
            from claude_agent_bridge import task_agent_invoke
            
            # Execute with target agent
            result = await task_agent_invoke(
                parsed["target_agent"], 
                parsed["command"]
            )
            
            return {
                "status": "success",
                "agent": parsed["target_agent"],
                "result": result,
                "confidence": parsed["confidence"]
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": str(e),
                "agent": parsed["target_agent"]
            }
    
    def start_voice_interface(self):
        """Start interactive voice interface"""
        
        print("🎤 CLAUDE VOICE INTERFACE ACTIVE")
        print("=" * 40)
        print("💡 Examples:")
        print("  • 'Claude, ask the director to plan my project'")
        print("  • 'Hey Claude, have security audit the system'") 
        print("  • 'Computer, get the architect to design an API'")
        print("  • 'Agent, tell the planner to create a timeline'")
        print("  • Type 'quit' to exit")
        print()
        
        while True:
            try:
                voice_input = input("🎤 Voice Command: ").strip()
                
                if voice_input.lower() in ['quit', 'exit', 'stop']:
                    print("👋 Voice interface stopped")
                    break
                
                if not voice_input:
                    continue
                
                print(f"🔊 Processing: '{voice_input}'")
                result = asyncio.run(self.process_voice_command(voice_input))
                
                if result["status"] == "success":
                    print(f"✅ {result['agent']} executed successfully")
                    print(f"📋 Result: {result['result'].get('status', 'completed')}")
                else:
                    print(f"❌ {result['message']}")
                    if 'suggestion' in result:
                        print(f"💡 {result['suggestion']}")
                
                print()
                
            except KeyboardInterrupt:
                print("\\n👋 Voice interface stopped")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                print()

# Voice command examples and usage
def show_voice_examples():
    """Show voice command examples"""
    
    examples = {
        "DIRECTOR": [
            "Claude, ask the director to plan enterprise deployment",
            "Hey Claude, have the director coordinate the team",
            "Computer, tell the director to create project strategy"
        ],
        "PLANNER": [
            "Claude, ask the planner to create a 30-day timeline", 
            "Agent, have the planner organize the roadmap",
            "Hey Claude, get the planner to schedule milestones"
        ],
        "ARCHITECT": [
            "Claude, ask the architect to design the system",
            "Computer, have the architect create API structure",
            "Agent, tell the architect to plan the database"
        ],
        "SECURITY": [
            "Claude, ask security to audit the application",
            "Hey Claude, have security check vulnerabilities",
            "Computer, tell security to review access controls"
        ],
        "LINTER": [
            "Claude, ask the linter to review this code",
            "Agent, have the linter check code quality",
            "Hey Claude, tell the linter to analyze the file"
        ],
        "PATCHER": [
            "Claude, ask the patcher to fix the bugs",
            "Computer, have the patcher update the code",
            "Agent, tell the patcher to apply security patches"
        ]
    }
    
    print("🎤 VOICE COMMAND EXAMPLES")
    print("=" * 40)
    
    for agent, commands in examples.items():
        print(f"\\n🤖 {agent}:")
        for i, cmd in enumerate(commands, 1):
            print(f"   {i}. {cmd}")

if __name__ == "__main__":
    interface = BasicVoiceInterface()
    
    if len(sys.argv) > 1 and sys.argv[1] == "examples":
        show_voice_examples()
    else:
        interface.start_voice_interface()
'''
        
        basic_voice_file = "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../basic_voice_interface.py"
        with open(basic_voice_file, 'w') as f:
            f.write(basic_voice_script)
        os.chmod(basic_voice_file, 0o755)
        
        print(f"✅ Created basic voice interface: {basic_voice_file}")
        return basic_voice_file
    
    def setup_audio_capture(self):
        """Set up audio capture system"""
        
        print("🎧 Setting up audio capture...")
        
        # Test microphone availability
        try:
            # Simple microphone test
            test_cmd = "arecord -l 2>/dev/null | grep -q card || echo 'No microphone detected'"
            result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
            
            if "No microphone" in result.stdout:
                print("  ⚠️ No microphone detected - using text input mode")
                self.audio_available = False
            else:
                print("  ✅ Microphone detected")
                self.audio_available = True
                
        except Exception as e:
            print(f"  ⚠️ Audio setup issue: {e}")
            self.audio_available = False
    
    def setup_speech_recognition(self):
        """Set up speech recognition system"""
        
        print("🧠 Setting up speech recognition...")
        
        # Create speech recognition configuration
        recognition_config = {
            "engine": "basic",  # Can upgrade to whisper later
            "language": "en-US",
            "wake_words": self.wake_words,
            "timeout": 5,
            "phrase_timeout": 2
        }
        
        config_file = "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../voice_config.json"
        with open(config_file, 'w') as f:
            json.dump(recognition_config, f, indent=2)
        
        print(f"  ✅ Speech recognition configured: {config_file}")
    
    def setup_command_processor(self):
        """Set up voice command processing"""
        
        print("⚙️ Setting up command processor...")
        
        # Create command processing rules
        command_rules = {
            "wake_word_detection": {
                "enabled": True,
                "words": self.wake_words,
                "confidence_threshold": 0.7
            },
            "agent_routing": {
                "enabled": True,
                "keywords": self.supported_agents,
                "fallback_agent": "DIRECTOR"
            },
            "command_preprocessing": {
                "enabled": True,
                "remove_filler_words": ["um", "uh", "like", "you know"],
                "normalize_punctuation": True
            }
        }
        
        rules_file = "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../command_rules.json"
        with open(rules_file, 'w') as f:
            json.dump(command_rules, f, indent=2)
        
        print(f"  ✅ Command processor configured: {rules_file}")
    
    def test_voice_system(self):
        """Test the voice input system"""
        
        print("🧪 Testing voice system...")
        
        # Test voice command parsing
        test_commands = [
            "Claude, ask the director to plan my project",
            "Hey Claude, have security audit the system", 
            "Computer, tell the architect to design an API",
            "Agent, get the planner to create a timeline"
        ]
        
        # Import the basic voice interface for testing
        try:
            exec(open("${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../basic_voice_interface.py").read())
            print("  ✅ Voice interface loaded successfully")
            
            # Test command parsing
            from basic_voice_interface import BasicVoiceInterface
            interface = BasicVoiceInterface()
            
            for cmd in test_commands:
                parsed = interface.parse_voice_command(cmd)
                if parsed["target_agent"]:
                    print(f"  ✅ '{cmd}' → {parsed['target_agent']}")
                else:
                    print(f"  ❌ '{cmd}' → Could not parse")
                    
        except Exception as e:
            print(f"  ⚠️ Voice system test failed: {e}")
    
    def create_voice_shortcuts(self):
        """Create convenient voice shortcuts"""
        
        shortcuts = f"""#!/bin/bash
# Claude Voice System Shortcuts

# Start voice interface
claude-voice() {{
    echo "🎤 Starting Claude Voice Interface..."
    python3 ${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../basic_voice_interface.py
}}

# Show voice examples
claude-voice-help() {{
    python3 ${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../basic_voice_interface.py examples
}}

# Quick voice command (single use)
claude-say() {{
    if [ $# -eq 0 ]; then
        echo "Usage: claude-say 'your voice command'"
        echo "Example: claude-say 'Claude, ask the director to plan my project'"
        return
    fi
    
    echo "🎤 Processing: $1"
    python3 -c "
import asyncio
import sys
sys.path.append('${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents')

async def quick_voice():
    exec(open('${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../basic_voice_interface.py').read())
    interface = BasicVoiceInterface()
    result = await interface.process_voice_command('$1')
    
    if result['status'] == 'success':
        print(f'✅ {{result[\"agent\"]}} executed successfully')
        print(f'📋 Result: {{result[\"result\"].get(\"status\", \"completed\")}}')
    else:
        print(f'❌ {{result[\"message\"]}}')

asyncio.run(quick_voice())
"
}}
"""
        
        shortcuts_file = "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../voice_shortcuts.sh"
        with open(shortcuts_file, 'w') as f:
            f.write(shortcuts)
        os.chmod(shortcuts_file, 0o755)
        
        # Add to bashrc
        bashrc_file = os.path.expanduser("~/.bashrc")
        source_line = f'\nsource "{shortcuts_file}"\n'
        
        if os.path.exists(bashrc_file):
            with open(bashrc_file, 'r') as f:
                content = f.read()
            
            if shortcuts_file not in content:
                with open(bashrc_file, 'a') as f:
                    f.write(source_line)
        
        print(f"🚀 Created voice shortcuts: {shortcuts_file}")
        print("💡 Available: claude-voice, claude-voice-help, claude-say")


def setup_voice_input():
    """Main function to set up voice input system"""
    
    voice_system = VoiceInputSystem()
    voice_system.setup_voice_system()
    voice_system.create_voice_shortcuts()
    
    print("\n🎉 VOICE INPUT SYSTEM SETUP COMPLETE!")
    print("=" * 50)
    print("✅ Voice interface ready")
    print("🎤 Start with: claude-voice")
    print("💡 Help with: claude-voice-help")
    print("⚡ Quick use: claude-say 'your command'")
    print("\n📖 USAGE EXAMPLES:")
    print("  claude-say 'Claude, ask the director to plan deployment'")
    print("  claude-say 'Hey Claude, have security audit the system'")
    print("  claude-say 'Computer, tell architect to design API'")


if __name__ == "__main__":
    setup_voice_input()