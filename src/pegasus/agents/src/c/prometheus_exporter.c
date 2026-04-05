/*
 * CLAUDE AGENT SYSTEM - COMPREHENSIVE PROMETHEUS METRICS EXPORTER
 * 
 * Production-ready Prometheus exporter for Claude Agent Communication System
 * Exposes all relevant metrics from the ultra-fast binary protocol and agent system
 * 
 * Features:
 * - Agent health and performance metrics
 * - Transport layer statistics
 * - Resource utilization monitoring
 * - Hardware-aware metrics (P-core/E-core)
 * - Real-time anomaly detection scores
 * - Message flow analysis
 * 
 * Author: MONITOR Agent v7.0
 * Version: 1.0.0 Production
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <time.h>
#include <stdint.h>
#include <stdatomic.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <errno.h>
#include <sys/sysinfo.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <dirent.h>
#include <math.h>

// Include transport protocol headers
#include "agent_protocol.h"

#define MAX_METRICS 2000
#define MAX_METRIC_NAME_LEN 256
#define MAX_LABEL_LEN 512
#define METRICS_BUFFER_SIZE (16 * 1024 * 1024)  // 16MB buffer
#define HTTP_PORT 8001
#define UPDATE_INTERVAL_MS 1000  // 1 second update interval
#define MAX_AGENTS 65536
#define MAX_HISTOGRAM_BUCKETS 30

// Metric types
typedef enum {
    METRIC_COUNTER,
    METRIC_GAUGE, 
    METRIC_HISTOGRAM,
    METRIC_SUMMARY
} metric_type_t;

// Histogram bucket
typedef struct {
    double le;
    atomic_uint_fast64_t count;
} histogram_bucket_t;

// Agent information
typedef struct {
    uint16_t agent_id;
    char agent_type[64];
    char agent_name[64];
    uint32_t last_heartbeat;
    atomic_uint_fast64_t messages_sent;
    atomic_uint_fast64_t messages_received;
    atomic_uint_fast64_t errors;
    atomic_uint_fast64_t processing_time_ns;
    atomic_uint_fast64_t queue_depth;
    double health_score;
    double failure_prediction_score;
    int cpu_usage_percent;
    int memory_usage_mb;
    bool is_active;
} agent_info_t;

// Metric structure
typedef struct {
    char name[MAX_METRIC_NAME_LEN];
    char help[512];
    metric_type_t type;
    char labels[MAX_LABEL_LEN];
    
    union {
        atomic_uint_fast64_t counter_value;
        atomic_int_fast64_t gauge_value;
        struct {
            atomic_uint_fast64_t count;
            atomic_uint_fast64_t sum;
            histogram_bucket_t buckets[MAX_HISTOGRAM_BUCKETS];
            int bucket_count;
        } histogram;
        struct {
            atomic_uint_fast64_t count;
            atomic_uint_fast64_t sum;
            double quantiles[5];  // 0.5, 0.9, 0.95, 0.99, 0.999
        } summary;
    } value;
    
    uint64_t last_update;
} metric_t;

// Message flow matrix
typedef struct {
    uint16_t source_agent;
    uint16_t target_agent;
    atomic_uint_fast64_t message_count;
    atomic_uint_fast64_t total_latency_ns;
    char message_type[32];
} message_flow_entry_t;

// Metrics registry
typedef struct {
    metric_t metrics[MAX_METRICS];
    int metric_count;
    pthread_mutex_t mutex;
    char buffer[METRICS_BUFFER_SIZE];
    
    // Agent tracking
    agent_info_t agents[MAX_AGENTS];
    int agent_count;
    
    // Message flow tracking
    message_flow_entry_t message_flows[MAX_AGENTS];
    int flow_count;
    
    // System information
    struct {
        int total_cores;
        int p_cores;
        int e_cores;
        long total_memory_mb;
        double cpu_utilization;
        double memory_utilization;
        double network_utilization;
    } system_info;
} metrics_registry_t;

// Global registry
static metrics_registry_t g_registry = {0};
static pthread_t g_collector_thread;
static pthread_t g_server_thread;
static volatile bool g_running = false;

// Latency buckets (in seconds)
static const double LATENCY_BUCKETS[] = {
    0.000001,   // 1μs
    0.000005,   // 5μs
    0.00001,    // 10μs
    0.000025,   // 25μs
    0.00005,    // 50μs
    0.0001,     // 100μs
    0.00025,    // 250μs
    0.0005,     // 500μs
    0.001,      // 1ms
    0.0025,     // 2.5ms
    0.005,      // 5ms
    0.01,       // 10ms
    0.025,      // 25ms
    0.05,       // 50ms
    0.1,        // 100ms
    0.25,       // 250ms
    0.5,        // 500ms
    1.0,        // 1s
    2.5,        // 2.5s
    5.0,        // 5s
    10.0        // 10s
};

// Size buckets (in bytes)
static const double SIZE_BUCKETS[] = {
    64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536,
    131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216
};

// Function prototypes
static int init_metrics_registry(void);
static int register_metric(const char* name, const char* help, metric_type_t type, const char* labels);
static void increment_counter(const char* name, const char* labels, uint64_t value);
static void set_gauge(const char* name, const char* labels, int64_t value);
static void observe_histogram(const char* name, const char* labels, double value);
static int start_http_server(void);
static void* http_server_thread(void* arg);
static void handle_metrics_request(int client_fd);
static int format_metrics_output(char* buffer, size_t buffer_size);
static void* metrics_collector_thread(void* arg);
static void collect_system_metrics(void);
static void collect_agent_metrics(void);
static void collect_transport_metrics(void);
static void collect_hardware_metrics(void);
static uint64_t get_monotonic_time_ns(void);
static double calculate_health_score(agent_info_t* agent);
static double calculate_failure_prediction(agent_info_t* agent);
static void update_agent_info(uint16_t agent_id, const char* agent_type, const char* agent_name);
static void record_message_flow(uint16_t source, uint16_t target, const char* msg_type, uint64_t latency_ns);

// Initialize the metrics registry
static int init_metrics_registry(void) {
    memset(&g_registry, 0, sizeof(g_registry));
    
    if (pthread_mutex_init(&g_registry.mutex, NULL) != 0) {
        fprintf(stderr, "Failed to initialize metrics mutex\n");
        return -1;
    }
    
    // System information
    g_registry.system_info.total_cores = get_nprocs();
    
    struct sysinfo si;
    if (sysinfo(&si) == 0) {
        g_registry.system_info.total_memory_mb = si.totalram * si.mem_unit / (1024 * 1024);
    }
    
    // Register core transport metrics
    register_metric("agent_transport_messages_total", 
                   "Total messages processed by transport layer",
                   METRIC_COUNTER, "direction,msg_type,priority,source_agent,target_agent");
    
    register_metric("agent_transport_bytes_total",
                   "Total bytes processed by transport layer", 
                   METRIC_COUNTER, "direction");
    
    register_metric("agent_transport_latency_seconds",
                   "Message transport latency distribution",
                   METRIC_HISTOGRAM, "msg_type,priority,source_agent,target_agent");
    
    register_metric("agent_transport_message_size_bytes",
                   "Message size distribution",
                   METRIC_HISTOGRAM, "msg_type,priority");
    
    register_metric("agent_transport_throughput_mps",
                   "Current transport throughput in messages per second",
                   METRIC_GAUGE, "");
    
    register_metric("agent_transport_errors_total",
                   "Transport layer errors",
                   METRIC_COUNTER, "error_type,severity,agent_id");
    
    register_metric("agent_transport_active_connections",
                   "Active transport connections",
                   METRIC_GAUGE, "");
    
    register_metric("agent_transport_queue_depth",
                   "Transport queue depth by priority",
                   METRIC_GAUGE, "priority");
    
    // Agent-specific metrics
    register_metric("agent_status",
                   "Agent status (1=active, 0=inactive)",
                   METRIC_GAUGE, "agent_id,agent_type,agent_name");
    
    register_metric("agent_health_score",
                   "Agent health score (0-100)",
                   METRIC_GAUGE, "agent_id,agent_type,agent_name");
    
    register_metric("agent_messages_processed_total",
                   "Total messages processed by agent",
                   METRIC_COUNTER, "agent_id,agent_type,action");
    
    register_metric("agent_processing_time_seconds",
                   "Message processing time distribution",
                   METRIC_HISTOGRAM, "agent_id,agent_type");
    
    register_metric("agent_queue_depth",
                   "Current queue depth for agent",
                   METRIC_GAUGE, "agent_id,agent_type");
    
    register_metric("agent_errors_total",
                   "Total errors by agent",
                   METRIC_COUNTER, "agent_id,agent_type,error_type");
    
    register_metric("agent_resource_usage",
                   "Resource usage by agent",
                   METRIC_GAUGE, "agent_id,agent_type,resource");
    
    // System metrics
    register_metric("system_cpu_utilization_ratio",
                   "System CPU utilization ratio",
                   METRIC_GAUGE, "core_type");
    
    register_metric("system_memory_usage_bytes",
                   "System memory usage",
                   METRIC_GAUGE, "type");
    
    register_metric("system_network_bytes_total",
                   "System network traffic",
                   METRIC_COUNTER, "direction,interface");
    
    register_metric("system_active_agents",
                   "Number of active agents by type",
                   METRIC_GAUGE, "agent_type");
    
    // Hardware-specific metrics
    register_metric("hardware_core_utilization_ratio",
                   "CPU core utilization by type",
                   METRIC_GAUGE, "core_type,core_id");
    
    register_metric("hardware_cache_misses_total",
                   "CPU cache misses",
                   METRIC_COUNTER, "cache_level,core_type");
    
    register_metric("hardware_temperature_celsius",
                   "Hardware temperature",
                   METRIC_GAUGE, "component");
    
    // Message flow metrics
    register_metric("message_flow_matrix",
                   "Message flow between agents",
                   METRIC_COUNTER, "source_agent,target_agent,message_type");
    
    register_metric("message_flow_latency_seconds",
                   "End-to-end message flow latency",
                   METRIC_HISTOGRAM, "source_agent,target_agent,message_type");
    
    // Failure prediction metrics
    register_metric("failure_prediction_score",
                   "Failure prediction score (0-100)",
                   METRIC_GAUGE, "agent_id,agent_type,component");
    
    register_metric("anomaly_detection_score",
                   "Anomaly detection score",
                   METRIC_GAUGE, "agent_id,source,detector_type");
    
    // Capacity planning metrics
    register_metric("capacity_utilization_ratio",
                   "Resource utilization for capacity planning",
                   METRIC_GAUGE, "resource_type,component");
    
    register_metric("capacity_saturation_prediction_seconds",
                   "Predicted time to resource saturation",
                   METRIC_GAUGE, "resource_type");
    
    return 0;
}

// Register a new metric
static int register_metric(const char* name, const char* help, metric_type_t type, const char* labels) {
    pthread_mutex_lock(&g_registry.mutex);
    
    if (g_registry.metric_count >= MAX_METRICS) {
        pthread_mutex_unlock(&g_registry.mutex);
        return -1;
    }
    
    metric_t* metric = &g_registry.metrics[g_registry.metric_count];
    strncpy(metric->name, name, MAX_METRIC_NAME_LEN - 1);
    strncpy(metric->help, help, 511);
    strncpy(metric->labels, labels, MAX_LABEL_LEN - 1);
    metric->type = type;
    metric->last_update = get_monotonic_time_ns();
    
    // Initialize based on type
    if (type == METRIC_HISTOGRAM) {
        const double* buckets;
        int bucket_count;
        
        if (strstr(name, "latency") || strstr(name, "time")) {
            buckets = LATENCY_BUCKETS;
            bucket_count = sizeof(LATENCY_BUCKETS) / sizeof(LATENCY_BUCKETS[0]);
        } else if (strstr(name, "size") || strstr(name, "bytes")) {
            buckets = SIZE_BUCKETS;
            bucket_count = sizeof(SIZE_BUCKETS) / sizeof(SIZE_BUCKETS[0]);
        } else {
            buckets = LATENCY_BUCKETS;
            bucket_count = sizeof(LATENCY_BUCKETS) / sizeof(LATENCY_BUCKETS[0]);
        }
        
        metric->value.histogram.bucket_count = bucket_count;
        for (int i = 0; i < bucket_count; i++) {
            metric->value.histogram.buckets[i].le = buckets[i];
            atomic_init(&metric->value.histogram.buckets[i].count, 0);
        }
        atomic_init(&metric->value.histogram.count, 0);
        atomic_init(&metric->value.histogram.sum, 0);
    } else if (type == METRIC_COUNTER) {
        atomic_init(&metric->value.counter_value, 0);
    } else if (type == METRIC_GAUGE) {
        atomic_init(&metric->value.gauge_value, 0);
    }
    
    g_registry.metric_count++;
    pthread_mutex_unlock(&g_registry.mutex);
    
    return 0;
}

// Increment a counter metric
static void increment_counter(const char* name, const char* labels, uint64_t value) {
    pthread_mutex_lock(&g_registry.mutex);
    
    for (int i = 0; i < g_registry.metric_count; i++) {
        metric_t* metric = &g_registry.metrics[i];
        if (strcmp(metric->name, name) == 0 && metric->type == METRIC_COUNTER) {
            if (strlen(labels) == 0 || strstr(metric->labels, labels)) {
                atomic_fetch_add(&metric->value.counter_value, value);
                metric->last_update = get_monotonic_time_ns();
            }
            break;
        }
    }
    
    pthread_mutex_unlock(&g_registry.mutex);
}

// Set a gauge metric
static void set_gauge(const char* name, const char* labels, int64_t value) {
    pthread_mutex_lock(&g_registry.mutex);
    
    for (int i = 0; i < g_registry.metric_count; i++) {
        metric_t* metric = &g_registry.metrics[i];
        if (strcmp(metric->name, name) == 0 && metric->type == METRIC_GAUGE) {
            if (strlen(labels) == 0 || strstr(metric->labels, labels)) {
                atomic_store(&metric->value.gauge_value, value);
                metric->last_update = get_monotonic_time_ns();
            }
            break;
        }
    }
    
    pthread_mutex_unlock(&g_registry.mutex);
}

// Observe a histogram metric
static void observe_histogram(const char* name, const char* labels, double value) {
    pthread_mutex_lock(&g_registry.mutex);
    
    for (int i = 0; i < g_registry.metric_count; i++) {
        metric_t* metric = &g_registry.metrics[i];
        if (strcmp(metric->name, name) == 0 && metric->type == METRIC_HISTOGRAM) {
            if (strlen(labels) == 0 || strstr(metric->labels, labels)) {
                atomic_fetch_add(&metric->value.histogram.count, 1);
                atomic_fetch_add(&metric->value.histogram.sum, (uint64_t)(value * 1e9));
                
                // Update buckets
                for (int j = 0; j < metric->value.histogram.bucket_count; j++) {
                    if (value <= metric->value.histogram.buckets[j].le) {
                        atomic_fetch_add(&metric->value.histogram.buckets[j].count, 1);
                    }
                }
                metric->last_update = get_monotonic_time_ns();
            }
            break;
        }
    }
    
    pthread_mutex_unlock(&g_registry.mutex);
}

// Start HTTP metrics server
static int start_http_server(void) {
    if (pthread_create(&g_server_thread, NULL, http_server_thread, NULL) != 0) {
        fprintf(stderr, "Failed to create HTTP server thread\n");
        return -1;
    }
    
    pthread_detach(g_server_thread);
    return 0;
}

// HTTP server thread
static void* http_server_thread(void* arg) {
    int server_fd, client_fd;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);
    
    // Create socket
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("socket failed");
        return NULL;
    }
    
    // Set socket options
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt))) {
        perror("setsockopt");
        return NULL;
    }
    
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(HTTP_PORT);
    
    // Bind socket
    if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) {
        perror("bind failed");
        return NULL;
    }
    
    // Listen for connections
    if (listen(server_fd, 10) < 0) {
        perror("listen");
        return NULL;
    }
    
    printf("Prometheus metrics server listening on port %d\n", HTTP_PORT);
    
    while (g_running) {
        if ((client_fd = accept(server_fd, (struct sockaddr*)&address, (socklen_t*)&addrlen)) < 0) {
            if (g_running) {
                perror("accept");
            }
            continue;
        }
        
        handle_metrics_request(client_fd);
        close(client_fd);
    }
    
    close(server_fd);
    return NULL;
}

// Handle HTTP metrics request
static void handle_metrics_request(int client_fd) {
    char buffer[1024];
    int bytes_read = read(client_fd, buffer, sizeof(buffer) - 1);
    
    if (bytes_read > 0) {
        buffer[bytes_read] = '\0';
        
        // Simple HTTP request parsing
        if (strstr(buffer, "GET /metrics") != NULL) {
            char* metrics_output = malloc(METRICS_BUFFER_SIZE);
            if (metrics_output) {
                int content_length = format_metrics_output(metrics_output, METRICS_BUFFER_SIZE);
                
                // Send HTTP response
                char response[512];
                snprintf(response, sizeof(response),
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/plain; version=0.0.4\r\n"
                    "Content-Length: %d\r\n"
                    "Connection: close\r\n\r\n", content_length);
                
                write(client_fd, response, strlen(response));
                write(client_fd, metrics_output, content_length);
                
                free(metrics_output);
            }
        } else if (strstr(buffer, "GET /health") != NULL) {
            const char* health_response = 
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 2\r\n"
                "Connection: close\r\n\r\nOK";
            write(client_fd, health_response, strlen(health_response));
        }
    }
}

// Format metrics for Prometheus output
static int format_metrics_output(char* buffer, size_t buffer_size) {
    int offset = 0;
    
    pthread_mutex_lock(&g_registry.mutex);
    
    for (int i = 0; i < g_registry.metric_count; i++) {
        metric_t* metric = &g_registry.metrics[i];
        
        // Skip metrics that haven't been updated recently
        uint64_t now = get_monotonic_time_ns();
        if (now - metric->last_update > 300000000000ULL) { // 5 minutes
            continue;
        }
        
        // Add help text
        offset += snprintf(buffer + offset, buffer_size - offset,
                          "# HELP %s %s\n", metric->name, metric->help);
        
        // Add type
        const char* type_str = "counter";
        switch (metric->type) {
            case METRIC_COUNTER: type_str = "counter"; break;
            case METRIC_GAUGE: type_str = "gauge"; break;
            case METRIC_HISTOGRAM: type_str = "histogram"; break;
            case METRIC_SUMMARY: type_str = "summary"; break;
        }
        offset += snprintf(buffer + offset, buffer_size - offset,
                          "# TYPE %s %s\n", metric->name, type_str);
        
        if (metric->type == METRIC_COUNTER) {
            uint64_t value = atomic_load(&metric->value.counter_value);
            offset += snprintf(buffer + offset, buffer_size - offset,
                              "%s %lu\n", metric->name, value);
        } else if (metric->type == METRIC_GAUGE) {
            int64_t value = atomic_load(&metric->value.gauge_value);
            offset += snprintf(buffer + offset, buffer_size - offset,
                              "%s %ld\n", metric->name, value);
        } else if (metric->type == METRIC_HISTOGRAM) {
            // Output histogram buckets
            for (int j = 0; j < metric->value.histogram.bucket_count; j++) {
                uint64_t count = atomic_load(&metric->value.histogram.buckets[j].count);
                offset += snprintf(buffer + offset, buffer_size - offset,
                                  "%s_bucket{le=\"%g\"} %lu\n", 
                                  metric->name, metric->value.histogram.buckets[j].le, count);
            }
            
            // Infinity bucket
            uint64_t total_count = atomic_load(&metric->value.histogram.count);
            offset += snprintf(buffer + offset, buffer_size - offset,
                              "%s_bucket{le=\"+Inf\"} %lu\n", metric->name, total_count);
            
            // Count and sum
            offset += snprintf(buffer + offset, buffer_size - offset,
                              "%s_count %lu\n", metric->name, total_count);
            
            uint64_t sum = atomic_load(&metric->value.histogram.sum);
            offset += snprintf(buffer + offset, buffer_size - offset,
                              "%s_sum %g\n", metric->name, (double)sum / 1e9);
        }
        
        offset += snprintf(buffer + offset, buffer_size - offset, "\n");
        
        if (offset >= buffer_size - 1000) {
            break; // Prevent buffer overflow
        }
    }
    
    pthread_mutex_unlock(&g_registry.mutex);
    
    return offset;
}

// Metrics collector thread
static void* metrics_collector_thread(void* arg) {
    struct timespec sleep_time = {1, 0}; // 1 second
    
    while (g_running) {
        collect_system_metrics();
        collect_agent_metrics();
        collect_transport_metrics();
        collect_hardware_metrics();
        
        nanosleep(&sleep_time, NULL);
    }
    
    return NULL;
}

// Collect system metrics
static void collect_system_metrics(void) {
    struct sysinfo si;
    if (sysinfo(&si) == 0) {
        // Memory metrics
        set_gauge("system_memory_usage_bytes", "type=\"total\"", si.totalram * si.mem_unit);
        set_gauge("system_memory_usage_bytes", "type=\"free\"", si.freeram * si.mem_unit);
        set_gauge("system_memory_usage_bytes", "type=\"used\"", 
                 (si.totalram - si.freeram) * si.mem_unit);
        
        // Load average
        set_gauge("system_load_average", "period=\"1m\"", (int64_t)(si.loads[0] * 100));
        set_gauge("system_load_average", "period=\"5m\"", (int64_t)(si.loads[1] * 100));
        set_gauge("system_load_average", "period=\"15m\"", (int64_t)(si.loads[2] * 100));
    }
    
    // CPU utilization from /proc/stat
    FILE* stat_file = fopen("/proc/stat", "r");
    if (stat_file) {
        char line[256];
        if (fgets(line, sizeof(line), stat_file)) {
            unsigned long user, nice, system, idle, iowait, irq, softirq;
            sscanf(line, "cpu %lu %lu %lu %lu %lu %lu %lu",
                   &user, &nice, &system, &idle, &iowait, &irq, &softirq);
            
            unsigned long total = user + nice + system + idle + iowait + irq + softirq;
            unsigned long used = total - idle - iowait;
            
            if (total > 0) {
                g_registry.system_info.cpu_utilization = (double)used / total;
                set_gauge("system_cpu_utilization_ratio", "", 
                         (int64_t)(g_registry.system_info.cpu_utilization * 10000));
            }
        }
        fclose(stat_file);
    }
    
    // Count active agents by type
    char agent_types[][32] = {
        "Director", "ProjectOrchestrator", "Architect", "Constructor", 
        "Patcher", "Debugger", "Testbed", "Linter", "Optimizer",
        "Security", "Bastion", "Infrastructure", "Monitor"
    };
    
    for (int i = 0; i < sizeof(agent_types)/sizeof(agent_types[0]); i++) {
        int count = 0;
        for (int j = 0; j < g_registry.agent_count; j++) {
            if (g_registry.agents[j].is_active && 
                strcmp(g_registry.agents[j].agent_type, agent_types[i]) == 0) {
                count++;
            }
        }
        
        char label[128];
        snprintf(label, sizeof(label), "agent_type=\"%s\"", agent_types[i]);
        set_gauge("system_active_agents", label, count);
    }
}

// Collect agent-specific metrics
static void collect_agent_metrics(void) {
    for (int i = 0; i < g_registry.agent_count; i++) {
        agent_info_t* agent = &g_registry.agents[i];
        if (!agent->is_active) continue;
        
        char label[256];
        snprintf(label, sizeof(label), "agent_id=\"%d\",agent_type=\"%s\",agent_name=\"%s\"",
                 agent->agent_id, agent->agent_type, agent->agent_name);
        
        // Agent status
        set_gauge("agent_status", label, agent->is_active ? 1 : 0);
        
        // Health score calculation
        agent->health_score = calculate_health_score(agent);
        set_gauge("agent_health_score", label, (int64_t)(agent->health_score * 100));
        
        // Queue depth
        set_gauge("agent_queue_depth", label, atomic_load(&agent->queue_depth));
        
        // Resource usage
        snprintf(label, sizeof(label), "agent_id=\"%d\",agent_type=\"%s\",resource=\"cpu\"",
                 agent->agent_id, agent->agent_type);
        set_gauge("agent_resource_usage", label, agent->cpu_usage_percent);
        
        snprintf(label, sizeof(label), "agent_id=\"%d\",agent_type=\"%s\",resource=\"memory\"",
                 agent->agent_id, agent->agent_type);
        set_gauge("agent_resource_usage", label, agent->memory_usage_mb);
        
        // Failure prediction
        agent->failure_prediction_score = calculate_failure_prediction(agent);
        snprintf(label, sizeof(label), "agent_id=\"%d\",agent_type=\"%s\",component=\"overall\"",
                 agent->agent_id, agent->agent_type);
        set_gauge("failure_prediction_score", label, 
                 (int64_t)(agent->failure_prediction_score * 100));
    }
}

// Collect transport layer metrics
static void collect_transport_metrics(void) {
    // Get stats from ultra-fast protocol
    ufp_stats_t stats;
    ufp_get_stats(&stats);
    
    // Update counters
    increment_counter("agent_transport_messages_total", "direction=\"sent\"", stats.messages_sent);
    increment_counter("agent_transport_messages_total", "direction=\"received\"", stats.messages_received);
    increment_counter("agent_transport_bytes_total", "direction=\"sent\"", stats.bytes_sent);
    increment_counter("agent_transport_bytes_total", "direction=\"received\"", stats.bytes_received);
    increment_counter("agent_transport_errors_total", "error_type=\"general\"", stats.errors);
    increment_counter("agent_transport_errors_total", "error_type=\"checksum\"", stats.checksum_failures);
    
    // Update gauges
    set_gauge("agent_transport_throughput_mps", "", (int64_t)(stats.throughput_mbps * 1000000 / 8));
    
    // Observe latency histogram
    if (stats.avg_latency_ns > 0) {
        observe_histogram("agent_transport_latency_seconds", "", stats.avg_latency_ns / 1e9);
    }
}

// Collect hardware-specific metrics
static void collect_hardware_metrics(void) {
    // CPU temperature from thermal zones
    DIR* thermal_dir = opendir("/sys/class/thermal");
    if (thermal_dir) {
        struct dirent* entry;
        while ((entry = readdir(thermal_dir)) != NULL) {
            if (strncmp(entry->d_name, "thermal_zone", 12) == 0) {
                char path[256];
                snprintf(path, sizeof(path), "/sys/class/thermal/%s/temp", entry->d_name);
                
                FILE* temp_file = fopen(path, "r");
                if (temp_file) {
                    int temp_millidegrees;
                    if (fscanf(temp_file, "%d", &temp_millidegrees) == 1) {
                        char label[64];
                        snprintf(label, sizeof(label), "component=\"%s\"", entry->d_name);
                        set_gauge("hardware_temperature_celsius", label, temp_millidegrees / 1000);
                    }
                    fclose(temp_file);
                }
            }
        }
        closedir(thermal_dir);
    }
    
    // Per-CPU utilization
    FILE* stat_file = fopen("/proc/stat", "r");
    if (stat_file) {
        char line[256];
        int cpu_id = 0;
        
        while (fgets(line, sizeof(line), stat_file)) {
            if (strncmp(line, "cpu", 3) == 0 && line[3] >= '0' && line[3] <= '9') {
                unsigned long user, nice, system, idle, iowait, irq, softirq;
                sscanf(line, "cpu%d %lu %lu %lu %lu %lu %lu %lu",
                       &cpu_id, &user, &nice, &system, &idle, &iowait, &irq, &softirq);
                
                unsigned long total = user + nice + system + idle + iowait + irq + softirq;
                unsigned long used = total - idle - iowait;
                
                if (total > 0) {
                    char label[64];
                    // Assume first cores are P-cores (simplified)
                    const char* core_type = (cpu_id < 8) ? "performance" : "efficiency";
                    snprintf(label, sizeof(label), "core_type=\"%s\",core_id=\"%d\"", 
                            core_type, cpu_id);
                    set_gauge("hardware_core_utilization_ratio", label, 
                             (int64_t)((double)used / total * 10000));
                }
            }
        }
        fclose(stat_file);
    }
}

// Calculate agent health score
static double calculate_health_score(agent_info_t* agent) {
    double score = 100.0;
    
    // Deduct for high error rate
    uint64_t errors = atomic_load(&agent->errors);
    uint64_t total_messages = atomic_load(&agent->messages_sent) + 
                             atomic_load(&agent->messages_received);
    if (total_messages > 0) {
        double error_rate = (double)errors / total_messages;
        score -= error_rate * 50.0;
    }
    
    // Deduct for high queue depth
    uint64_t queue_depth = atomic_load(&agent->queue_depth);
    if (queue_depth > 1000) {
        score -= (queue_depth - 1000) * 0.01;
    }
    
    // Deduct for high CPU usage
    if (agent->cpu_usage_percent > 80) {
        score -= (agent->cpu_usage_percent - 80) * 0.5;
    }
    
    // Deduct for old heartbeat
    uint32_t now = time(NULL);
    if (now - agent->last_heartbeat > 10) {
        score -= (now - agent->last_heartbeat - 10) * 2.0;
    }
    
    return fmax(0.0, fmin(100.0, score));
}

// Calculate failure prediction score
static double calculate_failure_prediction(agent_info_t* agent) {
    double risk = 0.0;
    
    // High error rate increases failure risk
    uint64_t errors = atomic_load(&agent->errors);
    uint64_t total_messages = atomic_load(&agent->messages_sent) + 
                             atomic_load(&agent->messages_received);
    if (total_messages > 0) {
        double error_rate = (double)errors / total_messages;
        risk += error_rate * 50.0;
    }
    
    // Increasing queue depth
    uint64_t queue_depth = atomic_load(&agent->queue_depth);
    if (queue_depth > 500) {
        risk += (queue_depth - 500) * 0.02;
    }
    
    // High resource usage
    if (agent->cpu_usage_percent > 90) {
        risk += (agent->cpu_usage_percent - 90) * 2.0;
    }
    
    if (agent->memory_usage_mb > 1024) {
        risk += (agent->memory_usage_mb - 1024) * 0.001;
    }
    
    // Missed heartbeats
    uint32_t now = time(NULL);
    if (now - agent->last_heartbeat > 5) {
        risk += (now - agent->last_heartbeat - 5) * 5.0;
    }
    
    return fmax(0.0, fmin(100.0, risk));
}

// Update agent information
static void update_agent_info(uint16_t agent_id, const char* agent_type, const char* agent_name) {
    pthread_mutex_lock(&g_registry.mutex);
    
    // Find existing agent or create new
    agent_info_t* agent = NULL;
    for (int i = 0; i < g_registry.agent_count; i++) {
        if (g_registry.agents[i].agent_id == agent_id) {
            agent = &g_registry.agents[i];
            break;
        }
    }
    
    if (!agent && g_registry.agent_count < MAX_AGENTS) {
        agent = &g_registry.agents[g_registry.agent_count++];
        agent->agent_id = agent_id;
        atomic_init(&agent->messages_sent, 0);
        atomic_init(&agent->messages_received, 0);
        atomic_init(&agent->errors, 0);
        atomic_init(&agent->processing_time_ns, 0);
        atomic_init(&agent->queue_depth, 0);
    }
    
    if (agent) {
        strncpy(agent->agent_type, agent_type, sizeof(agent->agent_type) - 1);
        strncpy(agent->agent_name, agent_name, sizeof(agent->agent_name) - 1);
        agent->last_heartbeat = time(NULL);
        agent->is_active = true;
    }
    
    pthread_mutex_unlock(&g_registry.mutex);
}

// Record message flow between agents
static void record_message_flow(uint16_t source, uint16_t target, const char* msg_type, uint64_t latency_ns) {
    pthread_mutex_lock(&g_registry.mutex);
    
    // Find existing flow entry or create new
    message_flow_entry_t* flow = NULL;
    for (int i = 0; i < g_registry.flow_count; i++) {
        if (g_registry.message_flows[i].source_agent == source &&
            g_registry.message_flows[i].target_agent == target &&
            strcmp(g_registry.message_flows[i].message_type, msg_type) == 0) {
            flow = &g_registry.message_flows[i];
            break;
        }
    }
    
    if (!flow && g_registry.flow_count < MAX_AGENTS) {
        flow = &g_registry.message_flows[g_registry.flow_count++];
        flow->source_agent = source;
        flow->target_agent = target;
        strncpy(flow->message_type, msg_type, sizeof(flow->message_type) - 1);
        atomic_init(&flow->message_count, 0);
        atomic_init(&flow->total_latency_ns, 0);
    }
    
    if (flow) {
        atomic_fetch_add(&flow->message_count, 1);
        atomic_fetch_add(&flow->total_latency_ns, latency_ns);
        
        // Update counter metric
        char label[256];
        snprintf(label, sizeof(label), "source_agent=\"%d\",target_agent=\"%d\",message_type=\"%s\"",
                 source, target, msg_type);
        increment_counter("message_flow_matrix", label, 1);
        
        // Update histogram metric
        observe_histogram("message_flow_latency_seconds", label, (double)latency_ns / 1e9);
    }
    
    pthread_mutex_unlock(&g_registry.mutex);
}

// Get monotonic time in nanoseconds
static uint64_t get_monotonic_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

// Public API functions
int prometheus_exporter_init(void) {
    printf("Initializing Claude Agent Prometheus Exporter v1.0.0...\n");
    
    if (init_metrics_registry() != 0) {
        fprintf(stderr, "Failed to initialize metrics registry\n");
        return -1;
    }
    
    g_running = true;
    
    if (start_http_server() != 0) {
        fprintf(stderr, "Failed to start HTTP server\n");
        return -1;
    }
    
    // Start metrics collector thread
    if (pthread_create(&g_collector_thread, NULL, metrics_collector_thread, NULL) != 0) {
        fprintf(stderr, "Failed to create metrics collector thread\n");
        return -1;
    }
    pthread_detach(g_collector_thread);
    
    printf("Prometheus exporter initialized successfully\n");
    printf("Metrics available at http://localhost:%d/metrics\n", HTTP_PORT);
    printf("Health check available at http://localhost:%d/health\n", HTTP_PORT);
    
    return 0;
}

void prometheus_exporter_record_message(uint16_t source, uint16_t target, 
                                       const char* msg_type, uint64_t latency_ns, size_t size_bytes) {
    // Record basic transport metrics
    increment_counter("agent_transport_messages_total", "", 1);
    increment_counter("agent_transport_bytes_total", "", size_bytes);
    observe_histogram("agent_transport_latency_seconds", "", (double)latency_ns / 1e9);
    observe_histogram("agent_transport_message_size_bytes", "", (double)size_bytes);
    
    // Record message flow
    record_message_flow(source, target, msg_type, latency_ns);
    
    // Update agent counters
    for (int i = 0; i < g_registry.agent_count; i++) {
        if (g_registry.agents[i].agent_id == source) {
            atomic_fetch_add(&g_registry.agents[i].messages_sent, 1);
        }
        if (g_registry.agents[i].agent_id == target) {
            atomic_fetch_add(&g_registry.agents[i].messages_received, 1);
        }
    }
}

void prometheus_exporter_record_error(uint16_t agent_id, const char* error_type, const char* severity) {
    increment_counter("agent_transport_errors_total", "", 1);
    
    // Update agent error count
    for (int i = 0; i < g_registry.agent_count; i++) {
        if (g_registry.agents[i].agent_id == agent_id) {
            atomic_fetch_add(&g_registry.agents[i].errors, 1);
            break;
        }
    }
}

void prometheus_exporter_update_agent(uint16_t agent_id, const char* agent_type, 
                                     const char* agent_name, uint32_t queue_depth,
                                     int cpu_percent, int memory_mb) {
    update_agent_info(agent_id, agent_type, agent_name);
    
    // Update resource usage
    for (int i = 0; i < g_registry.agent_count; i++) {
        if (g_registry.agents[i].agent_id == agent_id) {
            atomic_store(&g_registry.agents[i].queue_depth, queue_depth);
            g_registry.agents[i].cpu_usage_percent = cpu_percent;
            g_registry.agents[i].memory_usage_mb = memory_mb;
            break;
        }
    }
}

void prometheus_exporter_cleanup(void) {
    g_running = false;
    
    // Wait a bit for threads to finish
    usleep(100000);
    
    pthread_mutex_destroy(&g_registry.mutex);
    printf("Prometheus exporter cleanup completed\n");
}

// Main function for standalone execution
#ifdef STANDALONE
int main(int argc, char* argv[]) {
    printf("Starting Claude Agent Prometheus Exporter\n");
    
    if (prometheus_exporter_init() != 0) {
        fprintf(stderr, "Failed to initialize prometheus exporter\n");
        return 1;
    }
    
    printf("Exporter running. Visit http://localhost:%d/metrics\n", HTTP_PORT);
    printf("Press Ctrl+C to exit\n");
    
    // Keep running
    while (1) {
        sleep(1);
    }
    
    prometheus_exporter_cleanup();
    return 0;
}
#endif