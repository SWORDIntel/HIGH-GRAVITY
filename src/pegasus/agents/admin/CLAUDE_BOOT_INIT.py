#!/usr/bin/env python3
"""
CLAUDE BOOT INITIALIZATION - Auto-load agents on every Claude Code boot
Makes all agents available immediately when Claude Code starts
"""

import json
import os
import subprocess
import sys
from pathlib import Path


class ClaudeBootInitializer:
    """Initializes agent system on every Claude Code boot"""
    
    __slots__ = []
    def __init__(self):
        self.agents_dir = "${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents"
        self.claude_config_dir = os.path.expanduser("~/.claude")
        self.init_marker = os.path.join(self.claude_config_dir, ".agents_initialized")
        
    def setup_boot_initialization(self):
        """Set up automatic initialization on Claude Code boot"""
        
        print("🚀 SETTING UP CLAUDE CODE BOOT INITIALIZATION")
        print("=" * 60)
        
        # 1. Create Claude config directory if it doesn't exist
        os.makedirs(self.claude_config_dir, exist_ok=True)
        
        # 2. Create initialization script
        self.create_init_script()
        
        # 3. Set up environment variables
        self.setup_environment_variables()
        
        # 4. Create auto-load configuration
        self.create_autoload_config()
        
        # 5. Test the initialization
        self.test_initialization()
        
        print("✅ Boot initialization setup complete!")
        print("🎯 Agents will auto-load on every Claude Code start")
        
    def create_init_script(self):
        """Create the initialization script that runs on boot"""
        
        init_script = f"""#!/usr/bin/env python3
# Auto-generated Claude Agent Initialization Script
import sys
import os

# Add agents to Python path
sys.path.insert(0, '{self.agents_dir}')

# Import and initialize agent bridge
try:
    from 03-BRIDGES.claude_agent_bridge import bridge, task_agent_invoke
    from 08-ADMIN-TOOLS.DEVELOPMENT_CLUSTER_DIRECT import DevelopmentCluster
    
    print("✅ Claude Agents initialized successfully!")
    print("🤖 Available agents: Director, PLANNER, Architect, Security, Linter, Patcher, Testbed")
    print("🔧 Development Cluster pipeline ready")
    print("🎤 Voice integration active")
    
    # Mark as initialized
    with open('{self.init_marker}', 'w') as f:
        f.write("agents_initialized=true\\n")
        
except ImportError as e:
    print(f"⚠️ Agent initialization failed: {{e}}")
    print("📍 Run: python3 {self.agents_dir}/CLAUDE_BOOT_INIT.py")

# Make agents globally available
globals()['task_agent_invoke'] = task_agent_invoke
globals()['DevelopmentCluster'] = DevelopmentCluster
"""
        
        init_file = os.path.join(self.claude_config_dir, "init_agents.py")
        with open(init_file, 'w') as f:
            f.write(init_script)
        os.chmod(init_file, 0o755)
        
        print(f"📄 Created initialization script: {init_file}")
    
    def setup_environment_variables(self):
        """Set up environment variables for agent system"""
        
        env_vars = {
            "CLAUDE_AGENTS_DIR": self.agents_dir,
            "CLAUDE_AGENTS_ENABLED": "true",
            "PYTHONPATH": f"{self.agents_dir}:${{PYTHONPATH}}"
        }
        
        # Create environment setup script
        env_script = "#!/bin/bash\n# Claude Agent Environment Variables\n\n"
        for var, value in env_vars.items():
            env_script += f'export {var}="{value}"\n'
        
        env_file = os.path.join(self.claude_config_dir, "agent_env.sh")
        with open(env_file, 'w') as f:
            f.write(env_script)
        os.chmod(env_file, 0o755)
        
        # Add to bashrc for persistence
        bashrc_addition = f"""
# Claude Agent System Auto-initialization
if [ -f "{env_file}" ]; then
    source "{env_file}"
fi

# Auto-load agents when Python starts
export PYTHONSTARTUP="{os.path.join(self.claude_config_dir, 'init_agents.py')}"
"""
        
        bashrc_file = os.path.expanduser("~/.bashrc")
        
        # Check if already added
        if os.path.exists(bashrc_file):
            with open(bashrc_file, 'r') as f:
                content = f.read()
            
            if "Claude Agent System" not in content:
                with open(bashrc_file, 'a') as f:
                    f.write(bashrc_addition)
                print("📝 Added agent initialization to ~/.bashrc")
        
        print("🌍 Environment variables configured")
    
    def create_autoload_config(self):
        """Create configuration for automatic loading"""
        
        autoload_config = {
            "version": "7.0",
            "auto_initialize": True,
            "agents_directory": self.agents_dir,
            "bridge_system": {
                "enabled": True,
                "auto_start": True
            },
            "binary_system": {
                "enabled": True,
                "auto_transition": True
            },
            "voice_system": {
                "enabled": True,
                "auto_start": False  # Start on demand
            },
            "available_agents": [
                "DIRECTOR", "PLANNER", "ARCHITECT", "SECURITY",
                "LINTER", "PATCHER", "TESTBED", "PROJECT_ORCHESTRATOR"
            ]
        }
        
        config_file = os.path.join(self.claude_config_dir, "agent_config.json")
        with open(config_file, 'w') as f:
            json.dump(autoload_config, f, indent=2)
        
        print(f"⚙️ Created auto-load configuration: {config_file}")
    
    def test_initialization(self):
        """Test that initialization works correctly"""
        
        print("🧪 Testing initialization...")
        
        # Test import
        test_script = f"""
import sys
sys.path.insert(0, '{self.agents_dir}')

try:
    from 03-BRIDGES.claude_agent_bridge import task_agent_invoke
    print("✅ Agent bridge import successful")
    
    from 08-ADMIN-TOOLS.DEVELOPMENT_CLUSTER_DIRECT import DevelopmentCluster
    print("✅ Development cluster import successful")
    
    print("🎉 All agent systems ready!")
    
except Exception as e:
    print(f"❌ Import failed: {{e}}")
"""
        
        # Run test
        result = subprocess.run([sys.executable, "-c", test_script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Initialization test passed")
            print(result.stdout)
        else:
            print("❌ Initialization test failed")
            print(result.stderr)
    
    def create_quick_start_commands(self):
        """Create quick commands for easy agent usage"""
        
        quick_commands = f"""#!/bin/bash
# Claude Agent Quick Commands

# Test all agents
claude-test-agents() {{
    python3 -c "
import sys
sys.path.insert(0, '{self.agents_dir}')
import asyncio
from 03-BRIDGES.claude_agent_bridge import task_agent_invoke

async def test_all():
    agents = ['DIRECTOR', 'PLANNER', 'ARCHITECT', 'SECURITY']
    for agent in agents:
        try:
            result = await task_agent_invoke(agent, 'Quick system test')
            print(f'✅ {{agent}}: {{result.get(\"status\", \"completed\")}}')
        except Exception as e:
            print(f'❌ {{agent}}: {{e}}')

asyncio.run(test_all())
"
}}

# Use specific agent
claude-agent() {{
    if [ $# -lt 2 ]; then
        echo "Usage: claude-agent AGENT_NAME \"prompt\""
        echo "Available: DIRECTOR, PLANNER, ARCHITECT, SECURITY, LINTER, PATCHER, TESTBED"
        return
    fi
    
    python3 -c "
import sys
sys.path.insert(0, '{self.agents_dir}')
import asyncio
from 03-BRIDGES.claude_agent_bridge import task_agent_invoke

async def use_agent():
    result = await task_agent_invoke('$1', '$2')
    print(f'Agent {{\"$1\"}} result: {{result}}')

asyncio.run(use_agent())
"
}}

# Run development pipeline
claude-dev-pipeline() {{
    if [ $# -lt 1 ]; then
        echo "Usage: claude-dev-pipeline file_path"
        return
    fi
    
    python3 -c "
import sys
sys.path.insert(0, '{self.agents_dir}')
from 08-ADMIN-TOOLS.DEVELOPMENT_CLUSTER_DIRECT import DevelopmentCluster

cluster = DevelopmentCluster()
result = cluster.process_file('$1')
print(f'Pipeline result: {{result}}')
"
}}
"""
        
        commands_file = os.path.join(self.claude_config_dir, "quick_commands.sh")
        with open(commands_file, 'w') as f:
            f.write(quick_commands)
        os.chmod(commands_file, 0o755)
        
        # Add to bashrc
        bashrc_file = os.path.expanduser("~/.bashrc")
        source_line = f'\nsource "{commands_file}"\n'
        
        if os.path.exists(bashrc_file):
            with open(bashrc_file, 'r') as f:
                content = f.read()
            
            if commands_file not in content:
                with open(bashrc_file, 'a') as f:
                    f.write(source_line)
        
        print(f"🚀 Created quick commands: {commands_file}")
        print("💡 Available commands: claude-test-agents, claude-agent, claude-dev-pipeline")


def setup_boot_initialization():
    """Main function to set up boot initialization"""
    initializer = ClaudeBootInitializer()
    initializer.setup_boot_initialization()
    initializer.create_quick_start_commands()
    
    print("\n🎉 CLAUDE CODE BOOT INITIALIZATION COMPLETE!")
    print("=" * 60)
    print("✅ Agents will auto-load on every Claude Code start")
    print("🔄 Restart your terminal or run: source ~/.bashrc")
    print("🧪 Test with: claude-test-agents")
    print("🤖 Use agents with: claude-agent DIRECTOR \"plan my project\"")


if __name__ == "__main__":
    setup_boot_initialization()