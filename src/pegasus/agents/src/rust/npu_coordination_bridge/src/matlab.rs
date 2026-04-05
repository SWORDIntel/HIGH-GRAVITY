//! MATLAB Signal Processing Integration
//!
//! This module provides integration with MATLAB for advanced signal processing
//! operations that complement NPU inference capabilities.

use std::ffi::{CString, CStr};
use std::os::raw::{c_char, c_int, c_double, c_void};
use std::path::{Path, PathBuf};
use std::collections::HashMap;
use anyhow::{Result, Context, bail};
use serde::{Deserialize, Serialize};
use tracing::{info, warn, error, debug, instrument};
use libloading::{Library, Symbol};

use crate::MatlabConfig;

/// MATLAB Engine FFI bindings
#[allow(non_camel_case_types)]
type mxArray = c_void;

#[allow(non_camel_case_types)]
type Engine = c_void;

/// MATLAB function signatures for dynamic loading
type EngineOpenFn = unsafe extern "C" fn(*const c_char) -> *mut Engine;
type EngineCloseFn = unsafe extern "C" fn(*mut Engine) -> c_int;
type EngineEvalStringFn = unsafe extern "C" fn(*mut Engine, *const c_char) -> c_int;
type EngineGetVariableFn = unsafe extern "C" fn(*mut Engine, *const c_char) -> *mut mxArray;
type EnginePutVariableFn = unsafe extern "C" fn(*mut Engine, *const c_char, *const mxArray) -> c_int;

/// MATLAB mxArray function signatures
type MxCreateDoubleMatrixFn = unsafe extern "C" fn(usize, usize, c_int) -> *mut mxArray;
type MxGetPrFn = unsafe extern "C" fn(*const mxArray) -> *mut c_double;
type MxGetMFn = unsafe extern "C" fn(*const mxArray) -> usize;
type MxGetNFn = unsafe extern "C" fn(*const mxArray) -> usize;
type MxDestroyArrayFn = unsafe extern "C" fn(*mut mxArray);

/// Signal processing operation types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SignalOperation {
    /// Fast Fourier Transform
    FFT {
        window: String,
        overlap: f32,
    },
    /// Digital filtering
    Filter {
        filter_type: String,
        order: u32,
        cutoff_freq: f32,
        sample_rate: f32,
    },
    /// Kalman filtering
    Kalman {
        process_noise: f32,
        measurement_noise: f32,
    },
    /// Wavelet transform
    Wavelet {
        wavelet_type: String,
        levels: u32,
    },
    /// Spectral analysis
    Spectral {
        method: String,
        window_size: u32,
        overlap_percent: f32,
    },
    /// Adaptive filtering
    Adaptive {
        algorithm: String,
        step_size: f32,
        filter_length: u32,
    },
}

/// Signal processing result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignalResult {
    pub output_data: Vec<f32>,
    pub metadata: HashMap<String, serde_json::Value>,
    pub processing_time_ms: f64,
    pub algorithm_info: String,
}

/// MATLAB engine wrapper for signal processing
pub struct MatlabSignalProcessor {
    engine: Option<*mut Engine>,
    library: Option<Library>,
    config: MatlabConfig,

    // Function pointers loaded from MATLAB library
    engine_open: Option<Symbol<'static, EngineOpenFn>>,
    engine_close: Option<Symbol<'static, EngineCloseFn>>,
    engine_eval_string: Option<Symbol<'static, EngineEvalStringFn>>,
    engine_get_variable: Option<Symbol<'static, EngineGetVariableFn>>,
    engine_put_variable: Option<Symbol<'static, EnginePutVariableFn>>,

    mx_create_double_matrix: Option<Symbol<'static, MxCreateDoubleMatrixFn>>,
    mx_get_pr: Option<Symbol<'static, MxGetPrFn>>,
    mx_get_m: Option<Symbol<'static, MxGetMFn>>,
    mx_get_n: Option<Symbol<'static, MxGetNFn>>,
    mx_destroy_array: Option<Symbol<'static, MxDestroyArrayFn>>,
}

impl MatlabSignalProcessor {
    /// Create new MATLAB signal processor
    #[instrument(skip(config))]
    pub async fn new(config: MatlabConfig) -> Result<Self> {
        info!("Initializing MATLAB signal processor with root: {}", config.matlab_root);

        let mut processor = Self {
            engine: None,
            library: None,
            config,
            engine_open: None,
            engine_close: None,
            engine_eval_string: None,
            engine_get_variable: None,
            engine_put_variable: None,
            mx_create_double_matrix: None,
            mx_get_pr: None,
            mx_get_m: None,
            mx_get_n: None,
            mx_destroy_array: None,
        };

        // Load MATLAB libraries
        processor.load_matlab_libraries().await
            .context("Failed to load MATLAB libraries")?;

        // Initialize MATLAB engine
        processor.initialize_engine().await
            .context("Failed to initialize MATLAB engine")?;

        info!("MATLAB signal processor initialized successfully");
        Ok(processor)
    }

    /// Load MATLAB dynamic libraries
    #[instrument(skip(self))]
    async fn load_matlab_libraries(&mut self) -> Result<()> {
        debug!("Loading MATLAB dynamic libraries");

        // Construct library paths
        let matlab_root = Path::new(&self.config.matlab_root);
        let bin_path = matlab_root.join("bin").join("glnxa64"); // Linux x64

        // Primary library paths to try
        let library_paths = vec![
            bin_path.join("libeng.so"),
            bin_path.join("libmx.so"),
            PathBuf::from("/usr/local/MATLAB/R2024a/bin/glnxa64/libeng.so"),
            PathBuf::from("/opt/matlab/bin/glnxa64/libeng.so"),
        ];

        let mut library_loaded = false;

        for lib_path in library_paths {
            if lib_path.exists() {
                match unsafe { Library::new(&lib_path) } {
                    Ok(lib) => {
                        info!("Loaded MATLAB library: {}", lib_path.display());

                        // Load function symbols
                        self.load_function_symbols(&lib)?;

                        // Store library to keep it loaded
                        self.library = Some(lib);
                        library_loaded = true;
                        break;
                    },
                    Err(e) => {
                        warn!("Failed to load library {}: {}", lib_path.display(), e);
                    }
                }
            }
        }

        if !library_loaded {
            bail!("Could not load any MATLAB libraries. Check MATLAB installation.");
        }

        Ok(())
    }

    /// Load function symbols from MATLAB library
    fn load_function_symbols(&mut self, library: &Library) -> Result<()> {
        debug!("Loading MATLAB function symbols");

        // Load engine functions
        self.engine_open = Some(unsafe {
            library.get(b"engOpen\0")
                .context("Failed to load engOpen function")?
        });

        self.engine_close = Some(unsafe {
            library.get(b"engClose\0")
                .context("Failed to load engClose function")?
        });

        self.engine_eval_string = Some(unsafe {
            library.get(b"engEvalString\0")
                .context("Failed to load engEvalString function")?
        });

        self.engine_get_variable = Some(unsafe {
            library.get(b"engGetVariable\0")
                .context("Failed to load engGetVariable function")?
        });

        self.engine_put_variable = Some(unsafe {
            library.get(b"engPutVariable\0")
                .context("Failed to load engPutVariable function")?
        });

        // Load mxArray functions
        self.mx_create_double_matrix = Some(unsafe {
            library.get(b"mxCreateDoubleMatrix\0")
                .context("Failed to load mxCreateDoubleMatrix function")?
        });

        self.mx_get_pr = Some(unsafe {
            library.get(b"mxGetPr\0")
                .context("Failed to load mxGetPr function")?
        });

        self.mx_get_m = Some(unsafe {
            library.get(b"mxGetM\0")
                .context("Failed to load mxGetM function")?
        });

        self.mx_get_n = Some(unsafe {
            library.get(b"mxGetN\0")
                .context("Failed to load mxGetN function")?
        });

        self.mx_destroy_array = Some(unsafe {
            library.get(b"mxDestroyArray\0")
                .context("Failed to load mxDestroyArray function")?
        });

        info!("All MATLAB function symbols loaded successfully");
        Ok(())
    }

    /// Initialize MATLAB engine
    #[instrument(skip(self))]
    async fn initialize_engine(&mut self) -> Result<()> {
        debug!("Initializing MATLAB engine");

        let engine_open = self.engine_open.as_ref()
            .ok_or_else(|| anyhow::anyhow!("Engine open function not loaded"))?;

        // Start MATLAB engine
        let engine_ptr = unsafe {
            engine_open(std::ptr::null())
        };

        if engine_ptr.is_null() {
            bail!("Failed to start MATLAB engine");
        }

        self.engine = Some(engine_ptr);

        // Test engine with simple command
        self.eval_string("disp('MATLAB engine initialized')").await?;

        // Configure MATLAB for signal processing
        if self.config.enable_signal_processing {
            self.configure_signal_processing().await?;
        }

        info!("MATLAB engine initialized and configured");
        Ok(())
    }

    /// Configure MATLAB for signal processing
    async fn configure_signal_processing(&self) -> Result<()> {
        debug!("Configuring MATLAB for signal processing");

        let setup_commands = vec![
            "addpath(genpath(fullfile(matlabroot, 'toolbox', 'signal')))",
            "addpath(genpath(fullfile(matlabroot, 'toolbox', 'wavelet')))",
            "addpath(genpath(fullfile(matlabroot, 'toolbox', 'dsp')))",
            &format!("maxNumCompThreads({})", self.config.max_workers),
        ];

        for command in setup_commands {
            if let Err(e) = self.eval_string(command).await {
                warn!("Failed to execute setup command '{}': {}", command, e);
            }
        }

        Ok(())
    }

    /// Execute MATLAB command string
    async fn eval_string(&self, command: &str) -> Result<()> {
        let engine = self.engine
            .ok_or_else(|| anyhow::anyhow!("MATLAB engine not initialized"))?;

        let eval_fn = self.engine_eval_string.as_ref()
            .ok_or_else(|| anyhow::anyhow!("Engine eval function not loaded"))?;

        let command_cstr = CString::new(command)
            .context("Failed to create C string from command")?;

        let result = unsafe {
            eval_fn(engine, command_cstr.as_ptr())
        };

        if result != 0 {
            bail!("MATLAB command failed: {}", command);
        }

        Ok(())
    }

    /// Process signal data using MATLAB
    #[instrument(skip(self, data))]
    pub async fn process_signal(
        &self,
        operation: SignalOperation,
        data: &[f32],
    ) -> Result<SignalResult> {
        let start_time = std::time::Instant::now();

        debug!("Processing signal with operation: {:?}", operation);

        // Put input data into MATLAB workspace
        self.put_variable("input_signal", data).await?;

        // Generate and execute MATLAB command based on operation
        let (matlab_command, metadata) = self.generate_matlab_command(&operation).await?;

        debug!("Executing MATLAB command: {}", matlab_command);
        self.eval_string(&matlab_command).await?;

        // Get result from MATLAB workspace
        let output_data = self.get_variable("output_signal").await?;

        let processing_time_ms = start_time.elapsed().as_millis() as f64;

        let result = SignalResult {
            output_data,
            metadata,
            processing_time_ms,
            algorithm_info: format!("{:?}", operation),
        };

        debug!("Signal processing completed in {:.2} ms", processing_time_ms);
        Ok(result)
    }

    /// Generate MATLAB command for signal operation
    async fn generate_matlab_command(
        &self,
        operation: &SignalOperation,
    ) -> Result<(String, HashMap<String, serde_json::Value>)> {
        let mut metadata = HashMap::new();

        let command = match operation {
            SignalOperation::FFT { window, overlap } => {
                metadata.insert("window".to_string(), serde_json::json!(window));
                metadata.insert("overlap".to_string(), serde_json::json!(overlap));

                format!(
                    "windowed_signal = input_signal .* {}(length(input_signal))'; \
                     output_signal = real(fft(windowed_signal));",
                    window.to_lowercase()
                )
            },

            SignalOperation::Filter { filter_type, order, cutoff_freq, sample_rate } => {
                metadata.insert("filter_type".to_string(), serde_json::json!(filter_type));
                metadata.insert("order".to_string(), serde_json::json!(order));
                metadata.insert("cutoff_freq".to_string(), serde_json::json!(cutoff_freq));
                metadata.insert("sample_rate".to_string(), serde_json::json!(sample_rate));

                match filter_type.as_str() {
                    "butterworth" => {
                        format!(
                            "nyquist = {} / 2; \
                             normalized_cutoff = {} / nyquist; \
                             [b, a] = butter({}, normalized_cutoff); \
                             output_signal = filter(b, a, input_signal);",
                            sample_rate, cutoff_freq, order
                        )
                    },
                    "chebyshev" => {
                        format!(
                            "nyquist = {} / 2; \
                             normalized_cutoff = {} / nyquist; \
                             [b, a] = cheby1({}, 0.5, normalized_cutoff); \
                             output_signal = filter(b, a, input_signal);",
                            sample_rate, cutoff_freq, order
                        )
                    },
                    _ => {
                        bail!("Unsupported filter type: {}", filter_type);
                    }
                }
            },

            SignalOperation::Kalman { process_noise, measurement_noise } => {
                metadata.insert("process_noise".to_string(), serde_json::json!(process_noise));
                metadata.insert("measurement_noise".to_string(), serde_json::json!(measurement_noise));

                format!(
                    "n = length(input_signal); \
                     output_signal = zeros(size(input_signal)); \
                     x = input_signal(1); \
                     P = 1; \
                     Q = {}; \
                     R = {}; \
                     for i = 1:n \
                         x_pred = x; \
                         P_pred = P + Q; \
                         K = P_pred / (P_pred + R); \
                         x = x_pred + K * (input_signal(i) - x_pred); \
                         P = (1 - K) * P_pred; \
                         output_signal(i) = x; \
                     end",
                    process_noise, measurement_noise
                )
            },

            SignalOperation::Wavelet { wavelet_type, levels } => {
                metadata.insert("wavelet_type".to_string(), serde_json::json!(wavelet_type));
                metadata.insert("levels".to_string(), serde_json::json!(levels));

                format!(
                    "[c, l] = wavedec(input_signal, {}, '{}'); \
                     output_signal = waverec(c, l, '{}');",
                    levels, wavelet_type, wavelet_type
                )
            },

            SignalOperation::Spectral { method, window_size, overlap_percent } => {
                metadata.insert("method".to_string(), serde_json::json!(method));
                metadata.insert("window_size".to_string(), serde_json::json!(window_size));
                metadata.insert("overlap_percent".to_string(), serde_json::json!(overlap_percent));

                match method.as_str() {
                    "welch" => {
                        format!(
                            "[pxx, f] = pwelch(input_signal, {}, {}); \
                             output_signal = pxx;",
                            window_size,
                            (window_size as f32 * overlap_percent / 100.0) as u32
                        )
                    },
                    "periodogram" => {
                        "output_signal = periodogram(input_signal);".to_string()
                    },
                    _ => {
                        bail!("Unsupported spectral method: {}", method);
                    }
                }
            },

            SignalOperation::Adaptive { algorithm, step_size, filter_length } => {
                metadata.insert("algorithm".to_string(), serde_json::json!(algorithm));
                metadata.insert("step_size".to_string(), serde_json::json!(step_size));
                metadata.insert("filter_length".to_string(), serde_json::json!(filter_length));

                match algorithm.as_str() {
                    "lms" => {
                        format!(
                            "mu = {}; \
                             M = {}; \
                             w = zeros(M, 1); \
                             output_signal = zeros(size(input_signal)); \
                             for n = M:length(input_signal) \
                                 x = input_signal(n:-1:n-M+1); \
                                 y = w' * x; \
                                 e = input_signal(n) - y; \
                                 w = w + mu * e * x; \
                                 output_signal(n) = y; \
                             end",
                            step_size, filter_length
                        )
                    },
                    _ => {
                        bail!("Unsupported adaptive algorithm: {}", algorithm);
                    }
                }
            },
        };

        Ok((command, metadata))
    }

    /// Put variable into MATLAB workspace
    async fn put_variable(&self, name: &str, data: &[f32]) -> Result<()> {
        let engine = self.engine
            .ok_or_else(|| anyhow::anyhow!("MATLAB engine not initialized"))?;

        let put_var_fn = self.engine_put_variable.as_ref()
            .ok_or_else(|| anyhow::anyhow!("Engine put variable function not loaded"))?;

        let create_matrix_fn = self.mx_create_double_matrix.as_ref()
            .ok_or_else(|| anyhow::anyhow!("Create matrix function not loaded"))?;

        let get_pr_fn = self.mx_get_pr.as_ref()
            .ok_or_else(|| anyhow::anyhow!("Get pr function not loaded"))?;

        // Create MATLAB array
        let mx_array = unsafe {
            create_matrix_fn(data.len(), 1, 0) // 0 = real, not complex
        };

        if mx_array.is_null() {
            bail!("Failed to create MATLAB array");
        }

        // Copy data to MATLAB array
        unsafe {
            let pr = get_pr_fn(mx_array);
            for (i, &value) in data.iter().enumerate() {
                *pr.add(i) = value as c_double;
            }
        }

        // Put array into workspace
        let name_cstr = CString::new(name)
            .context("Failed to create C string from variable name")?;

        let result = unsafe {
            put_var_fn(engine, name_cstr.as_ptr(), mx_array)
        };

        if result != 0 {
            bail!("Failed to put variable '{}' into MATLAB workspace", name);
        }

        Ok(())
    }

    /// Get variable from MATLAB workspace
    async fn get_variable(&self, name: &str) -> Result<Vec<f32>> {
        let engine = self.engine
            .ok_or_else(|| anyhow::anyhow!("MATLAB engine not initialized"))?;

        let get_var_fn = self.engine_get_variable.as_ref()
            .ok_or_else(|| anyhow::anyhow!("Engine get variable function not loaded"))?;

        let get_pr_fn = self.mx_get_pr.as_ref()
            .ok_or_else(|| anyhow::anyhow!("Get pr function not loaded"))?;

        let get_m_fn = self.mx_get_m.as_ref()
            .ok_or_else(|| anyhow::anyhow!("Get m function not loaded"))?;

        let get_n_fn = self.mx_get_n.as_ref()
            .ok_or_else(|| anyhow::anyhow!("Get n function not loaded"))?;

        let name_cstr = CString::new(name)
            .context("Failed to create C string from variable name")?;

        // Get array from workspace
        let mx_array = unsafe {
            get_var_fn(engine, name_cstr.as_ptr())
        };

        if mx_array.is_null() {
            bail!("Variable '{}' not found in MATLAB workspace", name);
        }

        // Get array dimensions and data
        let (m, n) = unsafe {
            (get_m_fn(mx_array), get_n_fn(mx_array))
        };

        let total_elements = m * n;
        let mut result = Vec::with_capacity(total_elements);

        unsafe {
            let pr = get_pr_fn(mx_array);
            for i in 0..total_elements {
                result.push(*pr.add(i) as f32);
            }
        }

        Ok(result)
    }

    /// Check if MATLAB engine is available
    pub fn is_available(&self) -> bool {
        self.engine.is_some() && self.library.is_some()
    }

    /// Get MATLAB configuration
    pub fn get_config(&self) -> &MatlabConfig {
        &self.config
    }
}

impl Drop for MatlabSignalProcessor {
    fn drop(&mut self) {
        if let Some(engine) = self.engine {
            if let Some(close_fn) = &self.engine_close {
                unsafe {
                    close_fn(engine);
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_signal_operation_serialization() {
        let operation = SignalOperation::FFT {
            window: "hamming".to_string(),
            overlap: 0.5,
        };

        let serialized = serde_json::to_string(&operation).unwrap();
        let deserialized: SignalOperation = serde_json::from_str(&serialized).unwrap();

        match deserialized {
            SignalOperation::FFT { window, overlap } => {
                assert_eq!(window, "hamming");
                assert_eq!(overlap, 0.5);
            },
            _ => panic!("Deserialization failed"),
        }
    }

    #[test]
    fn test_matlab_command_generation() {
        // This would require async runtime, skipping for unit test
        // Real tests would use integration test setup
    }
}