#!/bin/bash
# Rollback script for Python reorganization
# Created: 2025-08-28T14:54:57.737545

echo "Rolling back Python source reorganization..."

# Backup current state (post-reorganization)
mv /home/ubuntu/claude-backups/agents/src/python /home/ubuntu/claude-backups/agents/src/python_failed_reorg_20250828_145457

# Extract backup
echo "Extracting backup from /home/ubuntu/claude-backups/agents/src/python_src_backup_20250828_145345.tar.gz..."
cd /home/ubuntu/claude-backups/agents/src
tar -xzf python_src_backup_20250828_145345.tar.gz

echo "✅ Rollback complete"
echo "Failed reorganization saved to: /home/ubuntu/claude-backups/agents/src/python_failed_reorg_*"
