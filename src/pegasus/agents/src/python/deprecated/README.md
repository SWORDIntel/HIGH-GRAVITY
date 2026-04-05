# Deprecated Files

This folder contains deprecated files that have been replaced by better implementations.

## Files in this folder

### agent_learning_system.py
- **Status**: DEPRECATED
- **Reason**: Uses SQLite database which has been replaced by PostgreSQL
- **Replacement**: Use `postgresql_learning_system.py` instead
- **Migration Date**: 2025-08-23

## Why these files are deprecated

We migrated from SQLite to PostgreSQL for the learning system because:

1. **Better Performance**: PostgreSQL handles concurrent access much better
2. **GitHub Sync**: PostgreSQL data can be exported/imported for repository sync
3. **Scalability**: PostgreSQL can handle much larger datasets
4. **Integration**: Works with the existing `claude_auth` database
5. **Features**: Advanced JSON support, triggers, stored procedures

## DO NOT USE

These files are kept for reference only. Do not use them in new development.

If you need the learning system, use:
- `../postgresql_learning_system.py` - Main learning system
- `../setup_learning_system.py` - Setup and configuration