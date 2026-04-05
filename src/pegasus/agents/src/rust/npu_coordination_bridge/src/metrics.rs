//! Performance metrics collection and analysis
//!
//! This module provides comprehensive performance monitoring for the NPU coordination bridge,
//! enabling real-time analysis and optimization of operations.

use std::collections::{HashMap, VecDeque};
use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use anyhow::{Result, Context};
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use tracing::{info, warn, debug, instrument};

use crate::NPUOperation;

/// Performance metrics for operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceMetrics {
    pub timestamp: u64,
    pub total_operations: u64,
    pub successful_operations: u64,
    pub failed_operations: u64,
    pub average_latency_us: f64,
    pub p95_latency_us: u64,
    pub p99_latency_us: u64,
    pub peak_latency_us: u64,
    pub throughput_ops_per_sec: f64,
    pub memory_usage_mb: f64,
    pub cpu_utilization_percent: f64,
    pub npu_utilization_percent: f64,
    pub error_rate_percent: f64,
    pub operation_breakdown: HashMap<String, OperationMetrics>,
}

/// Metrics for specific operation types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationMetrics {
    pub count: u64,
    pub average_latency_us: f64,
    pub success_rate_percent: f64,
    pub peak_throughput_ops_per_sec: f64,
    pub memory_usage_mb: f64,
}

/// Latency measurement for percentile calculations
#[derive(Debug, Clone, Copy)]
struct LatencyMeasurement {
    latency_us: u64,
    timestamp: Instant,
}

/// Metrics collector for real-time performance monitoring
pub struct MetricsCollector {
    name: String,

    // Operation tracking
    operation_counts: Arc<RwLock<HashMap<String, u64>>>,
    success_counts: Arc<RwLock<HashMap<String, u64>>>,
    failure_counts: Arc<RwLock<HashMap<String, u64>>>,

    // Latency tracking
    latency_history: Arc<RwLock<VecDeque<LatencyMeasurement>>>,
    latency_by_operation: Arc<RwLock<HashMap<String, VecDeque<u64>>>>,

    // Throughput tracking
    throughput_history: Arc<RwLock<VecDeque<(Instant, u64)>>>,

    // Resource utilization
    memory_samples: Arc<RwLock<VecDeque<(Instant, f64)>>>,
    cpu_samples: Arc<RwLock<VecDeque<(Instant, f64)>>>,
    npu_samples: Arc<RwLock<VecDeque<(Instant, f64)>>>,

    // Configuration
    history_size: usize,
    sample_interval: Duration,
}

impl Default for PerformanceMetrics {
    fn default() -> Self {
        Self {
            timestamp: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs(),
            total_operations: 0,
            successful_operations: 0,
            failed_operations: 0,
            average_latency_us: 0.0,
            p95_latency_us: 0,
            p99_latency_us: 0,
            peak_latency_us: 0,
            throughput_ops_per_sec: 0.0,
            memory_usage_mb: 0.0,
            cpu_utilization_percent: 0.0,
            npu_utilization_percent: 0.0,
            error_rate_percent: 0.0,
            operation_breakdown: HashMap::new(),
        }
    }
}

impl MetricsCollector {
    /// Create new metrics collector
    #[instrument(skip_all)]
    pub fn new(name: &str) -> Result<Self> {
        info!("Creating metrics collector: {}", name);

        Ok(Self {
            name: name.to_string(),
            operation_counts: Arc::new(RwLock::new(HashMap::new())),
            success_counts: Arc::new(RwLock::new(HashMap::new())),
            failure_counts: Arc::new(RwLock::new(HashMap::new())),
            latency_history: Arc::new(RwLock::new(VecDeque::new())),
            latency_by_operation: Arc::new(RwLock::new(HashMap::new())),
            throughput_history: Arc::new(RwLock::new(VecDeque::new())),
            memory_samples: Arc::new(RwLock::new(VecDeque::new())),
            cpu_samples: Arc::new(RwLock::new(VecDeque::new())),
            npu_samples: Arc::new(RwLock::new(VecDeque::new())),
            history_size: 10000, // Keep last 10k measurements
            sample_interval: Duration::from_millis(100), // Sample every 100ms
        })
    }

    /// Start metrics collection
    #[instrument(skip(self))]
    pub async fn start(&self) -> Result<()> {
        info!("Starting metrics collection for {}", self.name);

        // Start background sampling task
        self.start_sampling_task().await?;

        Ok(())
    }

    /// Record operation start
    #[instrument(skip(self, operation))]
    pub async fn record_operation_start(&self, operation: &NPUOperation) {
        let operation_type = self.get_operation_type(operation);

        let mut counts = self.operation_counts.write().await;
        *counts.entry(operation_type).or_insert(0) += 1;

        debug!("Recorded operation start: {}", self.get_operation_type(operation));
    }

    /// Record operation completion
    #[instrument(skip(self, result))]
    pub async fn record_operation_completion(
        &self,
        result: &crate::OperationResult,
        execution_time_us: u64,
    ) {
        let operation_type = "generic".to_string(); // Would extract from result in real implementation

        // Record latency
        {
            let mut latency_history = self.latency_history.write().await;
            latency_history.push_back(LatencyMeasurement {
                latency_us: execution_time_us,
                timestamp: Instant::now(),
            });

            // Maintain history size
            while latency_history.len() > self.history_size {
                latency_history.pop_front();
            }
        }

        // Record by operation type
        {
            let mut latency_by_op = self.latency_by_operation.write().await;
            let op_latencies = latency_by_op.entry(operation_type.clone()).or_insert_with(VecDeque::new);
            op_latencies.push_back(execution_time_us);

            while op_latencies.len() > self.history_size {
                op_latencies.pop_front();
            }
        }

        // Record success/failure
        if result.success {
            let mut successes = self.success_counts.write().await;
            *successes.entry(operation_type).or_insert(0) += 1;
        } else {
            let mut failures = self.failure_counts.write().await;
            *failures.entry(operation_type).or_insert(0) += 1;
        }

        debug!("Recorded operation completion: success={}, latency={}us", result.success, execution_time_us);
    }

    /// Get current performance metrics
    #[instrument(skip(self))]
    pub async fn get_current_metrics(&self) -> PerformanceMetrics {
        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();

        // Calculate aggregate metrics
        let (total_ops, successful_ops, failed_ops) = self.calculate_totals().await;
        let latency_stats = self.calculate_latency_statistics().await;
        let throughput = self.calculate_throughput().await;
        let resource_utilization = self.calculate_resource_utilization().await;
        let operation_breakdown = self.calculate_operation_breakdown().await;

        let error_rate = if total_ops > 0 {
            (failed_ops as f64 / total_ops as f64) * 100.0
        } else {
            0.0
        };

        PerformanceMetrics {
            timestamp,
            total_operations: total_ops,
            successful_operations: successful_ops,
            failed_operations: failed_ops,
            average_latency_us: latency_stats.average,
            p95_latency_us: latency_stats.p95,
            p99_latency_us: latency_stats.p99,
            peak_latency_us: latency_stats.peak,
            throughput_ops_per_sec: throughput,
            memory_usage_mb: resource_utilization.memory,
            cpu_utilization_percent: resource_utilization.cpu,
            npu_utilization_percent: resource_utilization.npu,
            error_rate_percent: error_rate,
            operation_breakdown,
        }
    }

    /// Record resource utilization sample
    pub async fn record_memory_usage(&self, memory_mb: f64) {
        let mut samples = self.memory_samples.write().await;
        samples.push_back((Instant::now(), memory_mb));

        while samples.len() > self.history_size {
            samples.pop_front();
        }
    }

    /// Record CPU utilization sample
    pub async fn record_cpu_utilization(&self, cpu_percent: f64) {
        let mut samples = self.cpu_samples.write().await;
        samples.push_back((Instant::now(), cpu_percent));

        while samples.len() > self.history_size {
            samples.pop_front();
        }
    }

    /// Record NPU utilization sample
    pub async fn record_npu_utilization(&self, npu_percent: f64) {
        let mut samples = self.npu_samples.write().await;
        samples.push_back((Instant::now(), npu_percent));

        while samples.len() > self.history_size {
            samples.pop_front();
        }
    }

    /// Get operation type string from NPU operation
    fn get_operation_type(&self, operation: &NPUOperation) -> String {
        match operation {
            NPUOperation::Initialize { .. } => "initialize".to_string(),
            NPUOperation::Inference { .. } => "inference".to_string(),
            NPUOperation::LoadModel { .. } => "load_model".to_string(),
            NPUOperation::SignalProcessing { .. } => "signal_processing".to_string(),
            NPUOperation::Benchmark { .. } => "benchmark".to_string(),
            NPUOperation::HealthCheck => "health_check".to_string(),
        }
    }

    /// Calculate total operation counts
    async fn calculate_totals(&self) -> (u64, u64, u64) {
        let op_counts = self.operation_counts.read().await;
        let success_counts = self.success_counts.read().await;
        let failure_counts = self.failure_counts.read().await;

        let total_ops = op_counts.values().sum();
        let successful_ops = success_counts.values().sum();
        let failed_ops = failure_counts.values().sum();

        (total_ops, successful_ops, failed_ops)
    }

    /// Calculate latency statistics
    async fn calculate_latency_statistics(&self) -> LatencyStatistics {
        let latency_history = self.latency_history.read().await;

        if latency_history.is_empty() {
            return LatencyStatistics::default();
        }

        let mut latencies: Vec<u64> = latency_history.iter().map(|m| m.latency_us).collect();
        latencies.sort_unstable();

        let average = latencies.iter().sum::<u64>() as f64 / latencies.len() as f64;
        let peak = *latencies.last().unwrap_or(&0);

        let p95_idx = (latencies.len() as f64 * 0.95) as usize;
        let p99_idx = (latencies.len() as f64 * 0.99) as usize;

        let p95 = latencies.get(p95_idx.saturating_sub(1)).copied().unwrap_or(0);
        let p99 = latencies.get(p99_idx.saturating_sub(1)).copied().unwrap_or(0);

        LatencyStatistics {
            average,
            p95,
            p99,
            peak,
        }
    }

    /// Calculate current throughput
    async fn calculate_throughput(&self) -> f64 {
        let throughput_history = self.throughput_history.read().await;

        if throughput_history.len() < 2 {
            return 0.0;
        }

        // Calculate operations per second over the last few samples
        let now = Instant::now();
        let cutoff = now - Duration::from_secs(5); // Last 5 seconds

        let recent_samples: Vec<_> = throughput_history.iter()
            .filter(|(timestamp, _)| *timestamp > cutoff)
            .collect();

        if recent_samples.len() < 2 {
            return 0.0;
        }

        let first = recent_samples.first().unwrap();
        let last = recent_samples.last().unwrap();

        let time_diff = last.0.duration_since(first.0).as_secs_f64();
        let op_diff = last.1.saturating_sub(first.1);

        if time_diff > 0.0 {
            op_diff as f64 / time_diff
        } else {
            0.0
        }
    }

    /// Calculate resource utilization
    async fn calculate_resource_utilization(&self) -> ResourceUtilization {
        let memory_samples = self.memory_samples.read().await;
        let cpu_samples = self.cpu_samples.read().await;
        let npu_samples = self.npu_samples.read().await;

        let memory = if memory_samples.is_empty() {
            0.0
        } else {
            memory_samples.iter().map(|(_, usage)| *usage).sum::<f64>() / memory_samples.len() as f64
        };

        let cpu = if cpu_samples.is_empty() {
            0.0
        } else {
            cpu_samples.iter().map(|(_, usage)| *usage).sum::<f64>() / cpu_samples.len() as f64
        };

        let npu = if npu_samples.is_empty() {
            0.0
        } else {
            npu_samples.iter().map(|(_, usage)| *usage).sum::<f64>() / npu_samples.len() as f64
        };

        ResourceUtilization { memory, cpu, npu }
    }

    /// Calculate operation breakdown metrics
    async fn calculate_operation_breakdown(&self) -> HashMap<String, OperationMetrics> {
        let op_counts = self.operation_counts.read().await;
        let success_counts = self.success_counts.read().await;
        let latency_by_op = self.latency_by_operation.read().await;

        let mut breakdown = HashMap::new();

        for (op_type, &count) in op_counts.iter() {
            let successes = success_counts.get(op_type).copied().unwrap_or(0);
            let success_rate = if count > 0 {
                (successes as f64 / count as f64) * 100.0
            } else {
                0.0
            };

            let average_latency = if let Some(latencies) = latency_by_op.get(op_type) {
                if latencies.is_empty() {
                    0.0
                } else {
                    latencies.iter().sum::<u64>() as f64 / latencies.len() as f64
                }
            } else {
                0.0
            };

            breakdown.insert(op_type.clone(), OperationMetrics {
                count,
                average_latency_us: average_latency,
                success_rate_percent: success_rate,
                peak_throughput_ops_per_sec: 0.0, // Would calculate from historical data
                memory_usage_mb: 0.0, // Would track per operation type
            });
        }

        breakdown
    }

    /// Start background sampling task
    async fn start_sampling_task(&self) -> Result<()> {
        let throughput_history = Arc::clone(&self.throughput_history);
        let sample_interval = self.sample_interval;

        tokio::spawn(async move {
            let mut operation_counter = 0u64;

            loop {
                tokio::time::sleep(sample_interval).await;

                // Sample throughput (simplified - would integrate with actual operation counting)
                operation_counter += 1; // Placeholder increment

                let mut throughput = throughput_history.write().await;
                throughput.push_back((Instant::now(), operation_counter));

                // Maintain history size
                while throughput.len() > 1000 {
                    throughput.pop_front();
                }
            }
        });

        Ok(())
    }
}

/// Latency statistics
#[derive(Debug, Default)]
struct LatencyStatistics {
    average: f64,
    p95: u64,
    p99: u64,
    peak: u64,
}

/// Resource utilization metrics
#[derive(Debug, Default)]
struct ResourceUtilization {
    memory: f64,
    cpu: f64,
    npu: f64,
}

/// Metrics export functionality
impl MetricsCollector {
    /// Export metrics in Prometheus format
    pub async fn export_prometheus_metrics(&self) -> String {
        let metrics = self.get_current_metrics().await;

        let mut output = String::new();

        // Total operations
        output.push_str(&format!("# HELP npu_bridge_operations_total Total number of operations\n"));
        output.push_str(&format!("# TYPE npu_bridge_operations_total counter\n"));
        output.push_str(&format!("npu_bridge_operations_total{{instance=\"{}\"}} {}\n", self.name, metrics.total_operations));

        // Success rate
        output.push_str(&format!("# HELP npu_bridge_success_rate Success rate percentage\n"));
        output.push_str(&format!("# TYPE npu_bridge_success_rate gauge\n"));
        let success_rate = if metrics.total_operations > 0 {
            (metrics.successful_operations as f64 / metrics.total_operations as f64) * 100.0
        } else {
            0.0
        };
        output.push_str(&format!("npu_bridge_success_rate{{instance=\"{}\"}} {:.2}\n", self.name, success_rate));

        // Latency metrics
        output.push_str(&format!("# HELP npu_bridge_latency_us Operation latency in microseconds\n"));
        output.push_str(&format!("# TYPE npu_bridge_latency_us histogram\n"));
        output.push_str(&format!("npu_bridge_latency_us{{instance=\"{}\",quantile=\"0.50\"}} {:.2}\n", self.name, metrics.average_latency_us));
        output.push_str(&format!("npu_bridge_latency_us{{instance=\"{}\",quantile=\"0.95\"}} {}\n", self.name, metrics.p95_latency_us));
        output.push_str(&format!("npu_bridge_latency_us{{instance=\"{}\",quantile=\"0.99\"}} {}\n", self.name, metrics.p99_latency_us));

        // Throughput
        output.push_str(&format!("# HELP npu_bridge_throughput_ops_per_sec Operations per second\n"));
        output.push_str(&format!("# TYPE npu_bridge_throughput_ops_per_sec gauge\n"));
        output.push_str(&format!("npu_bridge_throughput_ops_per_sec{{instance=\"{}\"}} {:.2}\n", self.name, metrics.throughput_ops_per_sec));

        // Resource utilization
        output.push_str(&format!("# HELP npu_bridge_memory_usage_mb Memory usage in megabytes\n"));
        output.push_str(&format!("# TYPE npu_bridge_memory_usage_mb gauge\n"));
        output.push_str(&format!("npu_bridge_memory_usage_mb{{instance=\"{}\"}} {:.2}\n", self.name, metrics.memory_usage_mb));

        output.push_str(&format!("# HELP npu_bridge_cpu_utilization_percent CPU utilization percentage\n"));
        output.push_str(&format!("# TYPE npu_bridge_cpu_utilization_percent gauge\n"));
        output.push_str(&format!("npu_bridge_cpu_utilization_percent{{instance=\"{}\"}} {:.2}\n", self.name, metrics.cpu_utilization_percent));

        output.push_str(&format!("# HELP npu_bridge_npu_utilization_percent NPU utilization percentage\n"));
        output.push_str(&format!("# TYPE npu_bridge_npu_utilization_percent gauge\n"));
        output.push_str(&format!("npu_bridge_npu_utilization_percent{{instance=\"{}\"}} {:.2}\n", self.name, metrics.npu_utilization_percent));

        output
    }

    /// Export metrics as JSON
    pub async fn export_json_metrics(&self) -> Result<String> {
        let metrics = self.get_current_metrics().await;
        serde_json::to_string_pretty(&metrics)
            .context("Failed to serialize metrics to JSON")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_metrics_collector_creation() {
        let collector = MetricsCollector::new("test");
        assert!(collector.is_ok());
    }

    #[tokio::test]
    async fn test_latency_recording() {
        let collector = MetricsCollector::new("test").unwrap();

        // Record some latency measurements
        for i in 1..=100 {
            let measurement = LatencyMeasurement {
                latency_us: i * 100, // 100us, 200us, ..., 10000us
                timestamp: Instant::now(),
            };

            let mut history = collector.latency_history.write().await;
            history.push_back(measurement);
        }

        let stats = collector.calculate_latency_statistics().await;
        assert!(stats.average > 0.0);
        assert!(stats.peak > 0);
        assert!(stats.p95 > stats.average as u64);
    }

    #[tokio::test]
    async fn test_operation_counting() {
        let collector = MetricsCollector::new("test").unwrap();

        // Record some operations
        let operation = NPUOperation::HealthCheck;

        for _ in 0..10 {
            collector.record_operation_start(&operation).await;
        }

        let op_counts = collector.operation_counts.read().await;
        assert_eq!(op_counts.get("health_check"), Some(&10));
    }

    #[tokio::test]
    async fn test_metrics_export() {
        let collector = MetricsCollector::new("test").unwrap();

        // Add some test data
        collector.record_memory_usage(100.0).await;
        collector.record_cpu_utilization(50.0).await;
        collector.record_npu_utilization(75.0).await;

        // Test JSON export
        let json_metrics = collector.export_json_metrics().await;
        assert!(json_metrics.is_ok());

        // Test Prometheus export
        let prometheus_metrics = collector.export_prometheus_metrics().await;
        assert!(prometheus_metrics.contains("npu_bridge_"));
        assert!(prometheus_metrics.contains("# HELP"));
        assert!(prometheus_metrics.contains("# TYPE"));
    }
}