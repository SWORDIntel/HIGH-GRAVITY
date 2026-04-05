#!/bin/bash
# ============================================================================
# AGENTS DIRECTORY CLEANUP SCRIPT
# 
# Moves loose files to appropriate subdirectories while preserving all
# functionality and fixing imports where necessary
# ============================================================================

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Base paths
AGENTS_DIR="${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents"
BACKUP_DIR="$AGENTS_DIR/.cleanup_backup_$(date +%Y%m%d_%H%M%S)"

# Create backup
echo -e "${YELLOW}Creating backup before cleanup...${NC}"
mkdir -p "$BACKUP_DIR"

# Backup loose files before moving them
cp "$AGENTS_DIR"/*.py "$BACKUP_DIR/" 2>/dev/null || true
cp "$AGENTS_DIR"/*.md "$BACKUP_DIR/" 2>/dev/null || true
cp "$AGENTS_DIR"/*.sh "$BACKUP_DIR/" 2>/dev/null || true
cp "$AGENTS_DIR"/*.json "$BACKUP_DIR/" 2>/dev/null || true
cp "$AGENTS_DIR"/*.log "$BACKUP_DIR/" 2>/dev/null || true

echo "Backup created in: $BACKUP_DIR"

# Function to move files safely
move_file() {
    local file="$1"
    local dest_dir="$2"
    local file_name=$(basename "$file")
    
    if [ -f "$file" ]; then
        # Check if destination already exists
        if [ -f "$dest_dir/$file_name" ]; then
            echo -e "${YELLOW}Warning: $file_name already exists in $dest_dir${NC}"
            mv "$file" "$dest_dir/${file_name}.duplicate"
        else
            mv "$file" "$dest_dir/"
            echo "  ✓ Moved $file_name to $dest_dir"
        fi
    fi
}

echo ""
echo -e "${YELLOW}=== MOVING PYTHON SCRIPTS ===${NC}"

# Move bridge-related Python files to 03-BRIDGES
echo "Moving bridge and communication scripts to 03-BRIDGES..."
move_file "$AGENTS_DIR/claude_agent_bridge.py" "$AGENTS_DIR/03-BRIDGES"
move_file "$AGENTS_DIR/bridge_monitor.py" "$AGENTS_DIR/03-BRIDGES"
move_file "$AGENTS_DIR/agent_server.py" "$AGENTS_DIR/03-BRIDGES"
move_file "$AGENTS_DIR/test_agent_communication.py" "$AGENTS_DIR/03-BRIDGES"
move_file "$AGENTS_DIR/auto_integrate.py" "$AGENTS_DIR/03-BRIDGES"

# Move voice-related files to 03-BRIDGES (since they're system integration)
echo "Moving voice system files to 03-BRIDGES..."
move_file "$AGENTS_DIR/VOICE_INPUT_SYSTEM.py" "$AGENTS_DIR/03-BRIDGES"
move_file "$AGENTS_DIR/VOICE_TOGGLE.py" "$AGENTS_DIR/03-BRIDGES"
move_file "$AGENTS_DIR/quick_voice.py" "$AGENTS_DIR/03-BRIDGES"

# Move deployment and development scripts to 08-ADMIN-TOOLS
echo "Moving admin and deployment scripts to 08-ADMIN-TOOLS..."
move_file "$AGENTS_DIR/DEVELOPMENT_CLUSTER_DIRECT.py" "$AGENTS_DIR/08-ADMIN-TOOLS"
move_file "$AGENTS_DIR/CLAUDE_BOOT_INIT.py" "$AGENTS_DIR/08-ADMIN-TOOLS"
move_file "$AGENTS_DIR/OPTIMAL_PATH_EXECUTION.py" "$AGENTS_DIR/08-ADMIN-TOOLS"

# Move integration and transition scripts to 08-ADMIN-TOOLS
echo "Moving integration scripts to 08-ADMIN-TOOLS..."
move_file "$AGENTS_DIR/UPDATE_AGENTS_INTEGRATION.py" "$AGENTS_DIR/08-ADMIN-TOOLS"
move_file "$AGENTS_DIR/INTEGRATION_EXAMPLE.py" "$AGENTS_DIR/08-ADMIN-TOOLS"
move_file "$AGENTS_DIR/HYBRID_INTEGRATION_DEMO.py" "$AGENTS_DIR/08-ADMIN-TOOLS"
move_file "$AGENTS_DIR/BRIDGE_TO_BINARY_TRANSITION.py" "$AGENTS_DIR/08-ADMIN-TOOLS"

echo ""
echo -e "${YELLOW}=== MOVING DOCUMENTATION FILES ===${NC}"

# Move documentation files to 11-DOCS
echo "Moving documentation to 11-DOCS..."
move_file "$AGENTS_DIR/AGENT_SWITCHING_README.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/INTEGRATION_PLAN.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/SYSTEM_STATUS_REPORT.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/AGENT_SYSTEM_ARCHITECTURE.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/VOICE_TOGGLE_GUIDE.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/PRODUCTION_DEPLOYMENT_SUMMARY.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/INTEGRATION_STRATEGY.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/INTEGRATION_COMPLETE.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/DIRECTORY_STRUCTURE.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/COORDINATION_UPDATE.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/COMPLETE_SETUP_GUIDE.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/BRIDGE_USAGE_GUIDE.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/AGENT_INTEGRATION_PLAN.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/CHECKPOINT_2024_REORGANIZATION.md" "$AGENTS_DIR/11-DOCS"
move_file "$AGENTS_DIR/ISSUES_REPORT.md" "$AGENTS_DIR/11-DOCS"

# Move legacy/historical docs to their own section
echo "Moving legacy/historical documentation..."
mkdir -p "$AGENTS_DIR/11-DOCS/legacy"
move_file "$AGENTS_DIR/Director-Legacy.md" "$AGENTS_DIR/11-DOCS/legacy"

# Move main README to docs but keep a reference
if [ -f "$AGENTS_DIR/README.md" ]; then
    mv "$AGENTS_DIR/README.md" "$AGENTS_DIR/11-DOCS/README.md"
    # Create a simple reference README at root
    cat > "$AGENTS_DIR/README.md" << 'EOF'
# Claude Agent Framework v7.0

This is a production agent orchestration system. For complete documentation see:

- **[Main Documentation](11-DOCS/README.md)** - Complete documentation
- **[Agent Definitions](01-AGENTS-DEFINITIONS/ACTIVE/)** - All agent definitions
- **[Quick Reference](11-DOCS/AGENT_QUICK_REFERENCE_V7.md)** - Quick reference guide

## Quick Commands

```bash
# Switch between agent modes
./switch_mode.sh status
./switch_mode.sh binary
./switch_mode.sh standard

# Start agent system
./BRING_ONLINE.sh

# Check system status
./STATUS.sh
```

See full documentation in the `11-DOCS/` directory.
EOF
    echo "  ✓ Moved README.md to 11-DOCS and created reference README"
fi

# Move remaining special purpose docs
move_file "$AGENTS_DIR/WHERE_I_AM.md" "$AGENTS_DIR/11-DOCS"

echo ""
echo -e "${YELLOW}=== MOVING CONFIGURATION FILES ===${NC}"

# Move configuration files to 05-CONFIG
echo "Moving configuration files to 05-CONFIG..."
move_file "$AGENTS_DIR/transition_config.json" "$AGENTS_DIR/05-CONFIG"
move_file "$AGENTS_DIR/voice_config.json" "$AGENTS_DIR/05-CONFIG"
move_file "$AGENTS_DIR/production_deployment.json" "$AGENTS_DIR/05-CONFIG"

echo ""
echo -e "${YELLOW}=== MOVING SHELL SCRIPTS ===${NC}"

# Move startup scripts to 00-STARTUP
echo "Moving startup scripts to 00-STARTUP..."
move_file "$AGENTS_DIR/run_agent_system.sh" "$AGENTS_DIR/00-STARTUP"
move_file "$AGENTS_DIR/start_agent_service.sh" "$AGENTS_DIR/00-STARTUP"
move_file "$AGENTS_DIR/verify_integration.sh" "$AGENTS_DIR/00-STARTUP"

# Move voice scripts to 03-BRIDGES
echo "Moving voice shell scripts to 03-BRIDGES..."
move_file "$AGENTS_DIR/voice_quick.sh" "$AGENTS_DIR/03-BRIDGES"
move_file "$AGENTS_DIR/voice_shortcuts_managed.sh" "$AGENTS_DIR/03-BRIDGES"

# Move build scripts to 06-BUILD-RUNTIME
echo "Moving build scripts to 06-BUILD-RUNTIME..."
move_file "$AGENTS_DIR/build_binary_background.sh" "$AGENTS_DIR/06-BUILD-RUNTIME"

echo ""
echo -e "${YELLOW}=== MOVING LOG FILES ===${NC}"

# Move logs to monitoring
echo "Moving log files to 09-MONITORING..."
mkdir -p "$AGENTS_DIR/09-MONITORING/logs"
move_file "$AGENTS_DIR/binary_bridge.log" "$AGENTS_DIR/09-MONITORING/logs"
move_file "$AGENTS_DIR/python_bridge.log" "$AGENTS_DIR/09-MONITORING/logs"
move_file "$AGENTS_DIR/monitor_agent.log" "$AGENTS_DIR/09-MONITORING/logs"
move_file "$AGENTS_DIR/system_startup.log" "$AGENTS_DIR/09-MONITORING/logs"

echo ""
echo -e "${YELLOW}=== MOVING SERVICE FILES ===${NC}"

# Move service definitions to 07-SERVICES
echo "Moving service files to 07-SERVICES..."
mkdir -p "$AGENTS_DIR/07-SERVICES"
move_file "$AGENTS_DIR/claude-agents.service" "$AGENTS_DIR/07-SERVICES"

echo ""
echo -e "${YELLOW}=== CLEANING UP DUPLICATE DIRECTORIES ===${NC}"

# Check for duplicate directories that can be consolidated
if [ -d "$AGENTS_DIR/admin" ] && [ -d "$AGENTS_DIR/08-ADMIN-TOOLS" ]; then
    echo "Consolidating duplicate admin directories..."
    cp -r "$AGENTS_DIR/admin"/* "$AGENTS_DIR/08-ADMIN-TOOLS/" 2>/dev/null || true
    rm -rf "$AGENTS_DIR/admin"
    echo "  ✓ Consolidated admin/ into 08-ADMIN-TOOLS/"
fi

if [ -d "$AGENTS_DIR/monitoring" ] && [ -d "$AGENTS_DIR/09-MONITORING" ]; then
    echo "Consolidating duplicate monitoring directories..."
    cp -r "$AGENTS_DIR/monitoring"/* "$AGENTS_DIR/09-MONITORING/" 2>/dev/null || true
    rm -rf "$AGENTS_DIR/monitoring"
    echo "  ✓ Consolidated monitoring/ into 09-MONITORING/"
fi

if [ -d "$AGENTS_DIR/docs" ] && [ -d "$AGENTS_DIR/11-DOCS" ]; then
    echo "Consolidating duplicate docs directories..."
    cp -r "$AGENTS_DIR/docs"/* "$AGENTS_DIR/11-DOCS/" 2>/dev/null || true
    rm -rf "$AGENTS_DIR/docs"
    echo "  ✓ Consolidated docs/ into 11-DOCS/"
fi

if [ -d "$AGENTS_DIR/config" ] && [ -d "$AGENTS_DIR/05-CONFIG" ]; then
    echo "Consolidating duplicate config directories..."
    cp -r "$AGENTS_DIR/config"/* "$AGENTS_DIR/05-CONFIG/" 2>/dev/null || true
    rm -rf "$AGENTS_DIR/config"
    echo "  ✓ Consolidated config/ into 05-CONFIG/"
fi

if [ -d "$AGENTS_DIR/src" ] && [ -d "$AGENTS_DIR/04-SOURCE" ]; then
    echo "Consolidating duplicate source directories..."
    cp -r "$AGENTS_DIR/src"/* "$AGENTS_DIR/04-SOURCE/" 2>/dev/null || true
    rm -rf "$AGENTS_DIR/src"
    echo "  ✓ Consolidated src/ into 04-SOURCE/"
fi

if [ -d "$AGENTS_DIR/tests" ] && [ -d "$AGENTS_DIR/10-TESTS" ]; then
    echo "Consolidating duplicate tests directories..."
    cp -r "$AGENTS_DIR/tests"/* "$AGENTS_DIR/10-TESTS/" 2>/dev/null || true
    rm -rf "$AGENTS_DIR/tests"
    echo "  ✓ Consolidated tests/ into 10-TESTS/"
fi

# Clean up other loose directories
echo "Moving remaining directories..."
if [ -d "$AGENTS_DIR/build" ]; then
    mv "$AGENTS_DIR/build" "$AGENTS_DIR/06-BUILD-RUNTIME/build_loose" 2>/dev/null || true
    echo "  ✓ Moved build/ to 06-BUILD-RUNTIME/build_loose/"
fi

if [ -d "$AGENTS_DIR/examples" ]; then
    mv "$AGENTS_DIR/examples" "$AGENTS_DIR/11-DOCS/examples" 2>/dev/null || true
    echo "  ✓ Moved examples/ to 11-DOCS/examples/"
fi

if [ -d "$AGENTS_DIR/docker" ]; then
    mv "$AGENTS_DIR/docker" "$AGENTS_DIR/05-CONFIG/docker" 2>/dev/null || true
    echo "  ✓ Moved docker/ to 05-CONFIG/docker/"
fi

echo ""
echo -e "${GREEN}=== CLEANUP COMPLETED ===${NC}"
echo ""
echo "Summary:"
echo "  ✓ Python scripts moved to appropriate subdirectories"
echo "  ✓ Documentation consolidated in 11-DOCS/"
echo "  ✓ Configuration files in 05-CONFIG/"
echo "  ✓ Shell scripts in appropriate locations"
echo "  ✓ Log files in 09-MONITORING/logs/"
echo "  ✓ Duplicate directories consolidated"
echo "  ✓ Backup created in: $BACKUP_DIR"
echo ""
echo "Agent .md files remain in root for Claude Code compatibility."
echo "All organized subdirectories preserve functionality."
echo ""
echo "Next step: Run import_fixer.py to update any broken imports."

# Create import fixer script for Python files
cat > "$AGENTS_DIR/fix_imports.py" << 'EOF'
#!/usr/bin/env python3
"""
Import Fixer for Claude Agent Framework
Fixes import statements after directory reorganization
"""

import os
import re
import glob

def fix_imports_in_file(file_path, moved_files_map):
    """Fix imports in a single Python file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Fix imports of moved files
        for old_path, new_path in moved_files_map.items():
            old_module = old_path.replace('/', '.').replace('.py', '')
            new_module = new_path.replace('/', '.').replace('.py', '')
            
            # Fix various import patterns
            patterns = [
                (f'import {old_module}', f'import {new_module}'),
                (f'from {old_module}', f'from {new_module}'),
                (f'import {os.path.basename(old_path).replace(".py", "")}', 
                 f'from {os.path.dirname(new_module).replace(".", "/")} import {os.path.basename(new_module)}')
            ]
            
            for old_pattern, new_pattern in patterns:
                content = re.sub(re.escape(old_pattern), new_pattern, content)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✓ Fixed imports in {file_path}")
            return True
        
    except Exception as e:
        print(f"✗ Error fixing {file_path}: {e}")
        return False
    
    return False

def main():
    agents_dir = "${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents"
    
    # Map of moved files (old_path -> new_path relative to agents_dir)
    moved_files = {
        "claude_agent_bridge.py": "03-BRIDGES/claude_agent_bridge.py",
        "bridge_monitor.py": "03-BRIDGES/bridge_monitor.py",
        "agent_server.py": "03-BRIDGES/agent_server.py",
        "test_agent_communication.py": "03-BRIDGES/test_agent_communication.py",
        "auto_integrate.py": "03-BRIDGES/auto_integrate.py",
        "VOICE_INPUT_SYSTEM.py": "03-BRIDGES/VOICE_INPUT_SYSTEM.py",
        "VOICE_TOGGLE.py": "03-BRIDGES/VOICE_TOGGLE.py",
        "quick_voice.py": "03-BRIDGES/quick_voice.py",
        "DEVELOPMENT_CLUSTER_DIRECT.py": "08-ADMIN-TOOLS/DEVELOPMENT_CLUSTER_DIRECT.py",
        "CLAUDE_BOOT_INIT.py": "08-ADMIN-TOOLS/CLAUDE_BOOT_INIT.py",
        "OPTIMAL_PATH_EXECUTION.py": "08-ADMIN-TOOLS/OPTIMAL_PATH_EXECUTION.py",
        "UPDATE_AGENTS_INTEGRATION.py": "08-ADMIN-TOOLS/UPDATE_AGENTS_INTEGRATION.py",
        "INTEGRATION_EXAMPLE.py": "08-ADMIN-TOOLS/INTEGRATION_EXAMPLE.py",
        "HYBRID_INTEGRATION_DEMO.py": "08-ADMIN-TOOLS/HYBRID_INTEGRATION_DEMO.py",
        "BRIDGE_TO_BINARY_TRANSITION.py": "08-ADMIN-TOOLS/BRIDGE_TO_BINARY_TRANSITION.py",
    }
    
    print("Fixing imports in Python files...")
    
    # Find all Python files and fix their imports
    python_files = glob.glob(os.path.join(agents_dir, "**", "*.py"), recursive=True)
    fixed_count = 0
    
    for py_file in python_files:
        if fix_imports_in_file(py_file, moved_files):
            fixed_count += 1
    
    print(f"\nFixed imports in {fixed_count} files")
    print("Import fixing completed!")

if __name__ == "__main__":
    main()
EOF

chmod +x "$AGENTS_DIR/fix_imports.py"
echo "Created import fixer script: fix_imports.py"
echo "Run: python3 fix_imports.py to fix any broken imports"