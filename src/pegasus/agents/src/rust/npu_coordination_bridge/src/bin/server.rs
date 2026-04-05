//! NPU Coordination Bridge Server
//!
//! Standalone server that exposes the NPU coordination bridge functionality
//! via WebSocket and HTTP APIs for external integration.

use std::net::SocketAddr;
use std::sync::Arc;
use anyhow::{Result, Context};
use clap::{Arg, Command};
use serde_json::json;
use tokio::net::TcpListener;
use tokio_tungstenite::{
    accept_async,
    tungstenite::{Message, Result as WsResult},
};
use tracing::{info, warn, error, debug, Level};
use tracing_subscriber;

use npu_coordination_bridge::{
    NPUCoordinationBridge, BridgeConfig, NPUConfig, NPUOperation, OperationResult
};

/// Server configuration
#[derive(Debug, Clone)]
struct ServerConfig {
    bind_address: SocketAddr,
    bridge_config: BridgeConfig,
    enable_http: bool,
    enable_websocket: bool,
    enable_metrics: bool,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            bind_address: "127.0.0.1:8080".parse().unwrap(),
            bridge_config: BridgeConfig::default(),
            enable_http: true,
            enable_websocket: true,
            enable_metrics: true,
        }
    }
}

/// NPU Bridge Server
struct NPUBridgeServer {
    config: ServerConfig,
    bridge: Arc<NPUCoordinationBridge>,
}

impl NPUBridgeServer {
    /// Create new server
    async fn new(config: ServerConfig) -> Result<Self> {
        info!("Creating NPU bridge server with config: {:#?}", config);

        let bridge = Arc::new(
            NPUCoordinationBridge::new(config.bridge_config.clone()).await
                .context("Failed to create NPU coordination bridge")?
        );

        bridge.start().await
            .context("Failed to start NPU coordination bridge")?;

        Ok(Self { config, bridge })
    }

    /// Start the server
    async fn start(&self) -> Result<()> {
        info!("Starting NPU bridge server on {}", self.config.bind_address);

        let listener = TcpListener::bind(self.config.bind_address).await
            .context("Failed to bind to address")?;

        info!("Server listening on {}", self.config.bind_address);

        while let Ok((stream, addr)) = listener.accept().await {
            debug!("New connection from: {}", addr);

            let bridge = Arc::clone(&self.bridge);
            let config = self.config.clone();

            tokio::spawn(async move {
                if let Err(e) = Self::handle_connection(stream, bridge, config).await {
                    error!("Error handling connection from {}: {}", addr, e);
                }
            });
        }

        Ok(())
    }

    /// Handle incoming connection
    async fn handle_connection(
        stream: tokio::net::TcpStream,
        bridge: Arc<NPUCoordinationBridge>,
        config: ServerConfig,
    ) -> Result<()> {
        // For simplicity, we'll handle everything as WebSocket
        let ws_stream = accept_async(stream).await
            .context("Failed to accept WebSocket connection")?;

        info!("WebSocket connection established");

        let (mut ws_sender, mut ws_receiver) = ws_stream.split();

        // Send welcome message
        let welcome = json!({
            "type": "welcome",
            "server": "NPU Coordination Bridge",
            "version": env!("CARGO_PKG_VERSION"),
            "capabilities": [
                "inference",
                "model_loading",
                "signal_processing",
                "benchmarking",
                "health_monitoring"
            ]
        });

        if let Err(e) = ws_sender.send(Message::Text(welcome.to_string())).await {
            warn!("Failed to send welcome message: {}", e);
        }

        // Handle incoming messages
        while let Some(msg) = ws_receiver.next().await {
            match msg {
                Ok(Message::Text(text)) => {
                    match Self::handle_text_message(&text, &bridge).await {
                        Ok(response) => {
                            if let Err(e) = ws_sender.send(Message::Text(response)).await {
                                error!("Failed to send response: {}", e);
                                break;
                            }
                        }
                        Err(e) => {
                            let error_response = json!({
                                "type": "error",
                                "error": e.to_string()
                            });

                            if let Err(e) = ws_sender.send(Message::Text(error_response.to_string())).await {
                                error!("Failed to send error response: {}", e);
                                break;
                            }
                        }
                    }
                }
                Ok(Message::Binary(data)) => {
                    // Handle binary data (e.g., model files, large datasets)
                    debug!("Received binary data: {} bytes", data.len());

                    let response = json!({
                        "type": "binary_received",
                        "size": data.len()
                    });

                    if let Err(e) = ws_sender.send(Message::Text(response.to_string())).await {
                        error!("Failed to send binary acknowledgment: {}", e);
                        break;
                    }
                }
                Ok(Message::Close(_)) => {
                    info!("WebSocket connection closed by client");
                    break;
                }
                Ok(Message::Ping(ping)) => {
                    if let Err(e) = ws_sender.send(Message::Pong(ping)).await {
                        error!("Failed to send pong: {}", e);
                        break;
                    }
                }
                Ok(Message::Pong(_)) => {
                    debug!("Received pong");
                }
                Err(e) => {
                    error!("WebSocket error: {}", e);
                    break;
                }
            }
        }

        info!("WebSocket connection closed");
        Ok(())
    }

    /// Handle text message from client
    async fn handle_text_message(
        text: &str,
        bridge: &Arc<NPUCoordinationBridge>,
    ) -> Result<String> {
        let request: serde_json::Value = serde_json::from_str(text)
            .context("Failed to parse JSON message")?;

        let request_type = request["type"].as_str()
            .ok_or_else(|| anyhow::anyhow!("Missing 'type' field in request"))?;

        let response = match request_type {
            "health_check" => {
                let operation = NPUOperation::HealthCheck;
                let result = bridge.execute_operation(operation).await?;

                json!({
                    "type": "operation_result",
                    "request_type": "health_check",
                    "result": result
                })
            }

            "inference" => {
                let model_id = request["model_id"].as_str()
                    .ok_or_else(|| anyhow::anyhow!("Missing 'model_id' field"))?;

                let input_data: Vec<f32> = request["input_data"].as_array()
                    .ok_or_else(|| anyhow::anyhow!("Missing 'input_data' field"))?
                    .iter()
                    .map(|v| v.as_f64().unwrap_or(0.0) as f32)
                    .collect();

                let batch_size = request["batch_size"].as_u64().unwrap_or(1) as u32;

                let operation = NPUOperation::Inference {
                    model_id: model_id.to_string(),
                    input_data,
                    batch_size,
                };

                let result = bridge.execute_operation(operation).await?;

                json!({
                    "type": "operation_result",
                    "request_type": "inference",
                    "result": result
                })
            }

            "load_model" => {
                let model_path = request["model_path"].as_str()
                    .ok_or_else(|| anyhow::anyhow!("Missing 'model_path' field"))?;

                let model_id = request["model_id"].as_str()
                    .ok_or_else(|| anyhow::anyhow!("Missing 'model_id' field"))?;

                let operation = NPUOperation::LoadModel {
                    model_path: model_path.to_string(),
                    model_id: model_id.to_string(),
                };

                let result = bridge.execute_operation(operation).await?;

                json!({
                    "type": "operation_result",
                    "request_type": "load_model",
                    "result": result
                })
            }

            "signal_processing" => {
                let operation_name = request["operation"].as_str()
                    .ok_or_else(|| anyhow::anyhow!("Missing 'operation' field"))?;

                let data: Vec<f32> = request["data"].as_array()
                    .ok_or_else(|| anyhow::anyhow!("Missing 'data' field"))?
                    .iter()
                    .map(|v| v.as_f64().unwrap_or(0.0) as f32)
                    .collect();

                let parameters = request["parameters"].clone();

                let operation = NPUOperation::SignalProcessing {
                    operation: operation_name.to_string(),
                    data,
                    parameters,
                };

                let result = bridge.execute_operation(operation).await?;

                json!({
                    "type": "operation_result",
                    "request_type": "signal_processing",
                    "result": result
                })
            }

            "benchmark" => {
                let duration_ms = request["duration_ms"].as_u64().unwrap_or(1000) as u32;
                let operation_type = request["operation_type"].as_str().unwrap_or("generic");

                let operation = NPUOperation::Benchmark {
                    duration_ms,
                    operation_type: operation_type.to_string(),
                };

                let result = bridge.execute_operation(operation).await?;

                json!({
                    "type": "operation_result",
                    "request_type": "benchmark",
                    "result": result
                })
            }

            "get_statistics" => {
                let stats = bridge.get_statistics().await?;

                json!({
                    "type": "statistics",
                    "statistics": stats
                })
            }

            _ => {
                return Err(anyhow::anyhow!("Unknown request type: {}", request_type));
            }
        };

        Ok(response.to_string())
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_max_level(Level::INFO)
        .init();

    // Parse command line arguments
    let matches = Command::new("npu-bridge-server")
        .version(env!("CARGO_PKG_VERSION"))
        .about("NPU Coordination Bridge Server")
        .arg(
            Arg::new("bind")
                .short('b')
                .long("bind")
                .value_name("ADDRESS")
                .help("Bind address for the server")
                .default_value("127.0.0.1:8080")
        )
        .arg(
            Arg::new("workers")
                .short('w')
                .long("workers")
                .value_name("COUNT")
                .help("Number of worker threads")
                .default_value("0") // 0 means use number of CPU cores
        )
        .arg(
            Arg::new("target-ops")
                .short('t')
                .long("target-ops")
                .value_name("OPS_PER_SEC")
                .help("Target operations per second")
                .default_value("50000")
        )
        .arg(
            Arg::new("max-latency")
                .short('l')
                .long("max-latency")
                .value_name("MICROSECONDS")
                .help("Maximum latency in microseconds")
                .default_value("1000")
        )
        .arg(
            Arg::new("npu-memory")
                .long("npu-memory")
                .value_name("MB")
                .help("NPU memory limit in MB")
                .default_value("256")
        )
        .arg(
            Arg::new("precision")
                .short('p')
                .long("precision")
                .value_name("PRECISION")
                .help("NPU precision mode")
                .default_value("FP16")
                .value_parser(["FP32", "FP16", "INT8", "INT4"])
        )
        .get_matches();

    // Parse configuration
    let bind_address: SocketAddr = matches.get_one::<String>("bind")
        .unwrap()
        .parse()
        .context("Invalid bind address")?;

    let worker_count: usize = matches.get_one::<String>("workers")
        .unwrap()
        .parse()
        .context("Invalid worker count")?;

    let worker_threads = if worker_count == 0 {
        num_cpus::get()
    } else {
        worker_count
    };

    let target_ops_per_sec: u32 = matches.get_one::<String>("target-ops")
        .unwrap()
        .parse()
        .context("Invalid target ops per second")?;

    let max_latency_us: u32 = matches.get_one::<String>("max-latency")
        .unwrap()
        .parse()
        .context("Invalid max latency")?;

    let npu_memory_mb: u32 = matches.get_one::<String>("npu-memory")
        .unwrap()
        .parse()
        .context("Invalid NPU memory limit")?;

    let precision = matches.get_one::<String>("precision").unwrap().clone();

    // Create server configuration
    let bridge_config = BridgeConfig {
        target_ops_per_sec,
        max_latency_us,
        worker_threads,
        buffer_size: 8192,
        npu_config: NPUConfig {
            device_id: "server_npu".to_string(),
            max_batch_size: 32,
            precision,
            memory_limit_mb: npu_memory_mb,
            enable_caching: true,
        },
        matlab_config: None,
    };

    let server_config = ServerConfig {
        bind_address,
        bridge_config,
        enable_http: true,
        enable_websocket: true,
        enable_metrics: true,
    };

    info!("Starting NPU Coordination Bridge Server");
    info!("Configuration: {:#?}", server_config);

    // Create and start server
    let server = NPUBridgeServer::new(server_config).await
        .context("Failed to create server")?;

    server.start().await
        .context("Server failed")?;

    Ok(())
}

// WebSocket client example for testing
#[cfg(test)]
mod tests {
    use super::*;
    use tokio_tungstenite::{connect_async, tungstenite::Message};
    use futures_util::{SinkExt, StreamExt};

    #[tokio::test]
    async fn test_websocket_client() {
        // This test requires a running server
        // Skip if server is not available
        if std::env::var("NPU_SERVER_TEST").is_err() {
            return;
        }

        let url = "ws://127.0.0.1:8080";
        let (ws_stream, _) = connect_async(url).await.expect("Failed to connect");
        let (mut write, mut read) = ws_stream.split();

        // Send health check request
        let health_check = json!({
            "type": "health_check"
        });

        write.send(Message::Text(health_check.to_string())).await.unwrap();

        // Read response
        if let Some(msg) = read.next().await {
            let response = msg.unwrap();
            if let Message::Text(text) = response {
                let parsed: serde_json::Value = serde_json::from_str(&text).unwrap();
                assert_eq!(parsed["type"], "operation_result");
                assert_eq!(parsed["request_type"], "health_check");
            }
        }
    }
}