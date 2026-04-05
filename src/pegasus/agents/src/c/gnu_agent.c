/*
 * GNU AGENT - GAUSSIAN NEURAL ACCELERATOR IMPLEMENTATION
 * Enhanced Communication System Integration with Intel GNA
 * 
 * Ultra-low power neural inference agent for Intel GNA (Gaussian Neural Accelerator)
 * Specializes in continuous AI workloads, anomaly detection, pattern recognition,
 * and always-on inference with minimal power consumption (<0.5W typical)
 * 
 * Version: 7.0.0 Production
 * UUID: g4u55-14n-pr0c-3550r-gna0x7d1e
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <pthread.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <math.h>
#include <signal.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <dlfcn.h>
#include <x86intrin.h>

// Include system headers
#include "agent_protocol.h"
#include "agent_system.h"
#include "compatibility_layer.h"
#include "ai_enhanced_router.h"

// ============================================================================
// CONSTANTS AND CONFIGURATION
// ============================================================================

#define GNU_AGENT_VERSION_MAJOR 7
#define GNU_AGENT_VERSION_MINOR 0
#define GNU_AGENT_VERSION_PATCH 0

// GNA Hardware Specifications
#define GNA_DEVICE_ID "8086:7e4c"
#define GNA_MEMORY_SIZE (4 * 1024 * 1024)  // 4MB SRAM
#define GNA_MAX_FREQUENCY 600               // MHz
#define GNA_MIN_FREQUENCY 200               // MHz
#define GNA_PEAK_TOPS 1                     // 1 TOPS at INT8

// Power Consumption Targets
#define POWER_IDLE_MW 50                    // 0.05W idle
#define POWER_ACTIVE_MW 300                  // 0.3W typical
#define POWER_PEAK_MW 500                    // 0.5W peak

// Performance Targets
#define TARGET_LATENCY_MS 5                 // 5ms per inference
#define TARGET_THROUGHPUT_SPS 100000        // 100K samples/sec
#define MAX_CONCURRENT_STREAMS 10

// Message Protocol
#define GNA_MAGIC 0x474E4130                // 'GNA0'
#define GNA_VERSION 0x0700                   // Version 7.0
#define MESSAGE_QUEUE_SIZE 1024
#define INFERENCE_BATCH_SIZE 32

// Thermal Thresholds (°C)
#define TEMP_OPTIMAL_MAX 45
#define TEMP_NORMAL_MAX 65
#define TEMP_CAUTION_MAX 75
#define TEMP_CRITICAL 85

// ============================================================================
// DATA STRUCTURES
// ============================================================================

// GNA Message Format
typedef struct __attribute__((packed)) {
    uint32_t magic;                         // 'GNA0' (0x474E4130)
    uint16_t version;                       // 0x0700
    uint16_t flags;                         // Status flags
    uint32_t stream_id;                     // Continuous stream identifier
    uint64_t timestamp;                     // Unix epoch nanos
    float anomaly_score;                    // 0.0-1.0 detection score
    uint8_t precision;                      // INT4/INT8/INT16
    uint32_t inference_us;                  // Inference time in microseconds
    
    // Extended fields
    uint16_t power_mw;                      // Current power in milliwatts
    float fps;                              // Inferences per second
    uint32_t latency_us;                    // Microseconds per inference
    float accuracy;                         // Current accuracy metric
    
    // Capabilities
    uint8_t models_loaded;                  // Number of concurrent models
    uint8_t streams_active;                 // Active inference streams
    uint32_t memory_used_kb;                // SRAM usage in KB
    
    // Payload
    uint32_t payload_size;
    uint8_t payload[0];                     // Variable size payload
} gna_message_t;

// GNA Message Flags
#define GNA_FLAG_STREAM_ACTIVE    (1 << 0)
#define GNA_FLAG_ANOMALY_DETECTED (1 << 1)
#define GNA_FLAG_LOW_POWER_MODE   (1 << 2)
#define GNA_FLAG_CONTINUOUS_MODE  (1 << 3)
#define GNA_FLAG_PATTERN_MATCH    (1 << 4)
#define GNA_FLAG_VOICE_DETECTED   (1 << 5)
#define GNA_FLAG_BUFFER_OVERFLOW  (1 << 6)
#define GNA_FLAG_PRECISION_REDUCED (1 << 7)

// Precision Modes
typedef enum {
    GNA_PRECISION_INT4 = 4,
    GNA_PRECISION_INT8 = 8,
    GNA_PRECISION_INT16 = 16
} gna_precision_t;

// Power Modes
typedef enum {
    GNA_POWER_ULTRA_LOW = 0,    // 0.1W - Wake word detection
    GNA_POWER_BALANCED = 1,     // 0.3W - Normal operation
    GNA_POWER_MAXIMUM = 2,      // 0.5W - Critical inference
    GNA_POWER_HYBRID = 3        // Variable - GNA + NPU
} gna_power_mode_t;

// Execution Profile
typedef struct {
    gna_power_mode_t power_mode;
    gna_precision_t precision;
    uint32_t frequency_mhz;
    uint32_t power_budget_mw;
    bool continuous_mode;
    bool anomaly_detection;
    bool voice_activity;
} gna_execution_profile_t;

// Model Descriptor
typedef struct {
    char name[128];
    char path[256];
    uint32_t size_bytes;
    gna_precision_t precision;
    uint32_t input_size;
    uint32_t output_size;
    float accuracy_baseline;
    
    void* model_handle;          // OpenVINO model handle
    void* compiled_model;        // Compiled for GNA
    void* infer_request;         // Inference request
    
    _Atomic uint64_t inference_count;
    _Atomic uint64_t total_latency_us;
    _Atomic uint32_t anomalies_detected;
} gna_model_t;

// Stream Context
typedef struct {
    uint32_t stream_id;
    char source[64];             // Audio device, sensor, etc.
    bool active;
    bool continuous;
    
    // Ring buffer for streaming data
    uint8_t* buffer;
    size_t buffer_size;
    _Atomic size_t write_pos;
    _Atomic size_t read_pos;
    
    // Stream statistics
    _Atomic uint64_t samples_processed;
    _Atomic uint64_t anomalies_found;
    _Atomic float avg_confidence;
    
    pthread_t processing_thread;
    pthread_mutex_t stream_lock;
} gna_stream_t;

// OpenVINO Integration
typedef struct {
    void* core;                  // OpenVINO Core object
    void* gna_plugin;           // GNA plugin handle
    bool hardware_mode;         // HW vs SW emulation
    
    // Configuration
    char config[512];           // JSON config string
    
    // Function pointers (dynamically loaded)
    void* (*ov_core_create)(void);
    void (*ov_core_free)(void*);
    void* (*ov_core_read_model)(void*, const char*, const char*);
    void* (*ov_core_compile_model)(void*, void*, const char*, void*);
    void* (*ov_compiled_model_create_infer_request)(void*);
    int (*ov_infer_request_infer)(void*);
    void* (*ov_infer_request_get_output_tensor)(void*, size_t);
    int (*ov_infer_request_set_input_tensor)(void*, size_t, void*);
} openvino_context_t;

// Performance Metrics
typedef struct {
    _Atomic uint64_t total_inferences;
    _Atomic uint64_t successful_inferences;
    _Atomic uint64_t failed_inferences;
    
    _Atomic uint64_t total_latency_us;
    _Atomic uint64_t min_latency_us;
    _Atomic uint64_t max_latency_us;
    
    _Atomic uint32_t current_power_mw;
    _Atomic uint32_t peak_power_mw;
    _Atomic uint64_t total_energy_mj;
    
    _Atomic uint32_t current_temp_c;
    _Atomic uint32_t peak_temp_c;
    
    _Atomic uint64_t anomalies_detected;
    _Atomic uint64_t patterns_matched;
    _Atomic uint64_t voice_activations;
} gna_metrics_t;

// Main GNU Agent Structure
typedef struct {
    // Basic agent fields
    ufp_context_t* comm_context;
    char name[64];
    uint32_t agent_id;
    agent_state_t state;
    
    // GNA specific
    char uuid[37];                          // Agent UUID
    gna_execution_profile_t profile;        // Current execution profile
    
    // Hardware access
    int gna_fd;                            // GNA device file descriptor
    void* gna_mmap;                        // Memory mapped region
    size_t gna_mmap_size;
    
    // OpenVINO integration
    openvino_context_t* openvino;
    
    // Models
    gna_model_t models[16];                // Loaded models
    uint32_t model_count;
    
    // Streams
    gna_stream_t streams[MAX_CONCURRENT_STREAMS];
    uint32_t stream_count;
    
    // Performance metrics
    gna_metrics_t metrics;
    
    // Message queue
    gna_message_t* message_queue;
    size_t queue_size;
    _Atomic size_t queue_head;
    _Atomic size_t queue_tail;
    
    // AI Router integration
    ai_routing_decision_t (*route_message)(const enhanced_msg_header_t*, const void*);
    
    // Thread management
    pthread_t monitor_thread;
    pthread_t inference_thread;
    pthread_t power_thread;
    
    // Control
    volatile bool running;
    pthread_mutex_t agent_lock;
    pthread_cond_t work_available;
} gnu_agent_t;

// Global agent instance
static gnu_agent_t* g_gnu_agent = NULL;

// ============================================================================
// HARDWARE DETECTION AND INITIALIZATION
// ============================================================================

static bool detect_gna_hardware(void) {
    FILE* fp = popen("lspci | grep -i '7e4c'", "r");
    if (!fp) return false;
    
    char buffer[256];
    bool found = false;
    
    if (fgets(buffer, sizeof(buffer), fp) != NULL) {
        if (strstr(buffer, "7e4c") || strstr(buffer, "Gaussian") || strstr(buffer, "GNA")) {
            found = true;
            printf("GNU Agent: Intel GNA device detected: %s", buffer);
        }
    }
    
    pclose(fp);
    return found;
}

static int init_gna_device(gnu_agent_t* agent) {
    // Try to open GNA device
    agent->gna_fd = open("/dev/gna0", O_RDWR);
    if (agent->gna_fd < 0) {
        // Try alternative paths
        agent->gna_fd = open("/dev/gna", O_RDWR);
        if (agent->gna_fd < 0) {
            printf("GNU Agent: Warning - GNA device not accessible, using software emulation\n");
            return -1;
        }
    }
    
    // Memory map the GNA SRAM
    agent->gna_mmap_size = GNA_MEMORY_SIZE;
    agent->gna_mmap = mmap(NULL, agent->gna_mmap_size,
                          PROT_READ | PROT_WRITE,
                          MAP_SHARED, agent->gna_fd, 0);
    
    if (agent->gna_mmap == MAP_FAILED) {
        printf("GNU Agent: Failed to map GNA memory\n");
        close(agent->gna_fd);
        agent->gna_fd = -1;
        return -1;
    }
    
    printf("GNU Agent: GNA device initialized (4MB SRAM mapped)\n");
    return 0;
}

// ============================================================================
// OPENVINO INTEGRATION
// ============================================================================

static int init_openvino(gnu_agent_t* agent) {
    agent->openvino = calloc(1, sizeof(openvino_context_t));
    if (!agent->openvino) return -ENOMEM;
    
    // Try to load OpenVINO library
    void* ov_lib = dlopen("libopenvino_c.so", RTLD_LAZY);
    if (!ov_lib) {
        printf("GNU Agent: OpenVINO not found, GNA inference disabled\n");
        free(agent->openvino);
        agent->openvino = NULL;
        return -1;
    }
    
    // Load function pointers
    openvino_context_t* ov = agent->openvino;
    ov->ov_core_create = dlsym(ov_lib, "ov_core_create");
    ov->ov_core_free = dlsym(ov_lib, "ov_core_free");
    ov->ov_core_read_model = dlsym(ov_lib, "ov_core_read_model_from_file");
    ov->ov_core_compile_model = dlsym(ov_lib, "ov_core_compile_model");
    ov->ov_compiled_model_create_infer_request = dlsym(ov_lib, "ov_compiled_model_create_infer_request");
    ov->ov_infer_request_infer = dlsym(ov_lib, "ov_infer_request_infer");
    ov->ov_infer_request_get_output_tensor = dlsym(ov_lib, "ov_infer_request_get_output_tensor");
    ov->ov_infer_request_set_input_tensor = dlsym(ov_lib, "ov_infer_request_set_input_tensor");
    
    // Create OpenVINO Core
    ov->core = ov->ov_core_create();
    if (!ov->core) {
        printf("GNU Agent: Failed to create OpenVINO Core\n");
        dlclose(ov_lib);
        free(agent->openvino);
        agent->openvino = NULL;
        return -1;
    }
    
    // Check if GNA device is available
    ov->hardware_mode = (agent->gna_fd >= 0);
    
    // Configure GNA plugin
    snprintf(ov->config, sizeof(ov->config),
            "{"
            "\"GNA_DEVICE_MODE\": \"%s\","
            "\"GNA_PRECISION\": \"I8\","
            "\"GNA_PERFORMANCE_HINT\": \"LATENCY\","
            "\"GNA_PWL_MAX_ERROR_PERCENT\": \"1.0\""
            "}",
            ov->hardware_mode ? "GNA_HW" : "GNA_SW_FP32");
    
    printf("GNU Agent: OpenVINO initialized (GNA mode: %s)\n",
           ov->hardware_mode ? "Hardware" : "Software");
    
    return 0;
}

// ============================================================================
// MODEL MANAGEMENT
// ============================================================================

static int load_gna_model(gnu_agent_t* agent, const char* model_path, const char* model_name) {
    if (!agent->openvino) {
        printf("GNU Agent: OpenVINO not available, cannot load model\n");
        return -1;
    }
    
    if (agent->model_count >= 16) {
        printf("GNU Agent: Maximum models already loaded\n");
        return -1;
    }
    
    gna_model_t* model = &agent->models[agent->model_count];
    memset(model, 0, sizeof(gna_model_t));
    
    // Set model properties
    strncpy(model->name, model_name, sizeof(model->name) - 1);
    strncpy(model->path, model_path, sizeof(model->path) - 1);
    
    // Get file size
    struct stat st;
    if (stat(model_path, &st) == 0) {
        model->size_bytes = st.st_size;
        
        // Check if model fits in GNA memory
        if (model->size_bytes > GNA_MEMORY_SIZE / 2) {
            printf("GNU Agent: Model too large for GNA (%u bytes > 2MB limit)\n", 
                   model->size_bytes);
            return -1;
        }
    }
    
    // Load model with OpenVINO
    openvino_context_t* ov = agent->openvino;
    
    model->model_handle = ov->ov_core_read_model(ov->core, model_path, NULL);
    if (!model->model_handle) {
        printf("GNU Agent: Failed to read model: %s\n", model_path);
        return -1;
    }
    
    // Compile model for GNA
    model->compiled_model = ov->ov_core_compile_model(ov->core, 
                                                      model->model_handle,
                                                      "GNA", 
                                                      ov->config);
    if (!model->compiled_model) {
        printf("GNU Agent: Failed to compile model for GNA\n");
        return -1;
    }
    
    // Create inference request
    model->infer_request = ov->ov_compiled_model_create_infer_request(model->compiled_model);
    if (!model->infer_request) {
        printf("GNU Agent: Failed to create inference request\n");
        return -1;
    }
    
    // Set default precision
    model->precision = GNA_PRECISION_INT8;
    model->accuracy_baseline = 0.95f;
    
    // Initialize counters
    atomic_store(&model->inference_count, 0);
    atomic_store(&model->total_latency_us, 0);
    atomic_store(&model->anomalies_detected, 0);
    
    agent->model_count++;
    
    printf("GNU Agent: Model loaded: %s (%.1f KB, INT%d)\n",
           model_name, model->size_bytes / 1024.0, model->precision);
    
    return 0;
}

// ============================================================================
// INFERENCE ENGINE
// ============================================================================

static int perform_inference(gnu_agent_t* agent, gna_model_t* model,
                           const void* input_data, size_t input_size,
                           void* output_data, size_t output_size) {
    if (!model->infer_request) return -1;
    
    uint64_t start_time = __builtin_ia32_rdtsc();
    
    // Set input tensor
    openvino_context_t* ov = agent->openvino;
    ov->ov_infer_request_set_input_tensor(model->infer_request, 0, (void*)input_data);
    
    // Run inference
    int ret = ov->ov_infer_request_infer(model->infer_request);
    if (ret != 0) {
        atomic_fetch_add(&agent->metrics.failed_inferences, 1);
        return -1;
    }
    
    // Get output tensor
    void* output_tensor = ov->ov_infer_request_get_output_tensor(model->infer_request, 0);
    if (output_tensor && output_data) {
        memcpy(output_data, output_tensor, output_size);
    }
    
    // Update metrics
    uint64_t end_time = __builtin_ia32_rdtsc();
    uint64_t latency_cycles = end_time - start_time;
    uint64_t latency_us = latency_cycles * 1000 / 3400; // Approximate conversion
    
    atomic_fetch_add(&model->inference_count, 1);
    atomic_fetch_add(&model->total_latency_us, latency_us);
    atomic_fetch_add(&agent->metrics.total_inferences, 1);
    atomic_fetch_add(&agent->metrics.successful_inferences, 1);
    atomic_fetch_add(&agent->metrics.total_latency_us, latency_us);
    
    // Update min/max latency
    uint64_t current_min = atomic_load(&agent->metrics.min_latency_us);
    while (latency_us < current_min) {
        if (atomic_compare_exchange_weak(&agent->metrics.min_latency_us,
                                        &current_min, latency_us)) {
            break;
        }
    }
    
    uint64_t current_max = atomic_load(&agent->metrics.max_latency_us);
    while (latency_us > current_max) {
        if (atomic_compare_exchange_weak(&agent->metrics.max_latency_us,
                                        &current_max, latency_us)) {
            break;
        }
    }
    
    return 0;
}

// ============================================================================
// CONTINUOUS STREAM PROCESSING
// ============================================================================

static void* stream_processor_thread(void* arg) {
    gna_stream_t* stream = (gna_stream_t*)arg;
    gnu_agent_t* agent = g_gnu_agent;
    
    if (!agent || !stream) return NULL;
    
    // Use first loaded model for stream processing
    if (agent->model_count == 0) {
        printf("GNU Agent: No models loaded for stream processing\n");
        return NULL;
    }
    
    gna_model_t* model = &agent->models[0];
    
    // Allocate buffers
    const size_t chunk_size = 1024;  // Process 1KB chunks
    uint8_t* input_buffer = aligned_alloc(64, chunk_size);
    float output_buffer[32];          // Anomaly scores
    
    if (!input_buffer) return NULL;
    
    printf("GNU Agent: Stream processor started for stream %u\n", stream->stream_id);
    
    while (stream->active && agent->running) {
        // Wait for data in ring buffer
        size_t write_pos = atomic_load(&stream->write_pos);
        size_t read_pos = atomic_load(&stream->read_pos);
        
        if (write_pos == read_pos) {
            usleep(1000); // 1ms sleep if no data
            continue;
        }
        
        // Calculate available data
        size_t available = (write_pos - read_pos) % stream->buffer_size;
        if (available < chunk_size) {
            usleep(100); // Wait for more data
            continue;
        }
        
        // Copy data from ring buffer
        pthread_mutex_lock(&stream->stream_lock);
        
        for (size_t i = 0; i < chunk_size; i++) {
            input_buffer[i] = stream->buffer[(read_pos + i) % stream->buffer_size];
        }
        
        atomic_store(&stream->read_pos, (read_pos + chunk_size) % stream->buffer_size);
        
        pthread_mutex_unlock(&stream->stream_lock);
        
        // Perform inference
        int ret = perform_inference(agent, model, 
                                   input_buffer, chunk_size,
                                   output_buffer, sizeof(output_buffer));
        
        if (ret == 0) {
            // Check for anomalies
            float max_score = 0.0f;
            for (int i = 0; i < 32; i++) {
                if (output_buffer[i] > max_score) {
                    max_score = output_buffer[i];
                }
            }
            
            if (max_score > 0.8f) {
                atomic_fetch_add(&stream->anomalies_found, 1);
                atomic_fetch_add(&agent->metrics.anomalies_detected, 1);
                
                // Send anomaly notification
                gna_message_t* msg = calloc(1, sizeof(gna_message_t));
                if (msg) {
                    msg->magic = GNA_MAGIC;
                    msg->version = GNA_VERSION;
                    msg->flags = GNA_FLAG_ANOMALY_DETECTED | GNA_FLAG_STREAM_ACTIVE;
                    msg->stream_id = stream->stream_id;
                    msg->timestamp = time(NULL) * 1000000000ULL;
                    msg->anomaly_score = max_score;
                    msg->precision = model->precision;
                    
                    // Queue message
                    size_t tail = atomic_load(&agent->queue_tail);
                    size_t next_tail = (tail + 1) % agent->queue_size;
                    
                    if (next_tail != atomic_load(&agent->queue_head)) {
                        memcpy(&agent->message_queue[tail], msg, sizeof(gna_message_t));
                        atomic_store(&agent->queue_tail, next_tail);
                        pthread_cond_signal(&agent->work_available);
                    }
                    
                    free(msg);
                }
            }
            
            atomic_fetch_add(&stream->samples_processed, 1);
        }
    }
    
    free(input_buffer);
    
    printf("GNU Agent: Stream processor stopped for stream %u\n", stream->stream_id);
    return NULL;
}

static int start_continuous_stream(gnu_agent_t* agent, const char* source, uint32_t stream_id) {
    if (agent->stream_count >= MAX_CONCURRENT_STREAMS) {
        printf("GNU Agent: Maximum streams already active\n");
        return -1;
    }
    
    gna_stream_t* stream = &agent->streams[agent->stream_count];
    memset(stream, 0, sizeof(gna_stream_t));
    
    stream->stream_id = stream_id;
    strncpy(stream->source, source, sizeof(stream->source) - 1);
    stream->active = true;
    stream->continuous = true;
    
    // Allocate ring buffer (1MB)
    stream->buffer_size = 1024 * 1024;
    stream->buffer = aligned_alloc(4096, stream->buffer_size);
    if (!stream->buffer) {
        return -ENOMEM;
    }
    
    atomic_store(&stream->write_pos, 0);
    atomic_store(&stream->read_pos, 0);
    atomic_store(&stream->samples_processed, 0);
    atomic_store(&stream->anomalies_found, 0);
    
    pthread_mutex_init(&stream->stream_lock, NULL);
    
    // Start processing thread
    pthread_create(&stream->processing_thread, NULL, stream_processor_thread, stream);
    
    agent->stream_count++;
    
    printf("GNU Agent: Started continuous stream %u from %s\n", stream_id, source);
    return 0;
}

// ============================================================================
// POWER MANAGEMENT
// ============================================================================

static void set_power_profile(gnu_agent_t* agent, gna_power_mode_t mode) {
    gna_execution_profile_t* profile = &agent->profile;
    
    switch (mode) {
        case GNA_POWER_ULTRA_LOW:
            profile->power_mode = GNA_POWER_ULTRA_LOW;
            profile->precision = GNA_PRECISION_INT8;
            profile->frequency_mhz = 200;
            profile->power_budget_mw = 100;
            printf("GNU Agent: Ultra-low power mode (0.1W)\n");
            break;
            
        case GNA_POWER_BALANCED:
            profile->power_mode = GNA_POWER_BALANCED;
            profile->precision = GNA_PRECISION_INT8;
            profile->frequency_mhz = 400;
            profile->power_budget_mw = 300;
            printf("GNU Agent: Balanced power mode (0.3W)\n");
            break;
            
        case GNA_POWER_MAXIMUM:
            profile->power_mode = GNA_POWER_MAXIMUM;
            profile->precision = GNA_PRECISION_INT16;
            profile->frequency_mhz = 600;
            profile->power_budget_mw = 500;
            printf("GNU Agent: Maximum performance mode (0.5W)\n");
            break;
            
        case GNA_POWER_HYBRID:
            profile->power_mode = GNA_POWER_HYBRID;
            profile->precision = GNA_PRECISION_INT8;
            profile->frequency_mhz = 400;
            profile->power_budget_mw = 400;
            printf("GNU Agent: Hybrid mode (GNA + NPU)\n");
            break;
    }
    
    atomic_store(&agent->metrics.current_power_mw, profile->power_budget_mw);
}

static void* power_monitor_thread(void* arg) {
    gnu_agent_t* agent = (gnu_agent_t*)arg;
    
    while (agent->running) {
        // Read temperature sensor
        FILE* temp_file = fopen("/sys/class/thermal/thermal_zone0/temp", "r");
        if (temp_file) {
            int temp_millidegrees;
            if (fscanf(temp_file, "%d", &temp_millidegrees) == 1) {
                uint32_t temp_c = temp_millidegrees / 1000;
                atomic_store(&agent->metrics.current_temp_c, temp_c);
                
                // Adjust power mode based on temperature
                if (temp_c > TEMP_CRITICAL) {
                    printf("GNU Agent: Critical temperature! Shutting down\n");
                    agent->running = false;
                } else if (temp_c > TEMP_CAUTION_MAX) {
                    set_power_profile(agent, GNA_POWER_ULTRA_LOW);
                } else if (temp_c > TEMP_NORMAL_MAX) {
                    set_power_profile(agent, GNA_POWER_BALANCED);
                }
            }
            fclose(temp_file);
        }
        
        // Estimate power consumption based on inference rate
        uint64_t inferences = atomic_load(&agent->metrics.total_inferences);
        static uint64_t last_inferences = 0;
        uint64_t delta_inferences = inferences - last_inferences;
        last_inferences = inferences;
        
        // Simple power model: base + dynamic based on inference rate
        uint32_t estimated_power = POWER_IDLE_MW + 
                                  (delta_inferences * POWER_ACTIVE_MW / TARGET_THROUGHPUT_SPS);
        
        if (estimated_power > POWER_PEAK_MW) {
            estimated_power = POWER_PEAK_MW;
        }
        
        atomic_store(&agent->metrics.current_power_mw, estimated_power);
        
        // Update total energy consumption
        atomic_fetch_add(&agent->metrics.total_energy_mj, estimated_power);
        
        sleep(1); // Check every second
    }
    
    return NULL;
}

// ============================================================================
// MESSAGE PROCESSING
// ============================================================================

static int gnu_process_message(gnu_agent_t* agent, ufp_message_t* msg) {
    printf("GNU Agent: Received message from %s (type: %d)\n", 
           msg->source, msg->msg_type);
    
    // Check message type
    if (msg->msg_type == UFP_MSG_MODEL_LOAD) {
        // Load a new model
        if (msg->payload && msg->payload_size > 0) {
            char* model_path = (char*)msg->payload;
            return load_gna_model(agent, model_path, "user_model");
        }
    } else if (msg->msg_type == UFP_MSG_STREAM_START) {
        // Start a new stream
        if (msg->payload && msg->payload_size > 0) {
            char* source = (char*)msg->payload;
            uint32_t stream_id = agent->stream_count + 1;
            return start_continuous_stream(agent, source, stream_id);
        }
    } else if (msg->msg_type == UFP_MSG_INFERENCE_REQUEST) {
        // Single inference request
        if (msg->payload && msg->payload_size > 0 && agent->model_count > 0) {
            float output[32];
            int ret = perform_inference(agent, &agent->models[0],
                                       msg->payload, msg->payload_size,
                                       output, sizeof(output));
            
            if (ret == 0) {
                // Send response
                ufp_message_t* response = ufp_message_create();
                strcpy(response->source, agent->name);
                strcpy(response->targets[0], msg->source);
                response->target_count = 1;
                response->msg_type = UFP_MSG_INFERENCE_RESPONSE;
                response->payload = output;
                response->payload_size = sizeof(output);
                
                ufp_send(agent->comm_context, response);
                ufp_message_destroy(response);
            }
        }
    }
    
    // Send acknowledgment
    ufp_message_t* ack = ufp_message_create();
    strcpy(ack->source, agent->name);
    strcpy(ack->targets[0], msg->source);
    ack->target_count = 1;
    ack->msg_type = UFP_MSG_ACK;
    
    ufp_send(agent->comm_context, ack);
    ufp_message_destroy(ack);
    
    return 0;
}

// ============================================================================
// MAIN AGENT FUNCTIONS
// ============================================================================

int gnu_init(gnu_agent_t* agent) {
    if (!agent) return -EINVAL;
    
    // Set agent properties
    strcpy(agent->name, "gnu");
    strcpy(agent->uuid, "g4u55-14n-pr0c-3550r-gna0x7d1e");
    agent->state = AGENT_STATE_INITIALIZING;
    
    // Initialize communication context
    agent->comm_context = ufp_create_context("gnu");
    if (!agent->comm_context) {
        printf("GNU Agent: Failed to create communication context\n");
        return -1;
    }
    
    // Detect GNA hardware
    if (!detect_gna_hardware()) {
        printf("GNU Agent: Warning - GNA hardware not detected, using emulation\n");
    }
    
    // Initialize GNA device
    if (init_gna_device(agent) != 0) {
        printf("GNU Agent: GNA device initialization failed, continuing with software\n");
    }
    
    // Initialize OpenVINO
    if (init_openvino(agent) != 0) {
        printf("GNU Agent: OpenVINO initialization failed\n");
        // Continue without OpenVINO - limited functionality
    }
    
    // Initialize message queue
    agent->queue_size = MESSAGE_QUEUE_SIZE;
    agent->message_queue = calloc(agent->queue_size, sizeof(gna_message_t));
    if (!agent->message_queue) {
        return -ENOMEM;
    }
    
    atomic_store(&agent->queue_head, 0);
    atomic_store(&agent->queue_tail, 0);
    
    // Initialize metrics
    atomic_store(&agent->metrics.total_inferences, 0);
    atomic_store(&agent->metrics.successful_inferences, 0);
    atomic_store(&agent->metrics.failed_inferences, 0);
    atomic_store(&agent->metrics.min_latency_us, UINT64_MAX);
    atomic_store(&agent->metrics.max_latency_us, 0);
    atomic_store(&agent->metrics.current_power_mw, POWER_IDLE_MW);
    atomic_store(&agent->metrics.current_temp_c, 25);
    
    // Set initial power profile
    set_power_profile(agent, GNA_POWER_BALANCED);
    
    // Initialize synchronization
    pthread_mutex_init(&agent->agent_lock, NULL);
    pthread_cond_init(&agent->work_available, NULL);
    
    // Register with discovery service
    agent_register("gnu", AGENT_TYPE_GNU, NULL, 0);
    
    // Register with AI router
    if (ai_is_initialized()) {
        printf("GNU Agent: Registering with AI router\n");
        agent->route_message = ai_get_routing_decision;
    }
    
    agent->running = true;
    agent->state = AGENT_STATE_ACTIVE;
    
    // Start monitoring threads
    pthread_create(&agent->power_thread, NULL, power_monitor_thread, agent);
    
    // Load default models if available
    if (access("models/voice_detector.xml", F_OK) == 0) {
        load_gna_model(agent, "models/voice_detector.xml", "voice_detector");
    }
    if (access("models/anomaly_detector.xml", F_OK) == 0) {
        load_gna_model(agent, "models/anomaly_detector.xml", "anomaly_detector");
    }
    
    printf("GNU Agent: Initialization complete (UUID: %s)\n", agent->uuid);
    return 0;
}

void gnu_run(gnu_agent_t* agent) {
    if (!agent) return;
    
    ufp_message_t msg;
    
    printf("GNU Agent: Entering main loop\n");
    
    while (agent->state == AGENT_STATE_ACTIVE && agent->running) {
        // Receive messages
        if (ufp_receive(agent->comm_context, &msg, 100) == UFP_SUCCESS) {
            gnu_process_message(agent, &msg);
        }
        
        // Check for queued GNA messages to send
        size_t head = atomic_load(&agent->queue_head);
        size_t tail = atomic_load(&agent->queue_tail);
        
        if (head != tail) {
            gna_message_t* gna_msg = &agent->message_queue[head];
            
            // Convert to UFP message and send
            ufp_message_t* out_msg = ufp_message_create();
            strcpy(out_msg->source, agent->name);
            out_msg->target_count = 1;
            strcpy(out_msg->targets[0], "broadcast");
            out_msg->msg_type = UFP_MSG_DATA;
            out_msg->payload = gna_msg;
            out_msg->payload_size = sizeof(gna_message_t) + gna_msg->payload_size;
            
            ufp_send(agent->comm_context, out_msg);
            ufp_message_destroy(out_msg);
            
            atomic_store(&agent->queue_head, (head + 1) % agent->queue_size);
        }
        
        // Small delay to prevent CPU spinning
        usleep(1000);
    }
    
    printf("GNU Agent: Exiting main loop\n");
}

void gnu_cleanup(gnu_agent_t* agent) {
    if (!agent) return;
    
    printf("GNU Agent: Shutting down\n");
    
    agent->running = false;
    agent->state = AGENT_STATE_TERMINATED;
    
    // Stop all streams
    for (uint32_t i = 0; i < agent->stream_count; i++) {
        gna_stream_t* stream = &agent->streams[i];
        stream->active = false;
        pthread_join(stream->processing_thread, NULL);
        free(stream->buffer);
        pthread_mutex_destroy(&stream->stream_lock);
    }
    
    // Wait for threads
    pthread_join(agent->power_thread, NULL);
    
    // Cleanup OpenVINO
    if (agent->openvino) {
        if (agent->openvino->core) {
            agent->openvino->ov_core_free(agent->openvino->core);
        }
        free(agent->openvino);
    }
    
    // Cleanup GNA device
    if (agent->gna_mmap && agent->gna_mmap != MAP_FAILED) {
        munmap(agent->gna_mmap, agent->gna_mmap_size);
    }
    if (agent->gna_fd >= 0) {
        close(agent->gna_fd);
    }
    
    // Cleanup communication
    if (agent->comm_context) {
        ufp_destroy_context(agent->comm_context);
    }
    
    // Cleanup message queue
    free(agent->message_queue);
    
    // Cleanup synchronization
    pthread_mutex_destroy(&agent->agent_lock);
    pthread_cond_destroy(&agent->work_available);
    
    // Print final statistics
    printf("\n=== GNU Agent Final Statistics ===\n");
    printf("Total inferences: %lu\n", atomic_load(&agent->metrics.total_inferences));
    printf("Successful: %lu\n", atomic_load(&agent->metrics.successful_inferences));
    printf("Failed: %lu\n", atomic_load(&agent->metrics.failed_inferences));
    
    uint64_t total_inferences = atomic_load(&agent->metrics.total_inferences);
    if (total_inferences > 0) {
        uint64_t avg_latency = atomic_load(&agent->metrics.total_latency_us) / total_inferences;
        printf("Average latency: %lu μs\n", avg_latency);
        printf("Min latency: %lu μs\n", atomic_load(&agent->metrics.min_latency_us));
        printf("Max latency: %lu μs\n", atomic_load(&agent->metrics.max_latency_us));
    }
    
    printf("Anomalies detected: %lu\n", atomic_load(&agent->metrics.anomalies_detected));
    printf("Total energy: %lu mJ\n", atomic_load(&agent->metrics.total_energy_mj));
    printf("Peak power: %u mW\n", atomic_load(&agent->metrics.peak_power_mw));
    printf("Peak temperature: %u°C\n", atomic_load(&agent->metrics.peak_temp_c));
    printf("\n");
    
    printf("GNU Agent: Shutdown complete\n");
}

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

int main(int argc, char* argv[]) {
    printf("================================================================================\n");
    printf("        GNU AGENT - GAUSSIAN NEURAL ACCELERATOR v%d.%d.%d                      \n",
           GNU_AGENT_VERSION_MAJOR, GNU_AGENT_VERSION_MINOR, GNU_AGENT_VERSION_PATCH);
    printf("================================================================================\n");
    
    // Allocate agent
    gnu_agent_t* agent = calloc(1, sizeof(gnu_agent_t));
    if (!agent) {
        fprintf(stderr, "Failed to allocate agent\n");
        return 1;
    }
    
    // Set global instance
    g_gnu_agent = agent;
    
    // Parse command line arguments
    gna_power_mode_t power_mode = GNA_POWER_BALANCED;
    bool continuous_mode = false;
    char* model_path = NULL;
    char* stream_source = NULL;
    
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--ultra-low-power") == 0) {
            power_mode = GNA_POWER_ULTRA_LOW;
        } else if (strcmp(argv[i], "--maximum-performance") == 0) {
            power_mode = GNA_POWER_MAXIMUM;
        } else if (strcmp(argv[i], "--hybrid") == 0) {
            power_mode = GNA_POWER_HYBRID;
        } else if (strcmp(argv[i], "--continuous") == 0) {
            continuous_mode = true;
        } else if (strcmp(argv[i], "--model") == 0 && i + 1 < argc) {
            model_path = argv[++i];
        } else if (strcmp(argv[i], "--stream") == 0 && i + 1 < argc) {
            stream_source = argv[++i];
        } else if (strcmp(argv[i], "--help") == 0) {
            printf("Usage: %s [options]\n", argv[0]);
            printf("Options:\n");
            printf("  --ultra-low-power     Run in ultra-low power mode (0.1W)\n");
            printf("  --maximum-performance Run at maximum performance (0.5W)\n");
            printf("  --hybrid             Use hybrid GNA+NPU mode\n");
            printf("  --continuous         Enable continuous inference mode\n");
            printf("  --model <path>       Load model from path\n");
            printf("  --stream <source>    Start stream from source\n");
            printf("  --help              Show this help message\n");
            free(agent);
            return 0;
        }
    }
    
    // Initialize agent
    if (gnu_init(agent) != 0) {
        fprintf(stderr, "Failed to initialize GNU agent\n");
        free(agent);
        return 1;
    }
    
    // Set power mode
    set_power_profile(agent, power_mode);
    
    // Load user model if specified
    if (model_path) {
        if (load_gna_model(agent, model_path, "user_model") != 0) {
            fprintf(stderr, "Failed to load model: %s\n", model_path);
        }
    }
    
    // Start stream if specified
    if (stream_source) {
        if (start_continuous_stream(agent, stream_source, 1) != 0) {
            fprintf(stderr, "Failed to start stream: %s\n", stream_source);
        }
    }
    
    // Setup signal handler for clean shutdown
    signal(SIGINT, [](int) { 
        if (g_gnu_agent) g_gnu_agent->running = false; 
    });
    signal(SIGTERM, [](int) { 
        if (g_gnu_agent) g_gnu_agent->running = false; 
    });
    
    // Run agent
    gnu_run(agent);
    
    // Cleanup
    gnu_cleanup(agent);
    
    free(agent);
    g_gnu_agent = NULL;
    
    return 0;
}