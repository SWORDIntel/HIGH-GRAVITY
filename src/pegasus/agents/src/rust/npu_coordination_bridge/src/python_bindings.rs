//! Python bindings for NPU coordination bridge using PyO3
//!
//! This module provides a seamless interface between Python and Rust
//! for high-performance NPU operations with minimal overhead.

use std::collections::HashMap;
use anyhow::Result;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use pyo3::exceptions::PyRuntimeError;
use serde_json;
use tokio::runtime::Runtime;

use crate::{
    NPUCoordinationBridge, BridgeConfig, NPUConfig, MatlabConfig,
    NPUOperation, OperationResult
};

/// Python wrapper for NPU coordination bridge
#[pyclass]
pub struct PyNPUBridge {
    bridge: Option<NPUCoordinationBridge>,
    runtime: Runtime,
    config: BridgeConfig,
}

/// Python wrapper for bridge configuration
#[pyclass]
#[derive(Clone)]
pub struct PyBridgeConfig {
    #[pyo3(get, set)]
    pub target_ops_per_sec: u32,
    #[pyo3(get, set)]
    pub max_latency_us: u32,
    #[pyo3(get, set)]
    pub worker_threads: usize,
    #[pyo3(get, set)]
    pub buffer_size: usize,
}

/// Python wrapper for NPU configuration
#[pyclass]
#[derive(Clone)]
pub struct PyNPUConfig {
    #[pyo3(get, set)]
    pub device_id: String,
    #[pyo3(get, set)]
    pub max_batch_size: u32,
    #[pyo3(get, set)]
    pub precision: String,
    #[pyo3(get, set)]
    pub memory_limit_mb: u32,
    #[pyo3(get, set)]
    pub enable_caching: bool,
}

/// Python wrapper for operation results
#[pyclass]
#[derive(Clone)]
pub struct PyOperationResult {
    #[pyo3(get)]
    pub success: bool,
    #[pyo3(get)]
    pub execution_time_us: u64,
    #[pyo3(get)]
    pub throughput_ops_per_sec: f64,
    #[pyo3(get)]
    pub memory_usage_mb: f64,
    #[pyo3(get)]
    pub data: Py<PyDict>,
    #[pyo3(get)]
    pub error: Option<String>,
}

#[pymethods]
impl PyBridgeConfig {
    #[new]
    fn new() -> Self {
        let default_config = BridgeConfig::default();
        Self {
            target_ops_per_sec: default_config.target_ops_per_sec,
            max_latency_us: default_config.max_latency_us,
            worker_threads: default_config.worker_threads,
            buffer_size: default_config.buffer_size,
        }
    }

    fn to_rust_config(&self, py: Python) -> PyResult<BridgeConfig> {
        Ok(BridgeConfig {
            target_ops_per_sec: self.target_ops_per_sec,
            max_latency_us: self.max_latency_us,
            worker_threads: self.worker_threads,
            buffer_size: self.buffer_size,
            npu_config: NPUConfig {
                device_id: "NPU".to_string(),
                max_batch_size: 32,
                precision: "FP16".to_string(),
                memory_limit_mb: 256,
                enable_caching: true,
            },
            matlab_config: None,
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "PyBridgeConfig(target_ops_per_sec={}, max_latency_us={}, worker_threads={}, buffer_size={})",
            self.target_ops_per_sec, self.max_latency_us, self.worker_threads, self.buffer_size
        )
    }
}

#[pymethods]
impl PyNPUConfig {
    #[new]
    fn new() -> Self {
        let default_config = NPUConfig {
            device_id: "NPU".to_string(),
            max_batch_size: 32,
            precision: "FP16".to_string(),
            memory_limit_mb: 256,
            enable_caching: true,
        };

        Self {
            device_id: default_config.device_id,
            max_batch_size: default_config.max_batch_size,
            precision: default_config.precision,
            memory_limit_mb: default_config.memory_limit_mb,
            enable_caching: default_config.enable_caching,
        }
    }

    fn to_rust_config(&self) -> NPUConfig {
        NPUConfig {
            device_id: self.device_id.clone(),
            max_batch_size: self.max_batch_size,
            precision: self.precision.clone(),
            memory_limit_mb: self.memory_limit_mb,
            enable_caching: self.enable_caching,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "PyNPUConfig(device_id='{}', max_batch_size={}, precision='{}', memory_limit_mb={}, enable_caching={})",
            self.device_id, self.max_batch_size, self.precision, self.memory_limit_mb, self.enable_caching
        )
    }
}

#[pymethods]
impl PyOperationResult {
    fn get_data_dict(&self, py: Python) -> PyResult<PyObject> {
        Ok(self.data.clone_ref(py).into())
    }

    fn __repr__(&self) -> String {
        format!(
            "PyOperationResult(success={}, execution_time_us={}, throughput_ops_per_sec={:.2}, memory_usage_mb={:.2})",
            self.success, self.execution_time_us, self.throughput_ops_per_sec, self.memory_usage_mb
        )
    }
}

#[pymethods]
impl PyNPUBridge {
    /// Create new NPU bridge instance
    #[new]
    fn new(config: Option<PyBridgeConfig>) -> PyResult<Self> {
        let runtime = Runtime::new()
            .map_err(|e| PyRuntimeError::new_err(format!("Failed to create async runtime: {}", e)))?;

        let bridge_config = if let Some(py_config) = config {
            Python::with_gil(|py| py_config.to_rust_config(py))?
        } else {
            BridgeConfig::default()
        };

        Ok(Self {
            bridge: None,
            runtime,
            config: bridge_config,
        })
    }

    /// Initialize the NPU bridge
    fn initialize(&mut self, py: Python) -> PyResult<()> {
        py.allow_threads(|| {
            self.runtime.block_on(async {
                let bridge = NPUCoordinationBridge::new(self.config.clone()).await
                    .map_err(|e| PyRuntimeError::new_err(format!("Failed to create bridge: {}", e)))?;

                bridge.start().await
                    .map_err(|e| PyRuntimeError::new_err(format!("Failed to start bridge: {}", e)))?;

                self.bridge = Some(bridge);
                Ok(())
            })
        })
    }

    /// Configure NPU hardware
    fn configure_npu(&self, py: Python, npu_config: PyNPUConfig) -> PyResult<PyOperationResult> {
        let bridge = self.bridge.as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("Bridge not initialized"))?;

        let rust_config = npu_config.to_rust_config();

        py.allow_threads(|| {
            self.runtime.block_on(async {
                let operation = NPUOperation::Initialize { config: rust_config };
                let result = bridge.execute_operation(operation).await
                    .map_err(|e| PyRuntimeError::new_err(format!("NPU initialization failed: {}", e)))?;

                self.convert_operation_result(result, py)
            })
        })
    }

    /// Load model onto NPU
    fn load_model(&self, py: Python, model_path: String, model_id: String) -> PyResult<PyOperationResult> {
        let bridge = self.bridge.as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("Bridge not initialized"))?;

        py.allow_threads(|| {
            self.runtime.block_on(async {
                let operation = NPUOperation::LoadModel { model_path, model_id };
                let result = bridge.execute_operation(operation).await
                    .map_err(|e| PyRuntimeError::new_err(format!("Model loading failed: {}", e)))?;

                self.convert_operation_result(result, py)
            })
        })
    }

    /// Run inference on loaded model
    fn run_inference(
        &self,
        py: Python,
        model_id: String,
        input_data: Vec<f32>,
        batch_size: Option<u32>,
    ) -> PyResult<PyOperationResult> {
        let bridge = self.bridge.as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("Bridge not initialized"))?;

        let batch_size = batch_size.unwrap_or(1);

        py.allow_threads(|| {
            self.runtime.block_on(async {
                let operation = NPUOperation::Inference {
                    model_id,
                    input_data,
                    batch_size,
                };
                let result = bridge.execute_operation(operation).await
                    .map_err(|e| PyRuntimeError::new_err(format!("Inference failed: {}", e)))?;

                self.convert_operation_result(result, py)
            })
        })
    }

    /// Process signal data
    fn process_signal(
        &self,
        py: Python,
        operation: String,
        data: Vec<f32>,
        parameters: Option<PyObject>,
    ) -> PyResult<PyOperationResult> {
        let bridge = self.bridge.as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("Bridge not initialized"))?;

        // Convert Python parameters to JSON
        let json_params = if let Some(params) = parameters {
            let json_str = Python::with_gil(|py| {
                let json_module = py.import("json")?;
                let json_str = json_module.call_method1("dumps", (params,))?;
                json_str.extract::<String>()
            })?;
            serde_json::from_str(&json_str)
                .map_err(|e| PyRuntimeError::new_err(format!("Invalid parameters: {}", e)))?
        } else {
            serde_json::json!({})
        };

        py.allow_threads(|| {
            self.runtime.block_on(async {
                let operation = NPUOperation::SignalProcessing {
                    operation,
                    data,
                    parameters: json_params,
                };
                let result = bridge.execute_operation(operation).await
                    .map_err(|e| PyRuntimeError::new_err(format!("Signal processing failed: {}", e)))?;

                self.convert_operation_result(result, py)
            })
        })
    }

    /// Run performance benchmark
    fn benchmark(&self, py: Python, duration_ms: u32, operation_type: String) -> PyResult<PyOperationResult> {
        let bridge = self.bridge.as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("Bridge not initialized"))?;

        py.allow_threads(|| {
            self.runtime.block_on(async {
                let operation = NPUOperation::Benchmark {
                    duration_ms,
                    operation_type,
                };
                let result = bridge.execute_operation(operation).await
                    .map_err(|e| PyRuntimeError::new_err(format!("Benchmark failed: {}", e)))?;

                self.convert_operation_result(result, py)
            })
        })
    }

    /// Check bridge health
    fn health_check(&self, py: Python) -> PyResult<PyOperationResult> {
        let bridge = self.bridge.as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("Bridge not initialized"))?;

        py.allow_threads(|| {
            self.runtime.block_on(async {
                let operation = NPUOperation::HealthCheck;
                let result = bridge.execute_operation(operation).await
                    .map_err(|e| PyRuntimeError::new_err(format!("Health check failed: {}", e)))?;

                self.convert_operation_result(result, py)
            })
        })
    }

    /// Get bridge statistics
    fn get_statistics(&self, py: Python) -> PyResult<PyObject> {
        let bridge = self.bridge.as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("Bridge not initialized"))?;

        py.allow_threads(|| {
            self.runtime.block_on(async {
                let stats = bridge.get_statistics().await
                    .map_err(|e| PyRuntimeError::new_err(format!("Failed to get statistics: {}", e)))?;

                // Convert JSON to Python dict
                let json_str = serde_json::to_string(&stats)
                    .map_err(|e| PyRuntimeError::new_err(format!("Failed to serialize statistics: {}", e)))?;

                Python::with_gil(|py| {
                    let json_module = py.import("json")?;
                    let python_dict = json_module.call_method1("loads", (json_str,))?;
                    Ok(python_dict.into())
                })
            })
        })
    }

    /// Set MATLAB configuration
    fn set_matlab_config(&mut self, matlab_root: String, enable_signal_processing: bool, max_workers: u32) {
        self.config.matlab_config = Some(MatlabConfig {
            matlab_root,
            enable_signal_processing,
            max_workers,
        });
    }

    /// Get current configuration
    fn get_config(&self, py: Python) -> PyResult<PyObject> {
        let config_json = serde_json::to_string(&self.config)
            .map_err(|e| PyRuntimeError::new_err(format!("Failed to serialize config: {}", e)))?;

        Python::with_gil(|py| {
            let json_module = py.import("json")?;
            let python_dict = json_module.call_method1("loads", (config_json,))?;
            Ok(python_dict.into())
        })
    }

    /// Batch processing for multiple operations
    fn batch_inference(
        &self,
        py: Python,
        model_id: String,
        batch_data: Vec<Vec<f32>>,
    ) -> PyResult<Vec<PyOperationResult>> {
        let bridge = self.bridge.as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("Bridge not initialized"))?;

        py.allow_threads(|| {
            self.runtime.block_on(async {
                let mut results = Vec::new();

                for input_data in batch_data {
                    let operation = NPUOperation::Inference {
                        model_id: model_id.clone(),
                        input_data,
                        batch_size: 1,
                    };

                    let result = bridge.execute_operation(operation).await
                        .map_err(|e| PyRuntimeError::new_err(format!("Batch inference failed: {}", e)))?;

                    let py_result = self.convert_operation_result(result, py)?;
                    results.push(py_result);
                }

                Ok(results)
            })
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "PyNPUBridge(initialized={}, target_ops_per_sec={})",
            self.bridge.is_some(),
            self.config.target_ops_per_sec
        )
    }
}

impl PyNPUBridge {
    /// Convert Rust OperationResult to Python wrapper
    fn convert_operation_result(&self, result: OperationResult, py: Python) -> PyResult<PyOperationResult> {
        // Convert data JSON to Python dict
        let data_dict = Python::with_gil(|py| {
            let json_module = py.import("json")?;
            let data_str = serde_json::to_string(&result.data)
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to serialize data: {}", e)))?;
            let python_dict = json_module.call_method1("loads", (data_str,))?;
            Ok::<Py<PyDict>, PyErr>(python_dict.downcast::<PyDict>()?.into())
        })?;

        Ok(PyOperationResult {
            success: result.success,
            execution_time_us: result.execution_time_us,
            throughput_ops_per_sec: result.throughput_ops_per_sec,
            memory_usage_mb: result.memory_usage_mb,
            data: data_dict,
            error: result.error,
        })
    }
}

/// Python module initialization
#[pymodule]
fn npu_coordination_bridge(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyNPUBridge>()?;
    m.add_class::<PyBridgeConfig>()?;
    m.add_class::<PyNPUConfig>()?;
    m.add_class::<PyOperationResult>()?;

    // Add module-level functions
    m.add_function(wrap_pyfunction!(create_default_bridge, m)?)?;
    m.add_function(wrap_pyfunction!(get_system_info, m)?)?;

    // Add constants
    m.add("DEFAULT_TARGET_OPS_PER_SEC", 50_000u32)?;
    m.add("DEFAULT_MAX_LATENCY_US", 1_000u32)?;
    m.add("VERSION", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}

/// Create a bridge with default configuration
#[pyfunction]
fn create_default_bridge() -> PyResult<PyNPUBridge> {
    PyNPUBridge::new(None)
}

/// Get system information relevant to NPU operations
#[pyfunction]
fn get_system_info(py: Python) -> PyResult<PyObject> {
    let info = serde_json::json!({
        "cpu_count": num_cpus::get(),
        "target_arch": std::env::consts::ARCH,
        "target_os": std::env::consts::OS,
        "version": env!("CARGO_PKG_VERSION"),
        "rust_version": env!("CARGO_PKG_RUST_VERSION"),
        "available_features": [
            "intel-optimizations",
            "openvino-integration",
            "matlab-support",
            "real-time-coordination"
        ]
    });

    let json_str = serde_json::to_string(&info)
        .map_err(|e| PyRuntimeError::new_err(format!("Failed to serialize system info: {}", e)))?;

    Python::with_gil(|py| {
        let json_module = py.import("json")?;
        let python_dict = json_module.call_method1("loads", (json_str,))?;
        Ok(python_dict.into())
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::prepare_freethreaded_python;

    #[test]
    fn test_python_bindings() {
        prepare_freethreaded_python();

        Python::with_gil(|py| {
            // Test bridge configuration
            let config = PyBridgeConfig::new();
            assert_eq!(config.target_ops_per_sec, 50_000);

            // Test NPU configuration
            let npu_config = PyNPUConfig::new();
            assert_eq!(npu_config.device_id, "NPU");
            assert_eq!(npu_config.precision, "FP16");

            // Test bridge creation
            let bridge = PyNPUBridge::new(Some(config));
            assert!(bridge.is_ok());
        });
    }

    #[test]
    fn test_system_info() {
        prepare_freethreaded_python();

        Python::with_gil(|py| {
            let info = get_system_info(py);
            assert!(info.is_ok());
        });
    }
}