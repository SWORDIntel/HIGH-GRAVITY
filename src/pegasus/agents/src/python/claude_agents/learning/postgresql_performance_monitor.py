#!/usr/bin/env python3
"""
PostgreSQL Performance Monitor for Team Alpha
==============================================
Real-time performance monitoring and metrics collection for async pipeline

Integrates with Docker PostgreSQL container on port 5433
Provides comprehensive performance tracking for 10x speedup validation
"""

import asyncio
import json
import logging
import queue
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras


@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    timestamp: float
    metric_name: str
    metric_value: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class PostgreSQLPerformanceMonitor:
    """Real-time PostgreSQL performance monitoring"""
    
    def __init__(self, host="localhost", port=5433, user="claude_agent", password="claude_secure_2024", database="claude_agents_auth"):
        self.connection_params = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database
        }
        
        self.connection = None
        self.monitoring_active = False
        
        # Performance metrics storage
        self.metrics_buffer = deque(maxlen=10000)
        self.real_time_stats = {}
        
        # Metric calculation windows
        self.throughput_window = deque(maxlen=100)
        self.latency_samples = deque(maxlen=1000)
        
        # Performance thresholds (from Phase 2 report)
        self.baseline_performance = {
            "avg_response_time_ms": 8.8,  # Phase 2 first run
            "cached_response_time_ms": 0.01,  # Phase 2 cached
            "baseline_speedup": 1226.7
        }
        
    async def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitoring_active:
            return
            
        try:
            # Establish database connection
            self.connection = psycopg2.connect(**self.connection_params)
            self.connection.autocommit = True
            
            self.monitoring_active = True
            
            # Start monitoring tasks
            asyncio.create_task(self._monitor_database_stats())
            asyncio.create_task(self._monitor_connection_stats())
            asyncio.create_task(self._monitor_query_performance())
            asyncio.create_task(self._calculate_performance_metrics())
            
            logging.info("PostgreSQL performance monitoring started")
            
        except Exception as e:
            logging.error(f"Failed to start PostgreSQL monitoring: {e}")
            self.monitoring_active = False
            raise
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        
        if self.connection:
            self.connection.close()
            self.connection = None
            
        logging.info("PostgreSQL performance monitoring stopped")
    
    async def _monitor_database_stats(self):
        """Monitor database-level statistics"""
        while self.monitoring_active:
            try:
                cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # Get database statistics
                cursor.execute("""
                    SELECT 
                        numbackends,
                        xact_commit,
                        xact_rollback,
                        blks_read,
                        blks_hit,
                        tup_returned,
                        tup_fetched,
                        tup_inserted,
                        tup_updated,
                        tup_deleted
                    FROM pg_stat_database 
                    WHERE datname = %s
                """, (self.connection_params["database"],))
                
                result = cursor.fetchone()
                if result:
                    timestamp = time.time()
                    
                    # Store individual metrics
                    for key, value in result.items():
                        if value is not None:
                            metric = PerformanceMetric(
                                timestamp=timestamp,
                                metric_name=f"db_{key}",
                                metric_value=float(value),
                                metadata={"category": "database_stats"}
                            )
                            self.metrics_buffer.append(metric)
                    
                    # Calculate cache hit ratio
                    if result['blks_read'] + result['blks_hit'] > 0:
                        cache_hit_ratio = result['blks_hit'] / (result['blks_read'] + result['blks_hit'])
                        cache_metric = PerformanceMetric(
                            timestamp=timestamp,
                            metric_name="cache_hit_ratio",
                            metric_value=cache_hit_ratio * 100,
                            metadata={"category": "performance", "unit": "percent"}
                        )
                        self.metrics_buffer.append(cache_metric)
                
                cursor.close()
                await asyncio.sleep(5.0)  # Update every 5 seconds
                
            except Exception as e:
                logging.error(f"Database stats monitoring error: {e}")
                await asyncio.sleep(10.0)
    
    async def _monitor_connection_stats(self):
        """Monitor connection and activity statistics"""
        while self.monitoring_active:
            try:
                cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # Get connection statistics
                cursor.execute("""
                    SELECT 
                        state,
                        COUNT(*) as connection_count
                    FROM pg_stat_activity
                    WHERE datname = %s
                    GROUP BY state
                """, (self.connection_params["database"],))
                
                results = cursor.fetchall()
                timestamp = time.time()
                
                total_connections = 0
                active_connections = 0
                
                for result in results:
                    connection_count = result['connection_count']
                    total_connections += connection_count
                    
                    if result['state'] == 'active':
                        active_connections = connection_count
                    
                    metric = PerformanceMetric(
                        timestamp=timestamp,
                        metric_name=f"connections_{result['state'] or 'idle'}",
                        metric_value=float(connection_count),
                        metadata={"category": "connections"}
                    )
                    self.metrics_buffer.append(metric)
                
                # Store total and active connections
                total_metric = PerformanceMetric(
                    timestamp=timestamp,
                    metric_name="total_connections",
                    metric_value=float(total_connections),
                    metadata={"category": "connections"}
                )
                self.metrics_buffer.append(total_metric)
                
                active_metric = PerformanceMetric(
                    timestamp=timestamp,
                    metric_name="active_connections", 
                    metric_value=float(active_connections),
                    metadata={"category": "connections"}
                )
                self.metrics_buffer.append(active_metric)
                
                cursor.close()
                await asyncio.sleep(3.0)  # Update every 3 seconds
                
            except Exception as e:
                logging.error(f"Connection stats monitoring error: {e}")
                await asyncio.sleep(10.0)
    
    async def _monitor_query_performance(self):
        """Monitor query performance and execution stats"""
        while self.monitoring_active:
            try:
                cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # Get query statistics if pg_stat_statements is available
                cursor.execute("""
                    SELECT 
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        max_exec_time,
                        min_exec_time,
                        rows
                    FROM pg_stat_statements
                    WHERE query LIKE '%agent%' OR query LIKE '%claude%'
                    ORDER BY calls DESC
                    LIMIT 10
                """)
                
                results = cursor.fetchall()
                timestamp = time.time()
                
                for i, result in enumerate(results):
                    if result['calls'] and result['calls'] > 0:
                        # Store query performance metrics
                        for metric_name in ['calls', 'total_exec_time', 'mean_exec_time', 'max_exec_time', 'min_exec_time', 'rows']:
                            if result[metric_name] is not None:
                                metric = PerformanceMetric(
                                    timestamp=timestamp,
                                    metric_name=f"query_{metric_name}_top{i+1}",
                                    metric_value=float(result[metric_name]),
                                    metadata={"category": "query_performance", "query_rank": i+1}
                                )
                                self.metrics_buffer.append(metric)
                        
                        # Add to latency samples for real-time calculation
                        if result['mean_exec_time']:
                            self.latency_samples.append(float(result['mean_exec_time']))
                
                cursor.close()
                await asyncio.sleep(10.0)  # Update every 10 seconds
                
            except Exception as e:
                # pg_stat_statements might not be available
                logging.debug(f"Query performance monitoring error (likely pg_stat_statements not available): {e}")
                await asyncio.sleep(30.0)
    
    async def _calculate_performance_metrics(self):
        """Calculate derived performance metrics"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(2.0)  # Calculate every 2 seconds
                
                current_time = time.time()
                
                # Calculate throughput (operations per second)
                recent_metrics = [m for m in self.metrics_buffer if current_time - m.timestamp < 60]  # Last minute
                
                if recent_metrics:
                    # Count different types of operations
                    operation_counts = defaultdict(int)
                    for metric in recent_metrics:
                        if 'tup_' in metric.metric_name or 'xact_' in metric.metric_name:
                            operation_counts[metric.metric_name] += metric.metric_value
                    
                    # Calculate operations per second
                    for operation, count in operation_counts.items():
                        if count > 0:
                            ops_per_second = count / 60.0  # Operations in last minute
                            
                            throughput_metric = PerformanceMetric(
                                timestamp=current_time,
                                metric_name=f"{operation}_per_second",
                                metric_value=ops_per_second,
                                metadata={"category": "throughput", "unit": "ops_per_second"}
                            )
                            self.metrics_buffer.append(throughput_metric)
                            self.throughput_window.append(ops_per_second)
                
                # Calculate current speedup vs baseline
                if self.latency_samples:
                    current_avg_latency = sum(self.latency_samples) / len(self.latency_samples)
                    baseline_latency = self.baseline_performance["avg_response_time_ms"]
                    
                    if current_avg_latency > 0 and baseline_latency > 0:
                        current_speedup = baseline_latency / current_avg_latency
                        
                        speedup_metric = PerformanceMetric(
                            timestamp=current_time,
                            metric_name="current_speedup_vs_baseline",
                            metric_value=current_speedup,
                            metadata={"category": "performance", "baseline": baseline_latency}
                        )
                        self.metrics_buffer.append(speedup_metric)
                
                # Update real-time stats
                self._update_real_time_stats()
                
            except Exception as e:
                logging.error(f"Performance calculation error: {e}")
                await asyncio.sleep(5.0)
    
    def _update_real_time_stats(self):
        """Update real-time statistics summary"""
        current_time = time.time()
        recent_window = 300  # Last 5 minutes
        
        recent_metrics = [m for m in self.metrics_buffer if current_time - m.timestamp < recent_window]
        
        if not recent_metrics:
            return
        
        # Group metrics by category
        by_category = defaultdict(list)
        for metric in recent_metrics:
            category = metric.metadata.get("category", "unknown")
            by_category[category].append(metric)
        
        stats = {}
        
        # Database performance stats
        db_metrics = by_category.get("database_stats", [])
        if db_metrics:
            latest_db = max(db_metrics, key=lambda m: m.timestamp)
            stats["database"] = {
                "active_connections": next((m.metric_value for m in db_metrics if m.metric_name == "db_numbackends"), 0),
                "cache_hit_ratio": next((m.metric_value for m in by_category.get("performance", []) if m.metric_name == "cache_hit_ratio"), 0),
                "transactions_committed": next((m.metric_value for m in db_metrics if m.metric_name == "db_xact_commit"), 0)
            }
        
        # Throughput stats
        throughput_metrics = by_category.get("throughput", [])
        if throughput_metrics:
            avg_throughput = sum(m.metric_value for m in throughput_metrics) / len(throughput_metrics)
            max_throughput = max(m.metric_value for m in throughput_metrics)
            stats["throughput"] = {
                "avg_ops_per_second": avg_throughput,
                "max_ops_per_second": max_throughput,
                "samples": len(throughput_metrics)
            }
        
        # Performance comparison
        perf_metrics = by_category.get("performance", [])
        speedup_metrics = [m for m in perf_metrics if m.metric_name == "current_speedup_vs_baseline"]
        if speedup_metrics:
            latest_speedup = max(speedup_metrics, key=lambda m: m.timestamp)
            stats["performance"] = {
                "current_speedup": latest_speedup.metric_value,
                "baseline_performance": self.baseline_performance,
                "improvement_factor": latest_speedup.metric_value / self.baseline_performance.get("baseline_speedup", 1)
            }
        
        self.real_time_stats = stats
    
    def get_current_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        return {
            "timestamp": time.time(),
            "monitoring_active": self.monitoring_active,
            "metrics_collected": len(self.metrics_buffer),
            "real_time_stats": self.real_time_stats.copy(),
            "baseline_comparison": {
                "phase2_baseline_speedup": self.baseline_performance["baseline_speedup"],
                "current_performance": self.real_time_stats.get("performance", {}),
                "database_health": self.real_time_stats.get("database", {}),
                "throughput_metrics": self.real_time_stats.get("throughput", {})
            }
        }
    
    async def record_pipeline_performance(self, task_id: str, processing_time: float, components_used: List[str]):
        """Record async pipeline performance in database"""
        if not self.monitoring_active or not self.connection:
            return
            
        try:
            cursor = self.connection.cursor()
            
            # Insert performance record
            cursor.execute("""
                INSERT INTO pipeline_performance 
                (task_id, processing_time_ms, components_used, timestamp) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                task_id,
                processing_time * 1000,  # Convert to milliseconds
                json.dumps(components_used),
                time.time()
            ))
            
            cursor.close()
            
        except Exception as e:
            # Table might not exist - create it
            try:
                cursor = self.connection.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pipeline_performance (
                        id SERIAL PRIMARY KEY,
                        task_id VARCHAR(255) UNIQUE,
                        processing_time_ms FLOAT,
                        components_used JSONB,
                        timestamp FLOAT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Retry the insert
                cursor.execute("""
                    INSERT INTO pipeline_performance 
                    (task_id, processing_time_ms, components_used, timestamp) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    task_id,
                    processing_time * 1000,
                    json.dumps(components_used),
                    time.time()
                ))
                
                cursor.close()
                
            except Exception as create_error:
                logging.error(f"Failed to create/insert pipeline performance: {create_error}")
    
    def export_metrics_to_file(self, filename: str = None) -> str:
        """Export collected metrics to JSON file"""
        if filename is None:
            filename = f"${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}postgresql_metrics_{int(time.time())}.json"
        
        metrics_data = {
            "export_timestamp": time.time(),
            "monitoring_duration": time.time() - (self.metrics_buffer[0].timestamp if self.metrics_buffer else time.time()),
            "total_metrics": len(self.metrics_buffer),
            "real_time_stats": self.real_time_stats,
            "baseline_performance": self.baseline_performance,
            "metrics": [asdict(metric) for metric in self.metrics_buffer]
        }
        
        with open(filename, 'w') as f:
            json.dump(metrics_data, f, indent=2, default=str)
        
        logging.info(f"Exported {len(self.metrics_buffer)} metrics to {filename}")
        return filename

# Integration function for async pipeline
async def integrate_postgresql_monitoring():
    """Integration function for PostgreSQL monitoring"""
    monitor = PostgreSQLPerformanceMonitor()
    
    try:
        await monitor.start_monitoring()
        
        # Run monitoring for 30 seconds as demonstration
        print("PostgreSQL monitoring started - collecting metrics...")
        
        for i in range(6):  # 6 iterations of 5 seconds each
            await asyncio.sleep(5.0)
            summary = monitor.get_current_performance_summary()
            
            print(f"\nMonitoring Update {i+1}/6:")
            if summary["real_time_stats"]:
                if "database" in summary["real_time_stats"]:
                    db_stats = summary["real_time_stats"]["database"]
                    print(f"  Database: {db_stats.get('active_connections', 0)} connections, "
                          f"{db_stats.get('cache_hit_ratio', 0):.1f}% cache hit ratio")
                
                if "throughput" in summary["real_time_stats"]:
                    throughput = summary["real_time_stats"]["throughput"]
                    print(f"  Throughput: {throughput.get('avg_ops_per_second', 0):.1f} avg ops/sec")
                
                if "performance" in summary["real_time_stats"]:
                    perf = summary["real_time_stats"]["performance"]
                    print(f"  Performance: {perf.get('current_speedup', 0):.1f}x current speedup")
            else:
                print("  Collecting initial metrics...")
        
        # Export metrics
        export_file = monitor.export_metrics_to_file()
        print(f"\nMetrics exported to: {export_file}")
        
        return monitor.get_current_performance_summary()
        
    finally:
        await monitor.stop_monitoring()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test PostgreSQL monitoring
    results = asyncio.run(integrate_postgresql_monitoring())
    print(f"\nPostgreSQL monitoring test completed: {len(results.get('real_time_stats', {}))} metric categories")