//! Coordination Engine for NPU Operations
//!
//! This module implements the core coordination engine that manages
//! concurrent NPU operations with sub-millisecond latency requirements.

use std::collections::{HashMap, VecDeque};
use std::sync::Arc;
use std::time::{Duration, Instant};
use anyhow::{Result, Context};
use serde::{Deserialize, Serialize};
use tokio::sync::{mpsc, RwLock, Mutex, Semaphore};
use tokio::time::timeout;
use tracing::{info, warn, error, debug, instrument};

/// Coordination message types for inter-component communication
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CoordinationMessage {
    /// Execute operation with priority
    ExecuteOperation {
        operation_id: String,
        priority: Priority,
        payload: serde_json::Value,
        deadline_us: u64,
    },
    /// Operation completed successfully
    OperationComplete {
        operation_id: String,
        result: serde_json::Value,
        execution_time_us: u64,
    },
    /// Operation failed
    OperationFailed {
        operation_id: String,
        error: String,
        execution_time_us: u64,
    },
    /// Health check request
    HealthCheck {
        component: String,
    },
    /// Performance metrics update
    MetricsUpdate {
        component: String,
        metrics: HashMap<String, f64>,
    },
    /// Resource allocation request
    ResourceAllocation {
        operation_id: String,
        resource_type: ResourceType,
        amount: u64,
    },
    /// Resource release notification
    ResourceRelease {
        operation_id: String,
        resource_type: ResourceType,
        amount: u64,
    },
}

/// Operation priority levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Priority {
    Low = 0,
    Normal = 1,
    High = 2,
    Critical = 3,
    RealTime = 4,
}

/// Resource types for coordination
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ResourceType {
    NPUMemory,
    NPUCompute,
    CPUCores,
    SystemMemory,
    NetworkBandwidth,
}

/// Operation scheduling state
#[derive(Debug, Clone)]
struct ScheduledOperation {
    operation_id: String,
    priority: Priority,
    deadline: Instant,
    payload: serde_json::Value,
    retry_count: u32,
    created_at: Instant,
}

/// Resource pool for managing hardware resources
#[derive(Debug)]
struct ResourcePool {
    npu_memory_mb: Arc<Semaphore>,
    npu_compute_units: Arc<Semaphore>,
    cpu_cores: Arc<Semaphore>,
    system_memory_mb: Arc<Semaphore>,
    allocations: Arc<Mutex<HashMap<String, Vec<(ResourceType, u64)>>>>,
}

/// Performance tracking for coordination decisions
#[derive(Debug, Default, Clone)]
pub struct CoordinationMetrics {
    pub total_operations: u64,
    pub successful_operations: u64,
    pub failed_operations: u64,
    pub average_latency_us: f64,
    pub peak_latency_us: u64,
    pub throughput_ops_per_sec: f64,
    pub queue_depth: usize,
    pub resource_utilization: HashMap<ResourceType, f64>,
}

/// Main coordination engine
pub struct CoordinationEngine {
    worker_count: usize,
    buffer_size: usize,

    // Message channels
    message_tx: mpsc::UnboundedSender<CoordinationMessage>,
    message_rx: Arc<Mutex<Option<mpsc::UnboundedReceiver<CoordinationMessage>>>>,

    // Operation scheduling
    operation_queue: Arc<Mutex<VecDeque<ScheduledOperation>>>,
    active_operations: Arc<RwLock<HashMap<String, ScheduledOperation>>>,

    // Resource management
    resource_pool: ResourcePool,

    // Performance tracking
    metrics: Arc<RwLock<CoordinationMetrics>>,

    // Worker control
    worker_handles: Arc<Mutex<Vec<tokio::task::JoinHandle<()>>>>,
    shutdown_signal: Arc<tokio::sync::Notify>,
}

impl ResourcePool {
    /// Create new resource pool with specified limits
    fn new(
        npu_memory_mb: u64,
        npu_compute_units: u64,
        cpu_cores: u64,
        system_memory_mb: u64,
    ) -> Self {
        Self {
            npu_memory_mb: Arc::new(Semaphore::new(npu_memory_mb as usize)),
            npu_compute_units: Arc::new(Semaphore::new(npu_compute_units as usize)),
            cpu_cores: Arc::new(Semaphore::new(cpu_cores as usize)),
            system_memory_mb: Arc::new(Semaphore::new(system_memory_mb as usize)),
            allocations: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Allocate resources for operation
    async fn allocate(&self, operation_id: &str, resource_type: ResourceType, amount: u64) -> Result<()> {
        let semaphore = match resource_type {
            ResourceType::NPUMemory => &self.npu_memory_mb,
            ResourceType::NPUCompute => &self.npu_compute_units,
            ResourceType::CPUCores => &self.cpu_cores,
            ResourceType::SystemMemory => &self.system_memory_mb,
            ResourceType::NetworkBandwidth => {
                // Network bandwidth not limited by semaphore
                return Ok(());
            }
        };

        // Try to acquire resources with timeout
        let permits = timeout(Duration::from_millis(100), semaphore.acquire_many(amount as u32)).await
            .map_err(|_| anyhow::anyhow!("Resource allocation timeout for {:?}", resource_type))?
            .map_err(|_| anyhow::anyhow!("Failed to acquire resource permits"))?;

        // Track allocation
        {
            let mut allocations = self.allocations.lock().await;
            allocations.entry(operation_id.to_string())
                .or_insert_with(Vec::new)
                .push((resource_type, amount));
        }

        // Keep permits alive by forgetting them (they'll be released on operation completion)
        permits.forget();

        debug!("Allocated {} units of {:?} for operation {}", amount, resource_type, operation_id);
        Ok(())
    }

    /// Release resources for operation
    async fn release(&self, operation_id: &str) -> Result<()> {
        let mut allocations = self.allocations.lock().await;

        if let Some(operation_allocations) = allocations.remove(operation_id) {
            for (resource_type, amount) in operation_allocations {
                let semaphore = match resource_type {
                    ResourceType::NPUMemory => &self.npu_memory_mb,
                    ResourceType::NPUCompute => &self.npu_compute_units,
                    ResourceType::CPUCores => &self.cpu_cores,
                    ResourceType::SystemMemory => &self.system_memory_mb,
                    ResourceType::NetworkBandwidth => continue,
                };

                semaphore.add_permits(amount as usize);
                debug!("Released {} units of {:?} for operation {}", amount, resource_type, operation_id);
            }
        }

        Ok(())
    }

    /// Get current resource utilization
    async fn get_utilization(&self) -> HashMap<ResourceType, f64> {
        let mut utilization = HashMap::new();

        // Calculate utilization for each resource type
        let npu_memory_used = 256 - self.npu_memory_mb.available_permits();
        utilization.insert(ResourceType::NPUMemory, npu_memory_used as f64 / 256.0);

        let npu_compute_used = 34 - self.npu_compute_units.available_permits();
        utilization.insert(ResourceType::NPUCompute, npu_compute_used as f64 / 34.0);

        let cpu_cores_used = 22 - self.cpu_cores.available_permits();
        utilization.insert(ResourceType::CPUCores, cpu_cores_used as f64 / 22.0);

        let system_memory_used = 8192 - self.system_memory_mb.available_permits();
        utilization.insert(ResourceType::SystemMemory, system_memory_used as f64 / 8192.0);

        utilization.insert(ResourceType::NetworkBandwidth, 0.0); // Not tracked

        utilization
    }
}

impl CoordinationEngine {
    /// Create new coordination engine
    #[instrument(skip_all)]
    pub async fn new(worker_count: usize, buffer_size: usize) -> Result<Self> {
        info!("Creating coordination engine with {} workers, buffer size {}", worker_count, buffer_size);

        let (message_tx, message_rx) = mpsc::unbounded_channel();

        // Configure resource pool based on Intel Meteor Lake specs
        let resource_pool = ResourcePool::new(
            256,   // 256MB NPU memory
            34,    // 34 TOPS NPU compute units
            22,    // 22 CPU cores (12 P-cores + 10 E-cores)
            8192,  // 8GB system memory allocation
        );

        Ok(Self {
            worker_count,
            buffer_size,
            message_tx,
            message_rx: Arc::new(Mutex::new(Some(message_rx))),
            operation_queue: Arc::new(Mutex::new(VecDeque::new())),
            active_operations: Arc::new(RwLock::new(HashMap::new())),
            resource_pool,
            metrics: Arc::new(RwLock::new(CoordinationMetrics::default())),
            worker_handles: Arc::new(Mutex::new(Vec::new())),
            shutdown_signal: Arc::new(tokio::sync::Notify::new()),
        })
    }

    /// Start the coordination engine
    #[instrument(skip(self))]
    pub async fn start(&self) -> Result<()> {
        info!("Starting coordination engine with {} workers", self.worker_count);

        // Take the receiver from the option
        let message_rx = {
            let mut rx_option = self.message_rx.lock().await;
            rx_option.take().context("Message receiver already taken")?
        };

        // Start message processor
        let message_processor = self.start_message_processor(message_rx).await?;

        // Start worker threads
        let workers = self.start_workers().await?;

        // Start metrics collector
        let metrics_collector = self.start_metrics_collector().await?;

        // Store handles
        let mut handles = self.worker_handles.lock().await;
        handles.push(message_processor);
        handles.extend(workers);
        handles.push(metrics_collector);

        info!("Coordination engine started with {} total tasks", handles.len());
        Ok(())
    }

    /// Submit operation for coordination
    #[instrument(skip(self, payload))]
    pub async fn submit_operation(
        &self,
        operation_id: String,
        priority: Priority,
        payload: serde_json::Value,
        deadline_us: u64,
    ) -> Result<()> {
        debug!("Submitting operation {} with priority {:?}", operation_id, priority);

        let message = CoordinationMessage::ExecuteOperation {
            operation_id,
            priority,
            payload,
            deadline_us,
        };

        self.message_tx.send(message)
            .context("Failed to submit operation to coordination engine")?;

        Ok(())
    }

    /// Send message to coordination engine
    pub async fn send_message(&self, message: CoordinationMessage) -> Result<()> {
        self.message_tx.send(message)
            .context("Failed to send message to coordination engine")?;
        Ok(())
    }

    /// Get current coordination metrics
    pub async fn get_metrics(&self) -> CoordinationMetrics {
        let metrics = self.metrics.read().await;
        metrics.clone()
    }

    /// Shutdown coordination engine
    #[instrument(skip(self))]
    pub async fn shutdown(&self) -> Result<()> {
        info!("Shutting down coordination engine");

        // Signal shutdown
        self.shutdown_signal.notify_waiters();

        // Wait for all workers to complete
        let mut handles = self.worker_handles.lock().await;
        while let Some(handle) = handles.pop() {
            if let Err(e) = handle.await {
                warn!("Worker task failed during shutdown: {}", e);
            }
        }

        info!("Coordination engine shutdown complete");
        Ok(())
    }

    /// Start message processor task
    async fn start_message_processor(
        &self,
        mut message_rx: mpsc::UnboundedReceiver<CoordinationMessage>,
    ) -> Result<tokio::task::JoinHandle<()>> {
        let operation_queue = Arc::clone(&self.operation_queue);
        let active_operations = Arc::clone(&self.active_operations);
        let resource_pool = ResourcePool::new(256, 34, 22, 8192); // Clone resource pool config
        let metrics = Arc::clone(&self.metrics);
        let shutdown_signal = Arc::clone(&self.shutdown_signal);

        let handle = tokio::spawn(async move {
            loop {
                tokio::select! {
                    message = message_rx.recv() => {
                        match message {
                            Some(msg) => {
                                if let Err(e) = Self::process_message(
                                    msg,
                                    &operation_queue,
                                    &active_operations,
                                    &resource_pool,
                                    &metrics,
                                ).await {
                                    error!("Failed to process message: {}", e);
                                }
                            }
                            None => {
                                warn!("Message channel closed, stopping message processor");
                                break;
                            }
                        }
                    }
                    _ = shutdown_signal.notified() => {
                        info!("Message processor received shutdown signal");
                        break;
                    }
                }
            }
        });

        Ok(handle)
    }

    /// Process coordination message
    async fn process_message(
        message: CoordinationMessage,
        operation_queue: &Arc<Mutex<VecDeque<ScheduledOperation>>>,
        active_operations: &Arc<RwLock<HashMap<String, ScheduledOperation>>>,
        resource_pool: &ResourcePool,
        metrics: &Arc<RwLock<CoordinationMetrics>>,
    ) -> Result<()> {
        match message {
            CoordinationMessage::ExecuteOperation { operation_id, priority, payload, deadline_us } => {
                let deadline = Instant::now() + Duration::from_micros(deadline_us);
                let operation = ScheduledOperation {
                    operation_id: operation_id.clone(),
                    priority,
                    deadline,
                    payload,
                    retry_count: 0,
                    created_at: Instant::now(),
                };

                // Add to queue with priority ordering
                let mut queue = operation_queue.lock().await;

                // Find insertion point based on priority
                let insert_pos = queue.iter()
                    .position(|op| op.priority < priority)
                    .unwrap_or(queue.len());

                queue.insert(insert_pos, operation.clone());

                // Track as active operation
                let mut active = active_operations.write().await;
                active.insert(operation_id, operation);

                debug!("Queued operation with priority {:?}, queue length: {}", priority, queue.len());
            }

            CoordinationMessage::OperationComplete { operation_id, result, execution_time_us } => {
                // Remove from active operations
                let mut active = active_operations.write().await;
                active.remove(&operation_id);

                // Release resources
                if let Err(e) = resource_pool.release(&operation_id).await {
                    warn!("Failed to release resources for operation {}: {}", operation_id, e);
                }

                // Update metrics
                let mut metrics = metrics.write().await;
                metrics.successful_operations += 1;
                metrics.total_operations += 1;

                // Update average latency
                let total_latency = metrics.average_latency_us * (metrics.total_operations - 1) as f64;
                metrics.average_latency_us = (total_latency + execution_time_us as f64) / metrics.total_operations as f64;

                if execution_time_us > metrics.peak_latency_us {
                    metrics.peak_latency_us = execution_time_us;
                }

                debug!("Operation {} completed in {} us", operation_id, execution_time_us);
            }

            CoordinationMessage::OperationFailed { operation_id, error, execution_time_us } => {
                // Handle failed operation
                let mut active = active_operations.write().await;

                if let Some(mut operation) = active.remove(&operation_id) {
                    operation.retry_count += 1;

                    // Retry if under limit and deadline not passed
                    if operation.retry_count < 3 && Instant::now() < operation.deadline {
                        // Re-queue with lower priority
                        let mut queue = operation_queue.lock().await;
                        queue.push_back(operation.clone());
                        active.insert(operation_id.clone(), operation);

                        debug!("Retrying operation {} (attempt {})", operation_id, operation.retry_count + 1);
                    } else {
                        // Release resources
                        if let Err(e) = resource_pool.release(&operation_id).await {
                            warn!("Failed to release resources for failed operation {}: {}", operation_id, e);
                        }

                        // Update failure metrics
                        let mut metrics = metrics.write().await;
                        metrics.failed_operations += 1;
                        metrics.total_operations += 1;

                        error!("Operation {} failed permanently: {}", operation_id, error);
                    }
                }
            }

            CoordinationMessage::ResourceAllocation { operation_id, resource_type, amount } => {
                if let Err(e) = resource_pool.allocate(&operation_id, resource_type, amount).await {
                    warn!("Resource allocation failed for operation {}: {}", operation_id, e);
                }
            }

            CoordinationMessage::ResourceRelease { operation_id, .. } => {
                if let Err(e) = resource_pool.release(&operation_id).await {
                    warn!("Resource release failed for operation {}: {}", operation_id, e);
                }
            }

            CoordinationMessage::HealthCheck { component } => {
                debug!("Health check received for component: {}", component);
            }

            CoordinationMessage::MetricsUpdate { component, metrics: component_metrics } => {
                debug!("Metrics update from {}: {:?}", component, component_metrics);
            }
        }

        Ok(())
    }

    /// Start worker tasks
    async fn start_workers(&self) -> Result<Vec<tokio::task::JoinHandle<()>>> {
        let mut handles = Vec::new();

        for worker_id in 0..self.worker_count {
            let handle = self.start_worker(worker_id).await?;
            handles.push(handle);
        }

        Ok(handles)
    }

    /// Start individual worker task
    async fn start_worker(&self, worker_id: usize) -> Result<tokio::task::JoinHandle<()>> {
        let operation_queue = Arc::clone(&self.operation_queue);
        let active_operations = Arc::clone(&self.active_operations);
        let shutdown_signal = Arc::clone(&self.shutdown_signal);

        let handle = tokio::spawn(async move {
            info!("Worker {} started", worker_id);

            loop {
                tokio::select! {
                    _ = tokio::time::sleep(Duration::from_millis(1)) => {
                        // Check for operations to process
                        let operation = {
                            let mut queue = operation_queue.lock().await;
                            queue.pop_front()
                        };

                        if let Some(operation) = operation {
                            // Process operation
                            Self::execute_operation(worker_id, operation, &active_operations).await;
                        }
                    }
                    _ = shutdown_signal.notified() => {
                        info!("Worker {} received shutdown signal", worker_id);
                        break;
                    }
                }
            }

            info!("Worker {} stopped", worker_id);
        });

        Ok(handle)
    }

    /// Execute operation in worker
    async fn execute_operation(
        worker_id: usize,
        operation: ScheduledOperation,
        active_operations: &Arc<RwLock<HashMap<String, ScheduledOperation>>>,
    ) {
        let start_time = Instant::now();

        debug!("Worker {} executing operation {}", worker_id, operation.operation_id);

        // Check if operation deadline has passed
        if Instant::now() > operation.deadline {
            warn!("Operation {} deadline exceeded, skipping", operation.operation_id);

            // Remove from active operations
            let mut active = active_operations.write().await;
            active.remove(&operation.operation_id);
            return;
        }

        // Simulate operation execution
        // In a real implementation, this would dispatch to appropriate handlers
        tokio::time::sleep(Duration::from_micros(100)).await; // Simulate 100μs execution

        let execution_time = start_time.elapsed();

        debug!("Worker {} completed operation {} in {:?}",
               worker_id, operation.operation_id, execution_time);

        // Remove from active operations
        let mut active = active_operations.write().await;
        active.remove(&operation.operation_id);
    }

    /// Start metrics collection task
    async fn start_metrics_collector(&self) -> Result<tokio::task::JoinHandle<()>> {
        let metrics = Arc::clone(&self.metrics);
        let operation_queue = Arc::clone(&self.operation_queue);
        let active_operations = Arc::clone(&self.active_operations);
        let shutdown_signal = Arc::clone(&self.shutdown_signal);

        let handle = tokio::spawn(async move {
            let mut last_update = Instant::now();
            let mut last_operation_count = 0u64;

            loop {
                tokio::select! {
                    _ = tokio::time::sleep(Duration::from_secs(1)) => {
                        // Update metrics every second
                        let mut metrics = metrics.write().await;

                        // Calculate throughput
                        let elapsed = last_update.elapsed().as_secs_f64();
                        let operation_delta = metrics.total_operations - last_operation_count;
                        metrics.throughput_ops_per_sec = operation_delta as f64 / elapsed;

                        // Update queue depth
                        let queue_len = operation_queue.lock().await.len();
                        metrics.queue_depth = queue_len;

                        last_update = Instant::now();
                        last_operation_count = metrics.total_operations;

                        debug!("Metrics updated: {} ops/sec, queue depth: {}",
                               metrics.throughput_ops_per_sec, metrics.queue_depth);
                    }
                    _ = shutdown_signal.notified() => {
                        info!("Metrics collector received shutdown signal");
                        break;
                    }
                }
            }
        });

        Ok(handle)
    }
}

impl Drop for CoordinationEngine {
    fn drop(&mut self) {
        debug!("CoordinationEngine dropped");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::test;

    #[test]
    async fn test_coordination_engine_creation() {
        let engine = CoordinationEngine::new(4, 1024).await;
        assert!(engine.is_ok());
    }

    #[test]
    async fn test_operation_submission() {
        let engine = CoordinationEngine::new(2, 100).await.unwrap();
        engine.start().await.unwrap();

        let result = engine.submit_operation(
            "test_op_1".to_string(),
            Priority::Normal,
            serde_json::json!({"test": "data"}),
            1000, // 1ms deadline
        ).await;

        assert!(result.is_ok());

        // Give some time for processing
        tokio::time::sleep(Duration::from_millis(10)).await;

        engine.shutdown().await.unwrap();
    }

    #[test]
    async fn test_priority_ordering() {
        let engine = CoordinationEngine::new(1, 100).await.unwrap();

        // Submit operations with different priorities
        engine.submit_operation("low".to_string(), Priority::Low, serde_json::json!({}), 1000).await.unwrap();
        engine.submit_operation("high".to_string(), Priority::High, serde_json::json!({}), 1000).await.unwrap();
        engine.submit_operation("critical".to_string(), Priority::Critical, serde_json::json!({}), 1000).await.unwrap();

        // Verify queue ordering
        let queue = engine.operation_queue.lock().await;
        assert_eq!(queue[0].priority, Priority::Critical);
        assert_eq!(queue[1].priority, Priority::High);
        assert_eq!(queue[2].priority, Priority::Low);
    }

    #[test]
    async fn test_resource_allocation() {
        let pool = ResourcePool::new(100, 10, 8, 1024);

        // Test allocation
        let result = pool.allocate("test_op", ResourceType::NPUMemory, 50).await;
        assert!(result.is_ok());

        // Test utilization
        let utilization = pool.get_utilization().await;
        assert!(utilization[&ResourceType::NPUMemory] > 0.0);

        // Test release
        let result = pool.release("test_op").await;
        assert!(result.is_ok());
    }
}