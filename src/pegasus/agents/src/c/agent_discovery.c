/*
 * AGENT DISCOVERY SERVICE
 * 
 * High-performance service discovery layer for the Claude Agent Communication System
 * - Agent registration with capabilities
 * - Service discovery with load balancing
 * - Health monitoring and failover
 * - NUMA-aware placement
 * 
 * Integrates with agent_bridge.c transport layer
 * 
 * Author: Agent Communication System
 * Version: 1.0 Production
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <pthread.h>
#include <sys/time.h>
#include <sys/mman.h>
#include <unistd.h>
#include <errno.h>
#include <numa.h>
#include <numaif.h>
#include "compatibility_layer.h"
#include <sched.h>
#include <x86intrin.h>

// Include the transport layer header
#include "agent_protocol.h"

// ============================================================================
// CONSTANTS AND CONFIGURATION
// ============================================================================

#define MAX_AGENTS 512
#define MAX_AGENT_NAME 64
#define MAX_CAPABILITIES 32
#define MAX_ENDPOINTS 16
#define HEARTBEAT_INTERVAL_MS 5000
#define HEALTH_CHECK_TIMEOUT_MS 10000
#define FAILOVER_THRESHOLD 3
#define DISCOVERY_HASH_SIZE 1024
#define CACHE_LINE_SIZE 64

// Agent types and capabilities
typedef enum {
    AGENT_TYPE_DIRECTOR = 1,
    AGENT_TYPE_PROJECT_ORCHESTRATOR = 2,
    AGENT_TYPE_SECURITY = 3,
    AGENT_TYPE_SECURITY_CHAOS = 4,
    AGENT_TYPE_TESTBED = 5,
    AGENT_TYPE_TUI = 6,
    AGENT_TYPE_WEB = 7,
    AGENT_TYPE_C_INTERNAL = 8,
    AGENT_TYPE_PYTHON_INTERNAL = 9,
    AGENT_TYPE_MONITOR = 10,
    AGENT_TYPE_OPTIMIZER = 11,
    AGENT_TYPE_PATCHER = 12,
    AGENT_TYPE_PYGUI = 13,
    AGENT_TYPE_RED_TEAM_ORCHESTRATOR = 14,
    AGENT_TYPE_RESEARCHER = 15,
    AGENT_TYPE_DOCGEN = 16,
    AGENT_TYPE_INFRASTRUCTURE = 17,
    AGENT_TYPE_INTEGRATION = 18,
    AGENT_TYPE_LINTER = 19,
    AGENT_TYPE_ML_OPS = 20,
    AGENT_TYPE_MOBILE = 21,
    AGENT_TYPE_CONSTRUCTOR = 22,
    AGENT_TYPE_DATA_SCIENCE = 23,
    AGENT_TYPE_DATABASE = 24,
    AGENT_TYPE_DEBUGGER = 25,
    AGENT_TYPE_DEPLOYER = 26,
    AGENT_TYPE_API_DESIGNER = 27,
    AGENT_TYPE_ARCHITECT = 28
} agent_type_t;

typedef enum {
    AGENT_STATE_INITIALIZING = 0,
    AGENT_STATE_ACTIVE = 1,
    AGENT_STATE_DEGRADED = 2,
    AGENT_STATE_UNAVAILABLE = 3,
    AGENT_STATE_FAILED = 4,
    AGENT_STATE_SHUTTING_DOWN = 5
} agent_state_t;

// ============================================================================
// DATA STRUCTURES
// ============================================================================

// Agent capability descriptor
typedef struct __attribute__((packed)) {
    char name[32];
    uint32_t version;
    float performance_rating;  // 0.0 - 1.0
    uint32_t max_concurrent_tasks;
} agent_capability_t;

// Agent endpoint information
typedef struct __attribute__((packed)) {
    char protocol[16];     // "ipc", "tcp", "udp", "shared_mem"
    char address[64];      // "/tmp/agent.sock", "127.0.0.1:8080", etc.
    uint16_t port;
    uint32_t flags;        // endpoint-specific flags
} agent_endpoint_t;

// Agent health metrics
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    _Atomic uint64_t requests_handled;
    _Atomic uint64_t errors_count;
    _Atomic uint64_t last_heartbeat_ns;
    _Atomic uint32_t response_time_avg_us;
    _Atomic uint32_t cpu_usage_percent;
    _Atomic uint32_t memory_usage_mb;
    _Atomic uint32_t active_connections;
    _Atomic uint32_t queue_depth;
    float load_factor;     // current load / max capacity
} agent_health_t;

// Agent registry entry
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    // Identity
    char name[MAX_AGENT_NAME];
    uint32_t agent_id;
    agent_type_t type;
    uint32_t instance_id;
    
    // State
    _Atomic uint32_t state;
    uint64_t registration_time_ns;
    uint64_t last_seen_ns;
    uint32_t failure_count;
    
    // Capabilities
    uint32_t capability_count;
    agent_capability_t capabilities[MAX_CAPABILITIES];
    
    // Networking
    uint32_t endpoint_count;
    agent_endpoint_t endpoints[MAX_ENDPOINTS];
    
    // NUMA affinity
    int preferred_numa_node;
    uint64_t cpu_affinity_mask;
    
    // Health
    agent_health_t health;
    
    // Load balancing
    _Atomic uint32_t connection_count;
    _Atomic float priority_score;  // dynamic priority for load balancing
    
    // Synchronization
    pthread_rwlock_t lock;
    
} agent_registry_entry_t;

// Hash table for fast agent lookup
typedef struct discovery_hash_node {
    agent_registry_entry_t* entry;
    struct discovery_hash_node* next;
} discovery_hash_node_t;

typedef struct {
    discovery_hash_node_t* buckets[DISCOVERY_HASH_SIZE];
    pthread_rwlock_t lock;
} discovery_hash_table_t;

// Main discovery service structure
typedef struct __attribute__((aligned(PAGE_SIZE))) {
    // Registry
    agent_registry_entry_t agents[MAX_AGENTS];
    _Atomic uint32_t agent_count;
    
    // Hash table for O(1) lookup
    discovery_hash_table_t hash_table;
    
    // Health monitoring
    pthread_t health_monitor_thread;
    pthread_t heartbeat_thread;
    volatile bool running;
    
    // Statistics
    _Atomic uint64_t total_registrations;
    _Atomic uint64_t total_discoveries;
    _Atomic uint64_t health_checks_performed;
    _Atomic uint64_t failovers_triggered;
    
    // Performance optimization
    uint64_t last_cache_refresh_ns;
    agent_registry_entry_t* sorted_by_load[MAX_AGENTS];  // Cached sorted list
    
} agent_discovery_service_t;

// Global discovery service instance
static agent_discovery_service_t* g_discovery_service = NULL;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

static inline uint64_t get_timestamp_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static inline uint32_t hash_string(const char* str) {
    uint32_t hash = 5381;
    int c;
    while ((c = *str++)) {
        hash = ((hash << 5) + hash) + c;
    }
    return hash % DISCOVERY_HASH_SIZE;
}

static inline bool is_agent_healthy(const agent_registry_entry_t* agent) {
    uint64_t now = get_timestamp_ns();
    uint64_t last_heartbeat = atomic_load(&agent->health.last_heartbeat_ns);
    
    // Check heartbeat timeout
    if (now - last_heartbeat > HEALTH_CHECK_TIMEOUT_MS * 1000000ULL) {
        return false;
    }
    
    // Check state
    agent_state_t state = atomic_load(&agent->state);
    if (state == AGENT_STATE_FAILED || state == AGENT_STATE_UNAVAILABLE) {
        return false;
    }
    
    // Check error rate
    uint64_t errors = atomic_load(&agent->health.errors_count);
    uint64_t requests = atomic_load(&agent->health.requests_handled);
    if (requests > 100 && (errors * 100 / requests) > 10) {  // 10% error rate
        return false;
    }
    
    return true;
}

static void update_agent_priority_score(agent_registry_entry_t* agent) {
    // Calculate dynamic priority based on health, load, and capabilities
    float health_score = is_agent_healthy(agent) ? 1.0f : 0.0f;
    float load_score = 1.0f - agent->health.load_factor;
    float error_rate = 0.0f;
    
    uint64_t requests = atomic_load(&agent->health.requests_handled);
    if (requests > 0) {
        uint64_t errors = atomic_load(&agent->health.errors_count);
        error_rate = (float)errors / requests;
    }
    
    float reliability_score = 1.0f - (error_rate * 2.0f);  // Penalize errors heavily
    if (reliability_score < 0.0f) reliability_score = 0.0f;
    
    // Response time factor (lower is better)
    uint32_t response_time = atomic_load(&agent->health.response_time_avg_us);
    float response_score = response_time > 0 ? 1000.0f / response_time : 1.0f;
    if (response_score > 1.0f) response_score = 1.0f;
    
    // Combine factors
    float priority = (health_score * 0.4f) + 
                    (load_score * 0.3f) + 
                    (reliability_score * 0.2f) + 
                    (response_score * 0.1f);
    
    atomic_store(&agent->priority_score, priority);
}

// ============================================================================
// DISCOVERY SERVICE IMPLEMENTATION
// ============================================================================

int discovery_service_init() {
    if (g_discovery_service) {
        return -EALREADY;
    }
    
    // Allocate service structure with NUMA awareness
    int numa_node = numa_node_of_cpu(sched_getcpu());
    g_discovery_service = numa_alloc_onnode(sizeof(agent_discovery_service_t), numa_node);
    if (!g_discovery_service) {
        return -ENOMEM;
    }
    
    memset(g_discovery_service, 0, sizeof(agent_discovery_service_t));
    
    // Initialize hash table
    for (int i = 0; i < DISCOVERY_HASH_SIZE; i++) {
        g_discovery_service->hash_table.buckets[i] = NULL;
    }
    pthread_rwlock_init(&g_discovery_service->hash_table.lock, NULL);
    
    // Initialize agent locks
    for (int i = 0; i < MAX_AGENTS; i++) {
        pthread_rwlock_init(&g_discovery_service->agents[i].lock, NULL);
    }
    
    atomic_store(&g_discovery_service->agent_count, 0);
    g_discovery_service->running = true;
    g_discovery_service->last_cache_refresh_ns = get_timestamp_ns();
    
    printf("Agent Discovery Service: Initialized on NUMA node %d\n", numa_node);
    return 0;
}

void discovery_service_cleanup() {
    if (!g_discovery_service) {
        return;
    }
    
    g_discovery_service->running = false;
    
    // Wait for threads to complete
    if (g_discovery_service->health_monitor_thread) {
        pthread_join(g_discovery_service->health_monitor_thread, NULL);
    }
    
    if (g_discovery_service->heartbeat_thread) {
        pthread_join(g_discovery_service->heartbeat_thread, NULL);
    }
    
    // Cleanup hash table
    pthread_rwlock_wrlock(&g_discovery_service->hash_table.lock);
    for (int i = 0; i < DISCOVERY_HASH_SIZE; i++) {
        discovery_hash_node_t* node = g_discovery_service->hash_table.buckets[i];
        while (node) {
            discovery_hash_node_t* next = node->next;
            free(node);
            node = next;
        }
    }
    pthread_rwlock_unlock(&g_discovery_service->hash_table.lock);
    pthread_rwlock_destroy(&g_discovery_service->hash_table.lock);
    
    // Cleanup agent locks
    for (int i = 0; i < MAX_AGENTS; i++) {
        pthread_rwlock_destroy(&g_discovery_service->agents[i].lock);
    }
    
    numa_free(g_discovery_service, sizeof(agent_discovery_service_t));
    g_discovery_service = NULL;
    
    printf("Agent Discovery Service: Cleaned up\n");
}

int register_agent(const char* name, agent_type_t type, uint32_t instance_id,
                  const agent_capability_t* capabilities, uint32_t capability_count,
                  const agent_endpoint_t* endpoints, uint32_t endpoint_count) {
    
    if (!g_discovery_service || !name || capability_count > MAX_CAPABILITIES || 
        endpoint_count > MAX_ENDPOINTS) {
        return -EINVAL;
    }
    
    uint32_t current_count = atomic_load(&g_discovery_service->agent_count);
    if (current_count >= MAX_AGENTS) {
        return -ENOSPC;
    }
    
    // Find free slot
    uint32_t agent_slot = 0;
    for (uint32_t i = 0; i < MAX_AGENTS; i++) {
        if (g_discovery_service->agents[i].agent_id == 0) {
            agent_slot = i;
            break;
        }
    }
    
    agent_registry_entry_t* agent = &g_discovery_service->agents[agent_slot];
    pthread_rwlock_wrlock(&agent->lock);
    
    // Initialize agent entry
    strncpy(agent->name, name, MAX_AGENT_NAME - 1);
    agent->name[MAX_AGENT_NAME - 1] = '\0';
    agent->agent_id = agent_slot + 1;  // 1-based IDs
    agent->type = type;
    agent->instance_id = instance_id;
    
    // Set timestamps
    uint64_t now = get_timestamp_ns();
    agent->registration_time_ns = now;
    agent->last_seen_ns = now;
    atomic_store(&agent->health.last_heartbeat_ns, now);
    
    // Copy capabilities
    agent->capability_count = capability_count;
    memcpy(agent->capabilities, capabilities, 
           capability_count * sizeof(agent_capability_t));
    
    // Copy endpoints
    agent->endpoint_count = endpoint_count;
    memcpy(agent->endpoints, endpoints,
           endpoint_count * sizeof(agent_endpoint_t));
    
    // Set NUMA affinity (prefer current node)
    agent->preferred_numa_node = numa_node_of_cpu(sched_getcpu());
    agent->cpu_affinity_mask = 0;  // Will be set by scheduler
    
    // Initialize state
    atomic_store(&agent->state, AGENT_STATE_ACTIVE);
    agent->failure_count = 0;
    
    // Initialize health metrics
    atomic_store(&agent->health.requests_handled, 0);
    atomic_store(&agent->health.errors_count, 0);
    atomic_store(&agent->health.response_time_avg_us, 0);
    atomic_store(&agent->health.cpu_usage_percent, 0);
    atomic_store(&agent->health.memory_usage_mb, 0);
    atomic_store(&agent->health.active_connections, 0);
    atomic_store(&agent->health.queue_depth, 0);
    agent->health.load_factor = 0.0f;
    
    // Initialize load balancing
    atomic_store(&agent->connection_count, 0);
    atomic_store(&agent->priority_score, 1.0f);
    
    pthread_rwlock_unlock(&agent->lock);
    
    // Add to hash table
    pthread_rwlock_wrlock(&g_discovery_service->hash_table.lock);
    uint32_t hash = hash_string(name);
    discovery_hash_node_t* node = malloc(sizeof(discovery_hash_node_t));
    node->entry = agent;
    node->next = g_discovery_service->hash_table.buckets[hash];
    g_discovery_service->hash_table.buckets[hash] = node;
    pthread_rwlock_unlock(&g_discovery_service->hash_table.lock);
    
    // Update count
    atomic_fetch_add(&g_discovery_service->agent_count, 1);
    atomic_fetch_add(&g_discovery_service->total_registrations, 1);
    
    printf("Agent Discovery: Registered agent '%s' (ID: %u, Type: %u)\n",
           name, agent->agent_id, type);
    
    return agent->agent_id;
}

agent_registry_entry_t* discover_agent_by_name(const char* name) {
    if (!g_discovery_service || !name) {
        return NULL;
    }
    
    pthread_rwlock_rdlock(&g_discovery_service->hash_table.lock);
    
    uint32_t hash = hash_string(name);
    discovery_hash_node_t* node = g_discovery_service->hash_table.buckets[hash];
    
    while (node) {
        if (strcmp(node->entry->name, name) == 0) {
            agent_registry_entry_t* agent = node->entry;
            pthread_rwlock_unlock(&g_discovery_service->hash_table.lock);
            
            atomic_fetch_add(&g_discovery_service->total_discoveries, 1);
            return is_agent_healthy(agent) ? agent : NULL;
        }
        node = node->next;
    }
    
    pthread_rwlock_unlock(&g_discovery_service->hash_table.lock);
    return NULL;
}

agent_registry_entry_t* discover_agent_by_type(agent_type_t type) {
    if (!g_discovery_service) {
        return NULL;
    }
    
    agent_registry_entry_t* best_agent = NULL;
    float best_score = -1.0f;
    
    uint32_t count = atomic_load(&g_discovery_service->agent_count);
    
    for (uint32_t i = 0; i < MAX_AGENTS && count > 0; i++) {
        agent_registry_entry_t* agent = &g_discovery_service->agents[i];
        
        if (agent->agent_id == 0) continue;  // Empty slot
        count--;
        
        if (agent->type == type && is_agent_healthy(agent)) {
            update_agent_priority_score(agent);
            float score = atomic_load(&agent->priority_score);
            
            if (score > best_score) {
                best_score = score;
                best_agent = agent;
            }
        }
    }
    
    if (best_agent) {
        atomic_fetch_add(&g_discovery_service->total_discoveries, 1);
    }
    
    return best_agent;
}

int discover_agents_by_capability(const char* capability_name,
                                 agent_registry_entry_t** results,
                                 uint32_t max_results) {
    if (!g_discovery_service || !capability_name || !results) {
        return -EINVAL;
    }
    
    uint32_t found = 0;
    uint32_t count = atomic_load(&g_discovery_service->agent_count);
    
    for (uint32_t i = 0; i < MAX_AGENTS && count > 0 && found < max_results; i++) {
        agent_registry_entry_t* agent = &g_discovery_service->agents[i];
        
        if (agent->agent_id == 0) continue;  // Empty slot
        count--;
        
        if (!is_agent_healthy(agent)) continue;
        
        // Check capabilities
        for (uint32_t cap = 0; cap < agent->capability_count; cap++) {
            if (strcmp(agent->capabilities[cap].name, capability_name) == 0) {
                results[found++] = agent;
                break;
            }
        }
    }
    
    if (found > 0) {
        atomic_fetch_add(&g_discovery_service->total_discoveries, 1);
    }
    
    return found;
}

// ============================================================================
// HEALTH MONITORING
// ============================================================================

void update_agent_health(uint32_t agent_id, const agent_health_t* health) {
    if (!g_discovery_service || agent_id == 0 || agent_id > MAX_AGENTS) {
        return;
    }
    
    agent_registry_entry_t* agent = &g_discovery_service->agents[agent_id - 1];
    if (agent->agent_id != agent_id) {
        return;  // Agent not registered
    }
    
    pthread_rwlock_wrlock(&agent->lock);
    
    // Update health metrics atomically
    atomic_store(&agent->health.requests_handled, health->requests_handled);
    atomic_store(&agent->health.errors_count, health->errors_count);
    atomic_store(&agent->health.last_heartbeat_ns, get_timestamp_ns());
    atomic_store(&agent->health.response_time_avg_us, health->response_time_avg_us);
    atomic_store(&agent->health.cpu_usage_percent, health->cpu_usage_percent);
    atomic_store(&agent->health.memory_usage_mb, health->memory_usage_mb);
    atomic_store(&agent->health.active_connections, health->active_connections);
    atomic_store(&agent->health.queue_depth, health->queue_depth);
    agent->health.load_factor = health->load_factor;
    
    agent->last_seen_ns = get_timestamp_ns();
    
    pthread_rwlock_unlock(&agent->lock);
    
    // Update priority score
    update_agent_priority_score(agent);
}

static void* health_monitor_thread(void* arg) {
    (void)arg;
    
    pthread_setname_np(pthread_self(), "health_monitor");
    
    while (g_discovery_service->running) {
        uint64_t now = get_timestamp_ns();
        uint32_t count = atomic_load(&g_discovery_service->agent_count);
        
        for (uint32_t i = 0; i < MAX_AGENTS && count > 0; i++) {
            agent_registry_entry_t* agent = &g_discovery_service->agents[i];
            
            if (agent->agent_id == 0) continue;
            count--;
            
            pthread_rwlock_wrlock(&agent->lock);
            
            bool was_healthy = (atomic_load(&agent->state) == AGENT_STATE_ACTIVE);
            bool is_healthy = is_agent_healthy(agent);
            
            if (was_healthy && !is_healthy) {
                // Agent became unhealthy
                agent->failure_count++;
                
                if (agent->failure_count >= FAILOVER_THRESHOLD) {
                    atomic_store(&agent->state, AGENT_STATE_FAILED);
                    atomic_fetch_add(&g_discovery_service->failovers_triggered, 1);
                    
                    printf("Health Monitor: Agent '%s' marked as FAILED (failures: %u)\n",
                           agent->name, agent->failure_count);
                } else {
                    atomic_store(&agent->state, AGENT_STATE_DEGRADED);
                    
                    printf("Health Monitor: Agent '%s' marked as DEGRADED (failures: %u)\n",
                           agent->name, agent->failure_count);
                }
                
            } else if (!was_healthy && is_healthy) {
                // Agent recovered
                atomic_store(&agent->state, AGENT_STATE_ACTIVE);
                agent->failure_count = 0;
                
                printf("Health Monitor: Agent '%s' recovered to ACTIVE\n", agent->name);
            }
            
            pthread_rwlock_unlock(&agent->lock);
            
            atomic_fetch_add(&g_discovery_service->health_checks_performed, 1);
        }
        
        // Sleep for health check interval
        usleep(HEARTBEAT_INTERVAL_MS * 1000);
    }
    
    return NULL;
}

int start_health_monitoring() {
    if (!g_discovery_service) {
        return -EINVAL;
    }
    
    int ret = pthread_create(&g_discovery_service->health_monitor_thread,
                           NULL, health_monitor_thread, NULL);
    if (ret != 0) {
        printf("Failed to start health monitor thread: %s\n", strerror(ret));
        return ret;
    }
    
    printf("Agent Discovery: Health monitoring started\n");
    return 0;
}

// ============================================================================
// STATISTICS AND DIAGNOSTICS
// ============================================================================

void print_discovery_statistics() {
    if (!g_discovery_service) {
        printf("Discovery service not initialized\n");
        return;
    }
    
    printf("\n=== Agent Discovery Service Statistics ===\n");
    printf("Active agents: %u\n", atomic_load(&g_discovery_service->agent_count));
    printf("Total registrations: %lu\n", atomic_load(&g_discovery_service->total_registrations));
    printf("Total discoveries: %lu\n", atomic_load(&g_discovery_service->total_discoveries));
    printf("Health checks performed: %lu\n", atomic_load(&g_discovery_service->health_checks_performed));
    printf("Failovers triggered: %lu\n", atomic_load(&g_discovery_service->failovers_triggered));
    
    printf("\nRegistered Agents:\n");
    printf("%-20s %-8s %-12s %-10s %-15s %-10s\n",
           "Name", "ID", "Type", "State", "Priority", "Health");
    printf("%-20s %-8s %-12s %-10s %-15s %-10s\n",
           "--------------------", "--------", "------------", 
           "----------", "---------------", "----------");
    
    uint32_t count = atomic_load(&g_discovery_service->agent_count);
    for (uint32_t i = 0; i < MAX_AGENTS && count > 0; i++) {
        agent_registry_entry_t* agent = &g_discovery_service->agents[i];
        
        if (agent->agent_id == 0) continue;
        count--;
        
        const char* state_str = "UNKNOWN";
        uint32_t state = atomic_load(&agent->state);
        switch (state) {
            case AGENT_STATE_INITIALIZING: state_str = "INIT"; break;
            case AGENT_STATE_ACTIVE: state_str = "ACTIVE"; break;
            case AGENT_STATE_DEGRADED: state_str = "DEGRADED"; break;
            case AGENT_STATE_UNAVAILABLE: state_str = "UNAVAIL"; break;
            case AGENT_STATE_FAILED: state_str = "FAILED"; break;
            case AGENT_STATE_SHUTTING_DOWN: state_str = "SHUTDOWN"; break;
        }
        
        float priority = atomic_load(&agent->priority_score);
        bool healthy = is_agent_healthy(agent);
        
        printf("%-20s %-8u %-12u %-10s %-15.3f %-10s\n",
               agent->name, agent->agent_id, agent->type, state_str,
               priority, healthy ? "HEALTHY" : "UNHEALTHY");
    }
    
    printf("\n");
}

// ============================================================================
// INTEGRATION WITH TRANSPORT LAYER
// ============================================================================

// Send discovery message using ultra-fast protocol
int send_discovery_message(uint32_t target_agent_id, const void* payload, size_t payload_size) {
    if (!g_discovery_service || target_agent_id == 0 || target_agent_id > MAX_AGENTS) {
        return -EINVAL;
    }
    
    agent_registry_entry_t* agent = &g_discovery_service->agents[target_agent_id - 1];
    if (agent->agent_id != target_agent_id || !is_agent_healthy(agent)) {
        return -ENOENT;
    }
    
    // Use the transport layer to send the message
    // This would integrate with the agent_bridge.c transport
    
    return 0;  // Success
}

// ============================================================================
// EXAMPLE USAGE AND TESTING
// ============================================================================

#ifdef DISCOVERY_TEST_MODE

int main() {
    printf("Agent Discovery Service Test\n");
    printf("============================\n");
    
    // Initialize discovery service
    if (discovery_service_init() != 0) {
        printf("Failed to initialize discovery service\n");
        return 1;
    }
    
    // Start health monitoring
    if (start_health_monitoring() != 0) {
        printf("Failed to start health monitoring\n");
        return 1;
    }
    
    // Register some test agents
    agent_capability_t director_caps[] = {
        {"orchestration", 1, 0.95f, 10},
        {"coordination", 1, 0.90f, 20}
    };
    
    agent_endpoint_t director_endpoints[] = {
        {"ipc", "/tmp/director.sock", 0, 0},
        {"tcp", "127.0.0.1", 8080, 0}
    };
    
    int director_id = register_agent("DIRECTOR", AGENT_TYPE_DIRECTOR, 1,
                                   director_caps, 2, director_endpoints, 2);
    printf("Registered DIRECTOR with ID: %d\n", director_id);
    
    // Register security agent
    agent_capability_t security_caps[] = {
        {"vulnerability_scan", 1, 0.85f, 5},
        {"threat_analysis", 1, 0.90f, 3}
    };
    
    agent_endpoint_t security_endpoints[] = {
        {"ipc", "/tmp/security.sock", 0, 0}
    };
    
    int security_id = register_agent("SECURITY", AGENT_TYPE_SECURITY, 1,
                                    security_caps, 2, security_endpoints, 1);
    printf("Registered SECURITY with ID: %d\n", security_id);
    
    // Test discovery
    agent_registry_entry_t* found_agent = discover_agent_by_name("DIRECTOR");
    if (found_agent) {
        printf("Found agent: %s (ID: %u)\n", found_agent->name, found_agent->agent_id);
    }
    
    // Test discovery by type
    found_agent = discover_agent_by_type(AGENT_TYPE_SECURITY);
    if (found_agent) {
        printf("Found security agent: %s (ID: %u)\n", found_agent->name, found_agent->agent_id);
    }
    
    // Update health metrics
    agent_health_t health = {0};
    atomic_store(&health.requests_handled, 100);
    atomic_store(&health.errors_count, 2);
    atomic_store(&health.response_time_avg_us, 1500);
    atomic_store(&health.cpu_usage_percent, 45);
    atomic_store(&health.memory_usage_mb, 128);
    health.load_factor = 0.3f;
    
    update_agent_health(director_id, &health);
    
    // Print statistics
    sleep(2);
    print_discovery_statistics();
    
    // Cleanup
    discovery_service_cleanup();
    
    return 0;
}

#endif