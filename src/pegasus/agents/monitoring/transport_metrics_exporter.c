/*
 * Transport Layer Metrics Exporter
 * High-performance C implementation for ultra-fast protocol metrics
 */

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

#include "ultra_fast_protocol.h"

#define MAX_METRICS 1000
#define MAX_METRIC_NAME_LEN 128
#define MAX_LABEL_LEN 64
#define METRICS_BUFFER_SIZE (1024 * 1024)  // 1MB buffer
#define HTTP_PORT 8001
#define UPDATE_INTERVAL_MS 100  // 100ms update interval

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

// Metric structure
typedef struct {
    char name[MAX_METRIC_NAME_LEN];
    char help[256];
    metric_type_t type;
    char labels[MAX_LABEL_LEN];
    
    union {
        atomic_uint_fast64_t counter_value;
        atomic_uint_fast64_t gauge_value;
        struct {
            atomic_uint_fast64_t count;
            atomic_uint_fast64_t sum;
            histogram_bucket_t buckets[20];
            int bucket_count;
        } histogram;
        struct {
            atomic_uint_fast64_t count;
            atomic_uint_fast64_t sum;
            double quantiles[5];  // 0.5, 0.9, 0.95, 0.99, 0.999
        } summary;
    } value;
} metric_t;

// Metrics registry
typedef struct {
    metric_t metrics[MAX_METRICS];
    int metric_count;
    pthread_mutex_t mutex;
    char buffer[METRICS_BUFFER_SIZE];
} metrics_registry_t;

// Global registry
static metrics_registry_t g_registry = {0};

// Latency buckets (in nanoseconds)
static const double LATENCY_BUCKETS[] = {
    1000,      // 1μs
    5000,      // 5μs
    10000,     // 10μs
    25000,     // 25μs
    50000,     // 50μs
    100000,    // 100μs
    250000,    // 250μs
    500000,    // 500μs
    1000000,   // 1ms
    2500000,   // 2.5ms
    5000000,   // 5ms
    10000000,  // 10ms
    25000000,  // 25ms
    50000000,  // 50ms
    100000000, // 100ms
    250000000, // 250ms
    500000000, // 500ms
    1000000000,// 1s
    2500000000,// 2.5s
    5000000000 // 5s
};

// Function prototypes
static int init_metrics_registry(void);
static int register_metric(const char* name, const char* help, metric_type_t type, const char* labels);
static void increment_counter(const char* name, const char* labels, uint64_t value);
static void set_gauge(const char* name, const char* labels, uint64_t value);
static void observe_histogram(const char* name, const char* labels, double value);
static int start_http_server(void);
static void* http_server_thread(void* arg);
static void handle_metrics_request(int client_fd);
static int format_metrics_output(char* buffer, size_t buffer_size);
static void* metrics_collector_thread(void* arg);
static void collect_transport_metrics(void);
static uint64_t get_monotonic_time_ns(void);

// Initialize the metrics registry
static int init_metrics_registry(void) {
    memset(&g_registry, 0, sizeof(g_registry));
    
    if (pthread_mutex_init(&g_registry.mutex, NULL) != 0) {
        fprintf(stderr, "Failed to initialize metrics mutex\n");
        return -1;
    }
    
    // Register core transport metrics
    register_metric("transport_messages_total", 
                   "Total messages processed by transport layer",
                   METRIC_COUNTER, "direction,msg_type,priority");
    
    register_metric("transport_bytes_total",
                   "Total bytes processed by transport layer", 
                   METRIC_COUNTER, "direction");
    
    register_metric("transport_latency_seconds",
                   "Message transport latency",
                   METRIC_HISTOGRAM, "msg_type,priority");
    
    register_metric("transport_throughput_mps",
                   "Current transport throughput in messages per second",
                   METRIC_GAUGE, "");
    
    register_metric("transport_errors_total",
                   "Transport layer errors",
                   METRIC_COUNTER, "error_type,severity");
    
    register_metric("transport_active_connections",
                   "Active transport connections",
                   METRIC_GAUGE, "");
    
    register_metric("transport_queue_depth",
                   "Transport queue depth",
                   METRIC_GAUGE, "priority");
    
    register_metric("transport_memory_usage_bytes",
                   "Transport layer memory usage",
                   METRIC_GAUGE, "pool_type");
    
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
    strncpy(metric->help, help, 255);
    strncpy(metric->labels, labels, MAX_LABEL_LEN - 1);
    metric->type = type;
    
    // Initialize histogram buckets if needed
    if (type == METRIC_HISTOGRAM) {
        metric->value.histogram.bucket_count = sizeof(LATENCY_BUCKETS) / sizeof(LATENCY_BUCKETS[0]);
        for (int i = 0; i < metric->value.histogram.bucket_count; i++) {
            metric->value.histogram.buckets[i].le = LATENCY_BUCKETS[i] / 1e9; // Convert to seconds
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
            atomic_fetch_add(&metric->value.counter_value, value);
            break;
        }
    }
    
    pthread_mutex_unlock(&g_registry.mutex);
}

// Set a gauge metric
static void set_gauge(const char* name, const char* labels, uint64_t value) {
    pthread_mutex_lock(&g_registry.mutex);
    
    for (int i = 0; i < g_registry.metric_count; i++) {
        metric_t* metric = &g_registry.metrics[i];
        if (strcmp(metric->name, name) == 0 && metric->type == METRIC_GAUGE) {
            atomic_store(&metric->value.gauge_value, value);
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
            atomic_fetch_add(&metric->value.histogram.count, 1);
            atomic_fetch_add(&metric->value.histogram.sum, (uint64_t)(value * 1e9)); // Store in nanoseconds
            
            // Update buckets
            for (int j = 0; j < metric->value.histogram.bucket_count; j++) {
                if (value <= metric->value.histogram.buckets[j].le) {
                    atomic_fetch_add(&metric->value.histogram.buckets[j].count, 1);
                }
            }
            break;
        }
    }
    
    pthread_mutex_unlock(&g_registry.mutex);
}

// Start HTTP metrics server
static int start_http_server(void) {
    pthread_t server_thread;
    
    if (pthread_create(&server_thread, NULL, http_server_thread, NULL) != 0) {
        fprintf(stderr, "Failed to create HTTP server thread\n");
        return -1;
    }
    
    pthread_detach(server_thread);
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
    
    printf("Metrics server listening on port %d\n", HTTP_PORT);
    
    while (1) {
        if ((client_fd = accept(server_fd, (struct sockaddr*)&address, (socklen_t*)&addrlen)) < 0) {
            perror("accept");
            continue;
        }
        
        handle_metrics_request(client_fd);
        close(client_fd);
    }
    
    return NULL;
}

// Handle HTTP metrics request
static void handle_metrics_request(int client_fd) {
    char buffer[1024];
    int bytes_read = read(client_fd, buffer, sizeof(buffer) - 1);
    
    if (bytes_read > 0) {
        buffer[bytes_read] = '\0';
        
        // Simple HTTP request parsing - just check for GET /metrics
        if (strstr(buffer, "GET /metrics") != NULL) {
            // Format metrics output
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
        }
    }
}

// Format metrics for Prometheus output
static int format_metrics_output(char* buffer, size_t buffer_size) {
    int offset = 0;
    
    pthread_mutex_lock(&g_registry.mutex);
    
    for (int i = 0; i < g_registry.metric_count; i++) {
        metric_t* metric = &g_registry.metrics[i];
        
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
            uint64_t value = atomic_load(&metric->value.gauge_value);
            offset += snprintf(buffer + offset, buffer_size - offset,
                              "%s %lu\n", metric->name, value);
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
    struct timespec sleep_time = {0, UPDATE_INTERVAL_MS * 1000000}; // Convert ms to ns
    
    while (1) {
        collect_transport_metrics();
        nanosleep(&sleep_time, NULL);
    }
    
    return NULL;
}

// Collect transport layer metrics
static void collect_transport_metrics(void) {
    ufp_stats_t stats;
    ufp_get_stats(&stats);
    
    // Update counters
    increment_counter("transport_messages_total", "", 
                     stats.messages_sent + stats.messages_received);
    increment_counter("transport_bytes_total", "", 
                     stats.bytes_sent + stats.bytes_received);
    increment_counter("transport_errors_total", "", stats.errors);
    
    // Update gauges
    set_gauge("transport_throughput_mps", "", 
              (uint64_t)stats.throughput_mbps * 1000000 / 8); // Convert MB/s to msgs/s approximation
    
    // Observe latency histogram
    if (stats.avg_latency_ns > 0) {
        observe_histogram("transport_latency_seconds", "", stats.avg_latency_ns / 1e9);
    }
    
    // System resource metrics
    FILE* meminfo = fopen("/proc/meminfo", "r");
    if (meminfo) {
        char line[256];
        while (fgets(line, sizeof(line), meminfo)) {
            if (strncmp(line, "MemTotal:", 9) == 0) {
                unsigned long mem_total;
                sscanf(line, "MemTotal: %lu kB", &mem_total);
                set_gauge("transport_memory_usage_bytes", "", mem_total * 1024);
                break;
            }
        }
        fclose(meminfo);
    }
}

// Get monotonic time in nanoseconds
static uint64_t get_monotonic_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

// Public API functions
int transport_metrics_init(void) {
    printf("Initializing transport metrics exporter...\n");
    
    if (ufp_init() != UFP_SUCCESS) {
        fprintf(stderr, "Failed to initialize ultra-fast protocol\n");
        return -1;
    }
    
    if (init_metrics_registry() != 0) {
        fprintf(stderr, "Failed to initialize metrics registry\n");
        return -1;
    }
    
    if (start_http_server() != 0) {
        fprintf(stderr, "Failed to start HTTP server\n");
        return -1;
    }
    
    // Start metrics collector thread
    pthread_t collector_thread;
    if (pthread_create(&collector_thread, NULL, metrics_collector_thread, NULL) != 0) {
        fprintf(stderr, "Failed to create metrics collector thread\n");
        return -1;
    }
    pthread_detach(collector_thread);
    
    printf("Transport metrics exporter initialized successfully\n");
    return 0;
}

void transport_metrics_record_message(const char* msg_type, const char* priority, uint64_t latency_ns) {
    // Record message count
    increment_counter("transport_messages_total", "", 1);
    
    // Record latency
    observe_histogram("transport_latency_seconds", "", (double)latency_ns / 1e9);
}

void transport_metrics_record_error(const char* error_type, const char* severity) {
    increment_counter("transport_errors_total", "", 1);
}

void transport_metrics_cleanup(void) {
    ufp_cleanup();
    pthread_mutex_destroy(&g_registry.mutex);
}

// Main function for standalone execution
#ifdef STANDALONE
int main(int argc, char* argv[]) {
    printf("Starting Claude Agent Transport Metrics Exporter\n");
    
    if (transport_metrics_init() != 0) {
        fprintf(stderr, "Failed to initialize transport metrics\n");
        return 1;
    }
    
    printf("Metrics exporter running. Visit http://localhost:%d/metrics\n", HTTP_PORT);
    printf("Press Ctrl+C to exit\n");
    
    // Keep running
    while (1) {
        sleep(1);
    }
    
    transport_metrics_cleanup();
    return 0;
}
#endif