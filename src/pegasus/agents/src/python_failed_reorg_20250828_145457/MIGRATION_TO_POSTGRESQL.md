---
name: Migration To Postgresql
---
# Migration from SQLite to PostgreSQL Learning System

## Status

We have successfully migrated from SQLite to PostgreSQL for the learning system. The old SQLite-based files are now **DEPRECATED** and should not be used.

## File Status

### ✅ Active (PostgreSQL-based)
- `postgresql_learning_system.py` - Main PostgreSQL learning system
- `setup_learning_system.py` - PostgreSQL setup and configuration
- `postgresql_learning_integration.py` - PostgreSQL integration utilities

### ⚠️ DEPRECATED (SQLite-based)
- `agent_learning_system.py` - **DO NOT USE** - Uses SQLite, replaced by PostgreSQL version

### 📝 Need Update
- `learning_orchestrator_bridge.py` - Currently imports deprecated `agent_learning_system.py`
- `learning_cli.py` - Currently imports deprecated `agent_learning_system.py`

## Migration Path

### For `learning_orchestrator_bridge.py`:
```python
# OLD (remove):
from agent_learning_system import AgentLearningSystem, TaskExecution, LearningEnabledOrchestrator

# NEW (use):
from postgresql_learning_system import PostgreSQLLearningSystem as AgentLearningSystem
from postgresql_learning_system import TaskExecution
```

### For `learning_cli.py`:
```python
# OLD (remove):
from agent_learning_system import AgentLearningSystem, TaskExecution

# NEW (use):
from postgresql_learning_system import PostgreSQLLearningSystem as AgentLearningSystem
from postgresql_learning_system import TaskExecution
```

## Key Differences

### Database Connection
**SQLite (old):**
```python
learning = AgentLearningSystem(db_path="agent_learning.db")
```

**PostgreSQL (new):**
```python
learning = PostgreSQLLearningSystem()
await learning.connect()
# ... use learning system ...
await learning.close()
```

### Async Operations
- SQLite version: Synchronous operations
- PostgreSQL version: Async operations (use `await`)

### Data Persistence
- SQLite: Local file `agent_learning.db`
- PostgreSQL: Centralized database on port 5433, data in `database/data/postgresql/`

### Data Export/Import
- SQLite: Manual backup of `.db` file
- PostgreSQL: Automatic export to `database/learning_data/` for GitHub sync

## Benefits of PostgreSQL

1. **Concurrent Access**: Multiple agents can read/write simultaneously
2. **Better Performance**: Optimized queries and indexes
3. **GitHub Sync**: Learning data automatically exports for version control
4. **Scalability**: Can handle much larger datasets
5. **Advanced Features**: JSON support, stored procedures, triggers
6. **Data Integrity**: ACID compliance, better transaction support

## Action Items

1. ✅ Create PostgreSQL-based learning system
2. ✅ Set up database initialization scripts
3. ✅ Create data export/import for GitHub sync
4. ⚠️ Update `learning_orchestrator_bridge.py` to use PostgreSQL
5. ⚠️ Update `learning_cli.py` to use PostgreSQL
6. ⚠️ Move `agent_learning_system.py` to deprecated folder
7. ⚠️ Test all integrations with PostgreSQL

## Recommendation

**DO NOT USE** `agent_learning_system.py` anymore. It's based on SQLite which we've migrated away from. Use `postgresql_learning_system.py` instead for all new development.

The SQLite version should be moved to a `deprecated/` folder to avoid confusion.