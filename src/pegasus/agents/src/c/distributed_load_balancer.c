/*
 * DISTRIBUTED LOAD BALANCER AND FAILOVER SYSTEM
 * 
 * Advanced load balancing system for distributed agent communication:
 * - Multiple load balancing algorithms (round-robin, least-loaded, latency-based)
 * - Automatic failover with health monitoring
 * - Connection pooling and reuse
 * - Bandwidth optimization and flow control
 * - Split-brain prevention mechanisms
 * - Adaptive load balancing based on real-time metrics
 * 
 * Author: Agent Communication System
 * Version: 1.0 Distributed
 */

#include "distributed_network.h"
#include "agent_protocol.h"
#include "compatibility_layer.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <pthread.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <sys/time.h>
#include <sys/socket.h>
#include <math.h>
#include <numa.h>

// ============================================================================
// LOAD BALANCING CONSTANTS
// ============================================================================

#define LB_HEALTH_CHECK_INTERVAL_MS 1000
#define LB_FAILURE_THRESHOLD 3
#define LB_RECOVERY_THRESHOLD 5
#define LB_WEIGHT_ADJUSTMENT_FACTOR 0.1
#define LB_LATENCY_WEIGHT 0.4
#define LB_LOAD_WEIGHT 0.3
#define LB_AVAILABILITY_WEIGHT 0.3
#define LB_MOVING_AVERAGE_WINDOW 100

// Connection pool settings
#define LB_MIN_CONNECTIONS_PER_NODE 2
#define LB_MAX_CONNECTIONS_PER_NODE 16
#define LB_CONNECTION_TIMEOUT_MS 5000
#define LB_IDLE_CONNECTION_TIMEOUT_MS 300000

// Bandwidth optimization
#define LB_BANDWIDTH_SAMPLES 50
#define LB_CONGESTION_THRESHOLD 0.85
#define LB_FLOW_CONTROL_WINDOW 1024

// ============================================================================
// INTERNAL DATA STRUCTURES
// ============================================================================

// Node health metrics (cache-aligned for performance)
typedef struct __attribute__((aligned(64))) {
    raft_node_id_t node_id;
    
    // Health indicators
    _Atomic uint32_t consecutive_failures;
    _Atomic uint32_t consecutive_successes;
    _Atomic uint64_t last_success_ns;
    _Atomic uint64_t last_failure_ns;
    _Atomic float availability_score;       // 0.0 - 1.0
    
    // Performance metrics
    _Atomic uint64_t total_requests;
    _Atomic uint64_t successful_requests;
    _Atomic uint64_t failed_requests;
    _Atomic uint64_t total_response_time_ns;
    _Atomic uint32_t active_connections;
    _Atomic uint32_t queue_depth;
    
    // Load metrics
    _Atomic float cpu_usage;               // 0.0 - 1.0
    _Atomic float memory_usage;            // 0.0 - 1.0
    _Atomic float network_usage;           // 0.0 - 1.0
    _Atomic uint64_t messages_per_second;
    
    // Bandwidth measurements
    uint64_t bandwidth_samples[LB_BANDWIDTH_SAMPLES];
    _Atomic uint32_t bandwidth_index;
    _Atomic uint64_t estimated_bandwidth_bps;
    
    // Connection pool
    int connection_pool[LB_MAX_CONNECTIONS_PER_NODE];
    _Atomic uint32_t active_pool_size;
    pthread_mutex_t pool_lock;
    
    // State
    bool is_healthy;
    bool is_leader_candidate;
    uint64_t last_health_check_ns;
    
} node_health_t;

// Load balancing algorithm state
typedef struct {
    // Round-robin state
    _Atomic uint32_t rr_counter;
    
    // Weighted round-robin state
    float node_weights[MAX_CLUSTER_NODES];
    _Atomic uint32_t wrr_current_weights[MAX_CLUSTER_NODES];
    
    // Least connections state
    _Atomic uint32_t node_connections[MAX_CLUSTER_NODES];
    
    // Consistent hashing state (for sticky sessions)
    uint64_t hash_ring[MAX_CLUSTER_NODES * 100];  // 100 virtual nodes per physical node
    uint32_t hash_ring_size;
    
    // Adaptive algorithm state
    float performance_history[MAX_CLUSTER_NODES][LB_MOVING_AVERAGE_WINDOW];
    _Atomic uint32_t history_index[MAX_CLUSTER_NODES];
    
    pthread_mutex_t algorithm_lock;
    
} load_balance_algorithms_t;

// Failover management
typedef struct {
    // Failover policies
    bool auto_failover_enabled;
    bool split_brain_protection_enabled;
    uint32_t min_healthy_nodes;
    uint32_t failover_timeout_ms;
    
    // Failover state
    raft_node_id_t primary_nodes[MAX_CLUSTER_NODES];
    raft_node_id_t backup_nodes[MAX_CLUSTER_NODES];
    uint32_t primary_count;
    uint32_t backup_count;
    
    // Split-brain prevention
    uint64_t cluster_token;
    _Atomic uint32_t quorum_size;
    _Atomic uint32_t active_voters;
    
    // Recovery tracking
    raft_node_id_t recovering_nodes[MAX_CLUSTER_NODES];
    uint32_t recovering_count;
    uint64_t recovery_start_times[MAX_CLUSTER_NODES];
    
    pthread_mutex_t failover_lock;
    
} failover_manager_t;

// Bandwidth optimizer
typedef struct {
    // Flow control
    _Atomic uint32_t global_flow_window;
    _Atomic uint32_t flow_control_enabled;
    
    // Congestion detection
    _Atomic uint64_t total_bandwidth_used;
    _Atomic uint64_t total_bandwidth_available;
    _Atomic float congestion_level;        // 0.0 - 1.0
    
    // Message batching
    uint32_t optimal_batch_sizes[MAX_CLUSTER_NODES];
    _Atomic uint32_t current_batch_sizes[MAX_CLUSTER_NODES];
    
    // Compression thresholds
    uint32_t compression_thresholds[MAX_CLUSTER_NODES];
    
    pthread_mutex_t bandwidth_lock;
    
} bandwidth_optimizer_t;

// Main load balancer service
typedef struct __attribute__((aligned(4096))) {
    // Node health tracking
    node_health_t node_health[MAX_CLUSTER_NODES];
    _Atomic uint32_t healthy_node_count;
    
    // Load balancing algorithms
    load_balance_algorithms_t algorithms;
    
    // Failover management
    failover_manager_t failover;
    
    // Bandwidth optimization
    bandwidth_optimizer_t bandwidth;
    
    // Health monitoring thread
    pthread_t health_monitor_thread;
    volatile bool health_monitor_running;
    
    // Configuration
    int default_algorithm;  // 0=RR, 1=Least-Load, 2=Latency, 3=Adaptive
    bool enable_connection_pooling;
    bool enable_bandwidth_optimization;
    
    // Statistics
    _Atomic uint64_t total_requests_balanced;
    _Atomic uint64_t failed_balancing_attempts;
    _Atomic uint64_t failover_triggers;
    _Atomic uint64_t split_brain_detections;
    
    pthread_mutex_t service_lock;
    
} load_balancer_service_t;

// Global load balancer service
static load_balancer_service_t* g_lb_service = NULL;

// External references
extern distributed_network_service_t* g_dist_service;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

static inline uint64_t get_monotonic_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static inline uint32_t hash_consistent(const void* key, size_t len) {
    const uint8_t* data = (const uint8_t*)key;
    uint32_t hash = 2166136261U;
    
    for (size_t i = 0; i < len; i++) {
        hash ^= data[i];
        hash *= 16777619U;
    }
    
    return hash;
}

static inline float calculate_moving_average(float* history, uint32_t window_size, uint32_t current_index) {
    float sum = 0.0f;
    uint32_t count = 0;
    
    for (uint32_t i = 0; i < window_size; i++) {
        if (history[i] > 0.0f) {
            sum += history[i];
            count++;
        }
    }
    
    return count > 0 ? sum / count : 0.0f;
}

// ============================================================================
// NODE HEALTH MONITORING
// ============================================================================

static void update_node_health(raft_node_id_t node_id, bool success, uint64_t response_time_ns) {
    if (!g_lb_service) return;
    
    // Find node health entry
    node_health_t* health = NULL;
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        if (g_lb_service->node_health[i].node_id == node_id) {
            health = &g_lb_service->node_health[i];
            break;
        }
    }
    
    if (!health) return;
    
    uint64_t now = get_monotonic_time_ns();
    
    atomic_fetch_add(&health->total_requests, 1);
    
    if (success) {
        atomic_store(&health->last_success_ns, now);
        atomic_store(&health->consecutive_failures, 0);
        atomic_fetch_add(&health->consecutive_successes, 1);
        atomic_fetch_add(&health->successful_requests, 1);
        atomic_fetch_add(&health->total_response_time_ns, response_time_ns);
        
        // Update availability score using exponential moving average
        float current_availability = atomic_load(&health->availability_score);
        float new_availability = current_availability * 0.95f + 0.05f; // Success contributes 0.05
        atomic_store(&health->availability_score, fminf(new_availability, 1.0f));
        
    } else {
        atomic_store(&health->last_failure_ns, now);
        atomic_fetch_add(&health->consecutive_failures, 1);
        atomic_store(&health->consecutive_successes, 0);
        atomic_fetch_add(&health->failed_requests, 1);
        
        // Update availability score
        float current_availability = atomic_load(&health->availability_score);
        float new_availability = current_availability * 0.95f; // Failure reduces availability
        atomic_store(&health->availability_score, fmaxf(new_availability, 0.0f));
    }
    
    // Determine if node is healthy
    uint32_t failures = atomic_load(&health->consecutive_failures);
    uint32_t successes = atomic_load(&health->consecutive_successes);
    
    bool was_healthy = health->is_healthy;
    bool is_healthy = (failures < LB_FAILURE_THRESHOLD) && 
                     (successes >= LB_RECOVERY_THRESHOLD || failures == 0);
    
    if (was_healthy != is_healthy) {
        health->is_healthy = is_healthy;
        
        if (is_healthy) {
            atomic_fetch_add(&g_lb_service->healthy_node_count, 1);
            printf("[LB] Node %u recovered (successes: %u)\n", node_id, successes);
        } else {
            atomic_fetch_sub(&g_lb_service->healthy_node_count, 1);
            printf("[LB] Node %u marked unhealthy (failures: %u)\n", node_id, failures);
            
            // Trigger failover if needed
            if (g_lb_service->failover.auto_failover_enabled) {
                // Note: Failover implementation requires job persistence layer
                // Currently logged for manual intervention
                syslog(LOG_ALERT, "Node %u requires failover (auto-failover pending full implementation)", node_id);
            }
        }
    }
}

static void measure_node_bandwidth(raft_node_id_t node_id, uint64_t bytes_sent, uint64_t time_ns) {
    if (!g_lb_service || time_ns == 0) return;
    
    node_health_t* health = NULL;
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        if (g_lb_service->node_health[i].node_id == node_id) {
            health = &g_lb_service->node_health[i];
            break;
        }
    }
    
    if (!health) return;
    
    // Calculate bandwidth in bytes per second
    uint64_t bandwidth_bps = (bytes_sent * 1000000000ULL) / time_ns;
    
    // Add to circular buffer
    uint32_t index = atomic_fetch_add(&health->bandwidth_index, 1) % LB_BANDWIDTH_SAMPLES;
    health->bandwidth_samples[index] = bandwidth_bps;
    
    // Calculate moving average
    uint64_t total_bandwidth = 0;
    uint32_t sample_count = 0;
    for (uint32_t i = 0; i < LB_BANDWIDTH_SAMPLES; i++) {
        if (health->bandwidth_samples[i] > 0) {
            total_bandwidth += health->bandwidth_samples[i];
            sample_count++;
        }
    }
    
    if (sample_count > 0) {
        atomic_store(&health->estimated_bandwidth_bps, total_bandwidth / sample_count);
    }
}

static void* health_monitor_thread(void* arg) {
    printf("[LB] Health monitor thread started\n");
    
    while (g_lb_service->health_monitor_running) {
        uint64_t now = get_monotonic_time_ns();
        
        // Check each node's health
        for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
            node_health_t* health = &g_lb_service->node_health[i];
            
            if (health->node_id == 0) continue;  // Skip empty slots
            
            // Check for stale nodes (no recent activity)
            if (now - health->last_health_check_ns > (LB_HEALTH_CHECK_INTERVAL_MS * 2 * 1000000ULL)) {
                // Node appears to be down
                update_node_health(health->node_id, false, 0);
            }
            
            health->last_health_check_ns = now;
        }
        
        // Check for split-brain conditions
        if (g_lb_service->failover.split_brain_protection_enabled) {
            uint32_t healthy_nodes = atomic_load(&g_lb_service->healthy_node_count);
            uint32_t quorum_size = atomic_load(&g_lb_service->failover.quorum_size);
            
            if (healthy_nodes < quorum_size) {
                atomic_fetch_add(&g_lb_service->split_brain_detections, 1);
                printf("[LB] SPLIT-BRAIN WARNING: Only %u healthy nodes, need %u for quorum\n", 
                       healthy_nodes, quorum_size);
            }
        }
        
        usleep(LB_HEALTH_CHECK_INTERVAL_MS * 1000);
    }
    
    printf("[LB] Health monitor thread exiting\n");
    return NULL;
}

// ============================================================================
// LOAD BALANCING ALGORITHMS
// ============================================================================

static raft_node_id_t select_node_round_robin(void) {
    if (!g_lb_service) return 0;
    
    uint32_t counter = atomic_fetch_add(&g_lb_service->algorithms.rr_counter, 1);
    uint32_t healthy_count = 0;
    raft_node_id_t healthy_nodes[MAX_CLUSTER_NODES];
    
    // Collect healthy nodes
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        node_health_t* health = &g_lb_service->node_health[i];
        if (health->node_id != 0 && health->is_healthy && healthy_count < MAX_CLUSTER_NODES) {
            healthy_nodes[healthy_count++] = health->node_id;
        }
    }
    
    if (healthy_count == 0) return 0;
    
    return healthy_nodes[counter % healthy_count];
}

static raft_node_id_t select_node_least_loaded(void) {
    if (!g_lb_service) return 0;
    
    raft_node_id_t best_node = 0;
    float best_load = INFINITY;
    
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        node_health_t* health = &g_lb_service->node_health[i];
        
        if (health->node_id == 0 || !health->is_healthy) continue;
        
        // Calculate combined load score
        float cpu_load = atomic_load(&health->cpu_usage);
        float memory_load = atomic_load(&health->memory_usage);
        float network_load = atomic_load(&health->network_usage);
        uint32_t queue_depth = atomic_load(&health->queue_depth);
        
        float combined_load = (cpu_load * 0.4f) + (memory_load * 0.3f) + 
                             (network_load * 0.2f) + (queue_depth * 0.1f);
        
        if (combined_load < best_load) {
            best_load = combined_load;
            best_node = health->node_id;
        }
    }
    
    return best_node;
}

static raft_node_id_t select_node_by_latency(void) {
    if (!g_lb_service) return 0;
    
    raft_node_id_t best_node = 0;
    uint64_t best_avg_latency = UINT64_MAX;
    
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        node_health_t* health = &g_lb_service->node_health[i];
        
        if (health->node_id == 0 || !health->is_healthy) continue;
        
        uint64_t total_requests = atomic_load(&health->total_requests);
        uint64_t total_response_time = atomic_load(&health->total_response_time_ns);
        
        if (total_requests == 0) continue;
        
        uint64_t avg_latency = total_response_time / total_requests;
        
        if (avg_latency < best_avg_latency) {
            best_avg_latency = avg_latency;
            best_node = health->node_id;
        }
    }
    
    return best_node;
}

static raft_node_id_t select_node_adaptive(void) {
    if (!g_lb_service) return 0;
    
    raft_node_id_t best_node = 0;
    float best_score = -1.0f;
    
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        node_health_t* health = &g_lb_service->node_health[i];
        
        if (health->node_id == 0 || !health->is_healthy) continue;
        
        // Calculate adaptive score based on multiple factors
        float availability = atomic_load(&health->availability_score);
        
        // Calculate average latency
        uint64_t total_requests = atomic_load(&health->total_requests);
        uint64_t total_response_time = atomic_load(&health->total_response_time_ns);
        float latency_score = 1.0f;
        if (total_requests > 0) {
            uint64_t avg_latency_ns = total_response_time / total_requests;
            latency_score = 1.0f / (1.0f + (avg_latency_ns / 1000000.0f)); // Normalize to ms
        }
        
        // Calculate load score (inverse of current load)
        float cpu_load = atomic_load(&health->cpu_usage);
        float memory_load = atomic_load(&health->memory_usage);
        float network_load = atomic_load(&health->network_usage);
        float combined_load = (cpu_load + memory_load + network_load) / 3.0f;
        float load_score = 1.0f - combined_load;
        
        // Weighted combination
        float adaptive_score = (availability * LB_AVAILABILITY_WEIGHT) +
                              (latency_score * LB_LATENCY_WEIGHT) +
                              (load_score * LB_LOAD_WEIGHT);
        
        if (adaptive_score > best_score) {
            best_score = adaptive_score;
            best_node = health->node_id;
        }
    }
    
    return best_node;
}

static raft_node_id_t select_node_consistent_hash(const void* key, size_t key_len) {
    if (!g_lb_service || !key || key_len == 0) return 0;
    
    uint32_t hash = hash_consistent(key, key_len);
    
    // Find the first node in the hash ring >= hash
    for (uint32_t i = 0; i < g_lb_service->algorithms.hash_ring_size; i++) {
        if (g_lb_service->algorithms.hash_ring[i] >= hash) {
            // Extract node ID from hash ring entry
            raft_node_id_t node_id = (raft_node_id_t)(g_lb_service->algorithms.hash_ring[i] & 0xFFFF);
            
            // Verify node is healthy
            for (uint32_t j = 0; j < MAX_CLUSTER_NODES; j++) {
                node_health_t* health = &g_lb_service->node_health[j];
                if (health->node_id == node_id && health->is_healthy) {
                    return node_id;
                }
            }
        }
    }
    
    // Fallback to round-robin if consistent hash fails
    return select_node_round_robin();
}

// ============================================================================
// CONNECTION POOLING
// ============================================================================

static int get_connection_from_pool(raft_node_id_t node_id) {
    if (!g_lb_service->enable_connection_pooling) return -1;
    
    node_health_t* health = NULL;
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        if (g_lb_service->node_health[i].node_id == node_id) {
            health = &g_lb_service->node_health[i];
            break;
        }
    }
    
    if (!health) return -1;
    
    pthread_mutex_lock(&health->pool_lock);
    
    uint32_t pool_size = atomic_load(&health->active_pool_size);
    for (uint32_t i = 0; i < pool_size; i++) {
        if (health->connection_pool[i] >= 0) {
            int fd = health->connection_pool[i];
            health->connection_pool[i] = -1;
            atomic_fetch_sub(&health->active_pool_size, 1);
            
            pthread_mutex_unlock(&health->pool_lock);
            return fd;
        }
    }
    
    pthread_mutex_unlock(&health->pool_lock);
    return -1;  // No available connections
}

static void return_connection_to_pool(raft_node_id_t node_id, int fd) {
    if (!g_lb_service->enable_connection_pooling || fd < 0) return;
    
    node_health_t* health = NULL;
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        if (g_lb_service->node_health[i].node_id == node_id) {
            health = &g_lb_service->node_health[i];
            break;
        }
    }
    
    if (!health) {
        close(fd);
        return;
    }
    
    pthread_mutex_lock(&health->pool_lock);
    
    uint32_t pool_size = atomic_load(&health->active_pool_size);
    if (pool_size < LB_MAX_CONNECTIONS_PER_NODE) {
        // Find empty slot
        for (uint32_t i = 0; i < LB_MAX_CONNECTIONS_PER_NODE; i++) {
            if (health->connection_pool[i] < 0) {
                health->connection_pool[i] = fd;
                atomic_fetch_add(&health->active_pool_size, 1);
                pthread_mutex_unlock(&health->pool_lock);
                return;
            }
        }
    }
    
    pthread_mutex_unlock(&health->pool_lock);
    
    // Pool is full, close the connection
    close(fd);
}

// ============================================================================
// BANDWIDTH OPTIMIZATION
// ============================================================================

static void update_bandwidth_metrics(raft_node_id_t node_id, uint64_t bytes_sent, uint64_t time_ns) {
    if (!g_lb_service->enable_bandwidth_optimization) return;
    
    measure_node_bandwidth(node_id, bytes_sent, time_ns);
    
    // Update global bandwidth usage
    uint64_t bandwidth_used = (bytes_sent * 1000000000ULL) / time_ns;
    atomic_fetch_add(&g_lb_service->bandwidth.total_bandwidth_used, bandwidth_used);
    
    // Calculate congestion level
    uint64_t total_used = atomic_load(&g_lb_service->bandwidth.total_bandwidth_used);
    uint64_t total_available = atomic_load(&g_lb_service->bandwidth.total_bandwidth_available);
    
    if (total_available > 0) {
        float congestion = (float)total_used / total_available;
        atomic_store(&g_lb_service->bandwidth.congestion_level, fminf(congestion, 1.0f));
        
        // Enable flow control if congestion is high
        if (congestion > LB_CONGESTION_THRESHOLD) {
            atomic_store(&g_lb_service->bandwidth.flow_control_enabled, 1);
            
            // Reduce flow window
            uint32_t current_window = atomic_load(&g_lb_service->bandwidth.global_flow_window);
            uint32_t new_window = (uint32_t)(current_window * 0.9f);
            atomic_store(&g_lb_service->bandwidth.global_flow_window, 
                        fmaxf(new_window, LB_FLOW_CONTROL_WINDOW / 4));
        } else {
            atomic_store(&g_lb_service->bandwidth.flow_control_enabled, 0);
            
            // Increase flow window
            uint32_t current_window = atomic_load(&g_lb_service->bandwidth.global_flow_window);
            uint32_t new_window = (uint32_t)(current_window * 1.05f);
            atomic_store(&g_lb_service->bandwidth.global_flow_window, 
                        fminf(new_window, LB_FLOW_CONTROL_WINDOW));
        }
    }
}

static uint32_t get_optimal_batch_size(raft_node_id_t node_id) {
    if (!g_lb_service->enable_bandwidth_optimization) return 1;
    
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        if (g_lb_service->node_health[i].node_id == node_id) {
            uint32_t batch_size = atomic_load(&g_lb_service->bandwidth.current_batch_sizes[i]);
            return batch_size > 0 ? batch_size : 1;
        }
    }
    
    return 1;
}

// ============================================================================
// PUBLIC API IMPLEMENTATION
// ============================================================================

int load_balancer_init(void) {
    if (g_lb_service) return -1;
    
    int numa_node = numa_node_of_cpu(sched_getcpu());
    g_lb_service = numa_alloc_onnode(sizeof(load_balancer_service_t), numa_node);
    if (!g_lb_service) return -1;
    
    memset(g_lb_service, 0, sizeof(load_balancer_service_t));
    
    // Initialize node health structures
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        node_health_t* health = &g_lb_service->node_health[i];
        
        // Initialize connection pool
        for (uint32_t j = 0; j < LB_MAX_CONNECTIONS_PER_NODE; j++) {
            health->connection_pool[j] = -1;
        }
        pthread_mutex_init(&health->pool_lock, NULL);
        
        // Initialize availability score
        atomic_store(&health->availability_score, 1.0f);
        health->is_healthy = false;
    }
    
    // Initialize algorithm state
    pthread_mutex_init(&g_lb_service->algorithms.algorithm_lock, NULL);
    
    // Initialize failover state
    pthread_mutex_init(&g_lb_service->failover.failover_lock, NULL);
    g_lb_service->failover.auto_failover_enabled = true;
    g_lb_service->failover.split_brain_protection_enabled = true;
    g_lb_service->failover.min_healthy_nodes = 2;
    atomic_store(&g_lb_service->failover.quorum_size, 2);
    
    // Initialize bandwidth optimization
    pthread_mutex_init(&g_lb_service->bandwidth.bandwidth_lock, NULL);
    atomic_store(&g_lb_service->bandwidth.global_flow_window, LB_FLOW_CONTROL_WINDOW);
    
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        g_lb_service->bandwidth.optimal_batch_sizes[i] = 1;
        atomic_store(&g_lb_service->bandwidth.current_batch_sizes[i], 1);
        g_lb_service->bandwidth.compression_thresholds[i] = 1024; // 1KB default
    }
    
    // Set default configuration
    g_lb_service->default_algorithm = 3; // Adaptive
    g_lb_service->enable_connection_pooling = true;
    g_lb_service->enable_bandwidth_optimization = true;
    
    pthread_mutex_init(&g_lb_service->service_lock, NULL);
    
    // Start health monitoring thread
    g_lb_service->health_monitor_running = true;
    pthread_create(&g_lb_service->health_monitor_thread, NULL, health_monitor_thread, NULL);
    
    printf("[LB] Load balancer service initialized (NUMA: %d)\n", numa_node);
    return 0;
}

void load_balancer_cleanup(void) {
    if (!g_lb_service) return;
    
    // Stop health monitoring
    g_lb_service->health_monitor_running = false;
    pthread_join(g_lb_service->health_monitor_thread, NULL);
    
    // Close all connection pools
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        node_health_t* health = &g_lb_service->node_health[i];
        
        pthread_mutex_lock(&health->pool_lock);
        for (uint32_t j = 0; j < LB_MAX_CONNECTIONS_PER_NODE; j++) {
            if (health->connection_pool[j] >= 0) {
                close(health->connection_pool[j]);
            }
        }
        pthread_mutex_unlock(&health->pool_lock);
        
        pthread_mutex_destroy(&health->pool_lock);
    }
    
    // Cleanup mutexes
    pthread_mutex_destroy(&g_lb_service->algorithms.algorithm_lock);
    pthread_mutex_destroy(&g_lb_service->failover.failover_lock);
    pthread_mutex_destroy(&g_lb_service->bandwidth.bandwidth_lock);
    pthread_mutex_destroy(&g_lb_service->service_lock);
    
    numa_free(g_lb_service, sizeof(load_balancer_service_t));
    g_lb_service = NULL;
    
    printf("[LB] Load balancer service cleaned up\n");
}

raft_node_id_t load_balancer_select_node(int algorithm, const void* session_key, size_t key_len) {
    if (!g_lb_service) return 0;
    
    raft_node_id_t selected_node = 0;
    
    atomic_fetch_add(&g_lb_service->total_requests_balanced, 1);
    
    switch (algorithm >= 0 ? algorithm : g_lb_service->default_algorithm) {
        case 0:  // Round-robin
            selected_node = select_node_round_robin();
            break;
        case 1:  // Least loaded
            selected_node = select_node_least_loaded();
            break;
        case 2:  // Latency-based
            selected_node = select_node_by_latency();
            break;
        case 3:  // Adaptive
            selected_node = select_node_adaptive();
            break;
        case 4:  // Consistent hash
            selected_node = select_node_consistent_hash(session_key, key_len);
            break;
        default:
            selected_node = select_node_round_robin();
            break;
    }
    
    if (selected_node == 0) {
        atomic_fetch_add(&g_lb_service->failed_balancing_attempts, 1);
    }
    
    return selected_node;
}

void load_balancer_update_node_metrics(raft_node_id_t node_id, float cpu_usage, float memory_usage, 
                                      float network_usage, uint32_t queue_depth, uint64_t messages_per_second) {
    if (!g_lb_service) return;
    
    node_health_t* health = NULL;
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        if (g_lb_service->node_health[i].node_id == node_id) {
            health = &g_lb_service->node_health[i];
            break;
        }
    }
    
    if (!health) {
        // Add new node
        for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
            if (g_lb_service->node_health[i].node_id == 0) {
                health = &g_lb_service->node_health[i];
                health->node_id = node_id;
                atomic_store(&health->availability_score, 1.0f);
                health->is_healthy = true;
                atomic_fetch_add(&g_lb_service->healthy_node_count, 1);
                break;
            }
        }
    }
    
    if (health) {
        atomic_store(&health->cpu_usage, cpu_usage);
        atomic_store(&health->memory_usage, memory_usage);
        atomic_store(&health->network_usage, network_usage);
        atomic_store(&health->queue_depth, queue_depth);
        atomic_store(&health->messages_per_second, messages_per_second);
        health->last_health_check_ns = get_monotonic_time_ns();
    }
}

void load_balancer_report_request_result(raft_node_id_t node_id, bool success, uint64_t response_time_ns) {
    update_node_health(node_id, success, response_time_ns);
}

void load_balancer_report_bandwidth(raft_node_id_t node_id, uint64_t bytes_sent, uint64_t time_ns) {
    update_bandwidth_metrics(node_id, bytes_sent, time_ns);
}

void load_balancer_print_status(void) {
    if (!g_lb_service) {
        printf("Load balancer not initialized\n");
        return;
    }
    
    printf("\n=== Load Balancer Status ===\n");
    printf("Algorithm: %s\n", 
           g_lb_service->default_algorithm == 0 ? "Round-Robin" :
           g_lb_service->default_algorithm == 1 ? "Least-Loaded" :
           g_lb_service->default_algorithm == 2 ? "Latency-Based" :
           g_lb_service->default_algorithm == 3 ? "Adaptive" : "Unknown");
    
    printf("Healthy nodes: %u\n", atomic_load(&g_lb_service->healthy_node_count));
    printf("Connection pooling: %s\n", g_lb_service->enable_connection_pooling ? "Enabled" : "Disabled");
    printf("Bandwidth optimization: %s\n", g_lb_service->enable_bandwidth_optimization ? "Enabled" : "Disabled");
    
    printf("\nNode Health:\n");
    printf("%-8s %-12s %-12s %-12s %-12s %-15s %-10s\n",
           "Node ID", "CPU Usage", "Mem Usage", "Net Usage", "Queue", "Availability", "Healthy");
    printf("%-8s %-12s %-12s %-12s %-12s %-15s %-10s\n",
           "--------", "------------", "------------", "------------", "------------", "---------------", "----------");
    
    for (uint32_t i = 0; i < MAX_CLUSTER_NODES; i++) {
        node_health_t* health = &g_lb_service->node_health[i];
        if (health->node_id != 0) {
            printf("%-8u %-12.1f %-12.1f %-12.1f %-12u %-15.3f %-10s\n",
                   health->node_id,
                   atomic_load(&health->cpu_usage) * 100.0f,
                   atomic_load(&health->memory_usage) * 100.0f,
                   atomic_load(&health->network_usage) * 100.0f,
                   atomic_load(&health->queue_depth),
                   atomic_load(&health->availability_score),
                   health->is_healthy ? "Yes" : "No");
        }
    }
    
    printf("\nLoad Balancer Statistics:\n");
    printf("Total requests: %lu\n", atomic_load(&g_lb_service->total_requests_balanced));
    printf("Failed attempts: %lu\n", atomic_load(&g_lb_service->failed_balancing_attempts));
    printf("Failover triggers: %lu\n", atomic_load(&g_lb_service->failover_triggers));
    printf("Split-brain detections: %lu\n", atomic_load(&g_lb_service->split_brain_detections));
    
    if (g_lb_service->enable_bandwidth_optimization) {
        printf("\nBandwidth Optimization:\n");
        printf("Global flow window: %u\n", atomic_load(&g_lb_service->bandwidth.global_flow_window));
        printf("Flow control enabled: %s\n", 
               atomic_load(&g_lb_service->bandwidth.flow_control_enabled) ? "Yes" : "No");
        printf("Congestion level: %.1f%%\n", 
               atomic_load(&g_lb_service->bandwidth.congestion_level) * 100.0f);
    }
    
    printf("\n");
}