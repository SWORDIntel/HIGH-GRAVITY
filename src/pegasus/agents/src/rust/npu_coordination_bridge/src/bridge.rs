//! Bridge module for NPU coordination
//!
//! This module provides the bridge functionality that connects various components
//! of the NPU coordination system.

use std::sync::Arc;
use anyhow::Result;
use tokio::sync::RwLock;
use tracing::{info, debug, instrument};

use crate::{
    coordination::{CoordinationEngine, CoordinationMessage, Priority},
    hardware::intel::IntelNPUManager,
    metrics::MetricsCollector,
    NPUOperation, OperationResult, BridgeConfig,
};

/// Bridge component that coordinates between different subsystems
pub struct NPUBridge {
    config: BridgeConfig,
    coordination_engine: Arc<CoordinationEngine>,
    npu_manager: Arc<IntelNPUManager>,
    metrics_collector: Arc<MetricsCollector>,
    operation_counter: Arc<RwLock<u64>>,
}

impl NPUBridge {
    /// Create new NPU bridge
    #[instrument(skip(config))]
    pub async fn new(config: BridgeConfig) -> Result<Self> {
        info!("Creating NPU bridge with configuration: {:#?}", config);

        // Initialize coordination engine
        let coordination_engine = Arc::new(
            CoordinationEngine::new(config.worker_threads, config.buffer_size).await?
        );

        // Initialize NPU manager
        let npu_manager = Arc::new(
            IntelNPUManager::new(&config.npu_config).await?
        );

        // Initialize metrics collector
        let metrics_collector = Arc::new(
            MetricsCollector::new("npu_bridge")?
        );

        Ok(Self {
            config,
            coordination_engine,
            npu_manager,
            metrics_collector,
            operation_counter: Arc::new(RwLock::new(0)),
        })
    }

    /// Start the bridge
    #[instrument(skip(self))]
    pub async fn start(&self) -> Result<()> {
        info!("Starting NPU bridge");

        // Start coordination engine
        self.coordination_engine.start().await?;

        // Start metrics collection
        self.metrics_collector.start().await?;

        // Initialize NPU
        self.npu_manager.initialize(&self.config.npu_config).await?;

        info!("NPU bridge started successfully");
        Ok(())
    }

    /// Execute operation through the bridge
    #[instrument(skip(self, operation))]
    pub async fn execute_operation(&self, operation: NPUOperation) -> Result<OperationResult> {
        debug!("Bridge executing operation: {:?}", std::mem::discriminant(&operation));

        // Generate operation ID
        let operation_id = self.generate_operation_id().await;

        // Record operation start
        self.metrics_collector.record_operation_start(&operation).await;

        // Determine priority based on operation type
        let priority = self.determine_operation_priority(&operation);

        // Submit to coordination engine
        let operation_json = serde_json::to_value(&operation)?;
        self.coordination_engine.submit_operation(
            operation_id.clone(),
            priority,
            operation_json,
            self.config.max_latency_us as u64,
        ).await?;

        // Execute the actual operation
        // In a real implementation, this would be handled by the coordination engine
        // For now, we'll execute directly
        let start_time = std::time::Instant::now();

        let result = match operation {
            NPUOperation::Initialize { config } => {
                self.npu_manager.initialize(&config).await?;
                OperationResult {
                    success: true,
                    execution_time_us: start_time.elapsed().as_micros() as u64,
                    throughput_ops_per_sec: 0.0,
                    memory_usage_mb: 0.0,
                    data: serde_json::json!({"status": "initialized"}),
                    error: None,
                    metrics: self.metrics_collector.get_current_metrics().await,
                }
            },
            NPUOperation::Inference { model_id, input_data, batch_size } => {
                let output = self.npu_manager.run_inference(&model_id, &input_data, batch_size).await?;
                let execution_time_us = start_time.elapsed().as_micros() as u64;
                let throughput = (batch_size as f64 * 1_000_000.0) / execution_time_us as f64;

                OperationResult {
                    success: true,
                    execution_time_us,
                    throughput_ops_per_sec: throughput,
                    memory_usage_mb: self.npu_manager.get_memory_usage().await.unwrap_or(0.0),
                    data: serde_json::json!({
                        "output": output,
                        "model_id": model_id,
                        "batch_size": batch_size
                    }),
                    error: None,
                    metrics: self.metrics_collector.get_current_metrics().await,
                }
            },
            NPUOperation::LoadModel { model_path, model_id } => {
                self.npu_manager.load_model(&model_path, &model_id).await?;
                OperationResult {
                    success: true,
                    execution_time_us: start_time.elapsed().as_micros() as u64,
                    throughput_ops_per_sec: 0.0,
                    memory_usage_mb: self.npu_manager.get_memory_usage().await.unwrap_or(0.0),
                    data: serde_json::json!({
                        "model_id": model_id,
                        "model_path": model_path,
                        "status": "loaded"
                    }),
                    error: None,
                    metrics: self.metrics_collector.get_current_metrics().await,
                }
            },
            NPUOperation::SignalProcessing { operation, data, parameters } => {
                // Placeholder for signal processing
                // In a real implementation, this would integrate with MATLAB processor
                let output_data = data; // Pass-through for now

                OperationResult {
                    success: true,
                    execution_time_us: start_time.elapsed().as_micros() as u64,
                    throughput_ops_per_sec: (data.len() as f64 * 1_000_000.0) / start_time.elapsed().as_micros() as f64,
                    memory_usage_mb: (data.len() * 4) as f64 / 1024.0 / 1024.0,
                    data: serde_json::json!({
                        "output": output_data,
                        "operation": operation,
                        "parameters": parameters
                    }),
                    error: None,
                    metrics: self.metrics_collector.get_current_metrics().await,
                }
            },
            NPUOperation::Benchmark { duration_ms, operation_type } => {
                // Run benchmark
                let mut operations = 0u64;
                let benchmark_start = std::time::Instant::now();
                let duration = std::time::Duration::from_millis(duration_ms as u64);

                while benchmark_start.elapsed() < duration {
                    // Simulate operation
                    tokio::time::sleep(std::time::Duration::from_micros(100)).await;
                    operations += 1;
                }

                let execution_time_us = start_time.elapsed().as_micros() as u64;
                let throughput = (operations as f64 * 1_000_000.0) / execution_time_us as f64;

                OperationResult {
                    success: true,
                    execution_time_us,
                    throughput_ops_per_sec: throughput,
                    memory_usage_mb: 0.0,
                    data: serde_json::json!({
                        "operations": operations,
                        "duration_ms": duration_ms,
                        "operation_type": operation_type
                    }),
                    error: None,
                    metrics: self.metrics_collector.get_current_metrics().await,
                }
            },
            NPUOperation::HealthCheck => {
                let npu_status = self.npu_manager.get_status().await;

                OperationResult {
                    success: true,
                    execution_time_us: start_time.elapsed().as_micros() as u64,
                    throughput_ops_per_sec: 0.0,
                    memory_usage_mb: self.npu_manager.get_memory_usage().await.unwrap_or(0.0),
                    data: serde_json::json!({
                        "bridge_status": "healthy",
                        "npu_status": npu_status,
                        "coordination_metrics": self.coordination_engine.get_metrics().await
                    }),
                    error: None,
                    metrics: self.metrics_collector.get_current_metrics().await,
                }
            },
        };

        // Record operation completion
        self.metrics_collector.record_operation_completion(&result, result.execution_time_us).await;

        // Send completion message to coordination engine
        let completion_msg = CoordinationMessage::OperationComplete {
            operation_id,
            result: serde_json::to_value(&result)?,
            execution_time_us: result.execution_time_us,
        };

        self.coordination_engine.send_message(completion_msg).await?;

        Ok(result)
    }

    /// Generate unique operation ID
    async fn generate_operation_id(&self) -> String {
        let mut counter = self.operation_counter.write().await;
        *counter += 1;
        format!("op_{:08}", *counter)
    }

    /// Determine operation priority
    fn determine_operation_priority(&self, operation: &NPUOperation) -> Priority {
        match operation {
            NPUOperation::HealthCheck => Priority::Low,
            NPUOperation::Initialize { .. } => Priority::High,
            NPUOperation::LoadModel { .. } => Priority::Normal,
            NPUOperation::Inference { .. } => Priority::High,
            NPUOperation::SignalProcessing { .. } => Priority::Normal,
            NPUOperation::Benchmark { .. } => Priority::Low,
        }
    }

    /// Get bridge configuration
    pub fn get_config(&self) -> &BridgeConfig {
        &self.config
    }

    /// Get coordination engine metrics
    pub async fn get_coordination_metrics(&self) -> crate::coordination::CoordinationMetrics {
        self.coordination_engine.get_metrics().await
    }

    /// Get NPU status
    pub async fn get_npu_status(&self) -> crate::hardware::intel::NPUStatus {
        self.npu_manager.get_status().await
    }

    /// Get performance metrics
    pub async fn get_performance_metrics(&self) -> crate::metrics::PerformanceMetrics {
        self.metrics_collector.get_current_metrics().await
    }

    /// Shutdown bridge
    #[instrument(skip(self))]
    pub async fn shutdown(&self) -> Result<()> {
        info!("Shutting down NPU bridge");

        // Shutdown coordination engine
        self.coordination_engine.shutdown().await?;

        info!("NPU bridge shutdown complete");
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{BridgeConfig, NPUConfig};

    #[tokio::test]
    async fn test_bridge_creation() {
        let config = BridgeConfig::default();
        let bridge = NPUBridge::new(config).await;
        assert!(bridge.is_ok());
    }

    #[tokio::test]
    async fn test_operation_execution() {
        let config = BridgeConfig::default();
        let bridge = NPUBridge::new(config).await.unwrap();
        bridge.start().await.unwrap();

        let operation = NPUOperation::HealthCheck;
        let result = bridge.execute_operation(operation).await;

        assert!(result.is_ok());
        let op_result = result.unwrap();
        assert!(op_result.success);

        bridge.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn test_priority_determination() {
        let config = BridgeConfig::default();
        let bridge = NPUBridge::new(config).await.unwrap();

        assert_eq!(bridge.determine_operation_priority(&NPUOperation::HealthCheck), Priority::Low);

        let init_op = NPUOperation::Initialize {
            config: NPUConfig {
                device_id: "test".to_string(),
                max_batch_size: 1,
                precision: "FP32".to_string(),
                memory_limit_mb: 100,
                enable_caching: false,
            }
        };
        assert_eq!(bridge.determine_operation_priority(&init_op), Priority::High);
    }
}