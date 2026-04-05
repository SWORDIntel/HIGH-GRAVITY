#!/bin/bash
# Rollback script for Python reorganization
# Created: 2025-08-28T14:56:39.622070

echo "Rolling back Python source reorganization..."

# Backup current state (post-reorganization)
mv /home/john/claude-backups/agents/src/python /home/john/claude-backups/agents/src/python_failed_reorg_20250828_145639

# Extract backup
echo "Extracting backup from /home/john/claude-backups/agents/src/python_src_backup_20250828_145525.tar.gz..."
cd /home/john/claude-backups/agents/src
tar -xzf python_src_backup_20250828_145525.tar.gz

echo "✅ Rollback complete"
echo "Failed reorganization saved to: /home/john/claude-backups/agents/src/python_failed_reorg_*"
