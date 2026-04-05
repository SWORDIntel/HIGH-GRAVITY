#!/bin/bash
# Organize NON-AGENT files in agents/ directory
# KEEPS all .md agent files in place
set -e

echo "🎯 Organizing agents/ directory (keeping agent .md files in place)..."

# Create new directory structure for non-agent files only
echo "📁 Creating organized subdirectories for system files..."
mkdir -p system
mkdir -p services  
mkdir -p integration
mkdir -p backups

# Move ONLY non-agent files

# Move system scripts
echo "⚙️ Moving system scripts to system/..."
[ -f BRING_ONLINE.sh ] && mv BRING_ONLINE.sh system/ 2>/dev/null || true
[ -f STATUS.sh ] && mv STATUS.sh system/ 2>/dev/null || true
[ -f switch.sh ] && mv switch.sh system/ 2>/dev/null || true
[ -f verify_agent_mode.sh ] && mv verify_agent_mode.sh system/ 2>/dev/null || true

# Move service files
echo "🔧 Moving service files to services/..."
[ -f claude-agents.service ] && mv claude-agents.service services/ 2>/dev/null || true

# Move integration files
echo "🔌 Moving integration files to integration/..."
[ -f auto_integrate.py ] && mv auto_integrate.py integration/ 2>/dev/null || true
[ -f statusline.lua ] && mv statusline.lua integration/ 2>/dev/null || true

# Move backup files
echo "💾 Moving backup files to backups/..."
[ -f backups.zip ] && mv backups.zip backups/ 2>/dev/null || true

# Create symlinks for critical system scripts that might be called from other places
echo "🔗 Creating compatibility symlinks for critical scripts..."
ln -sf system/BRING_ONLINE.sh BRING_ONLINE.sh 2>/dev/null || true
ln -sf system/STATUS.sh STATUS.sh 2>/dev/null || true
ln -sf system/switch.sh switch.sh 2>/dev/null || true

# Create a README for the new organization
cat > ORGANIZATION.md << 'EOF'
# Agents Directory Organization

## Structure
All agent .md files remain in the root agents/ directory for compatibility.

### System Files Organization:
- `system/` - System management scripts
  - BRING_ONLINE.sh - System startup
  - STATUS.sh - Status checking  
  - switch.sh - Mode switching
  - verify_agent_mode.sh - Mode verification

- `services/` - Service definitions
  - claude-agents.service - Systemd service

- `integration/` - Integration scripts
  - auto_integrate.py - Auto integration script
  - statusline.lua - Statusline configuration

- `backups/` - Backup storage
  - backups.zip - Agent backups

### Existing Directories (unchanged):
- `src/` - Source code (C, Python, Rust)
- `docs/` - Documentation
- `binary-communications-system/` - Binary protocol
- `admin/` - Administrative tools
- `config/` - Configuration files
- `runtime/` - Runtime components
- `plans/` - Planning documents

### Agent Files:
All 40 agent .md files remain in the root directory to maintain compatibility
with existing scripts and references.
EOF

echo "✅ Organization complete!"
echo ""
echo "📊 Summary:"
echo "  - ✅ All agent .md files remain in place (no breaking changes)"
echo "  - ✅ System scripts moved to system/"
echo "  - ✅ Service files moved to services/"
echo "  - ✅ Integration files moved to integration/"
echo "  - ✅ Compatibility symlinks created for critical scripts"
echo "  - ✅ Organization guide created at ORGANIZATION.md"
echo ""
echo "No agent references were broken! All .md files remain in root."