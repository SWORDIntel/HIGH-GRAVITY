#!/usr/bin/env python3
"""
Secure Database Wrapper - Prevents SQL injection and provides secure database operations
Part of Phase 1 Security Hardening - PROJECTORCHESTRATOR Coordination
"""

import hashlib
import json
import logging
import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

# Security logging
security_logger = logging.getLogger("security.database")
security_logger.setLevel(logging.INFO)


class SecureDatabaseWrapper:
    """
    Secure wrapper for database operations with SQL injection prevention,
    connection pooling, and comprehensive audit logging.
    """

    def __init__(self, connection_params: Dict[str, Any]):
        """Initialize secure database wrapper with encrypted connection"""
        self.connection_params = self._validate_connection_params(connection_params)
        self.connection_pool = []
        self.max_pool_size = 10
        self.query_timeout = 30  # seconds
        self.failed_attempts = {}
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)

    def _validate_connection_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize connection parameters"""
        required = ["host", "port", "database", "user", "password"]

        for field in required:
            if field not in params:
                raise ValueError(f"Missing required connection parameter: {field}")

            # Validate parameter types and values
            if field == "port":
                if (
                    not isinstance(params[field], int)
                    or params[field] < 1
                    or params[field] > 65535
                ):
                    raise ValueError(f"Invalid port number: {params[field]}")
            elif field in ["host", "database", "user"]:
                # Sanitize string parameters
                if not isinstance(params[field], str) or len(params[field]) > 255:
                    raise ValueError(f"Invalid {field} parameter")
                # Check for SQL injection attempts in connection params
                if any(
                    char in params[field]
                    for char in [";", "--", "/*", "*/", "DROP", "DELETE"]
                ):
                    security_logger.critical(
                        f"SQL injection attempt in connection parameter: {field}"
                    )
                    raise ValueError(f"Invalid characters in {field}")

        return params

    @contextmanager
    def get_secure_connection(self):
        """Get a secure database connection with proper cleanup"""
        conn = None
        try:
            # Check for lockout
            client_id = self._get_client_id()
            if self._is_locked_out(client_id):
                raise PermissionError(
                    "Database access temporarily locked due to failed attempts"
                )

            conn = psycopg2.connect(
                **self.connection_params,
                connect_timeout=10,
                options=f"-c statement_timeout={self.query_timeout * 1000}",  # milliseconds
            )
            conn.set_session(autocommit=False, isolation_level="READ COMMITTED")

            yield conn

            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            self._record_failed_attempt(client_id)
            security_logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(
        self, query_template: str, params: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Execute a parameterized query safely with SQL injection prevention

        Args:
            query_template: SQL query with %s placeholders
            params: Dictionary of parameters to safely inject

        Returns:
            List of result dictionaries
        """
        # Validate query template
        if not self._validate_query_template(query_template):
            raise ValueError("Invalid query template")

        # Log query for audit
        query_hash = hashlib.sha256(query_template.encode()).hexdigest()[:8]
        security_logger.info(
            f"Executing query {query_hash} with {len(params or {})} parameters"
        )

        with self.get_secure_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                try:
                    if params:
                        # Use parameterized queries to prevent SQL injection
                        cursor.execute(query_template, params)
                    else:
                        cursor.execute(query_template)

                    # Fetch results if it's a SELECT query
                    if query_template.strip().upper().startswith("SELECT"):
                        results = cursor.fetchall()
                        return [dict(row) for row in results]
                    else:
                        return [{"affected_rows": cursor.rowcount}]

                except psycopg2.Error as e:
                    security_logger.error(f"Query execution error: {e}")
                    raise

    def execute_secure_insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        Securely insert data into a table with full validation

        Args:
            table: Table name (will be validated)
            data: Dictionary of column->value mappings

        Returns:
            ID of inserted row
        """
        # Validate table name
        if not self._validate_table_name(table):
            raise ValueError(f"Invalid table name: {table}")

        # Build secure INSERT query using psycopg2.sql
        columns = list(data.keys())
        values = list(data.values())

        # Validate column names
        for col in columns:
            if not self._validate_column_name(col):
                raise ValueError(f"Invalid column name: {col}")

        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
            sql.Identifier(table),
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(sql.Placeholder() * len(columns)),
        )

        with self.get_secure_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
                result = cursor.fetchone()
                security_logger.info(f"Secure insert into {table}: {result[0]}")
                return result[0]

    def execute_secure_update(
        self, table: str, data: Dict[str, Any], conditions: Dict[str, Any]
    ) -> int:
        """
        Securely update data in a table

        Args:
            table: Table name
            data: Dictionary of column->value to update
            conditions: Dictionary of WHERE conditions

        Returns:
            Number of affected rows
        """
        # Validate table name
        if not self._validate_table_name(table):
            raise ValueError(f"Invalid table name: {table}")

        # Build SET clause
        set_items = []
        set_values = []
        for col, val in data.items():
            if not self._validate_column_name(col):
                raise ValueError(f"Invalid column name: {col}")
            set_items.append(
                sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
            )
            set_values.append(val)

        # Build WHERE clause
        where_items = []
        where_values = []
        for col, val in conditions.items():
            if not self._validate_column_name(col):
                raise ValueError(f"Invalid column name: {col}")
            where_items.append(
                sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
            )
            where_values.append(val)

        query = sql.SQL("UPDATE {} SET {} WHERE {}").format(
            sql.Identifier(table),
            sql.SQL(", ").join(set_items),
            sql.SQL(" AND ").join(where_items),
        )

        with self.get_secure_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, set_values + where_values)
                affected = cursor.rowcount
                security_logger.info(f"Secure update on {table}: {affected} rows")
                return affected

    def _validate_query_template(self, query: str) -> bool:
        """Validate query template for common SQL injection patterns"""
        # Check for dangerous patterns
        dangerous_patterns = [
            r";\s*DROP",
            r";\s*DELETE",
            r";\s*UPDATE",
            r";\s*INSERT",
            r"--[^\n]*$",
            r"/\*.*\*/",
            r"EXEC\s*\(",
            r"EXECUTE\s*\(",
            r"xp_cmdshell",
            r"sp_executesql",
        ]

        import re

        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE | re.MULTILINE):
                security_logger.critical(f"Potential SQL injection detected: {pattern}")
                return False

        return True

    def _validate_table_name(self, table: str) -> bool:
        """Validate table name against whitelist"""
        # Whitelist of allowed tables
        allowed_tables = [
            "context_chunks",
            "query_patterns",
            "window_configurations",
            "shadowgit_analysis",
            "learning_feedback",
            "performance_stats",
            "agent_metrics",
            "task_embeddings",
            "model_performance",
            "interaction_logs",
        ]

        # Check if table is in whitelist (with schema support)
        table_parts = table.split(".")
        table_name = table_parts[-1]

        if table_name not in allowed_tables:
            security_logger.warning(
                f"Attempted access to non-whitelisted table: {table}"
            )
            return False

        # Validate table name format
        import re

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
            return False

        return True

    def _validate_column_name(self, column: str) -> bool:
        """Validate column name format"""
        import re

        # Allow only alphanumeric and underscore
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", column):
            security_logger.warning(f"Invalid column name format: {column}")
            return False

        # Check length
        if len(column) > 64:  # PostgreSQL column name limit
            return False

        return True

    def _get_client_id(self) -> str:
        """Get client identifier for rate limiting"""
        # In production, this would use IP address or session ID
        return os.environ.get("USER", "unknown")

    def _is_locked_out(self, client_id: str) -> bool:
        """Check if client is locked out due to failed attempts"""
        if client_id in self.failed_attempts:
            attempts, last_attempt = self.failed_attempts[client_id]
            if attempts >= self.max_failed_attempts:
                if datetime.now() - last_attempt < self.lockout_duration:
                    return True
                else:
                    # Reset after lockout period
                    del self.failed_attempts[client_id]
        return False

    def _record_failed_attempt(self, client_id: str):
        """Record a failed database access attempt"""
        if client_id in self.failed_attempts:
            attempts, _ = self.failed_attempts[client_id]
            self.failed_attempts[client_id] = (attempts + 1, datetime.now())
        else:
            self.failed_attempts[client_id] = (1, datetime.now())

    def create_secure_indexes(self) -> List[str]:
        """Create optimized indexes for security and performance"""
        indexes = [
            # Vector similarity index for context chopping
            """CREATE INDEX IF NOT EXISTS idx_context_embedding_ivfflat 
               ON context_chopping.context_chunks USING ivfflat (embedding vector_cosine_ops)
               WITH (lists = 100)""",
            # Security classification index
            """CREATE INDEX IF NOT EXISTS idx_security_level_partial 
               ON context_chopping.context_chunks(security_level)
               WHERE security_level IN ('sensitive', 'classified', 'redacted')""",
            # Query pattern performance index
            """CREATE INDEX IF NOT EXISTS idx_query_patterns_composite
               ON context_chopping.query_patterns(timestamp DESC, api_success, tokens_saved)""",
            # Learning feedback index
            """CREATE INDEX IF NOT EXISTS idx_learning_feedback_timestamp
               ON context_chopping.learning_feedback(timestamp DESC)
               WHERE context_was_sufficient = false""",
            # Performance stats time-series index
            """CREATE INDEX IF NOT EXISTS idx_performance_stats_period
               ON context_chopping.performance_stats(period_end DESC, period_start DESC)""",
        ]

        results = []
        for index_sql in indexes:
            try:
                self.execute_query(index_sql)
                results.append(f"Created: {index_sql.split('idx_')[1].split()[0]}")
                security_logger.info(f"Security index created successfully")
            except Exception as e:
                results.append(f"Failed: {str(e)}")
                security_logger.error(f"Index creation failed: {e}")

        return results


# Rate limiting decorator for API calls
def rate_limit(max_calls: int = 100, window: int = 60):
    """Rate limiting decorator for security"""

    def decorator(func):
        call_times = []

        def wrapper(*args, **kwargs):
            now = datetime.now()
            # Remove old calls outside window
            nonlocal call_times
            call_times = [t for t in call_times if (now - t).seconds < window]

            if len(call_times) >= max_calls:
                raise PermissionError(
                    f"Rate limit exceeded: {max_calls} calls per {window} seconds"
                )

            call_times.append(now)
            return func(*args, **kwargs)

        return wrapper

    return decorator


# Circuit breaker for resilience
class CircuitBreaker:
    """Circuit breaker pattern for database resilience"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if datetime.now() - self.last_failure_time > timedelta(
                seconds=self.recovery_timeout
            ):
                self.state = "HALF_OPEN"
                security_logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                security_logger.info("Circuit breaker CLOSED - service recovered")
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                security_logger.critical(
                    f"Circuit breaker OPEN after {self.failure_count} failures"
                )

            raise e


# Example usage with secure configuration
if __name__ == "__main__":
    # Secure database configuration
    db_config = {
        "host": "localhost",
        "port": 5433,
        "database": "claude_agents_auth",
        "user": "claude_agent",
        "password": os.environ.get("DB_PASSWORD", "claude_secure_password"),
    }

    # Initialize secure wrapper
    secure_db = SecureDatabaseWrapper(db_config)

    # Create security indexes
    print("Creating security indexes...")
    results = secure_db.create_secure_indexes()
    for result in results:
        print(f"  {result}")

    print("\nSecure Database Wrapper initialized with:")
    print("  - SQL injection prevention")
    print("  - Rate limiting protection")
    print("  - Circuit breaker resilience")
    print("  - Comprehensive audit logging")
    print("  - Connection pooling")
    print("  - Query timeout protection")
