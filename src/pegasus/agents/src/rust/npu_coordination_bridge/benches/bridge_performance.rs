use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use tokio::runtime::Runtime;

use npu_coordination_bridge::{
    NPUCoordinationBridge, BridgeConfig, NPUConfig, NPUOperation, OperationResult
};

fn benchmark_bridge_operations(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    // Create bridge with optimized configuration
    let config = BridgeConfig {
        target_ops_per_sec: 50_000,
        max_latency_us: 1_000,
        worker_threads: num_cpus::get(),
        buffer_size: 8192,
        npu_config: NPUConfig {
            device_id: "benchmark_npu".to_string(),
            max_batch_size: 32,
            precision: "FP16".to_string(),
            memory_limit_mb: 256,
            enable_caching: true,
        },
        matlab_config: None,
    };

    let bridge = rt.block_on(async {
        let bridge = NPUCoordinationBridge::new(config).await.unwrap();
        bridge.start().await.unwrap();
        bridge
    });

    let mut group = c.benchmark_group("npu_operations");

    // Benchmark health check (lowest latency)
    group.bench_function("health_check", |b| {
        b.to_async(&rt).iter(|| async {
            let operation = NPUOperation::HealthCheck;
            black_box(bridge.execute_operation(operation).await.unwrap())
        })
    });

    // Benchmark inference with different batch sizes
    for batch_size in [1, 4, 8, 16, 32].iter() {
        group.bench_with_input(
            BenchmarkId::new("inference", batch_size),
            batch_size,
            |b, &batch_size| {
                b.to_async(&rt).iter(|| async {
                    let input_data = vec![1.0f32; 224 * 224 * 3 * batch_size as usize];
                    let operation = NPUOperation::Inference {
                        model_id: "benchmark_model".to_string(),
                        input_data,
                        batch_size,
                    };
                    black_box(bridge.execute_operation(operation).await.unwrap())
                })
            },
        );
    }

    // Benchmark signal processing
    for signal_size in [256, 512, 1024, 2048, 4096].iter() {
        group.bench_with_input(
            BenchmarkId::new("signal_fft", signal_size),
            signal_size,
            |b, &signal_size| {
                b.to_async(&rt).iter(|| async {
                    let signal_data = vec![1.0f32; signal_size];
                    let operation = NPUOperation::SignalProcessing {
                        operation: "fft".to_string(),
                        data: signal_data,
                        parameters: serde_json::json!({"window": "hamming"}),
                    };
                    black_box(bridge.execute_operation(operation).await.unwrap())
                })
            },
        );
    }

    group.finish();
}

fn benchmark_concurrent_operations(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    let config = BridgeConfig {
        target_ops_per_sec: 50_000,
        max_latency_us: 1_000,
        worker_threads: num_cpus::get(),
        buffer_size: 16384,
        npu_config: NPUConfig {
            device_id: "concurrent_benchmark_npu".to_string(),
            max_batch_size: 32,
            precision: "FP16".to_string(),
            memory_limit_mb: 512,
            enable_caching: true,
        },
        matlab_config: None,
    };

    let bridge = rt.block_on(async {
        let bridge = NPUCoordinationBridge::new(config).await.unwrap();
        bridge.start().await.unwrap();
        bridge
    });

    let mut group = c.benchmark_group("concurrent_operations");

    // Benchmark concurrent execution
    for concurrency in [1, 2, 4, 8, 16].iter() {
        group.bench_with_input(
            BenchmarkId::new("concurrent_health_checks", concurrency),
            concurrency,
            |b, &concurrency| {
                b.to_async(&rt).iter(|| async {
                    let mut handles = Vec::new();

                    for _ in 0..concurrency {
                        let bridge = &bridge;
                        let handle = tokio::spawn(async move {
                            let operation = NPUOperation::HealthCheck;
                            bridge.execute_operation(operation).await.unwrap()
                        });
                        handles.push(handle);
                    }

                    let results: Vec<OperationResult> = futures::future::join_all(handles)
                        .await
                        .into_iter()
                        .map(|r| r.unwrap())
                        .collect();

                    black_box(results)
                })
            },
        );
    }

    group.finish();
}

fn benchmark_throughput_sustained(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    let config = BridgeConfig {
        target_ops_per_sec: 50_000,
        max_latency_us: 500, // Tighter latency requirement
        worker_threads: num_cpus::get(),
        buffer_size: 32768,
        npu_config: NPUConfig {
            device_id: "throughput_benchmark_npu".to_string(),
            max_batch_size: 32,
            precision: "FP16".to_string(),
            memory_limit_mb: 1024,
            enable_caching: true,
        },
        matlab_config: None,
    };

    let bridge = rt.block_on(async {
        let bridge = NPUCoordinationBridge::new(config).await.unwrap();
        bridge.start().await.unwrap();
        bridge
    });

    c.bench_function("sustained_throughput_1000_ops", |b| {
        b.to_async(&rt).iter(|| async {
            let mut handles = Vec::new();

            // Launch 1000 concurrent operations
            for i in 0..1000 {
                let bridge = &bridge;
                let handle = tokio::spawn(async move {
                    let operation = if i % 10 == 0 {
                        // 10% inference operations
                        NPUOperation::Inference {
                            model_id: "throughput_test".to_string(),
                            input_data: vec![1.0f32; 256],
                            batch_size: 1,
                        }
                    } else {
                        // 90% health checks
                        NPUOperation::HealthCheck
                    };

                    bridge.execute_operation(operation).await.unwrap()
                });
                handles.push(handle);
            }

            let results: Vec<OperationResult> = futures::future::join_all(handles)
                .await
                .into_iter()
                .map(|r| r.unwrap())
                .collect();

            // Verify all operations succeeded
            let success_count = results.iter().filter(|r| r.success).count();
            assert_eq!(success_count, 1000);

            black_box(results)
        })
    });
}

fn benchmark_latency_percentiles(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    let config = BridgeConfig {
        target_ops_per_sec: 50_000,
        max_latency_us: 100, // Very tight latency requirement
        worker_threads: num_cpus::get(),
        buffer_size: 1024,
        npu_config: NPUConfig {
            device_id: "latency_benchmark_npu".to_string(),
            max_batch_size: 1, // Single operations for latency measurement
            precision: "FP16".to_string(),
            memory_limit_mb: 128,
            enable_caching: true,
        },
        matlab_config: None,
    };

    let bridge = rt.block_on(async {
        let bridge = NPUCoordinationBridge::new(config).await.unwrap();
        bridge.start().await.unwrap();
        bridge
    });

    c.bench_function("latency_measurement_single_op", |b| {
        b.to_async(&rt).iter(|| async {
            let operation = NPUOperation::HealthCheck;
            let result = bridge.execute_operation(operation).await.unwrap();

            // Verify sub-millisecond latency
            assert!(result.execution_time_us < 1000,
                    "Operation took {}us, expected <1000us", result.execution_time_us);

            black_box(result)
        })
    });
}

criterion_group!(
    benches,
    benchmark_bridge_operations,
    benchmark_concurrent_operations,
    benchmark_throughput_sustained,
    benchmark_latency_percentiles
);
criterion_main!(benches);