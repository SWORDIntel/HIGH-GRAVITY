#!/usr/bin/env python3
"""
VOICE SYSTEM TOGGLE - Easy on/off control for voice input
Simple commands to enable/disable voice system
"""

import json
import os
import subprocess
import sys
from pathlib import Path


class VoiceToggle:
    """Simple voice system toggle controller"""
    
    __slots__ = []
    def __init__(self):
        self.agents_dir = "${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents"
        self.config_file = os.path.join(self.agents_dir, "voice_config.json")
        self.voice_pid_file = os.path.join(self.agents_dir, ".voice_system.pid")
        
    def get_voice_status(self):
        """Check if voice system is currently enabled/running"""
        
        # Check config file
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                enabled = config.get("enabled", False)
        else:
            enabled = False
        
        # Check if voice process is running
        running = os.path.exists(self.voice_pid_file)
        
        return {
            "enabled": enabled,
            "running": running,
            "status": "active" if enabled and running else "inactive"
        }
    
    def enable_voice(self):
        """Enable voice system"""
        
        print("🎤 ENABLING VOICE SYSTEM...")
        
        # Create/update config
        config = {
            "enabled": True,
            "auto_start": True,
            "wake_words": ["claude", "agent", "hey claude", "computer"],
            "interface": "basic_voice_interface.py",
            "shortcuts_enabled": True
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Add voice shortcuts to bashrc if not already there
        self.setup_voice_shortcuts()
        
        print("✅ Voice system enabled!")
        print("🎯 Available commands:")
        print("  • claude-voice          - Start interactive voice")
        print("  • claude-voice-help     - Show voice examples")  
        print("  • claude-say 'command'  - Quick voice command")
        print("  • voice-toggle off      - Disable voice system")
        
        return {"status": "enabled", "shortcuts_added": True}
    
    def disable_voice(self):
        """Disable voice system"""
        
        print("🔇 DISABLING VOICE SYSTEM...")
        
        # Update config
        config = {
            "enabled": False,
            "auto_start": False,
            "disabled_at": "user_request"
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Stop any running voice processes
        self.stop_voice_processes()
        
        # Remove voice shortcuts (optional)
        # self.remove_voice_shortcuts()  # Uncomment if you want to remove shortcuts
        
        print("✅ Voice system disabled!")
        print("🔇 Voice commands are now inactive")
        print("💡 Re-enable with: voice-toggle on")
        
        return {"status": "disabled", "processes_stopped": True}
    
    def setup_voice_shortcuts(self):
        """Set up voice command shortcuts"""
        
        shortcuts_script = f"""
# Claude Voice System Shortcuts (Auto-generated)
claude-voice() {{
    if [ -f "{self.config_file}" ]; then
        ENABLED=$(python3 -c "import json; print(json.load(open('{self.config_file}'))['enabled'])" 2>/dev/null || echo "false")
        if [ "$ENABLED" = "True" ]; then
            echo "🎤 Starting Claude Voice Interface..."
            python3 {self.agents_dir}/basic_voice_interface.py
        else
            echo "🔇 Voice system disabled. Enable with: voice-toggle on"
        fi
    else
        echo "⚠️ Voice system not configured. Run: voice-toggle on"
    fi
}}

claude-voice-help() {{
    if [ -f "{self.config_file}" ]; then
        ENABLED=$(python3 -c "import json; print(json.load(open('{self.config_file}'))['enabled'])" 2>/dev/null || echo "false")
        if [ "$ENABLED" = "True" ]; then
            python3 {self.agents_dir}/basic_voice_interface.py examples
        else
            echo "🔇 Voice system disabled. Enable with: voice-toggle on"
        fi
    else
        echo "⚠️ Voice system not configured. Run: voice-toggle on"
    fi
}}

claude-say() {{
    if [ $# -eq 0 ]; then
        echo "Usage: claude-say 'your voice command'"
        echo "Example: claude-say 'Claude, ask the director to plan my project'"
        return
    fi
    
    if [ -f "{self.config_file}" ]; then
        ENABLED=$(python3 -c "import json; print(json.load(open('{self.config_file}'))['enabled'])" 2>/dev/null || echo "false")
        if [ "$ENABLED" = "True" ]; then
            echo "🎤 Processing: $1"
            python3 {self.agents_dir}/quick_voice.py "$1"
        else
            echo "🔇 Voice system disabled. Enable with: voice-toggle on"
        fi
    else
        echo "⚠️ Voice system not configured. Run: voice-toggle on"
    fi
}}

voice-toggle() {{
    python3 {self.agents_dir}/VOICE_TOGGLE.py "$@"
}}
"""
        
        # Write shortcuts to file
        shortcuts_file = os.path.join(self.agents_dir, "voice_shortcuts_managed.sh")
        with open(shortcuts_file, 'w') as f:
            f.write(shortcuts_script.strip())
        os.chmod(shortcuts_file, 0o755)
        
        # Add to bashrc if not already there
        bashrc_file = os.path.expanduser("~/.bashrc")
        source_line = f'\n# Claude Voice System (managed)\nsource "{shortcuts_file}"\n'
        
        if os.path.exists(bashrc_file):
            with open(bashrc_file, 'r') as f:
                content = f.read()
            
            if "voice_shortcuts_managed.sh" not in content:
                with open(bashrc_file, 'a') as f:
                    f.write(source_line)
                print("📝 Added voice shortcuts to ~/.bashrc")
    
    def stop_voice_processes(self):
        """Stop any running voice processes"""
        
        try:
            # Kill any voice interface processes
            subprocess.run(["pkill", "-f", "basic_voice_interface.py"], 
                         capture_output=True)
            
            # Remove PID file if it exists
            if os.path.exists(self.voice_pid_file):
                os.remove(self.voice_pid_file)
                
        except Exception as e:
            print(f"⚠️ Warning: Could not stop all voice processes: {e}")
    
    def status(self):
        """Show voice system status"""
        
        status = self.get_voice_status()
        
        print("🎤 VOICE SYSTEM STATUS")
        print("=" * 30)
        print(f"Status: {'✅ ENABLED' if status['enabled'] else '🔇 DISABLED'}")
        print(f"Running: {'✅ YES' if status['running'] else '❌ NO'}")
        
        if status['enabled']:
            print("\n🎯 Available Commands:")
            print("  • claude-voice          - Interactive voice interface")
            print("  • claude-voice-help     - Show voice examples")
            print("  • claude-say 'command'  - Quick voice command")
            print("  • voice-toggle off      - Disable voice system")
            
            print("\n💡 Voice Command Examples:")
            print("  • claude-say 'Claude, ask director to plan project'")
            print("  • claude-say 'Hey Claude, have security audit system'")
            print("  • claude-say 'Computer, tell architect to design API'")
        else:
            print("\n💡 To enable:")
            print("  • voice-toggle on")
        
        return status
    
    def quick_setup(self):
        """Quick setup with minimal configuration"""
        
        print("⚡ QUICK VOICE SETUP")
        print("=" * 25)
        
        # Create minimal config
        config = {
            "enabled": True,
            "mode": "quick",
            "interface": "text_based"  # No audio dependencies
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Create simple voice command
        quick_voice_cmd = f"""#!/bin/bash
# Quick voice command
if [ $# -eq 0 ]; then
    echo "Usage: voice 'your command'"
    echo "Example: voice 'plan my project'"
    exit 1
fi

python3 -c "
import asyncio
import sys
sys.path.append('{self.agents_dir}')
from claude_agent_bridge import task_agent_invoke

async def quick_voice():
    command = '$1'
    # Simple agent detection
    if 'plan' in command or 'strategy' in command:
        agent = 'DIRECTOR'
    elif 'security' in command or 'audit' in command:
        agent = 'SECURITY'
    elif 'design' in command or 'architecture' in command:
        agent = 'ARCHITECT'
    else:
        agent = 'DIRECTOR'
    
    print(f'🎤 Routing to {{agent}}: {{command}}')
    try:
        result = await task_agent_invoke(agent, command)
        print(f'✅ {{agent}} completed: {{result.get(\"status\", \"success\")}}')
    except Exception as e:
        print(f'❌ Error: {{e}}')

asyncio.run(quick_voice())
"
"""
        
        voice_cmd_file = os.path.join(self.agents_dir, "voice_quick.sh")
        with open(voice_cmd_file, 'w') as f:
            f.write(quick_voice_cmd)
        os.chmod(voice_cmd_file, 0o755)
        
        # Add alias to bashrc
        alias_line = f'\nalias voice="{voice_cmd_file}"\n'
        bashrc_file = os.path.expanduser("~/.bashrc")
        
        if os.path.exists(bashrc_file):
            with open(bashrc_file, 'r') as f:
                content = f.read()
            
            if voice_cmd_file not in content:
                with open(bashrc_file, 'a') as f:
                    f.write(alias_line)
        
        print("✅ Quick voice setup complete!")
        print("🎯 Usage: voice 'plan my project'")
        print("🔄 Restart terminal or run: source ~/.bashrc")


def main():
    """Main voice toggle interface"""
    
    toggle = VoiceToggle()
    
    if len(sys.argv) < 2:
        # No arguments - show status
        toggle.status()
        return
    
    command = sys.argv[1].lower()
    
    if command in ['on', 'enable', 'start']:
        toggle.enable_voice()
    elif command in ['off', 'disable', 'stop']:
        toggle.disable_voice()
    elif command in ['status', 'check']:
        toggle.status()
    elif command in ['quick', 'setup']:
        toggle.quick_setup()
    else:
        print("🎤 VOICE SYSTEM TOGGLE")
        print("=" * 25)
        print("Usage:")
        print("  voice-toggle on      - Enable voice system")
        print("  voice-toggle off     - Disable voice system")
        print("  voice-toggle status  - Show current status")
        print("  voice-toggle quick   - Quick minimal setup")
        print()
        print("Examples:")
        print("  voice-toggle on")
        print("  voice-toggle status")
        print("  voice-toggle off")


if __name__ == "__main__":
    main()